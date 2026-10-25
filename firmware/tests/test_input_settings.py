"""Persistence, defaults and interrupted writes for input-mode settings."""
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class InputSettingsTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location(
            "tested_input_settings", Path(__file__).resolve().parents[1] / "input_settings.py")
        self.settings = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.settings)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = str(Path(self.directory.name) / "input_mode.cfg")

    def test_missing_invalid_and_unfinished_settings_default_to_off(self):
        self.assertFalse(self.settings.load_input_mode(self.path))
        Path(self.path + ".tmp").write_text("On\n")
        self.assertFalse(self.settings.load_input_mode(self.path))
        for value in ("", "True", "On garbage", "Offx"):
            Path(self.path).write_text(value)
            self.assertFalse(self.settings.load_input_mode(self.path))

    def test_both_modes_survive_reload_and_unchanged_choice_does_not_write(self):
        with patch.object(self.settings.os, "sync") as sync:
            for enabled in (False, True, False):
                self.assertTrue(self.settings.save_input_mode(enabled, self.path))
                self.assertEqual(self.settings.load_input_mode(self.path), enabled)
                sync.reset_mock()
                with patch.object(self.settings.os, "rename") as rename:
                    self.assertFalse(self.settings.save_input_mode(enabled, self.path))
                    rename.assert_not_called()
                    sync.assert_not_called()

    def test_failed_write_or_rename_preserves_previous_setting(self):
        Path(self.path).write_text("On\n")
        for operation in ("sync", "rename"):
            with self.subTest(operation=operation):
                with patch.object(self.settings.os, operation, side_effect=OSError("failure")):
                    with self.assertRaises(OSError):
                        self.settings.save_input_mode(False, self.path)
                self.assertTrue(self.settings.load_input_mode(self.path))
        with patch("builtins.open", side_effect=OSError("read-only filesystem")):
            with self.assertRaises(OSError):
                self.settings.save_input_mode(False, self.path)
        self.assertTrue(self.settings.load_input_mode(self.path))


if __name__ == "__main__":
    unittest.main()
