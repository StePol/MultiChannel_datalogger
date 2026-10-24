"""PC checks of splash geometry, dynamic version and startup-only delay."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class LogoTests(unittest.TestCase):
    def setUp(self):
        self.frames = []
        def framebuffer(data, width, height, format):
            frame = (bytes(data), width, height, format)
            self.frames.append(frame)
            return frame
        fake = types.SimpleNamespace(FrameBuffer=framebuffer, MONO_HLSB=3)
        spec = importlib.util.spec_from_file_location(
            "tested_logo", Path(__file__).resolve().parents[1] / "logo.py")
        self.logo = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"framebuf": fake}):
            spec.loader.exec_module(self.logo)
        self.events = []
        events = self.events
        class Display:
            def fill(self, color): events.append(("fill", color))
            def blit(self, frame, x, y): events.append(("blit", x, y))
            def text(self, text, x, y, color): events.append(("text", text, x, y, color))
            def show(self): events.append(("show",))
        self.display = Display()

    def test_bitmap_is_fixed_and_versions_are_drawn_separately(self):
        original = bytes(self.logo._DATA)
        self.assertEqual(len(original), 128 * 64 // 8)
        for version in ("1.0.0", "1.2.3", "0.0.0-dev"):
            self.events.clear()
            self.logo.draw_logo(self.display, version)
            label = "v" + version
            self.assertIn(("text", label, 124 - len(label) * 8, 52, 1), self.events)
            self.assertEqual(self.frames[-1], (original, 128, 64, 3))
            self.assertEqual(bytes(self.logo._DATA), original)

    def test_long_version_stays_inside_reserved_strip(self):
        self.logo.draw_logo(self.display, "123456.123456.123456")
        event = next(e for e in self.events if e[0] == "text")
        _, label, x, y, color = event
        self.assertTrue(label.endswith("~"))
        self.assertGreaterEqual(x, 3)
        self.assertLessEqual(x + len(label) * 8, 125)
        self.assertGreaterEqual(y, 51)
        self.assertLessEqual(y + 8, 62)

    def test_startup_displays_then_waits_two_seconds_and_clears(self):
        fake_time = types.SimpleNamespace(
            sleep_ms=lambda duration: self.events.append(("sleep", duration)))
        with patch.dict(sys.modules, {"time": fake_time}):
            self.logo.show_startup(self.display, "1.0.0")
        self.assertEqual(self.events, [
            ("fill", 0), ("blit", 0, 0), ("text", "v1.0.0", 76, 52, 1),
            ("show",), ("sleep", 2000), ("fill", 0), ("show",)])


if __name__ == "__main__":
    unittest.main()
