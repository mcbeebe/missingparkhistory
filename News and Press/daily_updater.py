#!/usr/bin/env python3
"""
NPS News & Press Daily Updater
================================
Automatically searches for new articles about NPS censorship / SO 3431 / EO 14253,
generates article card HTML via the Anthropic API, and inserts them into
news-and-press.html in chronological order.

Requirements:
    pip install anthropic requests beautifulsoup4

Environment variables:
    ANTHROPIC_API_KEY   — Your Anthropic API key
    SERPER_API_KEY      — (Optional) Serper.dev API key for web search
                          If not set, falls back to a simple requests-based search.

Usage:
    python daily_updater.py                  # Run the updater
    python daily_updater.py --dry-run        # Preview without modifying HTML
    python daily_updater.py --force          # Run even if already updated today
"""

import os
import re
import sys
import json
import shutil
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import anthropic
import requests
from bs4 import BeautifulSoup

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).parent.resolve()
HTML_FILE = SCRIPT_DIR / "news-and-press.html"
ARCHIVE_DIR = SCRIPT_DIR / "Archive"
LOG_FILE = SCRIPT_DIR / "updater.log"

SEARCH_QUERIES = [
    "NPS sign removal national park censorship {month} {year}",
    "Secretary Order 3431 national park {month} {year}",
    "national park exhibit removed signs {month} {year}",
    "NPCA national parks lawsuit Democracy Forward {year}",
    "MissingParkHistory Save Our Signs national park {year}",
    "national park interpretive sign executive order {month} {year}",
    "Sierra Club national park FOIA {year}",
]

# Sources to check directly (RSS or news pages)
KEY_SOURCES = [
    "https://www.npca.org/news",
    "https://www.nationalparkstraveler.org",
    "https://democracyforward.org/news",
]

ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="a"),
    ],
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Web Search
# ---------------------------------------------------------------------------

def search_serper(query: str, api_key: str, num_results: int = 10) -> list[dict]:
    """Search via Serper.dev API."""
    resp = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
        json={"q": query, "num": num_results},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("link", ""),
            "snippet": item.get("snippet", ""),
            "date": item.get("date", ""),
            "source": item.get("source", ""),
        })
    return results


def search_duckduckgo(query: str, num_results: int = 10) -> list[dict]:
    """Fallback: scrape DuckDuckGo Lite for results."""
    try:
        resp = requests.get(
            "https://lite.duckduckgo.com/lite/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0 (NPS-News-Updater/1.0)"},
            timeout=15,
        )
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        results = []
        for a_tag in soup.select("a.result-link")[:num_results]:
            results.append({
                "title": a_tag.get_text(strip=True),
                "url": a_tag.get("href", ""),
                "snippet": "",
                "date": "",
                "source": "",
            })
        return results
    except Exception as e:
        log.warning(f"DuckDuckGo fallback failed: {e}")
        return []


def run_searches() -> list[dict]:
    """Run all search queries and return deduplicated results."""
    now = datetime.now()
    month = now.strftime("%B")
    year = str(now.year)

    serper_key = os.environ.get("SERPER_API_KEY", "")
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    for query_template in SEARCH_QUERIES:
        query = query_template.format(month=month, year=year)
        log.info(f"Searching: {query}")

        try:
            if serper_key:
                results = search_serper(query, serper_key)
            else:
                results = search_duckduckgo(query)
        except Exception as e:
            log.warning(f"Search failed for '{query}': {e}")
            continue

        for r in results:
            url = r.get("url", "").rstrip("/")
            if url and url not in seen_urls:
                seen_urls.add(url)
                all_results.append(r)

    log.info(f"Total unique search results: {len(all_results)}")
    return all_results


# ---------------------------------------------------------------------------
# HTML Parsing Helpers
# ---------------------------------------------------------------------------

def get_existing_urls(html_content: str) -> set[str]:
    """Extract all article URLs already in the HTML."""
    return set(re.findall(r'href="(https?://[^"]+)"', html_content))


def get_last_update_date(html_content: str) -> Optional[str]:
    """Extract the last-updated date from the banner."""
    match = re.search(r'datetime="(\d{4}-\d{2}-\d{2})"', html_content)
    return match.group(1) if match else None


def update_banner_date(html_content: str, new_date: str, article_count: int) -> str:
    """Update the banner with new date and article count."""
    # Update date
    html_content = re.sub(
        r'datetime="\d{4}-\d{2}-\d{2}"',
        f'datetime="{new_date}"',
        html_content,
    )
    html_content = re.sub(
        r'>(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}<',
        f'>{datetime.strptime(new_date, "%Y-%m-%d").strftime("%B %d, %Y").replace(" 0", " ")}<',
        html_content,
    )
    # Update article count
    html_content = re.sub(
        r'\d+ articles tracked',
        f'{article_count} articles tracked',
        html_content,
    )
    return html_content


# ---------------------------------------------------------------------------
# Claude API: Evaluate & Generate
# ---------------------------------------------------------------------------

def evaluate_and_generate(
    client: anthropic.Anthropic,
    search_results: list[dict],
    existing_urls: set[str],
    html_content: str,
) -> list[str]:
    """
    Use Claude to:
    1. Filter search results for relevance and novelty
    2. Generate properly formatted article card HTML for new entries
    """
    # Prepare search results as context
    results_text = ""
    for i, r in enumerate(search_results):
        results_text += (
            f"\n--- Result {i+1} ---\n"
            f"Title: {r['title']}\n"
            f"URL: {r['url']}\n"
            f"Date: {r.get('date', 'unknown')}\n"
            f"Source: {r.get('source', 'unknown')}\n"
            f"Snippet: {r.get('snippet', '')}\n"
        )

    existing_urls_text = "\n".join(sorted(existing_urls)[:100])

    prompt = f"""You are the MissingParkHistory.org news curator. Your job is to review search 
results and identify NEW, relevant articles about NPS sign/exhibit censorship under 
Executive Order 14253 and Secretary's Order 3431.

EXISTING URLS ALREADY ON THE PAGE (do NOT duplicate these):
{existing_urls_text}

SEARCH RESULTS TO EVALUATE:
{results_text}

INSTRUCTIONS:
1. Filter for articles that are:
   - Directly about NPS sign/exhibit censorship, SO 3431, EO 14253, related lawsuits, 
     or preservation/resistance efforts
   - NOT already on the page (check URLs above)
   - From reputable sources (major news outlets, advocacy orgs, academic journals)
   - Contain genuinely new information (not just rewrites of existing coverage)

2. For each qualifying article, generate an HTML article card using EXACTLY this format:

<article class="article-card" data-tags="TAG_CLASS">
  <div class="article-date">
    <div class="month-day">Mon DD</div>
    <div class="date-detail">YYYY</div>
  </div>
  <div class="article-body">
    <div class="article-meta">
      <span class="article-source">SOURCE NAME</span>
      <span class="article-tag tag-CLASS">TAG LABEL</span>
    </div>
    <h3><a href="URL" target="_blank">HEADLINE</a></h3>
    <p class="article-summary">2-4 sentence paraphrased summary with key facts.</p>
    <a href="URL" class="read-more" target="_blank">Read at Source &rarr;</a>
  </div>
</article>

Valid tag classes: order, removal, resistance, lawsuit, leak, court
Valid tag CSS classes: tag-order, tag-removal, tag-resistance, tag-lawsuit, tag-leak, tag-court

3. Return ONLY the HTML cards, one per article, separated by a blank line.
   If no new relevant articles are found, return exactly: NO_NEW_ARTICLES

4. CRITICAL: Every summary must be paraphrased in your own words. Never quote directly.
   Include specific names, dates, numbers. Note why each article matters.
"""

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
        )
        result_text = response.content[0].text.strip()

        if result_text == "NO_NEW_ARTICLES":
            log.info("Claude found no new relevant articles.")
            return []

        # Extract article cards
        cards = re.findall(
            r'<article class="article-card".*?</article>',
            result_text,
            re.DOTALL,
        )
        log.info(f"Claude generated {len(cards)} new article cards.")
        return cards

    except Exception as e:
        log.error(f"Anthropic API call failed: {e}")
        return []


# ---------------------------------------------------------------------------
# HTML Insertion
# ---------------------------------------------------------------------------

def insert_cards(html_content: str, new_cards: list[str]) -> str:
    """Insert new article cards into the HTML in chronological order."""
    for card in new_cards:
        # Extract the year from the card
        year_match = re.search(r'<div class="date-detail">(\d{4})</div>', card)
        if not year_match:
            log.warning("Could not extract year from card, skipping.")
            continue
        year = year_match.group(1)

        # Find the year section
        year_marker_pattern = (
            rf'<div class="year-marker"><h2>{year}</h2></div>'
        )
        if year_marker_pattern not in html_content and re.search(
            rf'class="year-marker">\s*<h2>{year}</h2>', html_content
        ) is None:
            # Need to create a new year section — insert before the footer
            new_section = f'\n  <div class="year-marker"><h2>{year}</h2></div>\n'
            html_content = html_content.replace(
                "</section>\n\n<!-- FOOTER -->",
                f"{new_section}\n</section>\n\n<!-- FOOTER -->",
            )

        # Insert the card at the end of the year section (before next year or </section>)
        # Find position after the year marker's last article
        next_year = str(int(year) + 1)
        next_year_marker = f'<div class="year-marker"><h2>{next_year}</h2></div>'

        if next_year_marker in html_content:
            # Insert before the next year marker
            html_content = html_content.replace(
                f"\n  {next_year_marker}",
                f"\n\n  {card}\n\n  {next_year_marker}",
            )
        else:
            # Insert before </section> (end of timeline)
            html_content = html_content.replace(
                "\n</section>\n\n<!-- FOOTER -->",
                f"\n\n  {card}\n\n</section>\n\n<!-- FOOTER -->",
            )

    return html_content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="NPS News Daily Updater")
    parser.add_argument("--dry-run", action="store_true", help="Preview without modifying HTML")
    parser.add_argument("--force", action="store_true", help="Run even if already updated today")
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("NPS News & Press Daily Updater — Starting")
    log.info("=" * 60)

    # Check API key
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        log.error("ANTHROPIC_API_KEY environment variable not set. Exiting.")
        sys.exit(1)

    # Read current HTML
    if not HTML_FILE.exists():
        log.error(f"HTML file not found: {HTML_FILE}")
        sys.exit(1)

    html_content = HTML_FILE.read_text(encoding="utf-8")

    # Check if already updated today
    today = datetime.now().strftime("%Y-%m-%d")
    last_update = get_last_update_date(html_content)
    if last_update == today and not args.force:
        log.info(f"Already updated today ({today}). Use --force to override.")
        return

    # Archive previous version
    if not args.dry_run:
        ARCHIVE_DIR.mkdir(exist_ok=True)
        archive_name = f"news-and-press_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        shutil.copy2(HTML_FILE, ARCHIVE_DIR / archive_name)
        log.info(f"Archived previous version: {archive_name}")

    # Run searches
    search_results = run_searches()
    if not search_results:
        log.info("No search results found. Updating banner date only.")
        if not args.dry_run:
            article_count = html_content.count('class="article-card"')
            html_content = update_banner_date(html_content, today, article_count)
            HTML_FILE.write_text(html_content, encoding="utf-8")
            log.info("Banner date updated. No new articles.")
        return

    # Get existing URLs to avoid duplicates
    existing_urls = get_existing_urls(html_content)

    # Use Claude to evaluate and generate cards
    client = anthropic.Anthropic(api_key=api_key)
    new_cards = evaluate_and_generate(client, search_results, existing_urls, html_content)

    if not new_cards:
        log.info("No new articles to add. Updating banner date only.")
        if not args.dry_run:
            article_count = html_content.count('class="article-card"')
            html_content = update_banner_date(html_content, today, article_count)
            HTML_FILE.write_text(html_content, encoding="utf-8")
        return

    if args.dry_run:
        log.info("=== DRY RUN — New cards that would be added: ===")
        for card in new_cards:
            print(card)
            print()
        return

    # Insert cards
    html_content = insert_cards(html_content, new_cards)

    # Update banner
    article_count = html_content.count('class="article-card"')
    html_content = update_banner_date(html_content, today, article_count)

    # Write
    HTML_FILE.write_text(html_content, encoding="utf-8")
    log.info(f"Updated HTML with {len(new_cards)} new articles. Total: {article_count}")

    # Git commit
    try:
        import subprocess
        subprocess.run(["git", "add", "news-and-press.html"], cwd=SCRIPT_DIR, check=True)
        commit_msg = f"news: auto-update {today} — added {len(new_cards)} article(s)"
        subprocess.run(["git", "commit", "-m", commit_msg], cwd=SCRIPT_DIR, check=True)
        log.info(f"Git commit: {commit_msg}")
    except Exception as e:
        log.warning(f"Git commit failed (non-fatal): {e}")

    log.info("Done.")


if __name__ == "__main__":
    main()
