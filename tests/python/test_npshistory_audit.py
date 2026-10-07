"""Offline tests for scripts/npshistory_audit.py (no network).

Run: python -m unittest discover -s tests/python
"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import npshistory_audit as na  # noqa: E402

THEMES_CFG = json.loads((ROOT / "data" / "npshistory_themes.json").read_text())
ALIASES = json.loads((ROOT / "data" / "npshistory_aliases.json").read_text())

HOME_SNIPPET = """
<select><option value="https://npshistory.com/park_histories.htm">Select Park or Region</option>
<option value="https://npshistory.com/park_histories.htm#abln"> Abraham Lincoln NHA</option>
<option value="https://npshistory.com/publications/mora/index.htm"> Mount Rainier NP (MORA)</option>
<option value="https://npshistory.com/publications/cari/index.htm"> Cane River Creole NHP (CARI)</option>
<option value="https://npshistory.com/publications/malw/index.htm"> Maggie L Walker NHS (MALW)</option>
</select>"""

INDEX_SNIPPET = """
<div class="park-header">
  <a name="cari"></a>
  <span class="park"><a href="publications/cari/index.htm" target="_blank">Cane River Creole National Historical Park</a></span>
</div>
<div class="park-header">
  <a name="crha"></a>
  <span class="park">Cane River National Heritage Area</span>
</div>"""

PARK_SNIPPET = """<html><head><title>Park Archives: Mount Rainier National Park</title></head><body>
<IMG SRC="index.jpg" ALT="Park Photo"><div class="image-credit">NPS photo</div>
<p>Mount Rainier rises above the Cascades. It is a volcano.</p>
<p class="credit">Source: NPS Brochure (2019)</p>
<p class="style3-18">Establishment</p>
<p class="style3-14">
Wilderness &#151; November 16, 1988<br>
Mount Rainier National Park &#151; March 2, 1899
</p>
<a name="documents"></a><span class="section">Documents</span>
<p class="hangingindent"><a href="adhi.pdf" target="_blank">Wonderland: An Administrative History of Mount Rainier National Park</a> <font size="-2">(Theodore Catton, May 1996; <a href="adhi/index.htm">HTML edition</a>)</font></p>
<p class="hangingindent"><a href="../usfs/fmt-v53n2-2003.pdf" target="_blank">A Burning Issue: American Indian Fire Use on the Mt. Rainier Forest Reserve</a> <font size="-2">(Cheryl A. Mack, 2003)</font></p>
<p class="hangingindent"><a href="nisqually-1956.pdf">Fluctuations of the Nisqually Glacier, Mt. Rainier, Washington, Since 1750</a> <font size="-2">(A.E. Harrison, 1956)</font></p>
<p class="hangingindent"><a href="mmp.pdf">Museum Management Plan, Mount Rainier National Park</a> <font size="-2">(Robert Applegate, Gay Hunter, September 2003)</font></p>
<p class="hangingindent">Assessing Elk Trail and Wallow Impacts</p>
<p class="hangingindent2"><a href="elk-impacts/f85.pdf">Assessing Elk Trail and Wallow Impacts: Quarterly Progress Report 1985</a> <font size="-2">(William J. Ripple, 1985)</font></p>
<p class="hangingindent">Annual Reports: <a href="ar/2017.pdf">2017</a> <a href="ar/2018.pdf">2018</a></p>
</body></html>"""


class ResolverTest(unittest.TestCase):
    def setUp(self):
        self.coded, self.uncoded = na.parse_home_options(HOME_SNIPPET)
        self.anchors = na.parse_park_index_anchors(INDEX_SNIPPET)

    def test_home_options(self):
        self.assertEqual(self.coded["MORA"]["url"], "https://npshistory.com/publications/mora/index.htm")
        self.assertEqual(self.coded["MORA"]["name"], "Mount Rainier NP")
        self.assertEqual([u["name"] for u in self.uncoded], ["Abraham Lincoln NHA"])

    def test_anchor_index(self):
        self.assertEqual(self.anchors["cari"]["url"], "https://npshistory.com/publications/cari/index.htm")
        self.assertIsNone(self.anchors["crha"]["url"])

    def test_direct_code(self):
        r = na.resolve("MORA", "Mount Rainier National Park", ALIASES, self.coded, self.anchors)
        self.assertEqual((r["kind"], r["url"]), ("park", "https://npshistory.com/publications/mora/index.htm"))

    def test_name_match_for_mismatched_codes(self):
        r = na.resolve("CACR", "Cane River Creole National Historical Park", ALIASES, self.coded, self.anchors)
        self.assertEqual(r["kind"], "name-match")
        self.assertEqual(r["npsh_code"], "CARI")
        r = na.resolve("MAWA", "Maggie L. Walker National Historic Site", ALIASES, self.coded, self.anchors)
        self.assertEqual((r["kind"], r["npsh_code"]), ("name-match", "MALW"))

    def test_admin_units_and_non_nps(self):
        self.assertEqual(na.resolve("SERO", "Southeast Regional Office", ALIASES, self.coded, self.anchors)["kind"], "no-page")
        self.assertEqual(na.resolve("BRMBR", "Bear River MBR", ALIASES, self.coded, self.anchors)["kind"], "non-nps")

    def test_guess_when_unknown(self):
        r = na.resolve("ZZZZ", "Nowhere", ALIASES, self.coded, self.anchors)
        self.assertEqual((r["kind"], r["url"]), ("guess", "https://npshistory.com/publications/zzzz/index.htm"))


class CodesTest(unittest.TestCase):
    def test_composite_split(self):
        codes = na.canonical_codes({"1": {"code": "GWMP,THIS"}, "2": {"code": "THIS"}, "3": {"code": "MORA"}})
        self.assertEqual(codes, {"GWMP": ["1"], "THIS": ["1", "2"], "MORA": ["3"]})

    def test_primary_code_skips_umbrella(self):
        self.assertEqual(na.primary_code("NAMA,LINC", ALIASES["umbrella"]), "LINC")
        self.assertEqual(na.primary_code("BEPA,NAMA", ALIASES["umbrella"]), "BEPA")
        self.assertEqual(na.primary_code("WEAR,CAKR,KOVA,NOAT", ALIASES["umbrella"]), "CAKR")
        self.assertEqual(na.primary_code("NAMA", ALIASES["umbrella"]), "NAMA")

    def test_real_park_data_has_no_blank_codes(self):
        data = json.loads((ROOT / "data" / "parkData.json").read_text())
        self.assertTrue(all(c for c in na.canonical_codes(data)))


class ParserTest(unittest.TestCase):
    def setUp(self):
        self.page = na.parse_park_page(PARK_SNIPPET, "https://npshistory.com/publications/mora/index.htm")

    def test_header_fields(self):
        self.assertEqual(self.page["name"], "Mount Rainier National Park")
        self.assertEqual(self.page["established"], ["Wilderness — November 16, 1988", "Mount Rainier National Park — March 2, 1899"])
        self.assertEqual(self.page["photo"], "https://npshistory.com/publications/mora/index.jpg")
        self.assertEqual(self.page["photo_credit"], "NPS photo")
        self.assertEqual(self.page["intro_words"], 10)

    def test_documents(self):
        docs = {d["title"]: d for d in self.page["docs"]}
        adhi = docs["Wonderland: An Administrative History of Mount Rainier National Park"]
        self.assertEqual(adhi["url"], "https://npshistory.com/publications/mora/adhi.pdf")
        self.assertEqual(adhi["year"], 1996)
        self.assertEqual(adhi["alt_urls"], ["https://npshistory.com/publications/mora/adhi/index.htm"])
        self.assertEqual(docs["A Burning Issue: American Indian Fire Use on the Mt. Rainier Forest Reserve"]["url"],
                         "https://npshistory.com/publications/usfs/fmt-v53n2-2003.pdf")
        self.assertEqual(docs["Assessing Elk Trail and Wallow Impacts: Quarterly Progress Report 1985"]["group"],
                         "Assessing Elk Trail and Wallow Impacts")
        self.assertIn("Annual Reports: 2017", docs)
        self.assertNotIn("HTML edition", docs)


class ClassifierTest(unittest.TestCase):
    def setUp(self):
        self.clf = na.Classifier(THEMES_CFG)

    def themes(self, title, cite="", group=""):
        return self.clf.doc({"title": title, "cite": cite, "group": group})[1]

    def cats(self, title, cite="", group=""):
        return self.clf.doc({"title": title, "cite": cite, "group": group})[0]

    def test_stonewall_jackson_is_not_lgbtq(self):
        self.assertNotIn("lgbtq", self.themes("Stonewall Jackson at Manassas"))
        self.assertIn("lgbtq", self.themes("Finding Our Place: Queer Heritage in the United States"))
        self.assertIn("lgbtq", self.themes("Stonewall National Monument Foundation Document"))
        self.assertNotIn("lgbtq", self.themes("Historic Resource Study: 'Stonewall' Jackson's Headquarters"))

    def test_author_names_do_not_count(self):
        self.assertNotIn("lgbtq", self.themes("Museum Management Plan", cite="(Robert Applegate, Gay Hunter, 2003)"))

    def test_place_names_are_not_indigenous(self):
        self.assertNotIn("indigenous", self.themes("Fluctuations of the Nisqually Glacier, Mt. Rainier, Washington, Since 1750"))
        self.assertIn("indigenous", self.themes("Plants, Tribal Traditions, and the Mountain: Nisqually Tribal Plant Gathering"))
        self.assertIn("indigenous", self.themes("Historical Overview of Indians and Mount Rainier"))
        self.assertNotIn("indigenous", self.themes("Indian Henry's Meadow Visitor Survey"))

    def test_black_history_vs_black_places(self):
        self.assertNotIn("black", self.themes("Black Canyon of the Gunnison Geology"))
        self.assertIn("black", self.themes("African American History at Fort Pulaski"))
        self.assertIn("black", self.themes("Buffalo Soldiers in the American Southwest"))

    def test_slavery_and_women(self):
        self.assertIn("slavery", self.themes("Enslaved People at the President's House"))
        self.assertIn("women", self.themes("Fay Fuller: First Woman to the Top of Mount Rainier"))

    def test_climate_and_carbon_river(self):
        self.assertIn("climate", self.themes("Change in Glacial Extent at Mount Rainier National Park from 1896 to 2015"))
        self.assertNotIn("climate", self.themes("Carbon River Road"))

    def test_labor_union_army(self):
        self.assertNotIn("labor_ccc", self.themes("Union Army Encampments at Petersburg"))
        self.assertIn("labor_ccc", self.themes("The Civilian Conservation Corps at Mount Rainier"))

    def test_japanese_american_and_latino(self):
        self.assertIn("japanese_american", self.themes("Confinement and Ethnicity: WWII Japanese American Relocation Sites"))
        self.assertIn("latino", self.themes("Hispanic Reflections on the American Landscape"))
        self.assertNotIn("latino", self.themes("Mission 66 for Mount Rainier National Park"))

    def test_categories(self):
        self.assertIn("adhi", self.cats("Wonderland: An Administrative History of Mount Rainier National Park"))
        self.assertIn("hrs", self.cats("Historic Resource Study: Nicodemus National Historic Site"))
        self.assertIn("cli_clr", self.cats("Cultural Landscapes Inventory: Longmire Developed Area"))
        self.assertIn("nrhp", self.cats("Paradise Inn", cite="National Register of Historic Places Nomination (1985)"))

    def test_topic_tags_map_to_themes(self):
        self.assertEqual(self.clf.tag_to_theme["Slavery & Enslaved People"], "slavery")
        self.assertEqual(self.clf.tag_to_theme["Japanese American Incarceration"], "japanese_american")


class SelfNameTest(unittest.TestCase):
    """A park's own name must not count as a theme hit for every document on its page."""

    def setUp(self):
        self.clf = na.Classifier(THEMES_CFG)

    def doc(self, title, group=""):
        return {"title": title, "url": "https://npshistory.com/x.pdf", "cite": "", "group": group, "year": None}

    def test_newsletters_at_amache_are_not_sources(self):
        s = na.summarize_docs([self.doc("Spring", group="Amache newsletter"), self.doc("Amache Cemetery")],
                              self.clf, "Amache National Historic Site")
        self.assertEqual(s["themes"]["japanese_american"], 0)

    def test_anchor_studies_inherit_the_park_theme(self):
        s = na.summarize_docs([self.doc("Foundation Document Overview, Amache National Historic Site"),
                               self.doc("Short History of Amache Japanese Internment Camp")],
                              self.clf, "Amache National Historic Site",
                              park_text="Amache was one of ten Japanese American incarceration sites; the internment of Japanese Americans is interpreted here.")
        self.assertEqual(s["themes"]["japanese_american"], 2)

    def test_eleanor_roosevelt_water_plan_is_not_womens_history(self):
        s = na.summarize_docs([self.doc("Water Resources Management Plan: Eleanor Roosevelt National Historic Site"),
                               self.doc("Historic Resource Study: Eleanor Roosevelt National Historic Site")],
                              self.clf, "Eleanor Roosevelt National Historic Site")
        self.assertEqual(s["themes"]["women"], 1)

    def test_coronado_bird_survey_is_not_latino(self):
        s = na.summarize_docs([self.doc("Springs Monitoring at Coronado National Memorial: 2024")],
                              self.clf, "Coronado National Memorial")
        self.assertEqual(s["themes"]["latino"], 0)

    def test_pulse_study_and_stonewall_texas(self):
        self.assertEqual(self.clf.doc({"title": "Pulse Study of the Madrona Pools", "cite": "", "group": ""})[1], [])
        self.assertEqual(self.clf.doc({"title": "Lyndon B. Johnson NHP - Stonewall - Texas", "cite": "", "group": ""})[1], [])


class GapTest(unittest.TestCase):
    def test_rubric(self):
        self.assertEqual(na.gap_for(0, 3, False, 3), "P1")
        self.assertEqual(na.gap_for(0, 1, False, 1), "P2")
        self.assertEqual(na.gap_for(1, 2, False, 3), "P3")
        self.assertEqual(na.gap_for(1, 0, False, 3), "NA")
        self.assertEqual(na.gap_for(0, 0, False, 3), "OK")
        self.assertEqual(na.gap_for(2, 5, True, 3), "OK")

    def test_boilerplate_detection_on_real_data(self):
        data = json.loads((ROOT / "data" / "parkData.json").read_text())
        mora = next(v for v in data.values() if v.get("code") == "MORA")
        self.assertIn(na.BOILERPLATE, mora["narrative"])


if __name__ == "__main__":
    unittest.main()
