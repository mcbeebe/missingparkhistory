"""The approved Tone & Sensitivity Review v1.0 edits stay applied, and every
rewritten passage cites its sources.

Run: python -m unittest discover -s tests/python
"""
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "docs" / "reviews" / "source"
sys.path.insert(0, str(SOURCE))

import apply_tone_review as atr  # noqa: E402

EDITS = json.loads((SOURCE / "tone-review-v1.0.json").read_text(encoding="utf-8"))
PARK_DATA = json.loads((ROOT / "data" / "parkData.json").read_text(encoding="utf-8"))
CITE = re.compile(r'<a href="([^"]+)"[^>]*class="cite"[^>]*>\[([^\]]+)\]</a>')


class ToneReviewAppliedTest(unittest.TestCase):
    def test_every_edit_is_applied(self):
        r = subprocess.run([sys.executable, str(SOURCE / "apply_tone_review.py"), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_every_rewrite_carries_a_citation(self):
        for e in EDITS:
            if not e["proposed_html"].strip():
                continue  # a deletion has nothing to cite
            with self.subTest(edit=e["id"]):
                self.assertTrue(CITE.search(atr.with_citations(e)), e["park"])

    def test_citation_links_are_real(self):
        seen = set()
        for e in EDITS:
            for href, label in CITE.findall(atr.with_citations(e)):
                seen.add(href)
                self.assertTrue(href.startswith("https://") or href == atr.RECORD_URL, href)
                self.assertNotIn(".json", label)
        self.assertIn(atr.RECORD_URL, seen)
        page, anchor = atr.RECORD_URL.split("#")
        self.assertIn(f'id="{anchor}"', (ROOT / page.lstrip("/")).read_text(encoding="utf-8"))

    def test_citations_also_reach_the_generated_park_pages(self):
        for e in EDITS:
            if e["field"] != "narrative" or not e.get("file") or not e["proposed_html"].strip():
                continue
            with self.subTest(edit=e["id"]):
                page = (ROOT / e["file"]).read_text(encoding="utf-8")
                self.assertIn(atr.with_citations(e), page)

    def test_grand_teton_no_longer_jumps_from_the_massacre_to_geology(self):
        nar = PARK_DATA["720"]["narrative"]
        self.assertNotIn("raw power of mountain geology", nar)
        self.assertNotIn("From the internal review records", nar)
        self.assertNotIn("&quot;&rdquo;", nar)
        why = nar.split("Why this matters:")[1]
        self.assertIn("Marias Massacre", why)
        self.assertIn("Blackfeet", why)

    def test_emmett_till_is_civil_rights_not_indigenous(self):
        rec = PARK_DATA["352"]
        self.assertIn("Civil Rights & Racial Justice", rec["topics"])
        self.assertNotIn("Indigenous & Native History", rec["topics"])
        self.assertNotIn("tribal consultation", rec["narrative"])

    def test_duplicate_source_labels_are_numbered(self):
        e = {"proposed_html": "<p>x</p>", "sources": [
            {"url": "https://www.nps.gov/a", "note": ""}, {"url": "https://www.nps.gov/b", "note": ""},
            {"url": "https://en.wikipedia.org/wiki/X", "note": ""}]}
        labels = [lab for _, lab in CITE.findall(atr.with_citations(e))]
        self.assertEqual(labels, ["NPS", "NPS 2"])  # Wikipedia dropped when a better source exists


if __name__ == "__main__":
    unittest.main()
