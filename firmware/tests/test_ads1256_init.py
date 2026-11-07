"""Check ADS1256 register verification without physical GPIO or SPI."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


class ADS1256InitTests(unittest.TestCase):
    def setUp(self):
        class Pin:
            IN, OUT = 0, 1

            def __init__(self, *args, **kwargs):
                pass

            def value(self, *args):
                return 0

        spec = importlib.util.spec_from_file_location(
            "tested_ads1256", Path(__file__).resolve().parents[1] / "ads1256.py")
        module = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"machine": types.SimpleNamespace(Pin=Pin)}):
            spec.loader.exec_module(module)
        self.driver = module.ADS1256
        self.module = module

    def initialize(self, status=0x30, mismatch=None, buffer_enabled=False):
        registers = {0: status, 1: 0x08, 2: 0x20, 3: 0x82}
        if mismatch is not None:
            registers[mismatch] ^= 0x02
        commands = []
        fake_time = types.SimpleNamespace(sleep_ms=lambda ms: None)
        with patch.object(self.module, "time", fake_time), \
                patch.object(self.driver, "_wait_ready"), \
                patch.object(self.driver, "_command", side_effect=commands.append), \
                patch.object(self.driver, "_write_reg"), \
                patch.object(self.driver, "_read_reg", side_effect=lambda reg: registers[reg]):
            self.driver(buffer_enabled=buffer_enabled)
        return commands

    def test_status_drdy_bit_may_be_high_or_low(self):
        for status in (0x30, 0x31):
            with self.subTest(status=status):
                self.assertIn(0xF0, self.initialize(status=status))

    def test_buffer_enabled_requires_bufen_and_calibrates(self):
        self.assertIn(0xF0, self.initialize(status=0x32, buffer_enabled=True))
        with self.assertRaises(OSError):
            self.initialize(status=0x30, buffer_enabled=True)

    def test_signed_raw_limits_and_voltage_conversion(self):
        adc = self.driver.__new__(self.driver)
        adc.cs = types.SimpleNamespace(value=lambda value: None)
        adc.vref = 2.503
        for bits, expected in ((0, 0), (0x7FFFFF, 8388607),
                               (0x800000, -8388608), (0xFFFFFF, -1)):
            with self.subTest(bits=bits), patch.object(self.module, "time", types.SimpleNamespace(sleep_us=lambda us: None)), \
                    patch.object(adc, "_wait_ready"), patch.object(adc, "_write_reg"), \
                    patch.object(adc, "_command"), patch.object(adc, "_write_byte"), \
                    patch.object(adc, "_read_byte", side_effect=[bits >> 16, (bits >> 8) & 255, bits & 255]):
                self.assertEqual(adc.read_raw_channel(7), expected)
        with patch.object(adc, "read_raw_channel", return_value=8388607):
            self.assertEqual(adc.read_channel(0), 5.006)

    def test_wrong_writable_bits_are_rejected_with_register_details(self):
        for register in range(4):
            with self.subTest(register=register):
                with self.assertRaisesRegex(OSError, "reg=0x{:02X} read=0x".format(register)):
                    self.initialize(mismatch=register)


if __name__ == "__main__":
    unittest.main()
