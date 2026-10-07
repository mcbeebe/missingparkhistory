#!/usr/bin/env python3
"""Regenerate sitemap.xml from the pages on disk.

Public pages are the root-level *.html files (minus drafts) and parks/*.html,
skipping pages that only redirect elsewhere. These are the same rules
tests/pages.ts uses for the layout tests. tests/python/test_sitemap.py fails
when sitemap.xml and the pages on disk disagree.

lastmod is each file's last commit date. changefreq and priority keep
whatever sitemap.xml already says for a URL; new URLs get the defaults below.

Usage:
    python scripts/build_sitemap.py           # rewrite sitemap.xml
    python scripts/build_sitemap.py --check   # exit 1 if a page is missing or stale
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = "https://missingparkhistory.org"
DRAFTS = {"logo-concepts.html", "logo-concepts-v2.html", "test-takeaction.html"}
# defaults for pages not yet in sitemap.xml: (changefreq, priority)
DEFAULTS = {
    "news-and-press.html": ("daily", "0.9"),
    "timeline.html": ("weekly", "0.8"),
    "legal-analysis.html": ("weekly", "0.8"),
}
ROOT_DEFAULT = ("monthly", "0.8")
PARK_DEFAULT = ("monthly", "0.7")


def is_redirect(path: Path) -> bool:
    return 'http-equiv="refresh"' in path.read_text(encoding="utf-8", errors="replace")


def public_pages(root: Path = ROOT) -> list[str]:
    """Repo-relative paths of every public page, in sitemap order."""
    top = sorted(p.name for p in root.glob("*.html") if p.name not in DRAFTS and not is_redirect(p))
    if "index.html" in top:
        top.remove("index.html")
        top.insert(0, "index.html")
    parks = sorted(f"parks/{p.name}" for p in (root / "parks").glob("*.html") if not is_redirect(p))
    return top + parks


def url_for(rel: str) -> str:
    return f"{SITE}/" if rel == "index.html" else f"{SITE}/{rel}"


def public_urls(root: Path = ROOT) -> list[str]:
    return [url_for(rel) for rel in public_pages(root)]


def last_commit_date(rel: str, root: Path = ROOT) -> str | None:
    out = subprocess.run(["git", "-C", str(root), "log", "-1", "--format=%cs", "--", rel],
                         capture_output=True, text=True).stdout.strip()
    return out or None


def existing_settings(xml: str) -> dict[str, tuple[str, str]]:
    found = {}
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>([^<]+)</loc>", block)
        cf = re.search(r"<changefreq>([^<]+)</changefreq>", block)
        pr = re.search(r"<priority>([^<]+)</priority>", block)
        if loc and cf and pr:
            found[loc.group(1).strip()] = (cf.group(1).strip(), pr.group(1).strip())
    return found


def build(root: Path = ROOT) -> str:
    path = root / "sitemap.xml"
    keep = existing_settings(path.read_text()) if path.exists() else {}
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel in public_pages(root):
        url = url_for(rel)
        default = PARK_DEFAULT if rel.startswith("parks/") else DEFAULTS.get(rel, ROOT_DEFAULT)
        changefreq, priority = keep.get(url, default)
        lines.append("  <url>")
        lines.append(f"    <loc>{url}</loc>")
        lastmod = last_commit_date(rel, root)
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{changefreq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main() -> int:
    path = ROOT / "sitemap.xml"
    if "--check" in sys.argv:
        listed = set(re.findall(r"<loc>([^<]+)</loc>", path.read_text()))
        expected = set(public_urls())
        missing, stale = sorted(expected - listed), sorted(listed - expected)
        for u in missing:
            print(f"missing: {u}")
        for u in stale:
            print(f"not a public page: {u}")
        return 1 if missing or stale else 0
    path.write_text(build())
    print(f"sitemap.xml: {len(public_pages())} URLs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
