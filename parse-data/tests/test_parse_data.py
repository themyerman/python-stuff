"""Unit tests for parse-data utilities."""

import csv
import importlib.util
import tempfile
import unittest
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
MODULE_PATH = BASE_DIR / "parse-csv.py"

spec = importlib.util.spec_from_file_location("parse_csv_mod", MODULE_PATH)
parse_csv_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parse_csv_mod)


class ParseCsvTests(unittest.TestCase):
    """Validate CSV filtering behavior."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = Path(self.temp_dir.name) / "sample.csv"
        with open(self.csv_path, "w", newline="", encoding="utf-8") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(["James", "Butt", "", "", "", "", "LA"])
            writer.writerow(["Josephine", "Darakjy", "", "", "", "", "MI"])
            writer.writerow(["Art", "Venere", "", "", "", "", "LA"])

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_filter_rows_by_state(self):
        rows = list(parse_csv_mod.filter_rows(self.csv_path, "la"))
        self.assertEqual(len(rows), 2)

    def test_filter_rows_by_state_and_name(self):
        rows = list(parse_csv_mod.filter_rows(self.csv_path, "LA", "Ar"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][0], "Art")

    def test_invalid_state_raises(self):
        with self.assertRaises(ValueError):
            list(parse_csv_mod.filter_rows(self.csv_path, "XX"))


if __name__ == "__main__":
    unittest.main()
