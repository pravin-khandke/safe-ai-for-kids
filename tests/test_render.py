import unittest

from kidsguard.levels import CategoryGroup, ProtectionLevel
from kidsguard.moderation import Action, Decision
from kidsguard.render import NO_WORDS_TEXT, render_decision, render_settings
from kidsguard.settings import default_settings
from kidsguard.standard import Standard


class SettingsScreenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard = Standard.load()

    def render(self, settings=None, **kwargs):
        return render_settings(settings or default_settings(), self.standard, **kwargs)

    def test_screen_has_every_section_from_the_design(self):
        screen = self.render(child_name="Om")
        for heading in (
            "Content Moderation",
            "Built-in Safety Features",
            "Enable Content Moderation",
            "Safety & Protection",
            "Harassment & Hate",
            "Violence & Adult Content",
            "Additional Settings",
            "Custom Word Filters",
        ):
            self.assertIn(heading, screen)

    def test_heading_names_the_child(self):
        self.assertIn("Om's conversations", self.render(child_name="Om"))
        self.assertIn("your child's conversations", self.render())

    def test_toggles_reflect_the_settings(self):
        settings = default_settings()
        settings.moderation_enabled = False
        settings.homework_mode = True
        screen = self.render(settings)
        self.assertIn("[ ] Use AI to automatically filter inappropriate content", screen)
        self.assertIn("[x] Homework Mode", screen)

    def test_levels_are_ticked_per_section(self):
        screen = self.render()
        self.assertEqual(screen.count("[x] High Protection"), 3)

    def test_all_four_levels_and_descriptions_are_listed(self):
        screen = self.render()
        for label in ("Very High Protection", "High Protection", "Medium Protection", "Low Protection"):
            self.assertIn(label, screen)
        self.assertIn("including mild references", screen)
        self.assertIn("insults and hateful language", screen)

    def test_empty_word_list_shows_the_design_copy(self):
        self.assertIn(NO_WORDS_TEXT, self.render())

    def test_words_are_numbered(self):
        settings = default_settings()
        settings.add_word("fortnite")
        settings.add_word("tiktok")
        screen = self.render(settings)
        self.assertIn("   1. fortnite", screen)
        self.assertIn("   2. tiktok", screen)

    def test_clamped_level_is_explained_on_screen(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.VIOLENCE_ADULT, ProtectionLevel.LOW)
        screen = self.render(settings, age_band="8-11")
        self.assertIn("applied as Very High Protection for ages 8-11", screen)

    def test_save_status_is_reported(self):
        self.assertIn("[saved]", self.render(config_path="kidsguard-settings.json", saved=True))
        self.assertIn("nothing was written", self.render(config_path="x.json", saved=False))

    def test_standard_provenance_is_shown(self):
        self.assertIn("v1.2 reviewed 2026-08", self.render())


class DecisionRenderingTests(unittest.TestCase):
    def test_refusal_prints_reason_level_and_explanation(self):
        decision = Decision(
            action=Action.REFUSE_WITH_EXPLANATION,
            reason="level_refusal",
            explanation="line one\nline two",
            category="violence",
            evidence=("sword fight",),
            suppressed=("harassment",),
            applied_level=ProtectionLevel.VERY_HIGH,
        )
        text = render_decision(decision, label="child")
        self.assertIn("child: refuse_with_explanation", text)
        self.assertIn("level in force: Very High Protection", text)
        self.assertIn("matched: sword fight", text)
        self.assertIn("also seen (not shown to child): harassment", text)
        self.assertIn("  line one", text)
        self.assertIn("  line two", text)

    def test_allow_prints_without_explanation(self):
        text = render_decision(Decision(action=Action.ALLOW, reason="allowed"), label="child")
        self.assertIn("allow", text)
        self.assertNotIn("matched:", text)


if __name__ == "__main__":
    unittest.main()
