"""parks/*.html are generated: every registered page must match the generator's output
and index.html's parksWithPages table must match the registry.

Fix a failure with:  python scripts/build_park_pages.py --update-index && python scripts/build_sitemap.py
Run: python -m unittest discover -s tests/python
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_park_pages as bpp  # noqa: E402


class ParkPagesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = bpp.load()

    def test_every_registered_page_is_current(self):
        stale = []
        for code, reg in self.data["registry"].items():
            out = ROOT / "parks" / f"{reg['slug']}.html"
            if not out.exists() or out.read_text() != bpp.render_page(code, self.data):
                stale.append(out.name)
        self.assertEqual(stale, [], "run: python scripts/build_park_pages.py")

    def test_every_registered_code_has_map_entries(self):
        missing = [c for c in self.data["registry"] if not bpp.entries_for(c, self.data["parkData"])]
        self.assertEqual(missing, [])

    def test_slugs_are_unique_and_stable_shape(self):
        slugs = [r["slug"] for r in self.data["registry"].values()]
        self.assertEqual(len(slugs), len(set(slugs)))
        for s in slugs:
            self.assertRegex(s, r"^[a-z0-9-]+$")

    def test_parks_with_pages_table_matches_registry(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn(bpp.parks_with_pages_literal(self.data), html, "run: python scripts/build_park_pages.py --update-index")

    def test_pages_carry_shared_nav_and_stylesheet(self):
        for reg in list(self.data["registry"].values())[:10]:
            html = (ROOT / "parks" / f"{reg['slug']}.html").read_text()
            self.assertIn('class="topnav-links"', html)
            self.assertIn('href="/park-page.css"', html)
            self.assertIn("<!-- park-history:start", html)

    def test_photo_paths_are_not_doubled(self):
        for reg in self.data["registry"].values():
            html = (ROOT / "parks" / f"{reg['slug']}.html").read_text()
            self.assertNotRegex(html, r"/images/\d+/images/")

    def test_photo_links_emit_real_dimensions(self):
        photos = [("1037", {"file": "images/1037/" + next((ROOT / "images" / "1037").glob("*.jpg")).name, "name": "x"})]
        out = bpp.photo_links("g", photos, 1, "entry-photo", "fallback")
        m = re.search(r'<img [^>]*width="(\d+)" height="(\d+)"', out)
        self.assertIsNotNone(m, out)
        self.assertGreater(int(m.group(1)), 0)
        self.assertGreater(int(m.group(2)), 0)

    def test_dim_attrs_skips_unreadable_files(self):
        self.assertEqual(bpp.dim_attrs("/images/does-not-exist.jpg"), "")

    def test_image_size_reads_png_and_jpeg(self):
        from image_size import image_size
        png = next((ROOT / "images").rglob("*.png"))
        jpg = next((ROOT / "images").rglob("*.jpg"))
        for f in (png, jpg):
            w, h = image_size(f)
            self.assertTrue(w > 0 and h > 0, f)

    def test_generated_park_images_have_dimensions(self):
        missing = []
        for reg in self.data["registry"].values():
            html = (ROOT / "parks" / f"{reg['slug']}.html").read_text()
            for tag in re.findall(r"<img [^>]*>", html):
                if "logo.svg" in tag or "width=" in tag:
                    continue
                src = re.search(r'src="/([^"]+)"', tag).group(1)
                if bpp.dim_attrs("/" + src):
                    missing.append(f"{reg['slug']}: {src}")
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
