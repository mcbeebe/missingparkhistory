"""The watcher's --coverage report runs on the saved snapshot and reads the site data.

Run: python -m unittest discover -s tests/python
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import sos_tracker_watch as w  # noqa: E402


class CoverageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        snap = json.loads((ROOT / "data/sos_tracker_snapshot.json").read_text())
        cls.text, cls.problems = w.coverage(snap, ROOT)

    def test_report_has_a_row_per_tracker_park(self):
        self.assertIn("| ACAD |", self.text)
        self.assertIn("| INDE |", self.text)
        self.assertIn("## All parks", self.text)

    def test_counts_are_numbers(self):
        self.assertIsInstance(self.problems, int)

    def test_name_matching_ignores_designations_and_apostrophes(self):
        self.assertEqual(w._norm("Harper\u2019s Ferry National Historic Park"), w._norm("Harpers Ferry National Historical Park"))
        self.assertEqual(w._norm("Cane River Creole National Historic Park"), w._norm("Cane River Creole National Historical Park"))


if __name__ == "__main__":
    unittest.main()
