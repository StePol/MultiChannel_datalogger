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

    def test_sample_counts_survive_reload_without_changing_input_mode(self):
        samples_path = str(Path(self.directory.name) / "ads_samples.cfg")
        with patch.object(self.settings.os, "sync") as sync:
            self.settings.save_input_mode(True, self.path)
            for count in (1, 2, 4, 8, 16, 32):
                with self.subTest(count=count):
                    self.assertTrue(self.settings.save_sample_count(count, samples_path))
                    self.assertEqual(self.settings.load_sample_count(samples_path), count)
                    self.assertTrue(self.settings.load_input_mode(self.path))
                    sync.reset_mock()
                    with patch.object(self.settings.os, "rename") as rename:
                        self.assertFalse(self.settings.save_sample_count(count, samples_path))
                        rename.assert_not_called()
                        sync.assert_not_called()
            self.settings.save_input_mode(False, self.path)
            self.assertEqual(self.settings.load_sample_count(samples_path), 32)

    def test_missing_invalid_or_unfinished_sample_count_defaults_to_one(self):
        self.assertEqual(self.settings.load_sample_count(self.path), 1)
        Path(self.path + ".tmp").write_text("32\n")
        self.assertEqual(self.settings.load_sample_count(self.path), 1)
        for value in ("", "0", "3", "64", "-1", "True", "8 garbage"):
            with self.subTest(value=value):
                Path(self.path).write_text(value)
                self.assertEqual(self.settings.load_sample_count(self.path), 1)

    def test_invalid_sample_count_is_rejected_without_overwriting(self):
        Path(self.path).write_text("8\n")
        for value in (0, 3, 64, -1, True, 2.0, "8"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.settings.save_sample_count(value, self.path)
                self.assertEqual(self.settings.load_sample_count(self.path), 8)

    def test_sample_save_failure_preserves_previous_count(self):
        Path(self.path).write_text("8\n")
        for operation in ("sync", "rename"):
            with self.subTest(operation=operation):
                with patch.object(self.settings.os, operation, side_effect=OSError("failure")):
                    with self.assertRaises(OSError):
                        self.settings.save_sample_count(32, self.path)
                self.assertEqual(self.settings.load_sample_count(self.path), 8)


if __name__ == "__main__":
    unittest.main()
