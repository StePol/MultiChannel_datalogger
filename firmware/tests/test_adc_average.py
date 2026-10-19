"""Run on the computer: python3 -m unittest discover -s firmware/tests"""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from adc_average import ADCAverage


class Source:
    def __init__(self):
        self.calls = 0

    def read_channel(self, channel):
        assert channel == self.calls % 8
        sweep = self.calls // 8
        self.calls += 1
        return channel + sweep


class AverageTests(unittest.TestCase):
    def test_means_only_publish_after_all_fresh_samples(self):
        for count in (1, 2, 4, 8, 16, 32):
            with self.subTest(count=count):
                avg, source = ADCAverage(count), Source()
                for _ in range(8 * count - 1):
                    self.assertIsNone(avg.step(source))
                self.assertEqual(avg.step(source),
                                 [ch + (count - 1) / 2 for ch in range(8)])
                self.assertEqual(source.calls, 8 * count)

    def test_new_batch_does_not_include_previous_samples(self):
        avg, source = ADCAverage(2), Source()
        results = [avg.step(source) for _ in range(32)]
        self.assertEqual(results[15], [ch + 0.5 for ch in range(8)])
        self.assertEqual(results[31], [ch + 2.5 for ch in range(8)])

    def test_invalid_count(self):
        for count in (0, -1, 3, 100):
            with self.assertRaises(ValueError):
                ADCAverage(count)


if __name__ == "__main__":
    unittest.main()
