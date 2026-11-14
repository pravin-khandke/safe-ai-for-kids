import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from kidsguard.cli import main


class CliTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.config = str(Path(self._tmp.name) / "kidsguard-settings.json")

    def run_cli(self, *argv):
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            code = main(["--config", self.config] + list(argv))
        return code, buffer.getvalue()

    def settings_json(self):
        return json.loads(Path(self.config).read_text(encoding="utf-8"))


class SettingsCommandsTests(CliTestCase):
    def test_show_prints_the_screen_and_writes_nothing(self):
        code, output = self.run_cli("show", "--child", "Om")
        self.assertEqual(code, 0)
        self.assertIn("Content Moderation", output)
        self.assertIn("Om's conversations", output)
        self.assertFalse(Path(self.config).exists())

    def test_set_level_all_writes_both_groups(self):
        code, output = self.run_cli("set-level", "all", "very-high")
        self.assertEqual(code, 0)
        self.assertIn("[saved]", output)
        self.assertEqual(
            self.settings_json()["levels"],
            {"harassment_hate": "very_high", "violence_adult": "very_high"},
        )

    def test_set_level_for_one_group_leaves_the_other(self):
        code, _ = self.run_cli("set-level", "harassment-hate", "low")
        self.assertEqual(code, 0)
        levels = self.settings_json()["levels"]
        self.assertEqual(levels["harassment_hate"], "low")
        self.assertEqual(levels["violence_adult"], "high")

    def test_bad_group_and_bad_level_exit_nonzero(self):
        self.assertEqual(self.run_cli("set-level", "gambling", "high")[0], 3)
        self.assertEqual(self.run_cli("set-level", "all", "extreme")[0], 3)

    def test_toggles_are_persisted(self):
        self.assertEqual(self.run_cli("toggle", "moderation", "off")[0], 0)
        self.assertEqual(self.run_cli("toggle", "homework", "on")[0], 0)
        payload = self.settings_json()
        self.assertFalse(payload["moderation_enabled"])
        self.assertTrue(payload["homework_mode"])
        self.assertEqual(self.run_cli("toggle", "nonsense", "on")[0], 3)

    def test_words_add_and_clear(self):
        self.assertEqual(self.run_cli("words", "add", "Fortnite")[0], 0)
        self.assertEqual(self.settings_json()["custom_words"], ["fortnite"])
        self.assertEqual(self.run_cli("words", "remove", "fortnite")[0], 0)
        self.assertEqual(self.settings_json()["custom_words"], [])
        self.run_cli("words", "add", "tiktok")
        code, output = self.run_cli("words", "clear")
        self.assertEqual(code, 0)
        self.assertIn("Cleared 1 filtered word", output)
        self.assertEqual(self.settings_json()["custom_words"], [])

    def test_reset_restores_defaults(self):
        self.run_cli("set-level", "all", "low")
        self.run_cli("words", "add", "fortnite")
        code, output = self.run_cli("reset")
        self.assertEqual(code, 0)
        self.assertIn("Reset every setting", output)
        payload = self.settings_json()
        self.assertEqual(payload["custom_words"], [])
        self.assertEqual(payload["levels"], {"harassment_hate": "high", "violence_adult": "high"})


class CheckAndModelsTests(CliTestCase):
    def test_refusal_exits_one(self):
        code, output = self.run_cli("check", "I want to kill myself", "--age", "12-15")
        self.assertEqual(code, 1)
        self.assertIn("refuse_and_route_to_crisis", output)
        self.assertIn("988", output)

    def test_allowed_message_exits_zero(self):
        code, output = self.run_cli("check", "how do plants make food", "--age", "12-15")
        self.assertEqual(code, 0)
        self.assertIn("allow", output)

    def test_check_honours_the_saved_level(self):
        self.run_cli("set-level", "all", "very-high")
        code, _ = self.run_cli("check", "the knight had a friendly sword fight", "--age", "16-18")
        self.assertEqual(code, 1)

    def test_check_honours_the_saved_word_list(self):
        self.run_cli("words", "add", "fortnite")
        code, output = self.run_cli("check", "my fortnite rank is gold", "--age", "16-18")
        self.assertEqual(code, 1)
        self.assertIn("custom_word", output)

    def test_models_lists_schoolwork_tools_in_homework_mode(self):
        self.run_cli("toggle", "homework", "on")
        code, output = self.run_cli("models", "--age", "12-15")
        self.assertEqual(code, 0)
        self.assertIn("Homework mode: on", output)
        self.assertIn("study-coach", output)
        self.assertNotIn("general-chat            General Chat", output)


if __name__ == "__main__":
    unittest.main()
