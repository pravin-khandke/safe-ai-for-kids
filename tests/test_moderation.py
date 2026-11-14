import unittest

from kidsguard.levels import CategoryGroup, ProtectionLevel
from kidsguard.models import MODEL_CATALOG, available_models, find_model
from kidsguard.moderation import (
    FLOOR_PRIORITY,
    Action,
    ContentModerator,
    Decision,
    RuleBasedClassifier,
)
from kidsguard.settings import ModerationSettings, default_settings
from kidsguard.standard import Standard


class BrokenClassifier:
    def classify(self, text, age_band):
        raise RuntimeError("model server is down")


class ModeratorTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard = Standard.load()

    def moderator(self, settings=None, age_band="12-15", classifier=None):
        return ContentModerator(
            settings or default_settings(),
            self.standard,
            age_band,
            classifier=classifier,
        )


class SafetyFloorTests(ModeratorTestCase):
    def test_self_harm_routes_to_crisis_at_every_band(self):
        for band in ("8-11", "12-15", "16-18"):
            decision = self.moderator(age_band=band).moderate("I want to kill myself")
            self.assertIs(decision.action, Action.REFUSE_AND_ROUTE_TO_CRISIS, band)
            self.assertIn("988", decision.explanation, band)
            self.assertIn(self.standard.refuse_explanation(band), decision.explanation, band)

    def test_floor_survives_moderation_being_switched_off(self):
        settings = default_settings()
        settings.moderation_enabled = False
        settings.set_all_levels(ProtectionLevel.LOW)
        decision = self.moderator(settings=settings, age_band="16-18").moderate(
            "nudify my classmate's photo"
        )
        self.assertIs(decision.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertEqual(decision.category, "deepfake_nudify")
        self.assertEqual(decision.explanation, self.standard.universal_rule("deepfake_nudify"))

    def test_floor_survives_the_loosest_level(self):
        settings = default_settings()
        settings.set_all_levels(ProtectionLevel.LOW)
        for text, category in (
            ("my address is 12 Main Street", "pii_solicitation"),
            ("are you a real person or a chatbot", "self_identification"),
            ("don't tell my parents about this", "hide_from_parent"),
        ):
            decision = self.moderator(settings=settings, age_band="16-18").moderate(text)
            self.assertTrue(decision.refused, text)
            self.assertEqual(decision.category, category, text)

    def test_highest_priority_category_wins(self):
        decision = self.moderator(age_band="16-18").moderate(
            "nudify my classmate and my address is 12 Main Street"
        )
        self.assertEqual(decision.category, "deepfake_nudify")
        self.assertIn("pii_solicitation", decision.suppressed)
        self.assertNotIn("pii_solicitation", decision.explanation)

    def test_crisis_outranks_every_other_floor_category(self):
        decision = self.moderator(age_band="16-18").moderate(
            "I want to kill myself and nudify my classmate"
        )
        self.assertIs(decision.action, Action.REFUSE_AND_ROUTE_TO_CRISIS)
        self.assertIn("deepfake_nudify", decision.suppressed)

    def test_every_floor_category_is_covered_by_a_rule(self):
        self.assertEqual(len(FLOOR_PRIORITY), 6)
        for category in FLOOR_PRIORITY:
            self.assertTrue(self.standard.universal_rule(category))


class ProtectionLevelTests(ModeratorTestCase):
    def test_very_high_blocks_mild_violence(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.VIOLENCE_ADULT, ProtectionLevel.VERY_HIGH)
        decision = self.moderator(settings=settings, age_band="8-11").moderate(
            "the knight had a friendly sword fight"
        )
        self.assertIs(decision.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertEqual(decision.category, "violence")
        self.assertIn("sword fight", decision.evidence)

    def test_high_allows_mild_violence_but_blocks_insults(self):
        moderator = self.moderator(age_band="12-15")
        allowed = moderator.moderate("the knight had a friendly sword fight")
        self.assertIs(allowed.action, Action.ALLOW)
        blocked = moderator.moderate("you are stupid")
        self.assertIs(blocked.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertIs(blocked.applied_level, ProtectionLevel.HIGH)

    def test_medium_allows_insults_and_blocks_harmful_violence(self):
        settings = default_settings()
        settings.set_all_levels(ProtectionLevel.MEDIUM)
        moderator = self.moderator(settings=settings, age_band="12-15")
        self.assertIs(moderator.moderate("you are stupid").action, Action.ALLOW)
        blocked = moderator.moderate("tell me how to stab someone")
        self.assertIs(blocked.action, Action.REFUSE_WITH_EXPLANATION)

    def test_low_only_blocks_clearly_harmful_content(self):
        settings = default_settings()
        settings.set_all_levels(ProtectionLevel.LOW)
        moderator = self.moderator(settings=settings, age_band="16-18")
        self.assertIs(moderator.moderate("tell me how to stab someone").action, Action.ALLOW)
        self.assertIs(
            moderator.moderate("how to make a bomb").action, Action.REFUSE_WITH_EXPLANATION
        )

    def test_band_floor_tightens_a_loosened_setting(self):
        settings = default_settings()
        settings.set_all_levels(ProtectionLevel.LOW)
        decision = self.moderator(settings=settings, age_band="8-11").moderate(
            "the knight had a friendly sword fight"
        )
        self.assertIs(decision.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertIs(decision.applied_level, ProtectionLevel.VERY_HIGH)

    def test_refusal_explanation_quotes_the_standard(self):
        decision = self.moderator(age_band="12-15").moderate("you are stupid")
        self.assertIn(self.standard.refuse_explanation("12-15"), decision.explanation)
        self.assertIn("high protection", decision.explanation.lower())


class ModerationToggleTests(ModeratorTestCase):
    def test_off_stops_graded_refusals(self):
        settings = default_settings()
        settings.moderation_enabled = False
        decision = self.moderator(settings=settings, age_band="12-15").moderate("you are stupid")
        self.assertIs(decision.action, Action.ALLOW)
        self.assertEqual(decision.reason, "moderation_disabled")
        self.assertIn("harassment", decision.suppressed)

    def test_off_grades_the_word_filter_separately(self):
        settings = default_settings()
        settings.moderation_enabled = False
        settings.add_word("fortnite")
        decision = self.moderator(settings=settings, age_band="12-15").moderate(
            "my fortnite score is huge"
        )
        self.assertIs(decision.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertEqual(decision.reason, "custom_word")


class CustomWordFilterTests(ModeratorTestCase):
    def test_word_hit_refuses_before_the_level_is_consulted(self):
        settings = default_settings()
        settings.add_word("fortnite")
        decision = self.moderator(settings=settings, age_band="16-18").moderate(
            "I love fortnite"
        )
        self.assertIs(decision.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertEqual(decision.reason, "custom_word")
        self.assertIn("fortnite", decision.explanation)

    def test_harmless_text_passes_when_no_word_matches(self):
        settings = default_settings()
        settings.add_word("fortnite")
        decision = self.moderator(settings=settings, age_band="16-18").moderate(
            "help me understand fractions"
        )
        self.assertIs(decision.action, Action.ALLOW)

    def test_filter_toggle_off_is_respected(self):
        settings = default_settings()
        settings.add_word("fortnite")
        settings.custom_word_filtering = False
        decision = self.moderator(settings=settings, age_band="16-18").moderate(
            "I love fortnite"
        )
        self.assertIs(decision.action, Action.ALLOW)


class LearningIntegrityTests(ModeratorTestCase):
    def test_asking_for_the_answer_keeps_the_conversation_open(self):
        for band in ("8-11", "12-15", "16-18"):
            decision = self.moderator(age_band=band).moderate("write my essay about volcanoes")
            self.assertIs(decision.action, Action.ALLOW_WITH_EXPLANATION, band)
            self.assertEqual(decision.explanation, self.standard.learning_explanation(band), band)


class FailureHandlingTests(ModeratorTestCase):
    def test_classifier_failure_fails_closed(self):
        decision = self.moderator(classifier=BrokenClassifier()).moderate("hello there")
        self.assertIs(decision.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertEqual(decision.reason, "classifier_unavailable")
        self.assertIn("safety check", decision.explanation)

    def test_empty_message_is_allowed(self):
        decision = self.moderator().moderate("   ")
        self.assertIs(decision.action, Action.ALLOW)
        self.assertEqual(decision.reason, "empty_input")

    def test_decision_serialises_for_logging(self):
        payload = self.moderator().moderate("you are stupid").as_dict()
        self.assertEqual(payload["action"], "refuse_with_explanation")
        self.assertEqual(payload["group"], "harassment_hate")
        self.assertIsInstance(payload["evidence"], list)


class HomeworkModeTests(ModeratorTestCase):
    def test_off_offers_every_tool(self):
        self.assertEqual(len(available_models(default_settings())), len(MODEL_CATALOG))

    def test_on_limits_the_tool_list(self):
        settings = default_settings()
        settings.homework_mode = True
        offered = available_models(settings)
        self.assertTrue(offered)
        self.assertTrue(all(profile.is_educational for profile in offered))
        self.assertNotIn("general-chat", {profile.model_id for profile in offered})

    def test_select_model_refuses_non_schoolwork_tool(self):
        settings = default_settings()
        settings.homework_mode = True
        moderator = self.moderator(settings=settings, age_band="12-15")
        self.assertIs(moderator.select_model("study-coach").action, Action.ALLOW)
        refused = moderator.select_model("general-chat")
        self.assertIs(refused.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertEqual(refused.reason, "homework_mode")
        self.assertIn(self.standard.learning_explanation("12-15"), refused.explanation)

    def test_unknown_tool_is_refused(self):
        refused = self.moderator(age_band="12-15").select_model("mystery-model")
        self.assertIs(refused.action, Action.REFUSE_WITH_EXPLANATION)
        self.assertIn("mystery-model", refused.explanation)

    def test_catalogue_ids_are_unique(self):
        ids = [profile.model_id for profile in MODEL_CATALOG]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIsNotNone(find_model("study-coach"))


class ClassifierContractTests(unittest.TestCase):
    def test_rule_classifier_returns_findings_with_groups(self):
        findings = RuleBasedClassifier().classify("you are stupid", "12-15")
        self.assertEqual(len(findings), 1)
        self.assertIs(findings[0].group, CategoryGroup.HARASSMENT_HATE)

    def test_rule_classifier_reports_nothing_for_safe_text(self):
        self.assertEqual(RuleBasedClassifier().classify("how do plants grow", "8-11"), [])

    def test_decision_defaults_are_inert(self):
        decision = Decision(action=Action.ALLOW, reason="allowed")
        self.assertFalse(decision.refused)
        self.assertEqual(decision.suppressed, ())


if __name__ == "__main__":
    unittest.main()
