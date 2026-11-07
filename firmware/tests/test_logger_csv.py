"""CSV units, direct raw codes and missing-scan behavior."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from logger_csv import make_record


class CSVTests(unittest.TestCase):
    def test_raw_and_voltage_units_and_failed_scan(self):
        codes = [-8388608, -1, 0, 1, 2, 3, 4, 8388607]
        for raw in (False, True):
            for values in (codes, None):
                header, row = make_record("12:00:00", 20, 50, 4.1,
                                          ["sensor"], [21.0], True, values,
                                          ads_raw=raw)
                self.assertEqual(header.strip().split(","),
                                 ["Cas", "SHT_T", "SHT_H"] +
                                 ["AN{}{}".format(i, "_RAW" if raw else "") for i in range(8)] +
                                 ["BAT", "sensor"])
                cells = row.strip().split(",")
                self.assertEqual(cells[3:11], ([str(v) if raw else "{:.6f}".format(v) for v in codes]
                                              if values is not None else [""] * 8))
                self.assertEqual(cells[11:], ["4.10", "21.0"])
