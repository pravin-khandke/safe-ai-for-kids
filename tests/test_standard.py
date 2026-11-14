import unittest

from kidsguard.levels import AGE_BANDS
from kidsguard.moderation import FLOOR_PRIORITY
from kidsguard.standard import Standard, StandardFormatError


class StandardParsingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.standard = Standard.load()

    def test_version_comes_from_the_footer(self):
        self.assertEqual(self.standard.version, "v1.2 reviewed 2026-08")

    def test_universal_strip_is_parsed(self):
        self.assertGreaterEqual(len(self.standard.universal_bullets), 10)
        self.assertTrue(
            any("Guardrails are not walls" in bullet for bullet in self.standard.universal_bullets)
        )

    def test_every_floor_category_has_exactly_one_rule(self):
        for category in FLOOR_PRIORITY:
            rule = self.standard.universal_rule(category)
            self.assertTrue(rule.strip(), category)
            self.assertNotIn("**", rule, "markdown bold should be stripped")

    def test_unknown_category_is_refused(self):
        with self.assertRaises(KeyError):
            self.standard.universal_rule("not_a_category")

    def test_refusal_explanation_is_verbatim_per_band(self):
        explanations = {band: self.standard.refuse_explanation(band) for band in AGE_BANDS}
        self.assertIn("address", explanations["8-11"])
        self.assertIn("fake nude images", explanations["12-15"])
        self.assertIn("can leak", explanations["16-18"])
        self.assertEqual(len(set(explanations.values())), 3)

    def test_learning_explanation_is_verbatim_per_band(self):
        for band, needle in (
            ("8-11", "won't learn"),
            ("12-15", "practice"),
            ("16-18", "academic discipline"),
        ):
            self.assertIn(needle, self.standard.learning_explanation(band))

    def test_self_harm_rule_requires_crisis_routing(self):
        rule = self.standard.universal_rule("self_harm").lower()
        self.assertIn("crisis line", rule)
        self.assertIn("trusted adult", rule)


class StandardStructureGuardTests(unittest.TestCase):
    """The parser must fail loudly when the document structure moves."""

    def setUp(self):
        self.text = Standard.default_path().read_text(encoding="utf-8")

    def test_missing_age_band_column_fails(self):
        broken = self.text.replace("**Ages 16–18**", "**Older teens**")
        with self.assertRaises(StandardFormatError):
            Standard.from_text(broken)

    def test_missing_refusal_quote_fails(self):
        broken = self.text.replace("**When it refuses", "When it refuses")
        with self.assertRaises(StandardFormatError):
            Standard.from_text(broken)

    def test_missing_grid_row_fails(self):
        broken = self.text.replace("| **What the adult checks**", "| Adult checks")
        with self.assertRaises(StandardFormatError):
            Standard.from_text(broken)

    def test_universal_section_missing_fails(self):
        broken = self.text.replace("## Always, at every age", "## Notes")
        with self.assertRaises(StandardFormatError):
            Standard.from_text(broken)

    def test_shipped_document_parses(self):
        standard = Standard.from_text(self.text)
        self.assertEqual(standard.version, "v1.2 reviewed 2026-08")


if __name__ == "__main__":
    unittest.main()
