"""sitemap.xml must list every public page and nothing else.

Fix a failure by running:  python scripts/build_sitemap.py
Run: python -m unittest discover -s tests/python
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_sitemap as bs  # noqa: E402


class SitemapTest(unittest.TestCase):
    def setUp(self):
        self.listed = re.findall(r"<loc>([^<]+)</loc>", (ROOT / "sitemap.xml").read_text())
        self.expected = bs.public_urls(ROOT)

    def test_every_public_page_is_listed(self):
        missing = sorted(set(self.expected) - set(self.listed))
        self.assertEqual(missing, [], "pages missing from sitemap.xml; run python scripts/build_sitemap.py")

    def test_only_public_pages_are_listed(self):
        stale = sorted(set(self.listed) - set(self.expected))
        self.assertEqual(stale, [], "sitemap.xml lists drafts, redirects or deleted pages; run python scripts/build_sitemap.py")

    def test_no_duplicates(self):
        self.assertEqual(len(self.listed), len(set(self.listed)))

    def test_redirect_pages_are_excluded(self):
        for rel in ("parks/lower-delaware-wsr.html", "parks/chesapeake-and-ohio-canal-nhp.html",
                    "parks/national-mall-and-memorial-parks.html"):
            if (ROOT / rel).exists():
                self.assertNotIn(bs.url_for(rel), self.listed)


if __name__ == "__main__":
    unittest.main()
