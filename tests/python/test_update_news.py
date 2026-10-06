"""Unit tests for scripts/update_news.py weekly jobs (synthesis + timeline),
its card handling, and the scripts/resort_cards.py step that runs after it.

Run: python -m unittest discover -s tests/python
"""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import resort_cards as rc  # noqa: E402
import update_news as un  # noqa: E402


def card(month_day: str, year: str, url: str, added: str | None = None, headline: str = "Headline") -> str:
    added_attr = f' data-added="{added}"' if added else ""
    return (
        f'  <article class="article-card" data-tags="removal" data-month="{year}-01" data-source="x"{added_attr}>\n'
        f'    <div class="article-date"><div class="month-day">{month_day}</div><div class="date-detail">{year}</div></div>\n'
        f'    <div class="article-body">\n'
        f'      <div class="article-meta"><span class="article-source">Source</span></div>\n'
        f'      <h3><a href="{url}" target="_blank">{headline}</a></h3>\n'
        f'      <p class="article-summary">A summary long enough to be useful.</p>\n'
        f'    </div>\n'
        f'  </article>\n'
    )


def legacy_card(month_day: str, year: str, url: str) -> str:
    """A card in the old hand-written format: data-tags only, no data-month."""
    return (
        f'<article class="article-card" data-tags="resistance">\n'
        f'  <div class="article-date">\n'
        f'    <div class="month-day">{month_day}</div>\n'
        f'    <div class="date-detail">{year}</div>\n'
        f'  </div>\n'
        f'  <div class="article-body"><h3><a href="{url}" target="_blank">Legacy card</a></h3></div>\n'
        f'</article>\n'
    )


def git_show(rev: str, path: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), "show", f"{rev}:{path}"],
                          capture_output=True, text=True, check=True).stdout


def year_headings(html: str) -> list[str]:
    return re.findall(r'<div class="year-marker"><h2>([^<]*)</h2></div>', html)


class CanonicalUrlTest(unittest.TestCase):
    def test_cnn_mirrors_collapse(self):
        urls = [
            "https://edition.cnn.com/2026/09/19/us/x",
            "https://us.cnn.com/2026/09/19/us/x",
            "https://www.cnn.com/2026/09/19/us/x/",
        ]
        self.assertEqual(len({un.canonical_url(u) for u in urls}), 1)


class ArticleWindowTest(unittest.TestCase):
    def test_includes_recently_added_older_articles(self):
        html = card("Sep 23", "2026", "https://a.example/1", added="2026-09-29") + \
               card("Sep 19", "2026", "https://a.example/2")
        got = un._articles_for_synthesis(html, "2026-09-28")
        self.assertEqual([a["url"] for a in got], ["https://a.example/1"])
        self.assertEqual(got[0]["added"], "2026-09-29")

    def test_published_in_window_still_included(self):
        html = card("Oct 1", "2026", "https://a.example/1")
        self.assertEqual(len(un._articles_for_synthesis(html, "2026-09-28")), 1)

    @unittest.skipUnless((ROOT / ".git").exists(), "needs git history")
    def test_reproduces_the_sep_28_bug_on_real_page(self):
        # The live page on Sep 28, 2026: newest article was Sep 19, so a strict
        # 7-day publish-date window was empty; widening finds the week's news.
        try:
            page = git_show("b1c9fcb", "news-and-press.html")
        except subprocess.CalledProcessError:
            self.skipTest("commit not in this clone")
        self.assertEqual(un._articles_for_synthesis(page, "2026-09-21"), [])
        since, arts = un._gather_weekly_articles(page, None, "2026-09-28")
        self.assertGreaterEqual(len(arts), 2)
        self.assertLess(since, "2026-09-21")


class CadenceTest(unittest.TestCase):
    def test_weekly_due(self):
        self.assertTrue(un.weekly_due(None, "2026-10-06"))
        self.assertFalse(un.weekly_due("2026-09-30", "2026-10-06"))
        self.assertTrue(un.weekly_due("2026-09-29", "2026-10-06"))

    def test_window_start(self):
        self.assertEqual(un.window_start(None, "2026-10-06"), "2026-09-29")
        self.assertEqual(un.window_start("2026-09-26", "2026-10-06"), "2026-09-26")
        self.assertEqual(un.window_start("2026-01-01", "2026-10-06"), "2026-09-15")

    def test_stamp_roundtrip(self):
        html = "<div>\n    <div class=\"nd-synthesis\">x</div>\n</div>"
        self.assertIsNone(un.read_stamp(html, "synthesis-updated"))
        html = un.write_stamp(html, "synthesis-updated", "2026-10-06", '<div class="nd-synthesis">')
        self.assertEqual(un.read_stamp(html, "synthesis-updated"), "2026-10-06")
        self.assertIn('    <!-- news-bot:synthesis-updated 2026-10-06 -->\n    <div class="nd-synthesis">', html)
        html = un.write_stamp(html, "synthesis-updated", "2026-10-13", '<div class="nd-synthesis">')
        self.assertEqual(html.count("news-bot:synthesis-updated"), 1)
        self.assertEqual(un.read_stamp(html, "synthesis-updated"), "2026-10-13")


INDEX_FIXTURE = """<div class="nd-header">
      <div class="nd-badge-row">
        <span class="nd-badge">A</span>
      </div>
    </div>
    <div class="nd-synthesis">
      <h3>Where the Fight Stands</h3>
      <p>old</p>
    </div>
    <div class="nd-articles">
"""


class SynthesisTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.index = Path(self.tmp.name) / "index.html"
        self.index.write_text(INDEX_FIXTURE, encoding="utf-8")
        self.p = mock.patch.object(un, "INDEX_FILE", self.index)
        self.p.start()

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def reply(self):
        return json.dumps({
            "paragraphs": ["P1 " + "x" * 80 + r" C:\path", "P2 " + "y" * 80],
            "badges": [{"emoji": "⚖️", "label": "One"}, {"emoji": "✊", "label": "Two"},
                       {"emoji": "📜", "label": "Three"}],
        })

    def test_refreshes_and_stamps(self):
        news = card("Oct 1", "2026", "https://a.example/1") + card("Oct 2", "2026", "https://a.example/2")
        with mock.patch.object(un, "_complete", return_value=self.reply()) as c:
            self.assertTrue(un.update_synthesis(news, "2026-10-06"))
        self.assertIn("https://a.example/1", c.call_args.args[0])
        out = self.index.read_text(encoding="utf-8")
        self.assertIn(r"C:\path", out)  # backslashes survive (no regex-template mangling)
        self.assertIn('<span class="nd-badge">✊ Two</span>', out)
        self.assertEqual(un.read_stamp(out, un.SYNTHESIS_STAMP), "2026-10-06")
        self.assertIn('<div class="nd-articles">', out)

    def test_too_few_articles_skips_without_stamp(self):
        with mock.patch.object(un, "_complete") as c:
            self.assertFalse(un.update_synthesis(card("Jan 1", "2026", "https://a.example/1"), "2026-10-06"))
        c.assert_not_called()
        self.assertIsNone(un.read_stamp(self.index.read_text(encoding="utf-8"), un.SYNTHESIS_STAMP))

    def test_frozen_is_untouched(self):
        self.index.write_text(INDEX_FIXTURE + "<!-- news-bot:freeze-synthesis -->", encoding="utf-8")
        with mock.patch.object(un, "_complete") as c:
            self.assertFalse(un.update_synthesis(card("Oct 1", "2026", "https://a/1") * 2, "2026-10-06"))
        c.assert_not_called()

    def test_refreshes_real_index_and_keeps_its_headline(self):
        real = (ROOT / "index.html").read_text(encoding="utf-8")
        self.index.write_text(real, encoding="utf-8")
        # Fixed articles, so the test doesn't depend on the real page's synthesis stamp.
        arts = [{"date": "2026-10-08", "source": "S", "tag": "court", "headline": "H", "summary": "S",
                 "url": f"https://a.example/{i}"} for i in (1, 2)]
        with mock.patch.object(un, "_gather_weekly_articles", return_value=("2026-10-06", arts)), \
                mock.patch.object(un, "_complete", return_value=self.reply()):
            self.assertTrue(un.update_synthesis("", "2026-10-13"))
        out = self.index.read_text(encoding="utf-8")
        self.assertEqual(un.read_stamp(out, un.SYNTHESIS_STAMP), "2026-10-13")
        self.assertEqual(re.findall(r'<span class="nd-badge">([^<]+)</span>', out), ["⚖️ One", "✊ Two", "📜 Three"])
        self.assertIn("<p>P1 ", out)
        # The pop-up's standing headline (and everything above the badges) is not the bot's to change.
        head = real.split('<div class="nd-badge-row">')[0]
        self.assertRegex(head, r'<div class="nd-header[^"]*">\s*<h2>[^<]+</h2>')
        self.assertEqual(out.split('<div class="nd-badge-row">')[0], head)
        self.assertEqual(out.split('<div class="nd-articles">', 1)[1], real.split('<div class="nd-articles">', 1)[1])


TIMELINE_FIXTURE = """<script>{"dateModified":"2026-06-12"}</script>
<div class="timeline-container">
  <div class="timeline-center"></div>
  <div class="timeline-events">
    <!-- news-bot:timeline-updated 2026-09-20 -->

    <div class="timeline-event info" data-type="info" data-date="2026-09-30">
      <div class="event-content">
        <div class="event-title">Newest</div>
        <a href="https://www.cnn.com/existing" class="event-link">View details →</a>
      </div>
    </div>

    <div class="timeline-event legal" data-type="legal" data-date="2026-06-12">
      <div class="event-content">
        <div class="event-title">Older</div>
      </div>
    </div>

  </div>
</div>

<div class="sources">
<p>Last updated: <time class="tl-updated" datetime="2026-06-12">June 12, 2026</time>.</p>
"""


def dates(html: str) -> list[str]:
    return re.findall(r'class="timeline-event [^"]*"[^>]*data-date="([^"]+)"', html)


class _EventLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and "event-link" in (a.get("class") or "").split():
            self.hrefs.append(a.get("href") or "")


def event_link_hrefs(html: str) -> list[str]:
    """Every a.event-link href, whatever its attribute order."""
    parser = _EventLinks()
    parser.feed(html)
    return parser.hrefs


class TimelineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tl = Path(self.tmp.name) / "timeline.html"
        self.tl.write_text(TIMELINE_FIXTURE, encoding="utf-8")
        self.p = mock.patch.object(un, "TIMELINE_FILE", self.tl)
        self.p.start()
        self.news = (card("Oct 2", "2026", "https://a.example/new", headline="New ruling")
                     + card("Jul 1", "2026", "https://a.example/old", added="2026-10-01")
                     + card("Sep 30", "2026", "https://edition.cnn.com/existing"))

    def tearDown(self):
        self.p.stop()
        self.tmp.cleanup()

    def ev(self, **kw):
        base = {"date": "2026-10-02", "type": "legal", "title": "Court Rules on Signs",
                "description": "A federal court ruled on the sign removals this week.",
                "url": "https://a.example/new"}
        base.update(kw)
        return base

    def test_validate_rejects_bad_events(self):
        cands = {"https://a.example/new", "https://edition.cnn.com/existing"}
        existing = {un.canonical_url("https://www.cnn.com/existing")}
        raw = [
            self.ev(url="https://not-tracked.example/x"),
            self.ev(url="https://edition.cnn.com/existing"),  # already on timeline (mirror)
            self.ev(type="opinion"),
            self.ev(date="2026-12-31"),  # future
            self.ev(date="Oct 2"),
            self.ev(title="x" * 200),
            self.ev(title='<img src=x onerror=alert(1)>Ruling & Order'),
        ]
        got = un.validate_timeline_events(raw, cands, existing, "2026-10-06")
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["title"], "Ruling &amp; Order")
        self.assertNotIn("<", got[0]["title"])

    def test_validate_caps_and_dedupes(self):
        cands = {"https://a.example/new"}
        got = un.validate_timeline_events([self.ev()] * 5, cands, set(), "2026-10-06")
        self.assertEqual(len(got), 1)

    def test_insert_keeps_newest_first(self):
        html = TIMELINE_FIXTURE
        for d in ["2026-10-02", "2026-07-01", "2025-01-15", "2026-09-30"]:
            html = un.insert_timeline_event(html, self.ev(date=d, url=f"https://a/{d}"))
        self.assertEqual(dates(html), sorted(dates(html), reverse=True))
        self.assertEqual(len(dates(html)), 6)
        self.assertNotIn("</div>\n    <div class=\"timeline-event", html)  # blank line kept between events

    def test_update_timeline_adds_sourced_event(self):
        reply = json.dumps({"events": [self.ev(), self.ev(url="https://hallucinated.example")]})
        with mock.patch.object(un, "_complete", return_value=reply) as c:
            status = un.update_timeline(self.news, "2026-10-06")
        self.assertEqual(status, "added 1 event(s)")
        prompt = c.call_args.args[0]
        self.assertIn("https://a.example/new", prompt)
        self.assertIn("https://a.example/old", prompt)  # added recently though published in July
        self.assertNotIn("https://edition.cnn.com/existing", prompt)  # already on timeline
        out = self.tl.read_text(encoding="utf-8")
        self.assertEqual(dates(out), ["2026-10-02", "2026-09-30", "2026-06-12"])
        self.assertIn('data-added-by="news-bot"', out)
        self.assertNotIn("hallucinated", out)
        self.assertEqual(un.read_stamp(out, un.TIMELINE_STAMP), "2026-10-06")
        self.assertIn('"dateModified":"2026-10-06"', out)
        self.assertIn('<time class="tl-updated" datetime="2026-10-06">October 6, 2026</time>', out)

    def test_rejects_newly_reported_old_event(self):
        # Regression (Oct 6, 2026 run): a Sep 26, 2026 article about a Sep 2025
        # Acadia removal came back as a "Sep 30, 2025" event, duplicating an
        # older timeline entry the model was never shown.
        news = card("Sep 26", "2026", "https://themainemonitor.org/acadia", added="2026-10-01")
        old = self.ev(date="2025-09-30", type="removal", title="Climate Signs Removed From Acadia",
                      url="https://themainemonitor.org/acadia")
        with mock.patch.object(un, "_complete", return_value=json.dumps({"events": [old]})) as c:
            self.assertEqual(un.update_timeline(news, "2026-10-06"), "checked; no new milestones")
        prompt = c.call_args.args[0]
        self.assertIn("2026-06-12 Older", prompt)  # every existing event is shown, with its date
        # One article widens the window to 21 days (2026-09-15), minus the 14-day grace.
        self.assertIn("on or after 2026-09-01", prompt)
        self.assertNotIn("themainemonitor", self.tl.read_text(encoding="utf-8"))

    def test_grace_window_allows_slightly_older_events(self):
        got = un.validate_timeline_events([self.ev(date="2026-09-10")], {"https://a.example/new"}, set(),
                                          "2026-10-06", "2026-09-06")
        self.assertEqual(len(got), 1)

    def test_zero_events_still_stamps(self):
        with mock.patch.object(un, "_complete", return_value='{"events": []}'):
            self.assertEqual(un.update_timeline(self.news, "2026-10-06"), "checked; no new milestones")
        out = self.tl.read_text(encoding="utf-8")
        self.assertEqual(un.read_stamp(out, un.TIMELINE_STAMP), "2026-10-06")
        self.assertIn('"dateModified":"2026-06-12"', out)
        self.assertIn('<time class="tl-updated" datetime="2026-06-12">June 12, 2026</time>', out)

    def test_model_failure_does_not_stamp(self):
        with mock.patch.object(un, "_complete", return_value=None):
            self.assertEqual(un.update_timeline(self.news, "2026-10-06"), "skipped (model call failed)")
        self.assertEqual(un.read_stamp(self.tl.read_text(encoding="utf-8"), un.TIMELINE_STAMP), "2026-09-20")

    def test_frozen(self):
        self.tl.write_text(TIMELINE_FIXTURE + "<!-- news-bot:freeze-timeline -->", encoding="utf-8")
        with mock.patch.object(un, "_complete") as c:
            self.assertIn("frozen", un.update_timeline(self.news, "2026-10-06"))
        c.assert_not_called()


class DigestTest(unittest.TestCase):
    """The pop-up digest must keep updating with the newsletter signup block
    between the article list and the footer (it silently stopped on Oct 5)."""

    def test_updates_real_index_with_signup_block(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        index = Path(tmp.name) / "index.html"
        real = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('<div class="nd-sub">', real)
        index.write_text(real, encoding="utf-8")
        news = (ROOT / "news-and-press.html").read_text(encoding="utf-8")
        with mock.patch.object(un, "INDEX_FILE", index):
            un.update_news_digest(news, "2026-10-06")
        out = index.read_text(encoding="utf-8")
        latest = un._recent_articles_from_html(news, limit=5)
        self.assertIn(latest[0]["url"], out)
        rng = re.search(r'<div class="nd-daterange">([^<]+)</div>', out).group(1)
        self.assertTrue(rng.startswith(f'{latest[-1]["mon"]} {latest[-1]["day"]} &ndash; {latest[0]["mon"]} {latest[0]["day"]}'), rng)
        # Everything outside the article list is untouched.
        self.assertEqual(out.count('<div class="nd-sub">'), 1)
        self.assertEqual(out.count('<div class="nd-footer">'), 1)
        self.assertEqual(out.split('<div class="nd-sub">')[1], real.split('<div class="nd-sub">')[1])
        self.assertEqual(out.count('<div class="nd-article">'), 5)


class YearHeadingTest(unittest.TestCase):
    """A missing or unparseable year must never become a <h2>None</h2> heading.

    The page carried one from June to October 2026: resort_cards.py (run after
    every bot update) filed cards without data-month under year None."""

    def raw(self, **kw):
        base = {"date": "2026-10-05", "source_name": "Src", "source_key": "npr", "tag": "court",
                "tag_label": "Court Ruling", "url": "https://t.example/x", "headline": "H",
                "summary_html": "Summary."}
        base.update(kw)
        return base

    def test_parse_article_skips_unparseable_dates(self):
        for bad in (None, "", "None", "June 2026", "2026-1-5", "2026-13-01", "2026-02-30", 20261005):
            with self.subTest(date=bad), self.assertLogs(un.log, "WARNING"):
                self.assertIsNone(un.parse_article(self.raw(date=bad)))
        self.assertEqual(un.parse_article(self.raw()).year, "2026")

    def test_insert_card_refuses_a_non_year(self):
        html = '<section class="timeline-section">\n<div class="year-marker"><h2>2026</h2></div>\n</section>'
        for bad in (None, "None", "", "26", "2026-10"):
            with self.subTest(year=bad), self.assertRaises(ValueError):
                un.insert_card(html, card("Oct 5", "2026", "https://t.example/x"), bad)

    def test_unlisted_source_keys_are_filed_under_other(self):
        # A data-source with no #filterSource option can't be picked in the filter.
        html = ('<select class="filter-select" id="filterSource">\n'
                '<option value="all">All Publications</option><option value="npr">NPR</option>\n'
                '<option value="senate">U.S. Senate</option><option value="other">Other</option>\n</select>')
        arts = [un.parse_article(self.raw(source_key=k)) for k in ("npr", "senate", "calmatters", "all")]
        un.coerce_unlisted_sources(arts, html)
        self.assertEqual([a.source_key for a in arts], ["npr", "senate", "other", "other"])

    def test_resort_files_cards_without_data_month_by_their_visible_date(self):
        html = ('<section class="timeline-section">\n'
                '<div class="year-marker"><h2>2026</h2></div>\n' + card("Jan 20", "2026", "https://a/2026")
                + '<div class="year-marker"><h2>2025</h2></div>\n' + card("Jan 5", "2025", "https://a/2025")
                + '<div class="year-marker"><h2>None</h2></div>\n'
                + legacy_card("Apr 20", "2026", "https://a/legacy-2026")
                + legacy_card("Jul 01", "2025", "https://a/legacy-2025") + '</section>\n')
        out = rc.resort(html)
        self.assertEqual(year_headings(out), ["2026", "2025"])
        self.assertEqual(re.findall(r'href="([^"]+)"', out),
                         ["https://a/legacy-2026", "https://a/2026", "https://a/legacy-2025", "https://a/2025"])
        self.assertTrue(rc.is_sorted(out)[0])
        self.assertEqual(rc.resort(out), out)  # re-running is a no-op (it used to add a blank line)

    def test_resort_refuses_a_card_with_no_year(self):
        html = ('<section class="timeline-section">\n<div class="year-marker"><h2>2026</h2></div>\n'
                + card("Jan 20", "2026", "https://a/1") + legacy_card("Spring", "Undated", "https://a/2")
                + '</section>\n')
        with self.assertRaisesRegex(ValueError, "no year"):
            rc.resort(html)
        # The workflow step fails loudly and leaves the page untouched.
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "news-and-press.html"
            path.write_text(html, encoding="utf-8")
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "resort_cards.py"), str(path)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertIn("Legacy card", r.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), html)

    @unittest.skipUnless((ROOT / ".git").exists(), "needs git history")
    def test_resort_fixes_the_real_none_heading(self):
        # The live page on Aug 29, 2026 ended with 13 data-month-less cards
        # under <h2>None</h2>, out of date order.
        try:
            page = git_show("b846656", "news-and-press.html")
        except subprocess.CalledProcessError:
            self.skipTest("commit not in this clone")
        self.assertIn("<h2>None</h2>", page)
        out = rc.resort(page)
        self.assertEqual(year_headings(out), ["2026", "2025"])
        self.assertTrue(rc.is_sorted(out)[0])
        self.assertEqual(sorted(rc.CARD_RE.findall(out)), sorted(rc.CARD_RE.findall(page)))


class RealNewsPageTest(unittest.TestCase):
    """The committed news-and-press.html must stay writable by the daily bot."""

    def setUp(self):
        self.html = (ROOT / "news-and-press.html").read_text(encoding="utf-8")

    def test_updated_line_and_count_are_bot_editable(self):
        self.assertIsNotNone(un.banner_date(self.html))
        out = un.update_banner(self.html, "2031-01-02", 999)
        self.assertEqual(un.banner_date(out), "2031-01-02")
        self.assertIn('<time datetime="2031-01-02">January 2, 2031</time>', out)
        self.assertIn("999 articles tracked", out)

    def test_new_card_lands_at_top_of_its_year(self):
        a = un.Article(date="2026-12-31", source_name="Src", source_key="other", url="https://t.example/x",
                       headline="Headline", summary_html="Summary.", tag="court", tag_label="Court Ruling")
        out = un.insert_card(self.html, un.render_card(a, "2026-12-31"), "2026")
        first = out.index('<article class="article-card"')
        self.assertIn("https://t.example/x", out[first:first + 1000])
        self.assertEqual(un.article_count(out), un.article_count(self.html) + 1)


class RealTimelineTest(unittest.TestCase):
    """The committed timeline.html must be parseable by the bot."""

    def test_real_timeline_is_newest_first_and_insertable(self):
        html = (ROOT / "timeline.html").read_text(encoding="utf-8")
        ds = dates(html)
        self.assertGreater(len(ds), 40)
        self.assertEqual(ds, sorted(ds, reverse=True))
        self.assertIsNotNone(un.read_stamp(html, un.TIMELINE_STAMP))
        self.assertEqual(html.count('<time class="tl-updated" datetime="'), 1)
        bumped = un.mark_timeline_modified(html, "2031-01-02")
        self.assertIn('<time class="tl-updated" datetime="2031-01-02">January 2, 2031</time>', bumped)
        self.assertIn('"dateModified":"2031-01-02"', bumped)
        out = un.insert_timeline_event(html, {"date": "2026-08-15", "type": "info", "title": "Test Event",
                                              "description": "A test description sentence.", "url": "https://t/x"})
        self.assertEqual(dates(out), sorted(dates(out), reverse=True))
        self.assertEqual(len(dates(out)), len(ds) + 1)

    def test_weekly_job_never_re_adds_a_linked_story(self):
        """Every source already linked from an event (including a second link on
        the same event) must count as on the timeline, so the bot skips it."""
        html = (ROOT / "timeline.html").read_text(encoding="utf-8")
        urls = [h for h in event_link_hrefs(html) if h.startswith("http")]
        self.assertGreater(len(urls), 20)
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        tl = Path(tmp.name) / "timeline.html"
        tl.write_text(html, encoding="utf-8")
        p = mock.patch.object(un, "TIMELINE_FILE", tl)
        p.start()
        self.addCleanup(p.stop)

        def run(url):
            story = {"url": url, "date": "2026-10-07", "source": "S", "headline": "H", "summary": "S"}
            with mock.patch.object(un, "_gather_weekly_articles", return_value=("2026-10-06", [story])), \
                    mock.patch.object(un, "_complete", return_value=None) as c:
                return un.update_timeline("", "2026-10-13"), c.call_count

        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(run(url), ("skipped (no new tracked articles since 2026-10-06)", 0))
        # Control: a story that is not on the timeline yet does reach the model.
        self.assertEqual(run("https://new.example/story"), ("skipped (model call failed)", 1))
        self.assertEqual(tl.read_text(encoding="utf-8"), html)


if __name__ == "__main__":
    unittest.main()
