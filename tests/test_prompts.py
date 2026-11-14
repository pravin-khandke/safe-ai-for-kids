import re
import unittest

from kidsguard.levels import CategoryGroup, ProtectionLevel
from kidsguard.moderation import FLOOR_PRIORITY
from kidsguard.prompts import (
    PROMPT_AGE_BANDS,
    SUBJECTS,
    PromptFormatError,
    TutorPromptSource,
    normalize_subject,
    render_tutor_prompt,
)
from kidsguard.settings import default_settings
from kidsguard.standard import Standard

EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF]")


class PromptSourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = TutorPromptSource.load()

    def test_version_and_sections_are_parsed(self):
        self.assertEqual(self.source.version, "v1.0")
        for band in PROMPT_AGE_BANDS:
            self.assertTrue(self.source.section("band:%s" % band).strip())
        for subject in SUBJECTS:
            self.assertTrue(self.source.section("subject:%s" % subject).strip())
        self.assertIn("Welcome", self.source.section("teaching_sequence"))

    def test_missing_band_section_is_refused(self):
        text = TutorPromptSource.load().sections["identity"]
        broken = "## Identity\n%s\n" % text
        with self.assertRaises(PromptFormatError):
            TutorPromptSource.from_text(broken)

    def test_missing_subject_section_is_refused(self):
        document = (
            __import__("pathlib").Path(TutorPromptSource.load().source).read_text(encoding="utf-8")
        )
        broken = document.replace("## Subject: art", "## Subject: drawing")
        with self.assertRaises(PromptFormatError):
            TutorPromptSource.from_text(broken)

    def test_subject_normalisation(self):
        self.assertEqual(normalize_subject(None), "unsure")
        self.assertEqual(normalize_subject("Maths"), "math")
        self.assertEqual(normalize_subject(" CHESS "), "unsure")


class RenderedPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard = Standard.load()

    def render(self, band="12-15", subject=None, settings=None, source=None):
        return render_tutor_prompt(
            self.standard,
            settings or default_settings(),
            band,
            subject,
            source=source,
        )

    def test_every_standard_refusal_appears_verbatim(self):
        for band in PROMPT_AGE_BANDS:
            text = self.render(band=band)
            for category in FLOOR_PRIORITY:
                self.assertIn(self.standard.universal_rule(category), text, category)

    def test_crisis_contact_and_adult_line_are_present(self):
        text = self.render(band="8-11")
        self.assertIn("988", text)
        self.assertIn("trusted adult", text.lower())

    def test_band_language_comes_from_the_standard(self):
        for band in PROMPT_AGE_BANDS:
            text = self.render(band=band)
            self.assertIn(self.standard.learning_explanation(band), text, band)
            self.assertIn(self.standard.refuse_explanation(band), text, band)

    def test_identity_and_band_substitution(self):
        text = self.render(band="8-11")
        self.assertIn("You are an AI", text)
        self.assertIn("not a counselor", text)
        self.assertIn("aged 8-11", text)
        self.assertNotIn("{age_band}", text)

    def test_band_sections_differ(self):
        younger = self.render(band="8-11")
        older = self.render(band="12-15")
        self.assertIn("adult is nearby", younger)
        self.assertIn("not a therapist", older)
        self.assertNotEqual(younger, older)

    def test_subject_blocks_are_selected(self):
        self.assertIn("worked example", self.render(subject="math"))
        self.assertIn("fill in the blanks", self.render(subject="reading"))
        self.assertIn("cause and effect", self.render(subject="science"))
        self.assertIn("timeline", self.render(subject="history"))
        self.assertIn("doodle", self.render(subject="art"))
        self.assertIn("Offer four topics", self.render(subject="unsure"))
        self.assertIn("Offer four topics", self.render(subject="chess"))

    def test_turn_discipline_and_formatting_are_stated(self):
        text = self.render()
        self.assertIn("One step per message", text)
        self.assertIn("Wait for the child", text)
        self.assertIn("emojis per section", text)
        self.assertIn("No external links", text)

    def test_no_links_and_no_emoji_in_the_prompt_itself(self):
        for subject in SUBJECTS:
            text = self.render(subject=subject)
            self.assertNotIn("http", text.lower())
            self.assertIsNone(EMOJI.search(text), subject)

    def test_protection_level_in_force_is_named(self):
        younger = self.render(band="8-11")
        self.assertIn(ProtectionLevel.VERY_HIGH.label, younger)
        # A loosened setting is reported as the level actually in force, which the
        # 12-15 floor holds at Medium.
        settings = default_settings()
        settings.set_level(CategoryGroup.VIOLENCE_ADULT, ProtectionLevel.LOW)
        older = self.render(band="12-15", settings=settings)
        self.assertIn(ProtectionLevel.MEDIUM.label, older)
        self.assertNotIn(ProtectionLevel.LOW.label, older)
        # A tightened setting is reported as itself.
        settings.set_all_levels(ProtectionLevel.VERY_HIGH)
        strict = self.render(band="12-15", settings=settings)
        self.assertIn(ProtectionLevel.VERY_HIGH.label, strict)

    def test_settings_crisis_contact_flows_through(self):
        settings = default_settings()
        settings.crisis_contact = "Kids Helpline 1800 55 1800 (Australia)"
        self.assertIn("1800 55 1800", self.render(settings=settings))

    def test_prompt_carries_both_provenance_stamps(self):
        text = self.render()
        self.assertIn("v1.2 reviewed 2026-08", text)
        self.assertIn("v1.0", text)

    def test_prompt_stays_small_enough_to_use_as_a_system_prompt(self):
        for band in PROMPT_AGE_BANDS:
            for subject in SUBJECTS:
                text = self.render(band=band, subject=subject)
                self.assertLess(len(text), 8000, (band, subject))

    def test_older_band_needs_its_own_document(self):
        with self.assertRaises(ValueError) as caught:
            self.render(band="16-18")
        self.assertIn("16-18", str(caught.exception))

    def test_broken_document_fails_the_render(self):
        source = TutorPromptSource.load()
        broken = TutorPromptSource(
            sections={key: value for key, value in source.sections.items() if key != "band:12-15"},
            version=source.version,
            source=source.source,
        )
        with self.assertRaises(PromptFormatError):
            self.render(band="12-15", source=broken)


if __name__ == "__main__":
    unittest.main()
