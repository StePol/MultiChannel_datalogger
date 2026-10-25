"""Test menu navigation and reset dispatch without Pico peripherals."""
import ast
import types
import unittest
from pathlib import Path


class RestartMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((Path(__file__).resolve().parents[1] / "main.py").read_text())
        encoder = next(node for node in tree.body
                       if isinstance(node, ast.FunctionDef) and node.name == "encoder_handler")
        loop = next(node for node in tree.body if isinstance(node, ast.While))
        button = next(node for node in loop.body
                      if isinstance(node, ast.If)
                      and "last_btn" in ast.unparse(node.test))
        cls.encoder_code = compile(ast.Module(body=[encoder], type_ignores=[]),
                                   "encoder_handler", "exec")
        cls.button_code = compile(ast.Module(body=[button], type_ignores=[]),
                                  "button handler", "exec")

    def test_restart_is_first_and_navigation_is_disabled_during_rec(self):
        context = {
            "mode": "PAUZA", "interval": -2, "last_clk_state": 0,
            "pin_clk": types.SimpleNamespace(value=lambda: 1),
            "pin_dt": types.SimpleNamespace(value=lambda: 1),
        }
        exec(self.encoder_code, context)
        def turn(direction):
            context["last_clk_state"] = 0
            context["pin_dt"] = types.SimpleNamespace(value=lambda: 0 if direction == 1 else 1)
            context["encoder_handler"](None)
        turn(-1)
        self.assertEqual(context["interval"], -3)
        turn(-1)
        self.assertEqual(context["interval"], -3)
        for expected in (-2, -1, 0, 5):
            turn(1)
            self.assertEqual(context["interval"], expected)
        context.update(mode="REC", interval=60)
        turn(-1)
        self.assertEqual(context["interval"], 60)

    def test_press_restarts_only_in_pause_and_syncs_before_reset(self):
        for mode, expected in (("PAUZA", ["sync", "reset"]), ("REC", [])):
            with self.subTest(mode=mode):
                events = []
                context = {
                    "mode": mode, "interval": -3, "last_btn": 1, "curr_btn": 0,
                    "time": types.SimpleNamespace(sleep_ms=lambda ms: None),
                    "ds_sensor": types.SimpleNamespace(scan=lambda: []),
                    "LED_EXT": types.SimpleNamespace(value=lambda value: None),
                    "uos": types.SimpleNamespace(sync=lambda: events.append("sync")),
                    "machine": types.SimpleNamespace(reset=lambda: events.append("reset")),
                }
                exec(self.button_code, context)
                self.assertEqual(events, expected)
                self.assertEqual(context["mode"], "PAUZA")
                if mode == "PAUZA":
                    events.clear()
                    context["last_btn"] = 0
                    exec(self.button_code, context)
                    self.assertEqual(events, [])

    def test_confirmed_input_mode_is_saved_even_if_adc_initialization_fails(self):
        for enabled in (False, True):
            for fail_save in (False, True):
                with self.subTest(enabled=enabled, fail_save=fail_save):
                    events = []
                    context = {
                        "mode": "ADC_MENU", "ads_menu_choice": 0 if enabled else 1,
                        "last_btn": 1, "curr_btn": 0,
                        "time": types.SimpleNamespace(sleep_ms=lambda ms: None),
                        "LED_EXT": types.SimpleNamespace(value=lambda value: None),
                    }
                    def set_mode(value):
                        context["ADS1256_ENABLED"] = value
                        context["ads_error"] = "ADC unavailable" if value else ""
                        events.append(("apply", value))
                    def save(value):
                        events.append(("save", value))
                        if fail_save:
                            raise OSError("flash failure")
                    context.update(set_input_mode=set_mode, save_input_mode=save)
                    exec(self.button_code, context)
                    self.assertEqual(events, [("apply", enabled), ("save", enabled)])
                    self.assertEqual(context["settings_error"], fail_save)
                    self.assertEqual(context["mode"], "ADC_MENU" if fail_save else "PAUZA")

    def test_sample_confirmation_saves_and_discards_unfinished_batch(self):
        for fail_save in (False, True):
            with self.subTest(fail_save=fail_save):
                saved = []
                def save(count):
                    saved.append(count)
                    if fail_save:
                        raise OSError("flash failure")
                context = {
                    "mode": "ADC_SAMPLES", "last_btn": 1, "curr_btn": 0,
                    "ADS1256_SAMPLE_OPTIONS": (1, 2, 4, 8, 16, 32),
                    "ads_sample_choice": 3, "ads_samples": 1,
                    "ads_values": [1] * 8, "ads_collecting": True,
                    "ADCAverage": lambda count: ("new batch", count),
                    "ADS1256_SCAN_MS": 1000,
                    "time": types.SimpleNamespace(sleep_ms=lambda ms: None,
                                                  ticks_ms=lambda: 5000,
                                                  ticks_add=lambda a, b: a + b),
                    "LED_EXT": types.SimpleNamespace(value=lambda value: None),
                    "save_sample_count": save,
                }
                exec(self.button_code, context)
                self.assertEqual(saved, [8])
                self.assertEqual(context["ads_samples"], 8)
                self.assertEqual(context["ads_average"], ("new batch", 8))
                self.assertFalse(context["ads_collecting"])
                self.assertIsNone(context["ads_values"])
                self.assertEqual(context["ads_scan_timer"], 4000)
                self.assertEqual(context["settings_error"], fail_save)
                self.assertEqual(context["mode"], "ADC_MENU")


if __name__ == "__main__":
    unittest.main()
