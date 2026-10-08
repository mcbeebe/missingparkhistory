"""Park History data layer: every source file is well-formed, published parks are fully sourced,
and data/parkHistory.json is compiled from data/park_history/*.json.

Fix a stale-compile failure with:  python scripts/build_park_history.py --compile
Run: python -m unittest discover -s tests/python
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import build_park_history as bph  # noqa: E402

SOURCES = bph.load_sources() if bph.SRC_DIR.exists() else {}
PARK_DATA = json.loads((ROOT / "data" / "parkData.json").read_text())
CODES = {c.strip() for rec in PARK_DATA.values() for c in str(rec.get("code", "")).split(",") if c.strip()}


class SourceFilesTest(unittest.TestCase):
    def test_every_file_validates(self):
        problems = [p for rec in SOURCES.values() for p in bph.validate(rec)]
        self.assertEqual(problems, [])

    def test_codes_exist_in_park_data(self):
        unknown = sorted(c for c in SOURCES if c not in CODES)
        self.assertEqual(unknown, [], "park_history files for codes that are not on the map")

    def test_file_name_matches_code(self):
        for f in bph.SRC_DIR.glob("*.json"):
            self.assertEqual(json.loads(f.read_text()).get("code"), f.stem)

    def test_legacy_summaries_never_publish(self):
        for code, rec in SOURCES.items():
            if rec.get("author") == "parks-page-legacy":
                self.assertNotEqual(rec.get("reviewStatus"), "published", code)


class CompiledFileTest(unittest.TestCase):
    def test_compiled_matches_sources(self):
        self.assertTrue(bph.COMPILED.exists(), "run python scripts/build_park_history.py --compile")
        self.assertEqual(bph.COMPILED.read_text(), bph.dumps_compiled(bph.compile_sources(SOURCES)),
                         "data/parkHistory.json is stale; run python scripts/build_park_history.py --compile")

    def test_compiled_drops_authoring_fields(self):
        compiled = json.loads(bph.COMPILED.read_text())
        for code, rec in compiled["parks"].items():
            self.assertNotIn("facts", rec)
            self.assertNotIn("author", rec)


class ValidatorRulesTest(unittest.TestCase):
    """The rules that keep unsourced text off the site."""

    def base(self, **over):
        rec = {
            "code": "ZZZZ", "name": "Test", "entries": [], "reviewStatus": "published", "lastReviewed": "2026-10-07",
            "author": "a", "verifiedBy": "b",
            "summary": "<p>" + "word " * 100 + '<a href="https://npshistory.com/x.htm" target="_blank" rel="noopener">[1]</a></p>',
            "sources": [{"url": "https://npshistory.com/x.htm", "title": "x"}],
            "themes": {"women": {"html": '<p>Fact. <a href="https://npshistory.com/y.pdf" target="_blank" rel="noopener">[2]</a></p>',
                                 "sources": [{"url": "https://npshistory.com/y.pdf", "title": "y"}]}},
            "facts": [{"claim": "Fact", "sourceUrl": "https://npshistory.com/y.pdf", "locator": "p. 1"}],
            "photos": [], "npshistory": {}, "corrections": [],
        }
        rec.update(over)
        return rec

    def test_clean_record_passes(self):
        self.assertEqual(bph.validate(self.base()), [])

    def test_paragraph_without_citation_fails(self):
        rec = self.base(summary="<p>" + "word " * 100 + "</p>")
        self.assertTrue(any("no inline citation" in p for p in bph.validate(rec)))

    def test_boilerplate_is_banned(self):
        rec = self.base()
        rec["themes"]["women"]["html"] = '<p>This park is one of hundreds of sites. <a href="https://npshistory.com/y.pdf">[2]</a></p>'
        self.assertTrue(any("banned text" in p for p in bph.validate(rec)))

    def test_author_cannot_verify_own_work(self):
        self.assertTrue(any("verifiedBy" in p for p in bph.validate(self.base(verifiedBy="a"))))

    def test_facts_required_when_published(self):
        self.assertTrue(any("facts[]" in p for p in bph.validate(self.base(facts=[]))))

    def test_inline_cite_must_be_listed(self):
        rec = self.base()
        rec["themes"]["women"]["html"] = '<p>Fact. <a href="https://npshistory.com/other.pdf">[9]</a></p>'
        self.assertTrue(any("not in sources" in p for p in bph.validate(rec)))

    def test_wikipedia_alone_is_rejected(self):
        rec = self.base()
        rec["themes"]["women"]["html"] = '<p>Fact. <a href="https://en.wikipedia.org/wiki/X">[2]</a></p>'
        rec["themes"]["women"]["sources"] = [{"url": "https://en.wikipedia.org/wiki/X", "title": "w"}]
        self.assertTrue(any("Wikipedia" in p for p in bph.validate(rec)))

    def test_photo_rules(self):
        rec = self.base(photos=[{"file": "images/history/zzzz/none.jpg", "caption": "c", "credit": "Photo courtesy of X",
                                 "license": "CC BY 4.0", "sourceUrl": "https://nps.gov/x", "imageUrl": "https://nps.gov/x.jpg",
                                 "evidenceUrl": "https://nps.gov/x", "capturedAt": "2026-10-07"}])
        problems = bph.validate(rec)
        self.assertTrue(any("license" in p for p in problems))
        self.assertTrue(any("public-domain credit" in p for p in problems))
        self.assertTrue(any("does not exist" in p for p in problems))

    def test_disallowed_tag(self):
        rec = self.base(summary='<p>' + 'word ' * 100 + '<script>x</script><a href="https://npshistory.com/x.htm">[1]</a></p>')
        self.assertTrue(any("disallowed tag" in p for p in bph.validate(rec)))

    def test_draft_is_lenient(self):
        rec = self.base(reviewStatus="draft", facts=[], verifiedBy="", summary="<p>short, no cite</p>")
        self.assertEqual(bph.validate(rec), [])


class RenderTest(unittest.TestCase):
    def test_published_block_has_sources_and_archive_link(self):
        rec = ValidatorRulesTest().base(npshistory={"indexUrl": "https://npshistory.com/publications/zzzz/index.htm", "docCount": 12})
        html = bph.render_block(rec)
        self.assertIn('class="ph-summary"', html)
        self.assertIn("ph-sources", html)
        self.assertIn("12 documents on NPSHistory.com", html)
        self.assertIn(bph.THEME_LABELS["women"], html)

    def test_unpublished_block_is_legacy_only(self):
        rec = ValidatorRulesTest().base(reviewStatus="legacy-unsourced", summary="<p>Old paragraph.</p>",
                                        npshistory={"indexUrl": "https://npshistory.com/publications/zzzz/index.htm"})
        html = bph.render_block(rec)
        self.assertIn("ph-legacy", html)
        self.assertNotIn("ph-sources", html)
        self.assertIn("Documentary record on NPSHistory.com", html)

    def test_theme_photo_sits_inside_its_section(self):
        if "MORA" not in SOURCES:
            self.skipTest("MORA not present")
        html = bph.render_block(SOURCES["MORA"])
        self.assertTrue(html.startswith('<figure class="ph-photo">'), "untagged photo should lead the section")
        climate = html.index(f"<h4>{bph._esc(bph.THEME_LABELS['climate'])}</h4>")
        nisqually = html.index("nisqually-glacier.jpg")
        next_section = html.find("<section", climate)
        self.assertGreater(nisqually, climate)
        self.assertTrue(next_section == -1 or nisqually < next_section)
        self.assertIn("Public domain (U.S. Government work)", html)
        self.assertNotIn(">PD-USGov-NPS<", html)

    def test_theme_key_must_match_a_section(self):
        rec = ValidatorRulesTest().base(photos=[{**SOURCES["MORA"]["photos"][0], "themeKey": "slavery"}]) if "MORA" in SOURCES else None
        if rec is None:
            self.skipTest("MORA not present")
        self.assertTrue(any("themeKey" in p for p in bph.validate(rec)))

    def test_mora_exemplar_renders_all_four_themes(self):
        if "MORA" not in SOURCES:
            self.skipTest("MORA not present")
        html = bph.render_block(SOURCES["MORA"]) if SOURCES["MORA"].get("reviewStatus") == "published" else ""
        if html:
            for key in ("indigenous", "climate", "women", "labor_ccc"):
                self.assertIn(f"<h4>{bph._esc(bph.THEME_LABELS[key])}</h4>", html)


if __name__ == "__main__":
    unittest.main()
