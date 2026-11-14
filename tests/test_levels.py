import unittest

from kidsguard.levels import (
    AGE_BAND_FLOOR,
    AGE_BANDS,
    CATEGORY_GROUP_LABEL,
    CategoryGroup,
    ProtectionLevel,
    band_floor,
    describe_level,
    normalize_band,
)


class ProtectionLevelTests(unittest.TestCase):
    def test_levels_are_ordered_strictest_first(self):
        ranks = [level.rank for level in ProtectionLevel]
        self.assertEqual(ranks, sorted(ranks))
        self.assertEqual(ProtectionLevel.VERY_HIGH.rank, 0)
        self.assertEqual(ProtectionLevel.LOW.rank, 3)

    def test_ceilings_rise_as_protection_loosens(self):
        ceilings = [level.ceiling for level in ProtectionLevel]
        self.assertEqual(ceilings, [1, 2, 3, 4])

    def test_parse_accepts_screen_labels(self):
        self.assertIs(ProtectionLevel.parse("Very High"), ProtectionLevel.VERY_HIGH)
        self.assertIs(ProtectionLevel.parse("very-high"), ProtectionLevel.VERY_HIGH)
        self.assertIs(ProtectionLevel.parse("MEDIUM"), ProtectionLevel.MEDIUM)

    def test_parse_rejects_nonsense(self):
        with self.assertRaises(ValueError):
            ProtectionLevel.parse("maximum")

    def test_stricter_picks_the_safer_level(self):
        self.assertIs(
            ProtectionLevel.stricter(ProtectionLevel.LOW, ProtectionLevel.HIGH),
            ProtectionLevel.HIGH,
        )
        self.assertIs(
            ProtectionLevel.stricter(ProtectionLevel.VERY_HIGH, ProtectionLevel.MEDIUM),
            ProtectionLevel.VERY_HIGH,
        )

    def test_descriptions_are_per_group(self):
        harassment = describe_level(ProtectionLevel.HIGH, CategoryGroup.HARASSMENT_HATE)
        violence = describe_level(ProtectionLevel.HIGH, CategoryGroup.VIOLENCE_ADULT)
        self.assertIn("insults", harassment)
        self.assertIn("graphic violence", violence)
        self.assertNotEqual(harassment, violence)
        for group in CategoryGroup:
            for level in ProtectionLevel:
                self.assertTrue(describe_level(level, group).strip())


class AgeBandTests(unittest.TestCase):
    def test_bands_are_the_standards_three(self):
        self.assertEqual(AGE_BANDS, ("8-11", "12-15", "16-18"))

    def test_normalize_accepts_en_dash_and_labels(self):
        self.assertEqual(normalize_band("8\u201311"), "8-11")
        self.assertEqual(normalize_band("Ages 12-15"), "12-15")

    def test_normalize_rejects_unknown_band(self):
        with self.assertRaises(ValueError):
            normalize_band("5-7")

    def test_floor_tightens_for_younger_children(self):
        self.assertIs(band_floor("8-11"), ProtectionLevel.VERY_HIGH)
        self.assertIs(band_floor("12-15"), ProtectionLevel.MEDIUM)
        self.assertIs(band_floor("16-18"), ProtectionLevel.LOW)

    def test_every_band_has_a_floor_and_a_label(self):
        self.assertEqual(set(AGE_BAND_FLOOR), set(AGE_BANDS))
        self.assertEqual(len(CATEGORY_GROUP_LABEL), len(list(CategoryGroup)))


if __name__ == "__main__":
    unittest.main()
