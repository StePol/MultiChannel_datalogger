"""Divider loading, editor workflow, persistence and published voltages."""
import ast
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adc_divider import (DEFAULT_DIVIDER, DividerMenu, divider_factor,
                        divider_label, measurement_range, scale_values, voltage_label)
import input_settings
from logger_csv import make_record
from adc_average import ADCAverage


class DividerTests(unittest.TestCase):
    def test_loaded_divider_and_ranges_for_both_impedances(self):
        config = (True, 10000, 90000)
        # 10k || 150k = 9375 ohm; 90k/9375 + 1 = 10.6.
        self.assertAlmostEqual(divider_factor(config, False), 10.6)
        self.assertAlmostEqual(divider_factor(config, True), 10.00225)
        self.assertAlmostEqual(measurement_range(config, False), 53.0)
        self.assertAlmostEqual(measurement_range(config, True), 30.00675)
        self.assertAlmostEqual(measurement_range(config, True, avdd=4.8), 28.0063)
        self.assertAlmostEqual(measurement_range(config, False, vref=2), 42.4)

    def test_no_divider_and_raw_preserve_unscaled_values(self):
        values = [-1.0, 0.0, 2.0, 3.0]
        for high in (False, True):
            self.assertEqual(divider_factor(DEFAULT_DIVIDER, high), 1)
            self.assertEqual(measurement_range(DEFAULT_DIVIDER, high), 3 if high else 5)
            self.assertEqual(divider_label(DEFAULT_DIVIDER, high), 'Del:No')
            self.assertIs(scale_values(values, False, DEFAULT_DIVIDER, high), values)
            self.assertIs(scale_values(values, True, (True, 1, 99999999), high), values)
            self.assertIsNone(scale_values(None, False, (True, 1, 1), high))

    def test_invalid_resistances_and_finite_extremes(self):
        for rgnd, rin in ((0, 1), (-1, 1), (1, -1), (100000000, 1),
                          (1, 100000000), (True, 1), (1, 1.5)):
            with self.assertRaises(ValueError):
                divider_factor((True, rgnd, rin), False)
        self.assertEqual(divider_factor((True, 1, 0), False), 1)
        factor = divider_factor((True, 1, 99999999), True)
        self.assertGreater(factor, 1)
        self.assertLess(factor, 2e8)

    def test_settings_reload_invalid_files_and_failed_save(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'divider.cfg')
            self.assertEqual(input_settings.load_divider(path), DEFAULT_DIVIDER)
            for value in ('', 'On,0,1', 'On,1,-1', 'On,1,2,3', 'On,True,1',
                          'bad,1,2', 'On,100000000,1', 'On,1'):
                Path(path).write_text(value)
                self.assertEqual(input_settings.load_divider(path), DEFAULT_DIVIDER)
            for enabled in (True, False):
                config = (enabled, 99999999, 99999998)
                with patch.object(input_settings.os, 'sync'):
                    self.assertTrue(input_settings.save_divider(config, path))
                    self.assertEqual(input_settings.load_divider(path), config)
                    with patch.object(input_settings.os, 'rename') as rename:
                        self.assertFalse(input_settings.save_divider(config, path))
                        rename.assert_not_called()
            original = input_settings.load_divider(path)
            for operation in ('sync', 'rename'):
                with patch.object(input_settings.os, operation, side_effect=OSError('failure')):
                    with self.assertRaises(OSError):
                        input_settings.save_divider((True, 10000, 90000), path)
                self.assertEqual(input_settings.load_divider(path), original)
            with self.assertRaises(ValueError):
                input_settings.save_divider((True, 0, 1), path)
            self.assertEqual(input_settings.load_divider(path), original)

    def test_resistor_editor_digits_and_apply_cancel(self):
        menu = DividerMenu(DEFAULT_DIVIDER)
        menu.turn(1)  # Rgnd
        menu.press()
        self.assertEqual(menu.stage, 'edit')
        for index, digit in enumerate('00002000'):
            old = (menu.value // (10 ** (7 - index))) % 10
            menu.turn(int(digit) - old)
            self.assertIsNone(menu.press())
        self.assertEqual(menu.rgnd, 2000)
        self.assertEqual(menu.stage, 'menu')
        self.assertEqual(menu.config, DEFAULT_DIVIDER)  # still a draft
        menu.choice = 4
        self.assertEqual(menu.press(), 'apply')
        self.assertEqual(menu.config, (True, 2000, 90000))
        menu = DividerMenu(menu.config)
        menu.choice = 5
        self.assertEqual(menu.press(), 'cancel')
        menu.choice = 0
        self.assertEqual(menu.press(), 'apply')
        self.assertEqual(menu.config, (False, 2000, 90000))

    def test_zero_rgnd_cannot_leave_editor_as_valid_value(self):
        menu = DividerMenu(DEFAULT_DIVIDER)
        menu.choice = 1
        menu.press()
        menu.value = 0
        menu.digit = 7
        self.assertIsNone(menu.press())
        self.assertTrue(menu.error)
        self.assertEqual(menu.rgnd, 10000)
        self.assertEqual(menu.stage, 'edit')
        menu.turn(1)
        menu.press()
        self.assertEqual(menu.rgnd, 1)
        self.assertEqual(menu.stage, 'menu')

    def test_all_menu_screens_fit_oled(self):
        rows = []
        oled = types.SimpleNamespace(text=lambda text, x, y: rows.append((text, x, y)),
                                     hline=lambda *args: None)
        menu = DividerMenu((True, 99999999, 99999999))
        for choice in range(6):
            for stage in ('menu', 'edit', 'info'):
                rows.clear()
                menu.choice, menu.stage = choice, stage
                menu.draw(oled, True)
                for text, x, y in rows:
                    self.assertLessEqual(len(text) * 8 + x, 128, text)
                    self.assertLessEqual(y + 8, 64)
        for config in ((True, 1, 99999999), (True, 10000, 90000), DEFAULT_DIVIDER):
            self.assertLessEqual(len('> ' + divider_label(config, False)), 16)
        for value in (1234.567890, 500000000, -500000000):
            self.assertLessEqual(len(voltage_label(7, value)), 16)

    def test_new_set_is_scaled_once_before_display_and_csv(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        publish = next(node for node in ast.walk(tree)
                       if isinstance(node, ast.If) and ast.unparse(node.test) == 'result is not None')
        code = compile(ast.Module(body=[publish], type_ignores=[]), 'publish ADC set', 'exec')
        for raw in (False, True):
            context = dict(result=[2.0] * 8, ads_raw=raw, ads_divider=(True, 10000, 90000),
                           ads_buffer=False, scale_values=scale_values,
                           time=types.SimpleNamespace(ticks_ms=lambda: 100))
            exec(code, context)
            expected = 2 if raw else 21.2
            self.assertAlmostEqual(context['ads_values'][0], expected)
            _, row = make_record('00:00:00', 20, 50, 4, [], [], True,
                                 context['ads_values'], ads_raw=raw)
            self.assertEqual(row.split(',')[3], '2' if raw else '21.200000')

    def test_apply_resets_batch_and_retries_same_setting_after_save_error(self):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        loop = next(node for node in tree.body if isinstance(node, ast.While))
        button = next(node for node in loop.body if isinstance(node, ast.If)
                      and 'last_btn' in ast.unparse(node.test))
        code = compile(ast.Module(body=[button], type_ignores=[]), 'button handler', 'exec')
        config = (True, 10000, 90000)
        for fail in (False, True):
            menu = DividerMenu(config)
            menu.choice = 4
            saves = []
            def save(value):
                saves.append(value)
                if fail:
                    raise OSError('flash failure')
            context = dict(mode='ADC_DIVIDER', divider_menu=menu, ads_divider=DEFAULT_DIVIDER,
                           last_btn=1, curr_btn=0, ads_samples=8, ads_raw=False, ads_buffer=False,
                           ads_values=[1] * 8, ads_collecting=True, ADCAverage=ADCAverage,
                           ADS1256_SCAN_MS=1000, ADS1256_AVDD=5.0, ADS1256_VREF=2.503,
                           time=types.SimpleNamespace(sleep_ms=lambda ms: None,
                                                     ticks_ms=lambda: 2000, ticks_add=lambda a, b: a+b),
                           LED_EXT=types.SimpleNamespace(value=lambda value: None),
                           save_divider=save, divider_label=divider_label,
                           divider_factor=divider_factor, measurement_range=measurement_range)
            exec(code, context)
            self.assertEqual(context['mode'], 'ADC_MENU')
            self.assertEqual(context['ads_divider'], config)
            self.assertEqual(saves, [config])
            self.assertIsNone(context['ads_values'])
            self.assertFalse(context['ads_collecting'])
            self.assertEqual(context['ads_average'].rounds, 0)
            self.assertEqual(context['settings_error'], fail)


class DividerNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tree = ast.parse((Path(__file__).resolve().parents[1] / 'main.py').read_text())
        encoder = next(node for node in tree.body
                       if isinstance(node, ast.FunctionDef) and node.name == 'encoder_handler')
        cls.code = compile(ast.Module(body=[encoder], type_ignores=[]), 'encoder', 'exec')

    def test_rec_cannot_edit_divider_and_menu_scroll_reaches_back(self):
        menu = DividerMenu(DEFAULT_DIVIDER)
        context = dict(mode='REC', interval=60, divider_menu=menu,
                       ads_menu_choice=5, last_clk_state=0,
                       pin_clk=types.SimpleNamespace(value=lambda: 1),
                       pin_dt=types.SimpleNamespace(value=lambda: 0))
        exec(self.code, context)
        context['encoder_handler'](None)
        self.assertEqual(menu.choice, 0)
        self.assertEqual(context['ads_menu_choice'], 5)
        context.update(mode='ADC_MENU', last_clk_state=0)
        context['encoder_handler'](None)
        self.assertEqual(context['ads_menu_choice'], 6)
        context.update(mode='ADC_DIVIDER', last_clk_state=0)
        context['encoder_handler'](None)
        self.assertEqual(menu.choice, 1)
