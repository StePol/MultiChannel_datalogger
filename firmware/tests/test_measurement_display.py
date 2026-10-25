"""Check measurement rows without initializing Pico peripherals."""
import ast
import types
import unittest
from pathlib import Path


class MeasurementDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source = (Path(__file__).resolve().parents[1] / "main.py").read_text()
        # Execute only the input-mode display branch, never main.py startup.
        tree = ast.parse(source)
        branch = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.If)
                      and isinstance(node.test, ast.Name)
                      and node.test.id == "ADS1256_ENABLED"
                      and any(isinstance(child, ast.Constant)
                              and child.value == "ADS meranie..."
                              for child in ast.walk(node)))
        cls.display_code = compile(ast.Module(body=[branch], type_ignores=[]),
                                   "main.py display branch", "exec")

    def draw(self, values, error=False, ticks=0, count=3):
        rows = []
        context = {
            "oled": types.SimpleNamespace(text=lambda *args: rows.append(args)),
            "ADS1256_ENABLED": True, "ads_values": values, "ads_error": error,
            "roms": [None] * count,
            "time": types.SimpleNamespace(ticks_ms=lambda: ticks),
        }
        exec(self.display_code, context)
        return rows

    def test_each_channel_uses_only_row_four_and_keeps_sensor_count(self):
        values = [i / 10 for i in range(8)]
        for step in range(16):
            channel = step % 8
            with self.subTest(step=step):
                self.assertEqual(self.draw(values, ticks=step * 2000), [
                    ("AN{}: {:.6f}V".format(channel, values[channel]), 0, 34),
                    ("DS: 3", 0, 44),
                ])

    def test_waiting_and_error_keep_sensor_count_on_row_five(self):
        for error, label in ((False, "ADS meranie..."), (True, "ADS1256 CHYBA")):
            for count in (0, 3):
                with self.subTest(error=error, count=count):
                    self.assertEqual(self.draw(None, error=error, count=count), [
                        (label, 0, 34), ("DS: {}".format(count), 0, 44),
                    ])


if __name__ == "__main__":
    unittest.main()
