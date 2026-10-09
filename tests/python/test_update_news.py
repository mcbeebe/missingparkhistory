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
        # Keep the synthesis mirror away from the real status.html.
        self.p2 = mock.patch.object(un, "STATUS_FILE", Path(self.tmp.name) / "no-status.html")
        self.p2.start()

    def tearDown(self):
        self.p2.stop()
        self.p.stop()
        self.tmp.cleanup()

    def reply(self):
        return json.dumps({
            "paragraph": "P1 " + "x" * 80 + r" C:\path " + '<a href="https://a.example/1">first story</a>.',
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


    def _run(self, paragraph: str) -> bool:
        news = card("Oct 1", "2026", "https://a.example/1") + card("Oct 2", "2026", "https://a.example/2")
        reply = json.dumps({"paragraph": paragraph, "badges": [
            {"emoji": "⚖️", "label": "One"}, {"emoji": "✊", "label": "Two"}, {"emoji": "📜", "label": "Three"}]})
        with mock.patch.object(un, "_complete", return_value=reply):
            return un.update_synthesis(news, "2026-10-06")

    def test_writes_one_paragraph_with_tracked_links_only(self):
        self.assertTrue(self._run(
            "Interior blocked <strong>130</strong> projects, "
            '<a href="https://www.a.example/1/">records show</a>; a '
            '<a href="https://evil.example/x">made-up link</a> is unwrapped. ' + "word " * 40))
        out = self.index.read_text(encoding="utf-8")
        syn = out.split('<div class="nd-synthesis">')[1].split("</div>")[0]
        self.assertEqual(syn.count("<p>"), 1)
        self.assertIn('<a href="https://a.example/1" target="_blank" rel="noopener">records show</a>', syn)
        self.assertNotIn("evil.example", syn)
        self.assertIn("made-up link", syn)
        self.assertIn("<strong>130</strong>", syn)

    def test_rejects_summary_that_is_too_long(self):
        long = '<a href="https://a.example/1">x</a> ' + "word " * (un.SYNTHESIS_HARD_MAX_WORDS + 5)
        self.assertFalse(self._run(long))
        self.assertIn("<p>old</p>", self.index.read_text(encoding="utf-8"))

    def test_rejects_summary_without_a_tracked_link(self):
        self.assertFalse(self._run('<a href="https://other.example/">x</a> ' + "word " * 60))
        self.assertIn("<p>old</p>", self.index.read_text(encoding="utf-8"))

    def test_prompt_asks_for_short_linked_paragraph(self):
        self.assertIn("ONE paragraph", un.SYNTHESIS_PROMPT)
        self.assertIn("<a href", un.SYNTHESIS_PROMPT)
        self.assertNotIn("TWO paragraphs", un.SYNTHESIS_PROMPT)


class SanitizeSynthesisTest(unittest.TestCase):
    URLS = ["https://news.example/story"]

    def clean(self, html: str) -> tuple[str, int]:
        return un.sanitize_synthesis_html(html, self.URLS)

    def test_keeps_allowed_link_and_canonicalizes(self):
        out, n = self.clean('See <a href="https://www.news.example/story/?utm=1">this</a>.')
        self.assertEqual(out, 'See <a href="https://news.example/story" target="_blank" rel="noopener">this</a>.')
        self.assertEqual(n, 1)

    def test_strips_disallowed_tags_and_attributes(self):
        out, n = self.clean('<p onclick="x"><script>alert(1)</script><strong class="c">A</strong> <em>B</em></p>')
        self.assertEqual(out, "alert(1)<strong>A</strong> <em>B</em>")
        self.assertEqual(n, 0)

    def test_unknown_and_javascript_links_are_unwrapped(self):
        out, n = self.clean('<a href="javascript:alert(1)">x</a> <a href="https://bad.example">y</a>')
        self.assertEqual(out, "x y")
        self.assertEqual(n, 0)

    def test_nested_and_unclosed_links(self):
        out, n = self.clean('<a href="https://news.example/story">a <a href="https://news.example/story">b</a> c')
        self.assertEqual(out.count("<a "), 1)
        self.assertEqual(out.count("</a>"), 1)
        self.assertEqual(n, 1)

    def test_entities_and_stray_brackets(self):
        out, _ = self.clean("Congress&rsquo;s 2% cut &mdash; 3 < 4")
        self.assertEqual(out, "Congress&rsquo;s 2% cut &mdash; 3 &lt; 4")

    def test_real_page_summary_is_short_and_linked(self):
        real = (ROOT / "index.html").read_text(encoding="utf-8")
        syn = real.split('<div class="nd-synthesis">')[1].split("</div>")[0]
        paras = re.findall(r"<p>(.*?)</p>", syn, re.DOTALL)
        self.assertEqual(len(paras), 1)
        self.assertLessEqual(un._word_count(paras[0]), un.SYNTHESIS_HARD_MAX_WORDS)
        hrefs = re.findall(r'<a href="([^"]+)"', paras[0])
        self.assertGreaterEqual(len(hrefs), 2)
        news = (ROOT / "news-and-press.html").read_text(encoding="utf-8")
        tracked = {un.canonical_url(u) for u in re.findall(r'href="(https?://[^"]+)"', news)}
        for h in hrefs:
            self.assertIn(un.canonical_url(h), tracked, h)
        status = (ROOT / "status.html").read_text(encoding="utf-8")
        self.assertIn(paras[0], status)  # the status page mirrors the same text


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


# ---------------------------------------------------------------------------
# Status page (status.html): synthesis mirror + weekly lanes/case board
# ---------------------------------------------------------------------------

def _lane(lid: str, trend: str, text: str) -> str:
    return (
        f'    <div class="lane" data-lane="{lid}" data-trend="{trend}">\n'
        f'      <div><div class="name">{lid}<small>x</small></div><span class="trend {trend}"><i></i>{trend}</span></div>\n'
        f'      <div class="latest"><b>Latest &middot; Sep 1, 2026</b>{text}</div>\n'
        f'      <div class="nextbox"><b>Next to watch</b>next {lid}</div>\n'
        f'    </div>\n'
    )


def _case(cid: str, status: str, text: str) -> str:
    return (
        f'    <div class="case" data-case="{cid}" data-status="{status}">\n'
        f'      <div><h3>{cid}</h3><div class="court">c</div></div>\n'
        f'      <span class="pill {status}">{status}</span>\n'
        f'      <div class="what">{text}</div>\n'
        f'    </div>\n'
    )


STATUS_FIXTURE = (
    '<script type="application/ld+json">{"dateModified":"2026-10-06"}</script>\n'
    '<time id="statusUpdated" datetime="2026-10-06">Oct 6, 2026</time>\n'
    '<!-- news-bot:status-updated 2026-10-06 -->\n'
    '<div class="section-heading">The four fronts</div>\n'
    '<div class="lanes">\n    <!-- status-bot:lanes-start -->\n'
    + "".join(_lane(k, "holding", f"old {k} text") for k in ("courts", "congress", "agency", "parks"))
    + '    <!-- status-bot:lanes-end -->\n</div>\n'
    '<div class="case-board">\n    <!-- status-bot:cases-start -->\n'
    + "".join(_case(k, "ongoing", f"old {k} text") for k in ("stonewall", "npca", "philadelphia", "sierra", "peer"))
    + '    <!-- status-bot:cases-end -->\n</div>\n'
    '<div class="nd-synthesis">\n  <h3>Where the Fight Stands</h3>\n  <p>OLD ONE</p>\n  <p>OLD TWO</p>\n</div>\n'
    '<!-- status-bot:synthesis-end -->\n'
    '<p class="prose">tail</p>\n'
)


class StatusBoardTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.status = Path(self.tmp.name) / "status.html"
        self.status.write_text(STATUS_FIXTURE, encoding="utf-8")
        self.index = Path(self.tmp.name) / "index.html"
        self.index.write_text(INDEX_FIXTURE, encoding="utf-8")
        self.patches = [mock.patch.object(un, "STATUS_FILE", self.status),
                        mock.patch.object(un, "INDEX_FILE", self.index)]
        for p in self.patches:
            p.start()
        self.urls = {"https://a.example/1", "https://a.example/2"}

    def tearDown(self):
        for p in self.patches:
            p.stop()
        self.tmp.cleanup()

    def news(self):
        return card("Oct 1", "2026", "https://a.example/1") + card("Oct 2", "2026", "https://a.example/2")

    def test_validate_keeps_only_cited_changed_entries(self):
        long = "A development long enough to be a real update of the lane text."
        raw = {
            "lanes": [
                {"id": "courts", "changed": False},
                {"id": "congress", "changed": True, "trend": "worsening", "latest_date": "2026-10-02",
                 "latest": long, "next": "Watch the bill.", "url": "https://a.example/1"},
                {"id": "agency", "changed": True, "trend": "worsening", "latest_date": "2026-10-02",
                 "latest": long, "next": "Watch.", "url": "https://evil.example/x"},      # untracked url
                {"id": "parks", "changed": True, "trend": "sideways", "latest_date": "2026-10-02",
                 "latest": long, "next": "Watch this.", "url": "https://a.example/2"},    # bad trend
                {"id": "weather", "changed": True, "trend": "mixed", "latest_date": "2026-10-02",
                 "latest": long, "next": "Watch this.", "url": "https://a.example/2"},    # unknown lane
            ],
            "cases": [
                {"id": "npca", "changed": True, "status": "paused", "update": long + " <b>x</b>",
                 "next": "", "url": "https://a.example/2"},
                {"id": "peer", "changed": True, "status": "won", "update": "short",
                 "next": "", "url": "https://a.example/2"},                               # too short
                {"id": "philadelphia", "changed": True, "status": "reversed", "update": long,
                 "next": "", "url": "https://a.example/2", "latest_date": "2027-01-01"},
            ],
        }
        lanes, cases = un.validate_status_board(raw, self.urls, "2026-10-06")
        self.assertEqual(sorted(lanes), ["congress"])
        self.assertEqual(sorted(cases), ["npca", "philadelphia"])
        self.assertNotIn("<b>", cases["npca"]["update"])  # model HTML is stripped

    def test_validate_rejects_future_dates_and_non_dicts(self):
        self.assertEqual(un.validate_status_board(["nope"], self.urls, "2026-10-06"), ({}, {}))
        raw = {"lanes": [{"id": "courts", "changed": True, "trend": "mixed", "latest_date": "2026-12-01",
                          "latest": "x" * 60, "next": "Watch the court.", "url": "https://a.example/1"}]}
        self.assertEqual(un.validate_status_board(raw, self.urls, "2026-10-06")[0], {})

    def test_update_rewrites_changed_blocks_only_and_stamps(self):
        reply = json.dumps({
            "lanes": [{"id": "courts", "changed": False}, {"id": "congress", "changed": False},
                      {"id": "agency", "changed": True, "trend": "worsening", "latest_date": "2026-10-02",
                       "latest": "Interior blocked 130 partner projects, records show on October 2.",
                       "next": "Whether the projects are reinstated.", "url": "https://a.example/1"},
                      {"id": "parks", "changed": False}],
            "cases": [{"id": "npca", "changed": True, "status": "paused",
                       "update": "The First Circuit kept its stay in place while briefing continues this month.",
                       "next": "A merits decision.", "url": "https://a.example/2"}],
        })
        with mock.patch.object(un, "_complete", return_value=reply) as c:
            self.assertTrue(un.update_status_board(self.news(), "2026-10-13"))
        prompt = c.call_args.args[0]
        self.assertIn("old courts text", prompt)
        self.assertIn("https://a.example/2", prompt)
        out = self.status.read_text(encoding="utf-8")
        # Changed blocks are rendered from the model's data...
        self.assertIn('data-lane="agency" data-trend="worsening"', out)
        self.assertIn("Latest &middot; Oct 2, 2026</b>Interior blocked 130", out)
        self.assertIn('<a class="src" href="https://a.example/1"', out)
        self.assertIn('data-case="npca" data-status="paused"', out)
        self.assertIn('<span class="pill paused">Injunction paused</span>', out)
        self.assertIn('<div class="next"><b>Next:</b> A merits decision.</div>', out)
        # ...unchanged blocks keep their HTML verbatim, in place.
        for k in ("courts", "congress", "parks"):
            self.assertIn(f"old {k} text", out)
        for k in ("stonewall", "philadelphia", "sierra", "peer"):
            self.assertIn(f"old {k} text", out)
        self.assertEqual(len(re.findall(r'<div class="lane" ', out)), 4)
        self.assertEqual(len(re.findall(r'<div class="case" ', out)), 5)
        # Date, JSON-LD and stamp move to today; markers survive for next time.
        self.assertIn('<time id="statusUpdated" datetime="2026-10-13">Oct 13, 2026</time>', out)
        self.assertIn('"dateModified":"2026-10-13"', out)
        self.assertEqual(un.read_stamp(out, un.STATUS_STAMP), "2026-10-13")
        for marker in ("lanes-start", "lanes-end", "cases-start", "cases-end", "synthesis-end"):
            self.assertIn(f"status-bot:{marker}", out)
        self.assertIn("<p>OLD ONE</p>", out)  # the board job never touches the synthesis

    def test_no_changes_still_bumps_date_and_stamp(self):
        reply = json.dumps({"lanes": [{"id": k, "changed": False} for k in un.STATUS_LANES],
                            "cases": [{"id": k, "changed": False} for k in un.STATUS_CASES]})
        with mock.patch.object(un, "_complete", return_value=reply):
            self.assertTrue(un.update_status_board(self.news(), "2026-10-13"))
        out = self.status.read_text(encoding="utf-8")
        self.assertEqual(un.read_stamp(out, un.STATUS_STAMP), "2026-10-13")
        self.assertIn('datetime="2026-10-13"', out)
        self.assertEqual(out.count("old "), STATUS_FIXTURE.count("old "))

    def test_too_few_articles_or_model_failure_leaves_page_alone(self):
        with mock.patch.object(un, "_complete") as c:
            self.assertFalse(un.update_status_board(card("Jan 1", "2026", "https://a.example/1"), "2026-10-13"))
        c.assert_not_called()
        with mock.patch.object(un, "_complete", return_value=None):
            self.assertFalse(un.update_status_board(self.news(), "2026-10-13"))
        self.assertEqual(self.status.read_text(encoding="utf-8"), STATUS_FIXTURE)

    def test_frozen(self):
        self.status.write_text(STATUS_FIXTURE + "<!-- news-bot:freeze-status -->", encoding="utf-8")
        with mock.patch.object(un, "_complete") as c:
            self.assertFalse(un.update_status_board(self.news(), "2026-10-13"))
        c.assert_not_called()

    def test_synthesis_is_mirrored_to_status_page(self):
        reply = json.dumps({
            "paragraph": "NEW ONE " + "x" * 60 + ' <a href="https://a.example/2">second</a>',
            "badges": [{"emoji": "⚖️", "label": "A"}, {"emoji": "✊", "label": "B"}, {"emoji": "📜", "label": "C"}],
        })
        with mock.patch.object(un, "_complete", return_value=reply):
            self.assertTrue(un.update_synthesis(self.news(), "2026-10-13"))
        out = self.status.read_text(encoding="utf-8")
        self.assertIn("<p>NEW ONE ", out)
        self.assertNotIn("OLD ONE", out)
        self.assertIn("<!-- status-bot:synthesis-end -->", out)
        self.assertIn('<p class="prose">tail</p>', out)
        self.assertIn("old courts text", out)  # lanes untouched by the synthesis job

    def test_real_status_page_has_the_markers_the_bot_needs(self):
        real = (ROOT / "status.html").read_text(encoding="utf-8")
        self.assertIsNotNone(un._status_region(real, "lanes"))
        self.assertIsNotNone(un._status_region(real, "cases"))
        a, b = un._status_region(real, "lanes")
        self.assertEqual(set(un._status_blocks(real[a:b], "lane")), set(un.STATUS_LANES))
        a, b = un._status_region(real, "cases")
        self.assertEqual(set(un._status_blocks(real[a:b], "case")), set(un.STATUS_CASES))
        self.assertRegex(real, un._STATUS_SYNTH_RE)
        self.assertRegex(real, un._STATUS_TIME_RE)
        self.assertIsNotNone(un.read_stamp(real, un.STATUS_STAMP))
