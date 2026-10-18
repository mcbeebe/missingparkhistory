"""data/blockedFunding.json must match its source CSV and account for every dollar.

Fix a stale-file failure by running:  python scripts/build_blocked_funding.py
Run: python -m unittest discover -s tests/python
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_blocked_funding as bf  # noqa: E402


class BlockedFundingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.built = bf.build()
        cls.on_disk = json.loads((ROOT / "data" / "blockedFunding.json").read_text(encoding="utf-8"))

    def test_file_is_current(self):
        self.assertEqual(self.on_disk, self.built, "blockedFunding.json is stale; run python scripts/build_blocked_funding.py")

    def test_published_totals(self):
        # 133 agreements disapproved Aug 7, 2026 and still disapproved Sep 9, totaling $25,947,857.
        m = self.built["meta"]
        self.assertEqual(m["n"], 133)
        self.assertEqual(m["usd"], 25947857)

    def test_on_map_plus_off_map_is_everything(self):
        m = self.built["meta"]
        self.assertEqual(m["map_n"] + m["offmap_n"], m["n"])
        self.assertLessEqual(abs(m["map_usd"] + m["offmap_usd"] - m["usd"]), 1)
        n = sum(p["n"] for p in self.built["parks"].values()) + sum(o["n"] for o in self.built["offmap"])
        self.assertEqual(n, m["n"])

    def test_every_mapped_park_has_coordinates(self):
        for code, p in self.built["parks"].items():
            self.assertIsInstance(p.get("lat"), (int, float), code)
            self.assertIsInstance(p.get("lon"), (int, float), code)

    def test_history_counts_match_items(self):
        for code, p in self.built["parks"].items():
            self.assertEqual(p["hist_n"], sum(i["hist"] for i in p["items"]), code)


if __name__ == "__main__":
    unittest.main()
