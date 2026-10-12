#!/usr/bin/env python3
"""
Weekly Watch newsletter → Buttondown subscribers.

Builds the week's issue from the live repo content (news cards added in the last
7 days + the homepage "Where the Fight Stands" synthesis), writes the brief and
take-action line with Claude, fills email/weekly-watch-template.html, and sends
it through the Buttondown API.

Modes:
  preview  Build the issue and write newsletter-preview.html. No Buttondown call.
  draft    Also create it as a Buttondown draft (review and send it yourself).
  send     Also send it to all subscribers.

Environment:
  ANTHROPIC_API_KEY   Writes the brief/take-action. Without it, preview mode
                      falls back to placeholder text; draft/send refuse to run.
  BUTTONDOWN_API_KEY  Required for draft/send.

Usage:
  python scripts/send_newsletter.py --mode preview
  python scripts/send_newsletter.py --mode send --scheduled

Each issue covers the previous full Monday–Sunday week, so every card lands in
exactly one issue however late GitHub starts the run.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
NEWS_FILE = REPO_ROOT / "news-and-press.html"
INDEX_FILE = REPO_ROOT / "index.html"
TEMPLATE_FILE = REPO_ROOT / "email" / "weekly-watch-template.html"
PREVIEW_FILE = REPO_ROOT / "newsletter-preview.html"

PT = ZoneInfo("America/Los_Angeles")
BUTTONDOWN_API = "https://api.buttondown.com/v1/emails"
LOGO_URL = "https://missingparkhistory.org/email-logo.png"
# A card counts as this week's news only if it was also published recently: bulk
# imports stamp old cards with today's data-added, and those must not flood an issue.
MAX_PUB_AGE_DAYS = 14
# Keeps the email under Gmail's ~102 KB clipping limit (each item is ~1 KB of HTML).
MAX_ARTICLES = 15
NEWS_URL = "https://missingparkhistory.org/news-and-press.html"
MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger("newsletter")


@dataclass
class Card:
    source: str
    date: date
    headline: str
    url: str
    summary: str  # plain text


# ---------------------------------------------------------------------------
# Content
# ---------------------------------------------------------------------------

def _text(fragment: str) -> str:
    """Strip tags and decode entities into plain text."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def cards_this_week(news_html: str, start: date, end: date) -> list[Card]:
    """Cards added in [start, end], newest first. Uses data-added when present (the
    bot stamps new cards), otherwise the article's displayed date. A stamped card
    published more than MAX_PUB_AGE_DAYS before `start` is skipped as a backfill."""
    oldest_pub = start - timedelta(days=MAX_PUB_AGE_DAYS)
    out = []
    for c in re.findall(r'<article class="article-card"[^>]*>.*?</article>', news_html, re.S):
        md = re.search(r'<div class="month-day">([^<]+)</div>', c)
        yr = re.search(r'<div class="date-detail">\s*(\d{4})', c)
        src = re.search(r'<span class="article-source">([^<]+)</span>', c)
        link = re.search(r'<h3[^>]*>\s*<a href="([^"]+)"[^>]*>(.*?)</a>', c, re.S)
        summ = re.search(r'<p class="article-summary">(.*?)</p>', c, re.S)
        if not (md and yr and src and link):
            continue
        tok = md.group(1).split()
        if len(tok) < 2 or tok[0][:3] not in MONTHS or not tok[1].isdigit():
            continue
        pub = date(int(yr.group(1)), MONTHS[tok[0][:3]], int(tok[1]))
        added = re.search(r'data-added="(\d{4}-\d{2}-\d{2})"', c)
        when = date.fromisoformat(added.group(1)) if added else pub
        if start <= when <= end and pub >= oldest_pub:
            out.append(Card(_text(src.group(1)), pub, _text(link.group(2)),
                            link.group(1).strip(), _text(summ.group(1)) if summ else ""))
    out.sort(key=lambda k: k.date, reverse=True)
    return out


# Words whose trailing period doesn't end a sentence ("since Sept. 26", "Rep. Smith").
_ABBREVIATIONS = {
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    "mr", "mrs", "ms", "dr", "st", "mt", "ft", "rep", "reps", "sen", "sens", "gov", "govs",
    "gen", "lt", "col", "sgt", "capt", "jr", "sr", "vs", "etc", "inc", "co", "corp", "dept", "u.s", "d.c",
}


def first_sentence(text: str) -> str:
    """First sentence of `text`, ending in a period. Ignores periods after common
    abbreviations and single initials, so "since Sept. 26" isn't cut short."""
    text = text.strip()
    for m in re.finditer(r'[.!?][\"\u201d\u2019)]*(?=\s+[A-Z0-9\"\u201c\u2018(])', text):
        word = re.search(r"(?:^|[\s(\[\"\u201c\u2018])([\w.]+)$", text[:m.start()])  # whole word, so "MLB’s." still ends
        token = word.group(1).lower() if word else ""
        if text[m.start()] == "." and (token in _ABBREVIATIONS or (len(token) == 1 and token.isalpha())):
            continue
        return text[:m.end()].strip()
    if not text or re.search(r'[.!?][\"\u201d\u2019)]*$', text):
        return text
    return text + "."


def cap_articles(cards: list[Card], limit: int = MAX_ARTICLES) -> tuple[list[Card], int]:
    """Keep the first `limit` cards (newest first); return them and how many were dropped."""
    return cards[:limit], max(0, len(cards) - limit)


def synthesis_text(index_html: str) -> str:
    m = re.search(r'<div class="nd-synthesis">(.*?)</div>\s*\n\s*<div class="nd-articles">', index_html, re.S)
    return _text(m.group(1)) if m else ""


# ---------------------------------------------------------------------------
# Claude: brief, take-action, one-line summaries
# ---------------------------------------------------------------------------

WRITE_PROMPT = """You write the weekly "Weekly Watch" newsletter for MissingParkHistory.org,
which tracks censorship of history and science at U.S. national parks (Executive
Order 14253, Secretary's Order 3431) and the fight against it.

Week: {window}

Background — the site's current "Where the Fight Stands" summary:
---
{synthesis}
---

This week's new articles (most recent first):
{articles}

Return ONLY JSON, first character `{{`:
{{
  "brief_html": "2-3 sentences: the week's throughline, specific names/numbers wrapped in <strong>. If there are no articles, say it was a quiet week and summarize where the fight stands from the background.",
  "take_action_html": "ONE sentence: a concrete, current ask grounded in this week's news or the background (e.g. urge representatives to oppose Secretary's Order 3431). <strong> allowed. Never invent bills, deadlines, or numbers.",
  "summaries": ["one paraphrased sentence per article, same order as the list above"]
}}

Rules: paraphrase, never quote; use only facts present above; no other HTML tags."""


def _safe_inline(s: str) -> str:
    """Escape everything, then re-allow plain <strong>/<em>."""
    s = html.escape(html.unescape(s), quote=False)
    return re.sub(r"&lt;(/?)(strong|em)&gt;", r"<\1\2>", s)


def write_copy(cards: list[Card], synthesis: str, window: str) -> dict:
    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.warning("ANTHROPIC_API_KEY not set; using placeholder copy (preview only)")
        return {
            "brief_html": "[Preview without ANTHROPIC_API_KEY: the weekly brief is written here.]",
            "take_action_html": "Urge your representatives to <strong>oppose Secretary&rsquo;s Order 3431</strong>.",
            "summaries": [first_sentence(c.summary) for c in cards],
        }
    import anthropic  # only needed when actually writing copy
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from update_news import MODEL_CANDIDATES  # one model list for both bots

    listing = "\n".join(
        f"{i}. [{c.date:%b %-d}] {c.source} — {c.headline}\n   {c.summary[:600]}"
        for i, c in enumerate(cards, 1)) or "(none this week)"
    prompt = WRITE_PROMPT.format(window=window, synthesis=synthesis or "(unavailable)", articles=listing)
    client = anthropic.Anthropic()
    last = None
    for model in MODEL_CANDIDATES:
        try:
            resp = client.messages.create(model=model, max_tokens=1500,
                                          messages=[{"role": "user", "content": prompt}])
            break
        except anthropic.NotFoundError as e:
            last = e
            continue
    else:
        raise RuntimeError(f"No available model: {last}")
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    text = text[text.find("{"): text.rfind("}") + 1]
    data = json.loads(text)
    sums = list(data.get("summaries") or [])
    if len(sums) != len(cards):
        log.warning("Got %d summaries for %d articles; falling back to card text", len(sums), len(cards))
        sums = [first_sentence(c.summary) for c in cards]
    return {"brief_html": data["brief_html"], "take_action_html": data["take_action_html"], "summaries": sums}


# ---------------------------------------------------------------------------
# Template
# ---------------------------------------------------------------------------

def article_item(c: Card, summary: str) -> str:
    e = lambda s: html.escape(s, quote=True)
    return (
        '<div style="padding:14px 0;border-bottom:1px solid #eceae2">'
        f'<div style="font-size:11px;color:#8a938a;font-weight:bold;letter-spacing:.4px">{e(c.source)} &middot; {c.date:%b %-d}</div>'
        '<div style="font-family:Georgia,\'Times New Roman\',serif;font-size:16px;line-height:1.35;margin-top:4px">'
        f'<a href="{e(c.url)}" style="color:#1b2a4a;text-decoration:none">{e(c.headline)}</a></div>'
        f'<div style="font-size:13px;line-height:1.55;color:#4a5248;margin-top:5px">{_safe_inline(summary)}</div>'
        f'<div style="margin-top:6px"><a href="{e(c.url)}" style="font-size:12px;font-weight:bold;color:#2D6A4F;text-decoration:none">Read at {e(c.source)} &rarr;</a></div>'
        '</div>'
    )


def more_item(n: int) -> str:
    """Closing line pointing to the site when the issue was capped at MAX_ARTICLES."""
    noun = "story" if n == 1 else "stories"
    return ('<div style="padding:14px 0;font-size:14px;color:#4a5248">'
            f'Plus {n} more {noun} this week &mdash; '
            f'<a href="{NEWS_URL}" style="font-weight:bold;color:#2D6A4F;text-decoration:none">see all coverage &rarr;</a></div>')


EMPTY_STATE = '<div style="padding:14px 0;font-size:14px;color:#4a5248">No new qualifying articles this week.</div>'


def build_issue(cards: list[Card], copy: dict, window_html: str, more: int = 0) -> str:
    """Fill the email template. `more` is how many articles were left out by the cap."""
    t = TEMPLATE_FILE.read_text(encoding="utf-8")
    t = re.sub(r"^\s*<!--.*?-->\s*", "", t, count=1, flags=re.S)  # instructions comment
    # Subscriber send: drop the editor-notes row, use the real logo image (Buttondown keeps images).
    t = re.sub(r"<!--EDITOR-NOTES-->.*?<!--/EDITOR-NOTES-->", "", t, flags=re.S)
    t = re.sub(r"<!--LOGO-->.*?<!--/LOGO-->",
               f'<img src="{LOGO_URL}" width="72" alt="Missing Park History" '
               'style="display:block;border:0;background-color:#ffffff;border-radius:6px;padding:4px">',
               t, flags=re.S)
    items = "".join(article_item(c, s) for c, s in zip(cards, copy["summaries"])) or EMPTY_STATE
    if more > 0:
        items += more_item(more)
    fills = {
        "DATE_RANGE": window_html,
        "BRIEF_HTML": _safe_inline(copy["brief_html"]),
        "ARTICLES_HTML": items,
        "TAKE_ACTION_HTML": _safe_inline(copy["take_action_html"]),
    }
    for k, v in fills.items():
        t = t.replace("{{" + k + "}}", v)
    leftover = re.findall(r"\{\{\w+\}\}", t)
    if leftover:
        raise ValueError(f"Unfilled placeholders: {leftover}")
    return t


# ---------------------------------------------------------------------------
# Buttondown
# ---------------------------------------------------------------------------

def _bd(method: str, url: str, key: str, payload: dict | None = None, live: bool = False) -> dict:
    headers = {"Authorization": f"Token {key}", "Content-Type": "application/json"}
    if live:
        headers["X-Buttondown-Live-Dangerously"] = "true"  # required for about_to_send
    req = urllib.request.Request(url, method=method, headers=headers,
                                 data=json.dumps(payload).encode() if payload is not None else None)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"Buttondown {method} {url} -> {e.code}: {e.read().decode()[:500]}") from None


def already_sent(subject: str, key: str) -> bool:
    data = _bd("GET", BUTTONDOWN_API + "?" + urllib.parse.urlencode({"subject": subject}), key)
    live = {"sent", "about_to_send", "in_flight", "scheduled", "imported"}
    return any(e.get("subject") == subject and e.get("status") in live for e in data.get("results", []))


# ---------------------------------------------------------------------------

# Scheduled runs send on Monday; Tuesday is a catch-up if Monday's runs all failed.
# The "already sent" check (same subject) keeps any retry from sending twice.
SEND_WEEKDAYS = (0, 1)


def last_full_week(today: date) -> tuple[date, date]:
    """The most recent complete Monday–Sunday week before `today`."""
    end = today - timedelta(days=today.weekday() + 1)
    return end - timedelta(days=6), end


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--mode", choices=["preview", "draft", "send"], default="preview")
    ap.add_argument("--scheduled", action="store_true",
                    help="Automatic run: exit quietly unless it's Monday (or Tuesday catch-up) in Pacific time.")
    args = ap.parse_args()

    key = os.environ.get("BUTTONDOWN_API_KEY", "")
    if args.scheduled and not key:
        # Shows on every automatic run, so a missing secret is visible before Monday.
        print("::warning::BUTTONDOWN_API_KEY is not set; the Weekly Watch cannot send. "
              "Add it under Settings > Secrets and variables > Actions.")

    today = datetime.now(PT).date()
    if args.scheduled and today.weekday() not in SEND_WEEKDAYS:
        log.info("Not a send day in Pacific time (%s); nothing to send.", today)
        return 0

    start, end = last_full_week(today)
    window = f"{start:%b %-d} – {end:%b %-d, %Y}"
    window_html = window.replace("–", "&ndash;")
    subject = f"MPH Weekly Watch — {window}"

    if args.mode != "preview":
        if not key:
            log.error("BUTTONDOWN_API_KEY is not set; add it as a repository secret.")
            return 2
        if not os.environ.get("ANTHROPIC_API_KEY"):
            log.error("ANTHROPIC_API_KEY is not set; refusing to send placeholder copy.")
            return 2
        if already_sent(subject, key):
            log.info("'%s' was already sent or queued in Buttondown; skipping.", subject)
            return 0

    cards = cards_this_week(NEWS_FILE.read_text(encoding="utf-8"), start, end)
    log.info("Window %s: %d article(s)", window, len(cards))
    for c in cards:
        log.info("  %s  %s — %s", c.date, c.source, c.headline)
    cards, more = cap_articles(cards)
    if more:
        log.warning("Capping the issue at %d articles; %d more are linked to the site.", MAX_ARTICLES, more)

    copy = write_copy(cards, synthesis_text(INDEX_FILE.read_text(encoding="utf-8")), window)
    body = build_issue(cards, copy, window_html, more)
    PREVIEW_FILE.write_text(body, encoding="utf-8")
    log.info("Wrote %s (%d bytes)", PREVIEW_FILE.name, len(body))

    if args.mode == "preview":
        return 0

    status = "about_to_send" if args.mode == "send" else "draft"
    # The leading comment tells Buttondown to treat the body as raw HTML.
    resp = _bd("POST", BUTTONDOWN_API, key,
               {"subject": subject, "body": "<!-- buttondown-editor-mode: plaintext -->" + body, "status": status},
               live=(status == "about_to_send"))
    log.info("Buttondown: created email %s with status %s", resp.get("id"), resp.get("status"))
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a") as f:
            f.write(f"## Weekly Watch\n- {subject}\n- {len(cards)} article(s)\n- Buttondown status: **{resp.get('status')}**\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
