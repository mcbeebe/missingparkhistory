#!/usr/bin/env python3
"""
NPS News & Press Daily Updater (GitHub Actions edition)
========================================================

Runs headlessly in CI. Calls the Anthropic API with the native web_search tool
to find new articles about NPS sign/exhibit censorship, then inserts HTML
cards into ``news-and-press.html`` in chronological order.

Environment:
    ANTHROPIC_API_KEY   Required. Your Anthropic API key.
    GITHUB_ACTIONS      Set by GitHub Actions; enables GH-specific output.

Usage:
    python scripts/update_news.py              # Normal run
    python scripts/update_news.py --dry-run    # Print diff; do not write
    python scripts/update_news.py --force      # Run even if banner already shows today
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import anthropic

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = REPO_ROOT / "news-and-press.html"
ARCHIVE_DIR = REPO_ROOT / "News and Press" / "Archive"

# Keep in sync with the SKILL frontmatter. Fall back through a small list so
# the workflow does not break the first time Anthropic retires a model alias.
MODEL_CANDIDATES = [
    "claude-sonnet-4-5",
    "claude-sonnet-4-5-20250929",
    "claude-sonnet-4-20250514",
]

MAX_TOOL_USES = 15
MAX_TOKENS = 8000

VALID_TAGS = {"order", "removal", "resistance", "lawsuit", "leak", "court"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("update-news")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@dataclass
class Article:
    """A curated article to add to the news page."""

    date: str                 # ISO format YYYY-MM-DD
    source_name: str          # Display name, e.g. "Washington Blade"
    source_key: str           # Filter key, e.g. "other"
    tag: str                  # One of VALID_TAGS
    tag_label: str            # Display label, e.g. "Court Victory"
    url: str
    headline: str
    summary_html: str         # Paraphrased summary; may contain <strong>

    @property
    def iso_month(self) -> str:
        return self.date[:7]

    @property
    def year(self) -> str:
        return self.date[:4]

    @property
    def display_month_day(self) -> str:
        dt = datetime.strptime(self.date, "%Y-%m-%d")
        return dt.strftime("%b %-d") if sys.platform != "win32" else dt.strftime("%b %#d")


def load_html() -> str:
    if not HTML_FILE.exists():
        log.error("HTML file not found: %s", HTML_FILE)
        sys.exit(1)
    return HTML_FILE.read_text(encoding="utf-8")


def write_html(content: str) -> None:
    HTML_FILE.write_text(content, encoding="utf-8")


_HOST_PREFIXES = ("www.", "us.", "uk.", "edition.", "m.", "mobile.", "amp.")


def canonical_url(url: str) -> str:
    """Normalize a URL for dedup. Lowercases the host, strips common host
    prefixes (www., us., uk., m., mobile., amp.), drops query string and
    fragment, and trims a trailing slash. Catches near-duplicates like
    `www.cnn.com/X` vs `us.cnn.com/X` (same article, different mirror)."""
    try:
        from urllib.parse import urlparse, urlunparse
        p = urlparse(url.strip())
        host = p.netloc.lower()
        for pref in _HOST_PREFIXES:
            if host.startswith(pref):
                host = host[len(pref):]
                break
        path = p.path.rstrip("/")
        return urlunparse((p.scheme.lower() or "https", host, path, "", "", ""))
    except Exception:
        return url.rstrip("/")


def existing_urls(html: str) -> set[str]:
    return {canonical_url(m) for m in re.findall(r'href="(https?://[^"]+)"', html)}


def banner_date(html: str) -> str | None:
    m = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', html)
    return m.group(1) if m else None


def article_count(html: str) -> int:
    return html.count('<article class="article-card"')


# ---------------------------------------------------------------------------
# Claude call
# ---------------------------------------------------------------------------


CURATION_PROMPT = """You are the daily news curator for MissingParkHistory.org.

Your task: find NEW articles about NPS sign/exhibit censorship under Executive
Order 14253 and Secretary's Order 3431, and return them as strict JSON.

**Relevance**: only articles directly about one of:
- NPS sign or exhibit removal/censorship
- EO 14253 ("Restoring Truth and Sanity to American History")
- Secretary's Order 3431
- Related litigation (NPCA v. DOI, Philadelphia's President's House suit,
  Sierra Club FOIA suit, Stonewall Pride flag suit)
- Preservation / resistance efforts (Save Our Signs, MissingParkHistory.org,
  legislative responses, advocacy coalitions)
- Congressional action: bills, resolutions, floor statements, press releases,
  committee hearings, and appropriations language related to NPS censorship,
  national park funding cuts, or NPS staffing reductions
- NPS budget cuts, staffing freezes, visitor center closures, or fee-free day
  changes tied to the current administration
- Books, commentary, or op-eds about national park history censorship,
  Indigenous erasure in parks, or climate science removal from parks
- State-level resistance or co-management pushback against federal NPS
  censorship directives

**Novelty**: skip articles whose URLs appear in EXISTING_URLS below. Skip
articles that merely rehash prior coverage without new facts, quotes, or
developments.

**Source quality**: prioritize original reporting from major outlets (WaPo,
NYT, NPR, AP, PBS, CBS, CNN) and domain-specific sources (NPCA, Outside, NPS
Traveler, Democracy Forward, Sierra Club). Congressional press releases from
senate.gov and house.gov are high-priority primary sources. Regional reporting
and opinion/commentary are welcome when they add local context or substantive
analysis.

**Time window**: only articles published on or after {since_date}.

**Searches to run** (use the web_search tool — run ALL of these; cast a wide
net and vary your queries):

Core NPS censorship:
- "NPS sign removal" OR "national park censorship" {current_month_year}
- "SO 3431" OR "Secretary Order 3431" {current_month_year}
- national park exhibit removed signs {current_month_year}
- "national park" "history removed" OR "history censored" {current_year}

Litigation:
- NPCA Democracy Forward national parks lawsuit {current_year}
- "President's House" Philadelphia slavery exhibit {current_month_year}
- Stonewall Pride flag national monument {current_month_year}
- Sierra Club national park FOIA {current_year}

Congressional / legislative:
- site:senate.gov national park censorship {current_year}
- site:house.gov national park censorship OR "national park service" {current_year}
- Congress "national park" bill censorship OR funding cuts {current_month_year}
- "national park service" appropriations amendment {current_year}

Indigenous, climate, and themed coverage:
- "national park" Indigenous history censorship OR erasure {current_month_year}
- "national park" climate change signs removed {current_month_year}
- "national park" slavery history removed OR censored {current_month_year}
- national park books censored OR flagged {current_month_year}

Budget and staffing:
- "national park service" budget cuts staffing {current_month_year}
- "national park service" visitor center closed OR closure {current_month_year}
- NPS fee-free days changed OR eliminated {current_year}

Opinion and regional:
- "national park censorship" opinion OR commentary {current_month_year}
- "national park" history censorship California OR Pennsylvania OR Massachusetts {current_month_year}

Also search these specific domains for recent pieces:
npca.org, nationalparkstraveler.org, democracyforward.org, sierraclub.org,
outsideonline.com, calmatters.org, hcn.org (High Country News),
markey.senate.gov, merkley.senate.gov, grijalva.house.gov

**Filtering**: Do NOT include articles about:
- Big Tech censorship, Section 230, social media content moderation
- State or city parks (only National Park Service)
- General conservation topics unrelated to NPS interpretive censorship

**Output**: return ONLY valid JSON matching this schema. Your response MUST
begin with the `{{` character — no prose intro ("Based on my searches..."),
no preamble, no markdown fences, no commentary after the JSON. The very
first character of your output must be `{{` and the last must be `}}`.

{{
  "articles": [
    {{
      "date": "YYYY-MM-DD",
      "source_name": "Display name (e.g. 'Washington Blade')",
      "source_key": "one of: wapo|npr|nbc|pbs|newsweek|thehill|outside|sfgate|inquirer|bostonglobe|npca|demforward|sierraclub|oah|govexec|notus|calmatters|hcn|senate|house|congress|other",
      "tag": "one of: order|removal|resistance|lawsuit|leak|court",
      "tag_label": "Short display label (e.g. 'Court Victory', 'Removal', 'State Coalition')",
      "url": "https://...",
      "headline": "Article headline",
      "summary_html": "2-4 sentence paraphrased summary. Wrap key terms in <strong>...</strong>. NEVER quote the source article directly — paraphrase. Include specific names, dates, and numbers."
    }}
  ]
}}

If no qualifying new articles are found, return {{"articles": []}}.

---

EXISTING_URLS (do not duplicate):
{existing_urls_list}
"""


def call_claude(since_date: str, urls: Iterable[str]) -> list[Article]:
    client = anthropic.Anthropic()
    now = datetime.now()
    prompt = CURATION_PROMPT.format(
        since_date=since_date,
        current_month_year=now.strftime("%B %Y"),
        current_year=now.year,
        existing_urls_list="\n".join(sorted(urls)),
    )

    def _create(model: str, max_uses: int):
        log.info("Calling Anthropic API with model=%s (max_uses=%d)", model, max_uses)
        return client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            tools=[{
                "type": "web_search_20250305",
                "name": "web_search",
                "max_uses": max_uses,
            }],
            messages=[{"role": "user", "content": prompt}],
        )

    last_err: Exception | None = None
    resp = None
    for model in MODEL_CANDIDATES:
        try:
            resp = _create(model, MAX_TOOL_USES)
            break
        except anthropic.NotFoundError as e:
            log.warning("Model %s not available: %s", model, e)
            last_err = e
            continue
        except anthropic.BadRequestError as e:
            if "prompt is too long" not in str(e):
                raise
            retry_uses = max(1, MAX_TOOL_USES // 2)
            log.warning(
                "Prompt too long with max_uses=%d; retrying once with max_uses=%d",
                MAX_TOOL_USES, retry_uses,
            )
            try:
                resp = _create(model, retry_uses)
                break
            except anthropic.BadRequestError as e2:
                log.error("Prompt still too long on retry; aborting run: %s", e2)
                emit_github_summary([
                    "## NPS News Daily Update",
                    "- Status: **Failed** — Anthropic API rejected the prompt as too long even after halving max_uses.",
                    "- Action: lower `MAX_TOOL_USES` further or trim queries in `CURATION_PROMPT`.",
                ])
                sys.exit(1)
    else:
        log.error("All candidate models failed; last error: %s", last_err)
        sys.exit(1)

    # Claude responses with tools include a mix of text and tool_use/tool_result
    # blocks. We want the final assistant text block.
    final_text = ""
    for block in resp.content:
        if getattr(block, "type", None) == "text":
            final_text = block.text  # keep last text block

    if not final_text:
        log.warning("No text block in Claude response")
        return []

    # Strip common junk
    final_text = final_text.strip()
    final_text = re.sub(r"^```(?:json)?\s*", "", final_text)
    final_text = re.sub(r"\s*```$", "", final_text)

    # Claude sometimes prefaces the JSON with prose ("Based on my searches...").
    # Extract the outermost JSON object — first '{' to last '}' — before parsing.
    first_brace = final_text.find("{")
    last_brace = final_text.rfind("}")
    if first_brace != -1 and last_brace > first_brace:
        final_text = final_text[first_brace : last_brace + 1]

    try:
        data = json.loads(final_text)
    except json.JSONDecodeError as e:
        log.error("Claude returned non-JSON output: %s", e)
        log.error("Raw output (first 1000 chars): %s", final_text[:1000])
        return []

    parsed = [parse_article(a) for a in data.get("articles", []) if a]
    return [a for a in parsed if a is not None]


def is_iso_date(value: str) -> bool:
    """True for a real calendar date written exactly as YYYY-MM-DD."""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return False
    return True


def parse_article(raw: dict) -> Article | None:
    # A single malformed article from the model must not abort the whole run.
    # Skip (with a warning) any entry missing a required field.
    required = ("date", "source_name", "url", "headline", "summary_html")
    missing = [k for k in required if not str(raw.get(k) or "").strip()]
    if missing:
        log.warning("Skipping malformed article (missing %s): %r", ", ".join(missing), raw)
        return None
    # The card's year heading, data-month and date label all derive from this.
    date = str(raw["date"]).strip()
    if not is_iso_date(date):
        log.warning("Skipping article with unparseable date %r: %r", date, raw)
        return None

    tag = raw.get("tag", "").strip().lower()
    if tag not in VALID_TAGS:
        log.warning("Invalid tag %r; coercing to 'removal'", tag)
        tag = "removal"
    return Article(
        date=date,
        source_name=raw["source_name"].strip(),
        source_key=raw.get("source_key", "other").strip().lower() or "other",
        tag=tag,
        tag_label=raw.get("tag_label", tag.title()).strip() or tag.title(),
        url=raw["url"].strip(),
        headline=raw["headline"].strip(),
        summary_html=raw["summary_html"].strip(),
    )


# ---------------------------------------------------------------------------
# HTML generation & insertion
# ---------------------------------------------------------------------------


def render_card(a: Article, added_iso: str) -> str:
    # data-added records when the bot added the card (not the publish date), so the
    # weekly newsletter can list everything added in the past 7 days.
    return (
        f'  <article class="article-card" data-tags="{a.tag}" '
        f'data-month="{a.iso_month}" data-source="{a.source_key}" data-added="{added_iso}">\n'
        f'    <div class="article-date">'
        f'<div class="month-day">{a.display_month_day}</div>'
        f'<div class="date-detail">{a.year}</div></div>\n'
        f'    <div class="article-body">\n'
        f'      <div class="article-meta">'
        f'<span class="article-source">{a.source_name}</span>'
        f'<span class="article-tag tag-{a.tag}">{a.tag_label}</span></div>\n'
        f'      <h3><a href="{a.url}" target="_blank">{a.headline}</a></h3>\n'
        f'      <p class="article-summary">{a.summary_html}</p>\n'
        f'      <a href="{a.url}" class="read-more" target="_blank">'
        f'Read at {a.source_name} &rarr;</a>\n'
        f'    </div>\n'
        f'  </article>\n'
    )


def insert_card(html: str, card: str, year: str) -> str:
    """Insert a card at the top of the given year's section.

    The page is ordered newest-first within each year. We insert right after the
    ``<div class="year-marker"><h2>{year}</h2></div>`` line. ``year`` must be a
    4-digit year: anything else raises rather than writing a heading like
    ``<h2>None</h2>``.
    """
    if not re.fullmatch(r"\d{4}", str(year)):
        raise ValueError(f"insert_card needs a 4-digit year, got {year!r}")
    marker = f'<div class="year-marker"><h2>{year}</h2></div>'
    idx = html.find(marker)
    if idx == -1:
        # Create a new year section at the top of the timeline section.
        section_open = '<section class="timeline-section">'
        sec_idx = html.find(section_open)
        if sec_idx == -1:
            log.warning("Could not locate timeline section; skipping insert")
            return html
        insert_at = sec_idx + len(section_open)
        return (
            html[:insert_at]
            + f'\n<div class="year-marker"><h2>{year}</h2></div>\n'
            + card
            + html[insert_at:]
        )

    # Insert immediately after the marker line (after its closing newline).
    after_marker = html.find("\n", idx) + 1
    return html[:after_marker] + card + html[after_marker:]


def sort_articles_desc(articles: list[Article]) -> list[Article]:
    return sorted(articles, key=lambda a: a.date, reverse=True)


def coerce_unlisted_sources(articles: list[Article], html: str) -> None:
    """File any article whose source_key has no option in the page's Source
    filter (#filterSource) under 'other', so every card stays filterable."""
    m = re.search(r'<select[^>]*id="filterSource"[^>]*>(.*?)</select>', html, re.DOTALL)
    if not m:
        log.warning("Source filter (#filterSource) not found; leaving source keys as-is")
        return
    offered = set(re.findall(r'<option value="([^"]+)"', m.group(1))) - {"all"}
    for a in articles:
        if a.source_key not in offered:
            log.info("No Source filter option for %r (%s); coercing to 'other'", a.source_key, a.source_name)
            a.source_key = "other"


# ---------------------------------------------------------------------------
# Banner update
# ---------------------------------------------------------------------------


def update_banner(html: str, today_iso: str, new_count: int) -> str:
    dt = datetime.strptime(today_iso, "%Y-%m-%d")
    pretty = dt.strftime("%B %-d, %Y") if sys.platform != "win32" else dt.strftime("%B %#d, %Y")

    html = re.sub(
        r'datetime="\d{4}-\d{2}-\d{2}">[^<]+<',
        f'datetime="{today_iso}">{pretty}<',
        html,
        count=1,
    )
    html = re.sub(
        r"(\d+)\s+articles tracked",
        f"{new_count} articles tracked",
        html,
        count=1,
    )
    # Both write paths call update_banner, so keep the month filter in sync here.
    return ensure_month_options(html)


def ensure_month_options(html: str) -> str:
    """Add a #filterMonth <option> for every month that has article cards but
    no option yet, so new months stay filterable. Existing options are kept;
    new ones are inserted in newest-first order."""
    m = re.search(r'(<select[^>]*id="filterMonth"[^>]*>)(.*?)(</select>)', html, re.DOTALL)
    if not m:
        log.warning("Month filter (#filterMonth) not found; skipping month sync")
        return html
    body = m.group(2)
    have = set(re.findall(r'<option value="(\d{4}-\d{2})"', body))
    missing = set(re.findall(r'data-month="(\d{4}-\d{2})"', html)) - have
    if not missing:
        return html
    for ym in sorted(missing, reverse=True):
        label = datetime.strptime(ym, "%Y-%m").strftime("%b %Y")
        opt = f'<option value="{ym}">{label}</option>'
        # Insert before the first existing option that is older than ym.
        older = next(
            (o for o in re.finditer(r'<option value="(\d{4}-\d{2})"', body) if o.group(1) < ym),
            None,
        )
        body = body[: older.start()] + opt + body[older.start():] if older else body.rstrip() + opt + "\n    "
    log.info("Added month filter option(s): %s", ", ".join(sorted(missing, reverse=True)))
    return html[: m.start(2)] + body + html[m.end(2):]


# ---------------------------------------------------------------------------
# Archive
# ---------------------------------------------------------------------------


INDEX_FILE = REPO_ROOT / "index.html"

TAG_LABELS = {
    "order": "The Order",
    "removal": "Removals",
    "resistance": "Resistance",
    "lawsuit": "Lawsuit",
    "leak": "Leaks",
    "court": "Court Victory",
}


def _is_frozen(idx_html: str, section: str) -> bool:
    """True if index.html carries a freeze marker for this section, so the bot
    should leave hand-edited content alone.

    Place any of these HTML comments anywhere in index.html:
      <!-- news-bot:freeze -->            freeze BOTH synthesis and digest
      <!-- news-bot:freeze-synthesis -->  freeze the 'Where the Fight Stands' text + badges
      <!-- news-bot:freeze-digest -->     freeze the 'Latest Coverage' list + date range
    Remove the marker to let the daily bot resume updating that section.
    """
    if re.search(r"<!--\s*news-bot:freeze\s*-->", idx_html):
        return True
    return bool(re.search(rf"<!--\s*news-bot:freeze-{section}\s*-->", idx_html))


def update_index_last_updated(today_iso: str) -> None:
    """Bump the 'Last Updated: <date>' footer stamp in index.html so it tracks
    the bot's most recent real run instead of going stale."""
    if not INDEX_FILE.exists():
        return
    dt = datetime.strptime(today_iso, "%Y-%m-%d")
    pretty = dt.strftime("%B %-d, %Y") if sys.platform != "win32" else dt.strftime("%B %#d, %Y")
    idx_html = INDEX_FILE.read_text(encoding="utf-8")
    new_idx, n = re.subn(
        r'(class="desktop-last-updated">\s*Last Updated:\s*)[^<]*(</div>)',
        lambda m: f"{m.group(1)}{pretty}{m.group(2)}",
        idx_html,
        count=1,
    )
    if n:
        INDEX_FILE.write_text(new_idx, encoding="utf-8")
        log.info("Updated index 'Last Updated' footer to %s", pretty)
    else:
        log.warning("Could not find 'Last Updated' footer in index.html")


def _recent_articles_from_html(html: str, limit: int = 5) -> list[dict]:
    """Extract the N most recent articles from news-and-press.html for the
    digest pop-up.  Returns dicts with keys: day, month, source, tag,
    tag_label, headline, url."""
    pattern = re.compile(
        r'<article class="article-card"[^>]*data-tags="([^"]*)"[^>]*>'
        r'.*?<div class="month-day">([^<]+)</div>'
        r'.*?<div class="date-detail">([^<]+)</div>'
        r'.*?<span class="article-source">([^<]+)</span>'
        r'.*?<h3><a href="([^"]+)"[^>]*>([^<]+)</a></h3>',
        re.DOTALL,
    )
    results = []
    for m in pattern.finditer(html):
        tag = m.group(1).strip()
        month_day = m.group(2).strip()          # e.g. "Apr 20"
        year = m.group(3).strip()               # e.g. "2026"
        parts = month_day.split()
        mon = parts[0] if parts else ""
        day = parts[1] if len(parts) > 1 else ""
        results.append({
            "day": day,
            "mon": mon,
            "year": year,
            "source": m.group(4).strip(),
            "tag": tag,
            "tag_label": TAG_LABELS.get(tag, tag.title()),
            "url": m.group(5).strip(),
            "headline": m.group(6).strip(),
        })
        if len(results) >= limit:
            break
    return results


_MONTHS = {m: i + 1 for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}


def _articles_for_synthesis(html: str, since_date: str, limit: int = 20) -> list[dict]:
    """Extract articles published OR added (data-added) on or after since_date
    for the weekly synthesis/timeline prompts.

    Coverage often surfaces days after publication, so publish date alone
    misses most of a week's news (the Sep 28 and Oct 5, 2026 Mondays found 0
    articles that way). Returns dicts with date, added, source, tag, headline,
    url, summary (HTML, may contain <strong>/<em>)."""
    cards = re.findall(
        r'<article class="article-card"[^>]*>.*?</article>', html, re.DOTALL,
    )
    sy, sm, sd = (int(x) for x in since_date.split("-"))
    results = []
    for c in cards:
        added_m = re.search(r'data-added="(\d{4}-\d{2}-\d{2})"', c.split(">", 1)[0])
        added = added_m.group(1) if added_m else ""
        md = re.search(r'<div class="month-day">([^<]+)</div>', c)
        yr = re.search(r'<div class="date-detail">([^<]+)</div>', c)
        src = re.search(r'<span class="article-source">([^<]+)</span>', c)
        h = re.search(r'<h3[^>]*>(?:.*?<a[^>]*>)?([^<]+)<', c, re.DOTALL)
        url = re.search(r'<h3[^>]*>.*?<a href="([^"]+)"', c, re.DOTALL)
        summary = re.search(r'<p class="article-summary">(.+?)</p>', c, re.DOTALL)
        tag = re.search(r'data-tags="([^"]*)"', c)
        if not (md and yr and src and h):
            continue
        tok = md.group(1).strip().split()
        if len(tok) < 2 or not tok[1].isdigit():
            continue
        month = _MONTHS.get(tok[0][:3])
        day = int(tok[1])
        ym = re.search(r'(\d{4})', yr.group(1))
        year = int(ym.group(1)) if ym else 0
        if not (month and year):
            continue
        if (year, month, day) < (sy, sm, sd) and not (added and added >= since_date):
            continue
        results.append({
            "date": f"{year:04d}-{month:02d}-{day:02d}",
            "added": added,
            "source": src.group(1).strip(),
            "tag": tag.group(1) if tag else "",
            "headline": h.group(1).strip(),
            "url": url.group(1) if url else "",
            "summary": re.sub(r"\s+", " ", summary.group(1)).strip() if summary else "",
        })
        if len(results) >= limit:
            break
    return results


def _tag_css_class(tag: str) -> str:
    return f"nd-tag-{tag}" if tag in TAG_LABELS else "nd-tag-order"


def update_news_digest(news_html: str, today_iso: str) -> None:
    """Regenerate the news digest pop-up inside index.html using the latest
    articles from the news page."""
    if not INDEX_FILE.exists():
        log.warning("index.html not found; skipping digest update")
        return

    articles = _recent_articles_from_html(news_html, limit=5)
    if not articles:
        log.info("No articles found for digest pop-up; skipping")
        return

    idx_html = INDEX_FILE.read_text(encoding="utf-8")

    if _is_frozen(idx_html, "digest"):
        log.info("News digest is frozen by a news-bot:freeze marker; leaving it unchanged")
        return

    # Build the articles block
    art_lines = []
    for a in articles:
        art_lines.append(
            f'      <div class="nd-article">\n'
            f'        <div class="nd-art-date"><div class="nd-day">{a["day"]}</div>'
            f'<div class="nd-mon">{a["mon"]}</div></div>\n'
            f'        <div class="nd-art-body">\n'
            f'          <div class="nd-art-meta"><span class="nd-art-source">{a["source"]}</span>'
            f'<span class="nd-art-tag {_tag_css_class(a["tag"])}">{a["tag_label"]}</span></div>\n'
            f'          <div class="nd-art-title"><a href="{a["url"]}" target="_blank" '
            f'rel="noopener">{a["headline"]}</a></div>\n'
            f'        </div>\n'
            f'      </div>\n'
        )
    articles_block = "\n".join(art_lines)

    # Build date range string
    if articles:
        first = articles[-1]
        last_art = articles[0]
        date_range = f'{first["mon"]} {first["day"]} &ndash; {last_art["mon"]} {last_art["day"]}, {last_art["year"]}'
    else:
        date_range = today_iso

    # Replace the articles section: from its opening div up to its closing
    # div, which is followed by the next pop-up block (the newsletter signup,
    # added Oct 2026, or the footer). Matching only the footer broke the
    # digest silently once the signup box was inserted between them.
    start_idx = idx_html.find('<div class="nd-articles">')
    end_m = re.compile(r'</div>\n\s*\n\s*<div class="nd-(?:sub|footer)">').search(idx_html, max(start_idx, 0))

    if start_idx == -1 or end_m is None:
        log.warning("Could not find digest markers in index.html; skipping")
        return
    end_idx = end_m.start()

    new_articles_section = (
        f'<div class="nd-articles">\n'
        f'      <h3>Latest Coverage</h3>\n\n'
        f'{articles_block}'
        f'    '
    )

    new_idx = idx_html[:start_idx] + new_articles_section + idx_html[end_idx:]

    # Update date range in header
    new_idx = re.sub(
        r'(<div class="nd-daterange">)[^<]+(</div>)',
        rf'\g<1>{date_range} &middot; {len(articles)} new developments\2',
        new_idx,
        count=1,
    )

    INDEX_FILE.write_text(new_idx, encoding="utf-8")
    log.info("Updated news digest pop-up in index.html with %d articles", len(articles))


SYNTHESIS_PROMPT = """You are the editorial voice of MissingParkHistory.org,
regenerating the "Where the Fight Stands" synthesis at the top of the
homepage news digest. Your output replaces a hand-curated narrative.

Tone reference (the most recent prior version — match this voice exactly):
---
{prior_synthesis}
---

Rules:
- TWO paragraphs, ~150-200 words each. No more, no less.
- Lead with the WEEK'S ANCHOR STORY (the single most consequential
  development), then add a second paragraph that adds another thread
  (legal, executive, or congressional) and contextualizes how the pieces
  fit together. Find the throughline; do not summarize each article.
- Voice: analytical, journalistic, structural. Use specific names, dates,
  numbers, dollar amounts. No vague phrases like "this week saw" or "many
  developments occurred."
- HTML: wrap key proper nouns and figures in <strong>...</strong>.
  Italicize key phrases, titles, or quoted concepts in <em>...</em>.
  Use &mdash; for em-dashes and &rsquo; for apostrophes.

ALSO produce THREE badge labels for the header. Each is one emoji + a short
label (3-5 words). Pick the three most newsworthy threads. Use one of
these unicode emojis (NOT HTML entities):
- 🏛️ for legislative/congressional action
- ⚖️ for courts/lawsuits
- 👁️ for removals/censorship visibility
- ✊ for resistance/protest
- 📖 for books/publications
- 📰 for media/press
- 📜 for executive orders / orders
- 🍁 for Indigenous/Native American themes

ARTICLES from {since_date} through {today} (most recent first):
{articles_block}

Return ONLY this JSON. The very first character of your response MUST be
`{{` — no prose intro, no markdown fences, no commentary:

{{
  "paragraphs": [
    "first paragraph HTML, with <strong> and <em>",
    "second paragraph HTML"
  ],
  "badges": [
    {{"emoji": "🏛️", "label": "Truth in NPs Act Introduced"}},
    {{"emoji": "⚖️", "label": "Plaintiffs File New Brief"}},
    {{"emoji": "📖", "label": "Native History in Spotlight"}}
  ]
}}
"""


# ---------------------------------------------------------------------------
# Weekly cadence (synthesis + timeline)
# ---------------------------------------------------------------------------
#
# Weekly jobs used to run only on Mondays and gave up silently when that one
# run found too little news, so a missed Monday meant another week of stale
# content. Each job now records when it last succeeded in an HTML comment
# stamp (<!-- news-bot:<name> YYYY-MM-DD -->) and runs on any day it is
# 7+ days stale, retrying daily until it succeeds.

WEEKLY_INTERVAL_DAYS = 7
MAX_LOOKBACK_DAYS = 21
SYNTHESIS_STAMP = "synthesis-updated"
TIMELINE_STAMP = "timeline-updated"


def _stamp_re(name: str) -> re.Pattern:
    return re.compile(rf"<!--\s*news-bot:{name}\s+(\d{{4}}-\d{{2}}-\d{{2}})\s*-->")


def read_stamp(html: str, name: str) -> str | None:
    """Return the YYYY-MM-DD in a `<!-- news-bot:<name> DATE -->` stamp, if any."""
    m = _stamp_re(name).search(html)
    return m.group(1) if m else None


def write_stamp(html: str, name: str, today_iso: str, anchor: str) -> str:
    """Set the stamp to today_iso, inserting it just before `anchor` if absent."""
    stamp = f"<!-- news-bot:{name} {today_iso} -->"
    new, n = _stamp_re(name).subn(stamp, html, count=1)
    if n:
        return new
    i = html.find(anchor)
    if i == -1:
        raise ValueError(f"anchor {anchor!r} not found for stamp {name}")
    line_start = html.rfind("\n", 0, i) + 1
    indent = html[line_start:i] if not html[line_start:i].strip() else ""
    return html[:i] + stamp + "\n" + indent + html[i:]


def _days_between(a_iso: str, b_iso: str) -> int:
    a = datetime.strptime(a_iso, "%Y-%m-%d").date()
    b = datetime.strptime(b_iso, "%Y-%m-%d").date()
    return (b - a).days


def weekly_due(last_iso: str | None, today_iso: str) -> bool:
    """True when a weekly job has never run or last succeeded 7+ days ago."""
    return last_iso is None or _days_between(last_iso, today_iso) >= WEEKLY_INTERVAL_DAYS


def window_start(last_iso: str | None, today_iso: str) -> str:
    """Start of the article window for a weekly job: everything since its last
    success (capped at MAX_LOOKBACK_DAYS), or the past week if it never ran."""
    today = datetime.strptime(today_iso, "%Y-%m-%d").date()
    if last_iso is None:
        return (today.fromordinal(today.toordinal() - WEEKLY_INTERVAL_DAYS)).isoformat()
    floor = today.fromordinal(today.toordinal() - MAX_LOOKBACK_DAYS).isoformat()
    return max(last_iso, floor)


def _complete(prompt: str, max_tokens: int) -> str | None:
    """One text completion, falling back through MODEL_CANDIDATES. Returns the
    response text, or None on any API failure (callers treat None as skip)."""
    client = anthropic.Anthropic()
    last_err: Exception | None = None
    for model in MODEL_CANDIDATES:
        try:
            log.info("Calling Anthropic API with model=%s", model)
            resp = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.NotFoundError as e:
            log.warning("Model %s not available: %s", model, e)
            last_err = e
            continue
        except anthropic.AnthropicError as e:
            log.error("API call failed: %s", e)
            return None
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text")
        return text or None
    log.error("All candidate models failed; last error: %s", last_err)
    return None


def _parse_json_object(text: str) -> dict | None:
    """Parse a JSON object from a model reply, tolerating fences and prose."""
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)
    fb, lb = text.find("{"), text.rfind("}")
    if fb == -1 or lb <= fb:
        return None
    try:
        data = json.loads(text[fb : lb + 1])
    except json.JSONDecodeError as e:
        log.error("Model returned non-JSON: %s; first 500 chars: %s", e, text[:500])
        return None
    return data if isinstance(data, dict) else None


def _gather_weekly_articles(news_html: str, last_iso: str | None, today_iso: str) -> tuple[str, list[dict]]:
    """Articles for a weekly job: since its last success, widening to
    MAX_LOOKBACK_DAYS if that window holds fewer than two."""
    since = window_start(last_iso, today_iso)
    articles = _articles_for_synthesis(news_html, since, limit=20)
    if len(articles) < 2:
        wider = window_start("0000-01-01", today_iso)
        if wider < since:
            since, articles = wider, _articles_for_synthesis(news_html, wider, limit=20)
    return since, articles


def update_synthesis(news_html: str, today_iso: str) -> bool:
    """Regenerate the 'Where the Fight Stands' synthesis paragraphs and the
    three header badges in index.html from articles published or added since
    the last successful refresh. On success, stamps index.html with today's
    date and returns True; returns False on any soft failure (existing
    synthesis stays in place and the next daily run retries)."""
    if not INDEX_FILE.exists():
        log.warning("index.html not found; skipping synthesis update")
        return False

    idx_html = INDEX_FILE.read_text(encoding="utf-8")

    if _is_frozen(idx_html, "synthesis"):
        log.info("Synthesis is frozen by a news-bot:freeze marker; leaving it unchanged")
        return False

    since_date, articles = _gather_weekly_articles(
        news_html, read_stamp(idx_html, SYNTHESIS_STAMP), today_iso
    )
    if len(articles) < 2:
        log.warning(
            "Only %d article(s) published or added since %s; skipping synthesis",
            len(articles), since_date,
        )
        return False

    syn_re = re.compile(
        r'<div class="nd-synthesis">.*?</div>(\s*\n\s*<div class="nd-articles">)',
        re.DOTALL,
    )
    badge_re = re.compile(
        r'<div class="nd-badge-row">.*?</div>(\s*\n\s*</div>)',
        re.DOTALL,
    )
    syn_match = syn_re.search(idx_html)
    badge_match = badge_re.search(idx_html)
    if not (syn_match and badge_match):
        log.warning("Could not locate synthesis or badge-row markers; skipping")
        return False

    prior_synthesis = syn_match.group(0).split('<div class="nd-articles">')[0].strip()
    articles_block = "\n\n".join(
        f"[{a['date']}] {a['source']} ({a['tag']}) — {a['headline']}\n"
        f"  Summary: {a['summary'][:500]}\n"
        f"  URL: {a['url']}"
        for a in articles
    )

    prompt = SYNTHESIS_PROMPT.format(
        prior_synthesis=prior_synthesis,
        since_date=since_date,
        today=today_iso,
        articles_block=articles_block,
    )

    text = _complete(prompt, max_tokens=2000)
    if not text:
        log.warning("No text in synthesis response")
        return False
    data = _parse_json_object(text)
    if data is None:
        return False

    paragraphs = data.get("paragraphs", [])
    badges = data.get("badges", [])
    if len(paragraphs) != 2 or not all(isinstance(p, str) and len(p) > 50 for p in paragraphs):
        log.warning("Synthesis paragraph schema mismatch (expected 2 substantive strings)")
        return False
    if len(badges) != 3 or not all(isinstance(b, dict) and "emoji" in b and "label" in b for b in badges):
        log.warning("Synthesis badge schema mismatch (expected 3 dicts with emoji+label)")
        return False

    new_synthesis = (
        '<div class="nd-synthesis">\n'
        '      <h3>Where the Fight Stands</h3>\n'
        f'      <p>{paragraphs[0]}</p>\n'
        f'      <p>{paragraphs[1]}</p>\n'
        '    </div>'
    )
    badge_lines = "\n".join(
        f'        <span class="nd-badge">{b["emoji"]} {b["label"]}</span>'
        for b in badges
    )
    new_badges = (
        '<div class="nd-badge-row">\n'
        f'{badge_lines}\n'
        '      </div>'
    )

    new_idx = syn_re.sub(lambda m: new_synthesis + m.group(1), idx_html, count=1)
    new_idx = badge_re.sub(lambda m: new_badges + m.group(1), new_idx, count=1)
    new_idx = write_stamp(new_idx, SYNTHESIS_STAMP, today_iso, '<div class="nd-synthesis">')

    INDEX_FILE.write_text(new_idx, encoding="utf-8")
    log.info(
        "Updated synthesis from %d article(s) since %s: %d paragraphs (~%d words), %d badges",
        len(articles), since_date, len(paragraphs),
        sum(len(re.sub(r"<[^>]+>", "", p).split()) for p in paragraphs),
        len(badges),
    )
    return True


# ---------------------------------------------------------------------------
# Timeline (timeline.html) — weekly, sourced milestones only
# ---------------------------------------------------------------------------

TIMELINE_FILE = REPO_ROOT / "timeline.html"
TIMELINE_TYPES = {"removal": "Removal", "restoration": "Restoration", "legal": "Legal", "info": "Update"}
TIMELINE_MAX_NEW = 3
TIMELINE_TITLE_MAX = 80
TIMELINE_DESC_MAX = 320
# Events may predate the article window by this much (coverage lags events);
# anything older is re-reporting of history, not a new milestone.
TIMELINE_GRACE_DAYS = 14
_TL_EVENT_RE = re.compile(r'\n    <div class="timeline-event [^"]*"[^>]*\bdata-date="(\d{4}-\d{2}-\d{2})"')

TIMELINE_PROMPT = """You maintain the public timeline on MissingParkHistory.org, which tracks
the removal of history and science content from U.S. national parks and the
legal and public fight over it.

Below are news articles the site tracked since {since_date}, and the titles of
events already on the timeline. Pick AT MOST {max_new} genuine milestones from
these articles that are not already on the timeline: a removal or restoration of
specific content, a court ruling or major filing, a new law/order/budget action,
or a significant revelation (leak, data, investigation). Skip opinion pieces,
event announcements, re-reporting of older events, and minor follow-ups.
Returning zero events is fine and expected in slow weeks.

Hard rules:
- Use ONLY facts stated in the article summary. Do not add facts, numbers, or
  characterizations that are not in it.
- "url" must be copied exactly from one of the articles below.
- Only add events that HAPPENED on or after {earliest}. An article that newly
  reports an older event (e.g. a 2025 removal covered in 2026) is not a new
  milestone; skip it, especially if a similar event is already listed below.
- "date" is the exact day the event happened, as stated in the summary, else
  the article date if the article itself is the news; format YYYY-MM-DD. Never
  invent a day the summary does not give.
- "type" is one of: removal, restoration, legal, info.
- "title": plain text, at most 70 characters, headline case.
- "description": plain text, 1-2 neutral sentences, at most 280 characters.

EXISTING TIMELINE EVENTS (date, title; most recent first):
{existing_titles}

ARTICLES (most recent first):
{articles_block}

Return ONLY this JSON, starting with `{{`:
{{"events": [{{"date": "2026-09-30", "type": "info", "title": "...", "description": "...", "url": "https://..."}}]}}
"""


def _plain(text: str) -> str:
    """Model output → safe plain text: drop tags, decode then re-escape entities."""
    import html as _html
    text = _html.unescape(re.sub(r"<[^>]+>", "", str(text)))
    return _html.escape(re.sub(r"\s+", " ", text).strip(), quote=False)


def validate_timeline_events(raw: object, candidate_urls: set[str], existing_urls: set[str],
                             today_iso: str, earliest_iso: str = "2025-01-01") -> list[dict]:
    """Keep only well-formed events that cite a tracked article not already on
    the timeline and happened between earliest_iso and today_iso. Returns at
    most TIMELINE_MAX_NEW cleaned events."""
    out: list[dict] = []
    seen = set(existing_urls)
    if not isinstance(raw, list):
        return out
    for ev in raw:
        if not isinstance(ev, dict):
            continue
        url = str(ev.get("url", "")).strip()
        typ = str(ev.get("type", "")).strip().lower()
        date_s = str(ev.get("date", "")).strip()
        title = _plain(ev.get("title", ""))
        desc = _plain(ev.get("description", ""))
        if url not in candidate_urls or canonical_url(url) in seen:
            log.info("Timeline: dropping event with untracked or duplicate url %s", url)
            continue
        if typ not in TIMELINE_TYPES:
            continue
        try:
            d = datetime.strptime(date_s, "%Y-%m-%d").date()
        except ValueError:
            continue
        if d.isoformat() > today_iso or d.isoformat() < max(earliest_iso, "2025-01-01"):
            log.info("Timeline: dropping event dated %s (outside %s..%s)", d, earliest_iso, today_iso)
            continue
        if not (5 <= len(title) <= TIMELINE_TITLE_MAX and 20 <= len(desc) <= TIMELINE_DESC_MAX):
            continue
        seen.add(canonical_url(url))
        out.append({"date": d.isoformat(), "type": typ, "title": title, "description": desc, "url": url})
        if len(out) >= TIMELINE_MAX_NEW:
            break
    return out


def render_timeline_event(ev: dict) -> str:
    import html as _html
    d = datetime.strptime(ev["date"], "%Y-%m-%d")
    label = f"{d.strftime('%b')} {d.day}, {d.year}"
    typ = ev["type"]
    return (
        f'\n    <div class="timeline-event {typ}" data-type="{typ}" data-date="{ev["date"]}" data-added-by="news-bot">\n'
        f'      <div class="event-dot"></div>\n'
        f'      <div class="event-content">\n'
        f'        <div class="event-date">{label}</div>\n'
        f'        <span class="event-type {typ}">{TIMELINE_TYPES[typ]}</span>\n'
        f'        <div class="event-title">{ev["title"]}</div>\n'
        f'        <div class="event-description">{ev["description"]}</div>\n'
        f'        <a href="{_html.escape(ev["url"])}" class="event-link" target="_blank" rel="noopener">View details →</a>\n'
        f'      </div>\n'
        f'    </div>\n'
    )


def insert_timeline_event(tl_html: str, ev: dict) -> str:
    """Insert an event so events stay newest-first by data-date (a new event
    goes above existing events with the same date)."""
    block = render_timeline_event(ev)
    for m in _TL_EVENT_RE.finditer(tl_html):
        if m.group(1) <= ev["date"]:
            return tl_html[: m.start()] + block + tl_html[m.start() :]
    # Older than everything: append after the last event block.
    last_close = tl_html.rfind("\n    </div>\n", 0, tl_html.index('\n  </div>\n</div>\n\n<div class="sources">'))
    if last_close == -1:
        raise ValueError("timeline.html: no event blocks found")
    pos = last_close + len("\n    </div>\n")
    return tl_html[:pos] + block + tl_html[pos:]


def mark_timeline_modified(tl_html: str, today_iso: str) -> str:
    """Set the page's last-modified date (JSON-LD dateModified and the footer's
    <time class="tl-updated">) to today_iso."""
    d = datetime.strptime(today_iso, "%Y-%m-%d")
    pretty = f"{d.strftime('%B')} {d.day}, {d.year}"
    tl_html = re.sub(r'"dateModified":"\d{4}-\d{2}-\d{2}"', f'"dateModified":"{today_iso}"', tl_html, count=1)
    return re.sub(
        r'(<time class="tl-updated" datetime=")\d{4}-\d{2}-\d{2}(">)[^<]*(</time>)',
        lambda m: f"{m.group(1)}{today_iso}{m.group(2)}{pretty}{m.group(3)}",
        tl_html,
        count=1,
    )


def update_timeline(news_html: str, today_iso: str) -> str:
    """Add up to TIMELINE_MAX_NEW sourced milestones to timeline.html from news
    published or added since the timeline's last update. Returns a short status
    for the run summary. Stamps timeline.html after every successful model
    call (even when it picks zero events) so the job runs once a week."""
    if not TIMELINE_FILE.exists():
        return "skipped (timeline.html missing)"
    tl_html = TIMELINE_FILE.read_text(encoding="utf-8")
    if re.search(r"<!--\s*news-bot:freeze(?:-timeline)?\s*-->", tl_html):
        return "skipped (frozen by news-bot:freeze-timeline)"

    existing = {canonical_url(u) for u in re.findall(r'href="([^"]+)" class="event-link"', tl_html)}
    since, articles = _gather_weekly_articles(news_html, read_stamp(tl_html, TIMELINE_STAMP), today_iso)
    articles = [a for a in articles if a["url"] and canonical_url(a["url"]) not in existing]
    if not articles:
        return f"skipped (no new tracked articles since {since})"

    # Every existing event (not just recent ones) so older events newly
    # re-reported can be recognised as duplicates.
    listed = re.findall(
        r'data-date="(\d{4}-\d{2}-\d{2})".*?<div class="event-title">([^<]+)</div>', tl_html, re.DOTALL,
    )
    earliest = (datetime.strptime(since, "%Y-%m-%d").date().toordinal() - TIMELINE_GRACE_DAYS)
    earliest_iso = datetime.fromordinal(earliest).strftime("%Y-%m-%d")
    prompt = TIMELINE_PROMPT.format(
        since_date=since,
        earliest=earliest_iso,
        max_new=TIMELINE_MAX_NEW,
        existing_titles="\n".join(f"- {d} {t}" for d, t in listed),
        articles_block="\n\n".join(
            f"[{a['date']}] {a['source']} — {a['headline']}\n"
            f"  Summary: {re.sub(r'<[^>]+>', '', a['summary'])[:600]}\n"
            f"  URL: {a['url']}"
            for a in articles
        ),
    )
    text = _complete(prompt, max_tokens=1500)
    data = _parse_json_object(text) if text else None
    if data is None:
        return "skipped (model call failed)"

    events = validate_timeline_events(
        data.get("events"), {a["url"] for a in articles}, existing, today_iso, earliest_iso,
    )
    for ev in events:
        tl_html = insert_timeline_event(tl_html, ev)
    if events:
        tl_html = mark_timeline_modified(tl_html, today_iso)
    tl_html = write_stamp(tl_html, TIMELINE_STAMP, today_iso, '    <div class="timeline-event ')
    TIMELINE_FILE.write_text(tl_html, encoding="utf-8")
    for ev in events:
        log.info("Timeline: added %s %s — %s", ev["date"], ev["type"], ev["title"])
    return f"added {len(events)} event(s)" if events else "checked; no new milestones"


def run_weekly_jobs(news_html: str, today_iso: str, force: bool) -> list[str]:
    """Run whichever weekly jobs are due; return run-summary lines."""
    lines = []
    idx = INDEX_FILE.read_text(encoding="utf-8") if INDEX_FILE.exists() else ""
    if force or weekly_due(read_stamp(idx, SYNTHESIS_STAMP), today_iso):
        log.info("Refreshing weekly synthesis narrative.")
        ok = update_synthesis(news_html, today_iso)
        lines.append(f"- Weekly synthesis: **{'refreshed' if ok else 'skipped — see log; retries tomorrow'}**")
    else:
        lines.append(f"- Weekly synthesis: not due (last {read_stamp(idx, SYNTHESIS_STAMP)})")

    tl = TIMELINE_FILE.read_text(encoding="utf-8") if TIMELINE_FILE.exists() else ""
    if force or weekly_due(read_stamp(tl, TIMELINE_STAMP), today_iso):
        lines.append(f"- Timeline: **{update_timeline(news_html, today_iso)}**")
    else:
        lines.append(f"- Timeline: not due (last {read_stamp(tl, TIMELINE_STAMP)})")
    return lines


def archive(today_iso: str) -> None:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    dst = ARCHIVE_DIR / f"news-and-press_{today_iso.replace('-', '')}.html"
    shutil.copy2(HTML_FILE, dst)
    log.info("Archived previous version to %s", dst.relative_to(REPO_ROOT))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def emit_github_summary(lines: list[str]) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not path:
        return
    with open(path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="NPS news daily updater")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing")
    parser.add_argument("--force", action="store_true", help="Run even if banner already shows today")
    parser.add_argument(
        "--force-synthesis",
        action="store_true",
        help="Run the weekly synthesis + timeline jobs even if they are not due",
    )
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        log.error("ANTHROPIC_API_KEY not set")
        return 2

    html = load_html()
    today_iso = datetime.now().strftime("%Y-%m-%d")
    last = banner_date(html)
    log.info("Banner last-updated: %s | today: %s", last, today_iso)

    # Weekly jobs (synthesis + timeline) run whenever they are 7+ days stale.
    force_weekly = args.force_synthesis

    if last == today_iso and not args.force:
        log.info("Banner already shows today; nothing to do for articles.")
        weekly = [] if args.dry_run else run_weekly_jobs(html, today_iso, force_weekly)
        emit_github_summary([
            "## NPS News Daily Update",
            f"- Date: **{today_iso}**",
            "- Status: **Skipped articles** — banner already shows today.",
            *weekly,
        ])
        return 0

    # Call Claude
    # Search for articles from the last 21 days so we catch anything missed,
    # including articles that are slow to appear in search indexes.
    since = (datetime.now().date().toordinal() - 21)
    since_date = datetime.fromordinal(since).strftime("%Y-%m-%d")
    existing = existing_urls(html)
    articles = call_claude(since_date, existing)
    # Dedup any returned-but-already-present URLs, AND any duplicates within
    # the same response (e.g. canonical + mirror of one CNN article).
    seen: set[str] = set()
    deduped = []
    for a in articles:
        c = canonical_url(a.url)
        if c in existing or c in seen:
            continue
        seen.add(c)
        deduped.append(a)
    articles = sort_articles_desc(deduped)
    coerce_unlisted_sources(articles, html)
    log.info("Claude returned %d qualifying new article(s)", len(articles))

    if not articles:
        # Bump banner date only.
        new_html = update_banner(html, today_iso, article_count(html))
        if args.dry_run:
            log.info("[dry-run] Would bump banner date only.")
        else:
            archive(today_iso)
            write_html(new_html)
            update_news_digest(new_html, today_iso)
            weekly = run_weekly_jobs(new_html, today_iso, force_weekly)
            update_index_last_updated(today_iso)
            log.info("No new articles. Banner date bumped.")
        emit_github_summary([
            "## NPS News Daily Update",
            f"- Date: **{today_iso}**",
            "- Status: **No new articles**. Banner date updated.",
            *([] if args.dry_run else weekly),
        ])
        return 0

    # Insert newest-last so each insertion still lands at the top of the year.
    new_html = html
    for a in reversed(articles):
        card = render_card(a, today_iso)
        new_html = insert_card(new_html, card, a.year)

    new_html = update_banner(new_html, today_iso, article_count(new_html))

    if args.dry_run:
        log.info("[dry-run] Would add %d article(s):", len(articles))
        for a in articles:
            log.info("  %s — %s (%s)", a.date, a.headline, a.url)
        return 0

    archive(today_iso)
    write_html(new_html)
    update_news_digest(new_html, today_iso)
    weekly = run_weekly_jobs(new_html, today_iso, force_weekly)
    update_index_last_updated(today_iso)
    log.info("Wrote %s with %d new article(s)", HTML_FILE.name, len(articles))

    lines = [
        "## NPS News Daily Update",
        f"- Date: **{today_iso}**",
        f"- **{len(articles)} new article(s) added**",
        *weekly,
        "",
    ]
    for a in articles:
        lines.append(f"- **{a.date}** — [{a.source_name}]({a.url}) — {a.headline}")
    emit_github_summary(lines)
    return 0


if __name__ == "__main__":
    sys.exit(main())
