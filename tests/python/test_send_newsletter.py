"""Weekly Watch issue building: which cards count as this week, the size cap,
and the fallback one-sentence summaries.

Run: python -m unittest discover -s tests/python
"""
import sys
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace as NS

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import send_newsletter as sn  # noqa: E402


def card_html(pub: date, headline: str, added: str | None = None, summary: str = "A summary.") -> str:
    attr = f' data-added="{added}"' if added else ""
    return (
        f'<article class="article-card" data-month="{pub:%Y-%m}" data-source="other"{attr}>\n'
        f'  <div class="article-date"><div class="month-day">{pub:%b} {pub.day}</div>'
        f'<div class="date-detail">{pub.year}</div></div>\n'
        f'  <div class="article-meta"><span class="article-source">Source</span></div>\n'
        f'  <h3><a href="https://example.org/{pub:%Y%m%d}" target="_blank">{headline}</a></h3>\n'
        f'  <p class="article-summary">{summary}</p>\n'
        f'</article>\n'
    )


START, END = date(2026, 10, 6), date(2026, 10, 12)


class CardsThisWeekTest(unittest.TestCase):
    def headlines(self, html):
        return [c.headline for c in sn.cards_this_week(html, START, END)]

    def test_card_added_this_week_and_published_recently_counts(self):
        self.assertEqual(self.headlines(card_html(date(2026, 10, 1), "Recent", "2026-10-07")), ["Recent"])

    def test_backfilled_old_card_is_skipped(self):
        # The Oct 7 bulk port stamped cards from 2025 with data-added=2026-10-07.
        html = card_html(date(2025, 6, 18), "Old", "2026-10-07") + card_html(date(2026, 9, 2), "Sept 2", "2026-10-07")
        self.assertEqual(self.headlines(html), [])

    def test_pub_age_boundary(self):
        edge = date(2026, 9, 22)  # START - 14 days
        html = card_html(edge, "Edge", "2026-10-07") + card_html(date(2026, 9, 21), "Too old", "2026-10-07")
        self.assertEqual(self.headlines(html), ["Edge"])

    def test_card_added_outside_window_is_skipped(self):
        self.assertEqual(self.headlines(card_html(date(2026, 10, 1), "Last week", "2026-10-05")), [])

    def test_unstamped_card_uses_publish_date(self):
        html = card_html(date(2026, 10, 8), "In window") + card_html(date(2026, 10, 2), "Before window")
        self.assertEqual(self.headlines(html), ["In window"])

    def test_sorted_newest_first(self):
        html = (card_html(date(2026, 9, 30), "B", "2026-10-07") + card_html(date(2026, 10, 9), "A")
                + card_html(date(2026, 9, 26), "C", "2026-10-07"))
        self.assertEqual(self.headlines(html), ["A", "B", "C"])

    def test_live_page_has_no_backfill_in_issue(self):
        html = (ROOT / "news-and-press.html").read_text(encoding="utf-8")
        for c in sn.cards_this_week(html, START, END):
            self.assertGreaterEqual(c.date, date(2026, 9, 22), c.headline)


GOOD_JSON = '{"brief_html": "A <strong>busy</strong> week.", "take_action_html": "Call.", "summaries": ["One."]}'


def reply(stop="end_turn", text=None, thinking=True, out=100, category=None):
    """A fake Messages API response shaped like the SDK's."""
    content = [NS(type="thinking", thinking="")] if thinking else []
    if text is not None:
        content.append(NS(type="text", text=text))
    return NS(stop_reason=stop, usage=NS(output_tokens=out), content=content,
              stop_details=NS(category=category) if stop == "refusal" else None)


class NotFound(Exception):
    pass


class FakeClient:
    def __init__(self, replies, missing_models=()):
        self.replies, self.missing, self.calls = list(replies), set(missing_models), []
        self.messages = self

    def create(self, **kw):
        self.calls.append(kw)
        if kw["model"] in self.missing:
            raise NotFound(kw["model"])
        return self.replies.pop(0)


class ParseCopyReplyTest(unittest.TestCase):
    def test_thinking_only_reply_that_hit_the_limit_is_rejected_not_crashed(self):
        # What the 2026-10-13 send got: the budget went to thinking, no text block.
        with self.assertLogs("newsletter", "ERROR") as logs:
            self.assertIsNone(sn.parse_copy_reply(reply("max_tokens", text=None, out=1500)))
        self.assertIn("no text", "\n".join(logs.output))

    def test_good_reply(self):
        self.assertEqual(sn.parse_copy_reply(reply(text=GOOD_JSON))["take_action_html"], "Call.")

    def test_fenced_json_with_prose(self):
        self.assertIsNotNone(sn.parse_copy_reply(reply(text="Here it is:\n```json\n" + GOOD_JSON + "\n```")))

    def test_refusal(self):
        with self.assertLogs("newsletter", "ERROR") as logs:
            self.assertIsNone(sn.parse_copy_reply(reply("refusal", text="", category="general_harms")))
        self.assertIn("general_harms", "\n".join(logs.output))

    def test_missing_required_field(self):
        with self.assertLogs("newsletter", "ERROR"):
            self.assertIsNone(sn.parse_copy_reply(reply(text='{"brief_html": "x", "summaries": []}')))

    def test_prose_without_json(self):
        self.assertIsNone(sn.parse_copy_reply(reply(text="Sorry, I can't format that.")))


class RequestCopyTest(unittest.TestCase):
    def test_retries_after_empty_reply(self):
        client = FakeClient([reply("max_tokens", out=1500), reply(text=GOOD_JSON)])
        data = sn.request_copy(client, "p", ["m1"], NotFound)
        self.assertEqual(data["brief_html"], "A <strong>busy</strong> week.")
        self.assertEqual(len(client.calls), 2)

    def test_uses_raised_token_limit(self):
        client = FakeClient([reply(text=GOOD_JSON)])
        sn.request_copy(client, "p", ["m1"], NotFound)
        self.assertGreaterEqual(client.calls[0]["max_tokens"], 16000)

    def test_falls_back_to_next_model_when_first_is_missing(self):
        client = FakeClient([reply(text=GOOD_JSON)], missing_models={"m1"})
        sn.request_copy(client, "p", ["m1", "m2"], NotFound)
        self.assertEqual([c["model"] for c in client.calls], ["m1", "m2"])

    def test_gives_up_after_all_attempts(self):
        client = FakeClient([reply("max_tokens"), reply("max_tokens")])
        with self.assertRaisesRegex(RuntimeError, "No usable copy"):
            sn.request_copy(client, "p", ["m1"], NotFound, attempts=2)

    def test_no_model_available(self):
        with self.assertRaisesRegex(RuntimeError, "No available model"):
            sn.request_copy(FakeClient([], missing_models={"m1"}), "p", ["m1"], NotFound)


class LastFullWeekTest(unittest.TestCase):
    def test_every_weekday_maps_to_previous_monday_sunday(self):
        # Mon Oct 12 .. Sun Oct 18, 2026 all map to Mon Oct 5 - Sun Oct 11.
        for day in range(12, 19):
            self.assertEqual(sn.last_full_week(date(2026, 10, day)), (date(2026, 10, 5), date(2026, 10, 11)), day)
        self.assertEqual(sn.last_full_week(date(2026, 10, 19)), (date(2026, 10, 12), date(2026, 10, 18)))

    def test_window_is_monday_to_sunday(self):
        start, end = sn.last_full_week(date(2026, 12, 29))
        self.assertEqual((start.weekday(), end.weekday(), (end - start).days), (0, 6, 6))

    def test_across_year_end(self):
        self.assertEqual(sn.last_full_week(date(2027, 1, 4)), (date(2026, 12, 28), date(2027, 1, 3)))

    def test_consecutive_weeks_do_not_overlap_or_gap(self):
        a = sn.last_full_week(date(2026, 10, 12))
        b = sn.last_full_week(date(2026, 10, 19))
        self.assertEqual((b[0] - a[1]).days, 1)

    def test_send_days_are_monday_and_tuesday(self):
        self.assertEqual(sn.SEND_WEEKDAYS, (0, 1))


class CapArticlesTest(unittest.TestCase):
    def test_cap(self):
        cards = list(range(20))
        self.assertEqual(sn.cap_articles(cards, 15), (list(range(15)), 5))
        self.assertEqual(sn.cap_articles(cards[:3], 15), ([0, 1, 2], 0))
        self.assertEqual(sn.cap_articles([], 15), ([], 0))

    def test_default_limit(self):
        self.assertEqual(len(sn.cap_articles(list(range(100)))[0]), sn.MAX_ARTICLES)


class FirstSentenceTest(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(sn.first_sentence("One thing happened. Then another."), "One thing happened.")

    def test_month_abbreviation(self):
        self.assertEqual(sn.first_sentence("Tracked since Sept. 26 by this site. More here."),
                         "Tracked since Sept. 26 by this site.")

    def test_title_abbreviation_and_initial(self):
        self.assertEqual(sn.first_sentence("Rep. Smith, Reps. Lee and John F. Kennedy agreed. Next."),
                         "Rep. Smith, Reps. Lee and John F. Kennedy agreed.")

    def test_us_and_decimals(self):
        self.assertEqual(sn.first_sentence("The U.S. Park Service lost $1.7 million. Next."),
                         "The U.S. Park Service lost $1.7 million.")

    def test_possessive_is_not_an_initial(self):
        self.assertEqual(sn.first_sentence("Sites coincided with MLB\u2019s. Wyoming objected."),
                         "Sites coincided with MLB\u2019s.")

    def test_abbreviation_after_parenthesis(self):
        self.assertEqual(sn.first_sentence("He published them (Sept. 21, 2026) in full. Next."),
                         "He published them (Sept. 21, 2026) in full.")

    def test_quote_after_period(self):
        self.assertEqual(sn.first_sentence('He called it "censorship." Others disagreed.'),
                         'He called it "censorship."')

    def test_question_mark_kept(self):
        self.assertEqual(sn.first_sentence("What changed? A lot."), "What changed?")
        self.assertEqual(sn.first_sentence("What changed?"), "What changed?")

    def test_single_sentence_without_period_gets_one(self):
        self.assertEqual(sn.first_sentence("No period here"), "No period here.")

    def test_empty(self):
        self.assertEqual(sn.first_sentence("   "), "")


class BuildIssueTest(unittest.TestCase):
    def setUp(self):
        self.cards = [sn.Card("Src", date(2026, 10, 1), f"Headline {i}", f"https://e.org/{i}", "S.")
                      for i in range(3)]
        self.copy = {"brief_html": "Brief.", "take_action_html": "Act.", "summaries": ["S."] * 3}

    def test_no_more_line_when_not_capped(self):
        body = sn.build_issue(self.cards, self.copy, "Oct 6 &ndash; Oct 12, 2026")
        self.assertNotIn("see all coverage", body)
        self.assertEqual(body.count("Read at Src"), 3)
        self.assertNotRegex(body, r"\{\{\w+\}\}")

    def test_more_line_when_capped(self):
        body = sn.build_issue(self.cards, self.copy, "w", more=4)
        self.assertIn("Plus 4 more stories this week", body)
        self.assertIn(sn.NEWS_URL, body)
        self.assertIn("Plus 1 more story", sn.build_issue(self.cards, self.copy, "w", more=1))

    def test_capped_issue_fits_under_gmail_clip_limit(self):
        cards = [sn.Card("A Fairly Long Source Name / Partner", date(2026, 10, 1), "H" * 120,
                         f"https://example.org/a/long/path/{i}", "") for i in range(sn.MAX_ARTICLES)]
        copy = {"brief_html": "B" * 600, "take_action_html": "T" * 300, "summaries": ["S" * 400] * sn.MAX_ARTICLES}
        body = sn.build_issue(cards, copy, "w", more=90)
        self.assertLess(len(body.encode("utf-8")), 100_000)


if __name__ == "__main__":
    unittest.main()
