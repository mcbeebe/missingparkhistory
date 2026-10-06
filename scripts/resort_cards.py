#!/usr/bin/env python3
"""Deterministically re-sort News & Press article cards.

Reads news-and-press.html, sorts every <article class="article-card"> block
chronologically (newest first) within its year, regenerates the year-marker
divs, and writes the file back. Card HTML is preserved byte-for-byte; only the
order of cards (and placement of year markers) changes.

Sort key per card:
  1. data-month="YYYY-MM"  -> primary (year, month), descending; a card without
     it falls back to its visible date ("Apr 20" / "2026"), and a card with no
     year at all is an error (it used to land under a "None" year heading)
  2. day parsed from the "<div class="month-day">Mon D</div>" label, descending
     (range/era labels with no day -> day 0, sorted to the end of their month)
  3. original document order -> stable tiebreak for same-date cards

It also re-sorts the homepage news-digest "Latest Coverage" list in
index.html (the <div class="nd-article"> blocks), which share the same
chronological-drift bug. The file is auto-detected by its content.

Usage:
    python scripts/resort_cards.py [path]            # rewrite in place
    python scripts/resort_cards.py [path] --check     # exit 1 if out of order
    python scripts/resort_cards.py [path] --dry-run   # report, don't write
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

CARD_RE = re.compile(r'<article class="article-card".*?</article>', re.S)
YEAR_MARKER_RE = re.compile(r'[ \t]*<div class="year-marker"><h2>\d{4}</h2></div>\n?')
DATA_MONTH_RE = re.compile(r'data-month="(\d{4})-(\d{2})"')
MONTH_DAY_RE = re.compile(r'month-day">([^<]*)<')
DAY_NUM_RE = re.compile(r'(\d{1,2})')
DATE_DETAIL_YEAR_RE = re.compile(r'date-detail">[^<]*?(\d{4})')
HEADLINE_RE = re.compile(r'<h3[^>]*>(.*?)</h3>', re.S)

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], start=1)}
ND_DAY_RE = re.compile(r'nd-day">\s*([0-9]{1,2})')
ND_MON_RE = re.compile(r'nd-mon">\s*([A-Za-z]{3})')


def extract_balanced_divs(html: str, class_name: str):
    """Yield (start, end, block) for each top-level <div class="class_name">…</div>,
    handling nested <div> correctly."""
    open_tag = f'<div class="{class_name}">'
    pos = 0
    while True:
        start = html.find(open_tag, pos)
        if start == -1:
            return
        depth = 0
        i = start
        n = len(html)
        while i < n:
            nxt_open = html.find("<div", i)
            nxt_close = html.find("</div>", i)
            if nxt_close == -1:
                return
            if nxt_open != -1 and nxt_open < nxt_close:
                depth += 1
                i = nxt_open + 4
            else:
                depth -= 1
                i = nxt_close + len("</div>")
                if depth == 0:
                    yield (start, i, html[start:i])
                    break
        pos = i


def card_date(card_html: str) -> tuple[int, int, int]:
    """(year, month, day) of a card, used both to sort it and to pick the
    year-marker it sits under.

    Year and month come from data-month; a card without it falls back to its
    visible date. Raises ValueError when no year can be found, so a card can
    never be filed under a bogus heading (cards without data-month used to be
    pushed to the end under <h2>None</h2>).
    """
    md = MONTH_DAY_RE.search(card_html)
    label = md.group(1) if md else ""
    d = DAY_NUM_RE.search(label)
    day = int(d.group(1)) if d else 0
    m = DATA_MONTH_RE.search(card_html)
    if m:
        return int(m.group(1)), int(m.group(2)), day
    y = DATE_DETAIL_YEAR_RE.search(card_html)
    if not y:
        h = HEADLINE_RE.search(card_html)
        what = re.sub(r"<[^>]+>", "", h.group(1)).strip() if h else card_html[:120]
        raise ValueError(f"news card has no data-month and no year in its date: {what!r}")
    return int(y.group(1)), MONTHS.get(label.strip()[:3].title(), 0), day


def card_sort_key(card_html: str, original_index: int):
    """Return an ascending sort key that yields newest-first ordering."""
    year, month, day = card_date(card_html)
    # Negate date components so a plain ascending sort gives newest first;
    # original_index ascending keeps same-date cards in their existing order.
    return (-year, -month, -day, original_index)


def resort(html: str) -> str:
    cards = CARD_RE.findall(html)
    if not cards:
        return html

    # Region to rewrite: from the first year-marker (or first card) through the
    # end of the last card. Everything outside is preserved untouched.
    first_marker = html.find('<div class="year-marker">')
    first_card = html.find('<article class="article-card"')
    start = min(x for x in (first_marker, first_card) if x != -1)
    last_card_end = html.rfind('</article>') + len('</article>')

    prefix = html[:start]
    suffix = html[last_card_end:]

    ordered = sorted(
        (c for c in cards),
        key=lambda c: card_sort_key(c, cards.index(c)),
    )
    # cards.index is O(n^2) but n is small (~150) and gives a stable tiebreak.

    out_lines = []
    current_year = None
    for card in ordered:
        year = f"{card_date(card)[0]:04d}"
        if year != current_year:
            out_lines.append(f'<div class="year-marker"><h2>{year}</h2></div>')
            current_year = year
        out_lines.append(card)

    # No trailing newline: suffix already starts with whatever followed the
    # last card, and adding one here grew the page by a blank line every run.
    rebuilt = "\n".join(out_lines)
    return prefix + rebuilt + suffix


def nd_sort_key(block: str, original_index: int):
    """Sort key for a homepage digest <div class="nd-article"> block."""
    mon = ND_MON_RE.search(block)
    day = ND_DAY_RE.search(block)
    month = MONTHS.get(mon.group(1).title(), 0) if mon else 0
    d = int(day.group(1)) if day else 0
    return (-month, -d, original_index)


def resort_digest(html: str) -> str:
    """Re-sort the index.html 'Latest Coverage' nd-article list, newest first."""
    blocks = list(extract_balanced_divs(html, "nd-article"))
    if not blocks:
        return html
    first_start = blocks[0][0]
    last_end = blocks[-1][1]
    originals = [b[2] for b in blocks]
    ordered = sorted(
        originals, key=lambda b: nd_sort_key(b, originals.index(b)))
    sep = "\n\n      "  # match existing indentation between nd-article blocks
    rebuilt = sep.join(ordered)
    return html[:first_start] + rebuilt + html[last_end:]


def is_sorted(html: str) -> tuple[bool, list[str]]:
    problems = []
    cards = CARD_RE.findall(html)
    keys = [card_sort_key(c, i) for i, c in enumerate(cards)]
    for i in range(1, len(keys)):
        if keys[i][:3] < keys[i - 1][:3]:
            problems.append(f"news card #{i} is newer than card #{i-1}")
    nd = [b[2] for b in extract_balanced_divs(html, "nd-article")]
    ndkeys = [nd_sort_key(b, i) for i, b in enumerate(nd)]
    for i in range(1, len(ndkeys)):
        if ndkeys[i][:2] < ndkeys[i - 1][:2]:
            problems.append(f"digest item #{i} is newer than item #{i-1}")
    return (not problems, problems)


def main() -> int:
    args = [a for a in sys.argv[1:]]
    path = Path("news-and-press.html")
    mode = None
    for a in args:
        if a in ("--check", "--dry-run"):
            mode = a
        else:
            path = Path(a)

    html = path.read_text(encoding="utf-8")
    before_cards = len(CARD_RE.findall(html))
    before_nd = len(list(extract_balanced_divs(html, "nd-article")))
    try:
        ok, problems = is_sorted(html)
    except ValueError as e:  # an undatable card: refuse to guess where it goes
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    if mode == "--check":
        if ok:
            print(f"OK: {before_cards} news cards + {before_nd} digest items "
                  f"already in chronological order.")
            return 0
        print(f"OUT OF ORDER: {len(problems)} problem(s):")
        for p in problems:
            print("  -", p)
        return 1

    new_html = resort(html)
    new_html = resort_digest(new_html)

    # Content integrity: the multiset of blocks must be unchanged.
    assert len(CARD_RE.findall(new_html)) == before_cards, "news card count changed"
    assert sorted(CARD_RE.findall(html)) == sorted(CARD_RE.findall(new_html)), (
        "news card content changed during re-sort")
    nd_before = sorted(b[2] for b in extract_balanced_divs(html, "nd-article"))
    nd_after = sorted(b[2] for b in extract_balanced_divs(new_html, "nd-article"))
    assert nd_before == nd_after, "digest item content changed during re-sort"
    ok_after, problems_after = is_sorted(new_html)
    assert ok_after, f"still out of order after sort: {problems_after}"

    if mode == "--dry-run":
        print(f"DRY RUN: would reorder {before_cards} news cards + {before_nd} "
              f"digest items; {len(problems)} out-of-order pair(s) fixed. "
              f"File not written.")
        return 0

    path.write_text(new_html, encoding="utf-8")
    print(f"Re-sorted {before_cards} news cards + {before_nd} digest items; "
          f"fixed {len(problems)} out-of-order pair(s). Wrote {path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
