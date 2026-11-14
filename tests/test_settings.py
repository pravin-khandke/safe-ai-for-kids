import json
import tempfile
import unittest
from pathlib import Path

from kidsguard.levels import CategoryGroup, ProtectionLevel
from kidsguard.settings import (
    DEFAULT_LEVELS,
    MAX_CUSTOM_WORDS,
    SCHEMA_VERSION,
    ModerationSettings,
    SettingsError,
    default_settings,
    normalize_word,
)


class DefaultsAndValidationTests(unittest.TestCase):
    def test_defaults_match_the_screen(self):
        settings = default_settings()
        self.assertTrue(settings.moderation_enabled)
        self.assertTrue(settings.custom_word_filtering)
        self.assertFalse(settings.homework_mode)
        self.assertEqual(settings.custom_words, [])
        self.assertEqual(settings.levels, DEFAULT_LEVELS)
        self.assertIn("988", settings.crisis_contact)

    def test_validate_needs_a_crisis_contact(self):
        settings = ModerationSettings()
        settings.crisis_contact = "   "
        with self.assertRaises(SettingsError):
            settings.validate()

    def test_validate_needs_every_group(self):
        settings = ModerationSettings()
        settings.levels.pop(CategoryGroup.HARASSMENT_HATE)
        with self.assertRaises(SettingsError):
            settings.validate()

    def test_validate_dedupes_words(self):
        settings = ModerationSettings(custom_words=["Fortnite", "fortnite ", " TIKTOK "])
        self.assertEqual(settings.validate().custom_words, ["fortnite", "tiktok"])


class WordListTests(unittest.TestCase):
    def test_normalize_lowercases_and_trims(self):
        self.assertEqual(normalize_word("  ForTnite  "), "fortnite")
        self.assertEqual(normalize_word('"shut up"'), "shut up")

    def test_normalize_rejects_short_empty_and_long(self):
        for bad in ("", "a", "   ", "x" * 61):
            with self.assertRaises(SettingsError):
                normalize_word(bad)

    def test_add_word_is_idempotent(self):
        settings = default_settings()
        self.assertEqual(settings.add_word("TikTok"), "tiktok")
        self.assertEqual(settings.add_word("tiktok"), "tiktok")
        self.assertEqual(settings.custom_words, ["tiktok"])

    def test_add_word_enforces_limit(self):
        settings = default_settings()
        settings.custom_words = ["word%d" % index for index in range(MAX_CUSTOM_WORDS)]
        with self.assertRaises(SettingsError):
            settings.add_word("onemore")

    def test_remove_word_reports_whether_it_was_there(self):
        settings = default_settings()
        settings.add_word("fortnite")
        self.assertTrue(settings.remove_word("Fortnite"))
        self.assertFalse(settings.remove_word("fortnite"))

    def test_clear_all_empties_only_the_words(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.HARASSMENT_HATE, ProtectionLevel.VERY_HIGH)
        settings.add_word("fortnite")
        settings.homework_mode = True
        settings.clear_custom_words()
        self.assertEqual(settings.custom_words, [])
        self.assertEqual(
            settings.levels[CategoryGroup.HARASSMENT_HATE], ProtectionLevel.VERY_HIGH
        )
        self.assertTrue(settings.homework_mode)

    def test_reset_restores_every_field(self):
        settings = default_settings()
        settings.moderation_enabled = False
        settings.custom_word_filtering = False
        settings.homework_mode = True
        settings.crisis_contact = "some other line"
        settings.add_word("fortnite")
        settings.set_all_levels(ProtectionLevel.LOW)
        settings.reset_to_default()
        fresh = default_settings()
        self.assertEqual(settings.to_dict(), fresh.to_dict())


class WordMatchingTests(unittest.TestCase):
    def test_matches_whole_words_case_insensitively(self):
        settings = default_settings()
        settings.add_word("fortnite")
        self.assertEqual(settings.matches_custom_word("I love FORTNITE"), "fortnite")
        self.assertIsNone(settings.matches_custom_word("I love fortnight"))

    def test_does_not_match_inside_a_longer_word(self):
        settings = default_settings()
        settings.add_word("ass")
        self.assertIsNone(settings.matches_custom_word("our whole class was happy"))
        self.assertEqual(settings.matches_custom_word("you ass"), "ass")

    def test_matches_common_inflections(self):
        settings = default_settings()
        settings.add_word("kill")
        for text in ("he kills", "they are killing it", "she killed it"):
            self.assertEqual(settings.matches_custom_word(text), "kill", text)

    def test_disabled_toggle_stops_matching(self):
        settings = default_settings()
        settings.add_word("fortnite")
        settings.custom_word_filtering = False
        self.assertFalse(settings.word_filter_active)
        self.assertIsNone(settings.matches_custom_word("I love fortnite"))

    def test_empty_list_is_not_active(self):
        self.assertFalse(default_settings().word_filter_active)


class LevelClampingTests(unittest.TestCase):
    def test_younger_band_enforces_the_standard_floor(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.VIOLENCE_ADULT, ProtectionLevel.LOW)
        self.assertIs(
            settings.effective_level(CategoryGroup.VIOLENCE_ADULT, "8-11"),
            ProtectionLevel.VERY_HIGH,
        )
        note = settings.clamp_note(CategoryGroup.VIOLENCE_ADULT, "8-11")
        self.assertIsNotNone(note)
        self.assertIn("Very High", note)

    def test_teen_band_respects_the_setting(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.VIOLENCE_ADULT, ProtectionLevel.LOW)
        self.assertIs(
            settings.effective_level(CategoryGroup.VIOLENCE_ADULT, "16-18"),
            ProtectionLevel.LOW,
        )
        self.assertIsNone(settings.clamp_note(CategoryGroup.VIOLENCE_ADULT, "16-18"))

    def test_setting_stricter_than_floor_is_kept(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.HARASSMENT_HATE, ProtectionLevel.VERY_HIGH)
        self.assertIs(
            settings.effective_level(CategoryGroup.HARASSMENT_HATE, "16-18"),
            ProtectionLevel.VERY_HIGH,
        )

    def test_global_control_sets_every_group(self):
        settings = default_settings()
        settings.set_all_levels(ProtectionLevel.MEDIUM)
        self.assertIs(settings.global_level, ProtectionLevel.MEDIUM)
        settings.set_level(CategoryGroup.HARASSMENT_HATE, ProtectionLevel.LOW)
        self.assertIsNone(settings.global_level)


class SerialisationTests(unittest.TestCase):
    def test_round_trip_preserves_every_field(self):
        settings = default_settings()
        settings.set_level(CategoryGroup.HARASSMENT_HATE, ProtectionLevel.VERY_HIGH)
        settings.custom_word_filtering = False
        settings.homework_mode = True
        settings.add_word("fortnite")
        restored = ModerationSettings.from_json(settings.to_json())
        self.assertEqual(restored.to_dict(), settings.to_dict())

    def test_payload_uses_readable_string_keys(self):
        payload = default_settings().to_dict()
        self.assertEqual(payload["schema_version"], SCHEMA_VERSION)
        self.assertEqual(
            payload["levels"],
            {"harassment_hate": "high", "violence_adult": "high"},
        )

    def test_unknown_group_is_rejected(self):
        payload = default_settings().to_dict()
        payload["levels"]["gambling"] = "high"
        with self.assertRaises(SettingsError):
            ModerationSettings.from_dict(payload)

    def test_bad_level_is_rejected(self):
        payload = default_settings().to_dict()
        payload["levels"]["harassment_hate"] = "extreme"
        with self.assertRaises(SettingsError):
            ModerationSettings.from_dict(payload)

    def test_schema_version_mismatch_is_rejected(self):
        payload = default_settings().to_dict()
        payload["schema_version"] = 99
        with self.assertRaises(SettingsError):
            ModerationSettings.from_dict(payload)

    def test_bad_json_and_bad_bool_are_rejected(self):
        with self.assertRaises(SettingsError):
            ModerationSettings.from_json("{not json")
        payload = default_settings().to_dict()
        payload["homework_mode"] = "sometimes"
        with self.assertRaises(SettingsError):
            ModerationSettings.from_dict(payload)

    def test_save_and_load_missing_file_gives_defaults(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "kidsguard-settings.json"
            self.assertEqual(ModerationSettings.load(path).to_dict(), default_settings().to_dict())
            settings = default_settings()
            settings.add_word("fortnite")
            settings.save(path)
            self.assertTrue(path.exists())
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))["custom_words"], ["fortnite"]
            )
            self.assertEqual(
                ModerationSettings.load(path).custom_words, ["fortnite"]
            )


if __name__ == "__main__":
    unittest.main()
