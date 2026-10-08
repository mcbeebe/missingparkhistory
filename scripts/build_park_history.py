#!/usr/bin/env python3
"""Park History data layer: per-park source files -> compiled data/parkHistory.json.

Each park unit gets one hand-authored file, data/park_history/<CODE>.json, holding a
sourced history of the site (summary, theme sections, photos, a fact ledger and the
NPSHistory.com anchor documents).  This script compiles those files into the single
minified data/parkHistory.json that index.html fetches, seeds files from the history
paragraphs that older parks/*.html pages carry, checks the compiled file is current, and
renders the shared "Park History" HTML block used by the park-page generator.

Schema (data/park_history/<CODE>.json) -- see docs/park-history-authoring.md:
  code, name, entries[], reviewStatus (legacy-unsourced|draft|reviewed|published),
  lastReviewed, author, verifiedBy, summary (HTML paragraphs), themes{key:{html, sources[]}},
  facts[{claim, sourceUrl, locator, interpretive?}], photos[{file, caption, credit, license,
  sourceUrl, imageUrl, evidenceUrl, capturedAt, waybackUrl?, themeKey?, width, height, bytes}],
  photoStatus, npshistory{indexUrl, adhiUrl, hrsUrl, ethnoUrls[], brochureUrls[], docCount},
  wayback{main}, corrections[{date, note}]

Only `published` parks render in the map modal; `legacy-unsourced` and `draft` text is
shown only on the parks/ pages (where it already was), never promoted.

Usage:
    python scripts/build_park_history.py --compile          # write data/parkHistory.json
    python scripts/build_park_history.py --check            # exit 1 if the compiled file is stale
    python scripts/build_park_history.py --seed-from-pages  # create legacy files from parks/*.html
    python scripts/build_park_history.py --render MORA      # print the HTML block for one park
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
SRC_DIR = DATA / "park_history"
COMPILED = DATA / "parkHistory.json"
NPSH_INDEX = DATA / "npshistory_index.json"

THEMES = ["indigenous", "women", "black", "slavery", "climate",
          "labor_ccc", "lgbtq", "japanese_american", "latino"]
THEME_LABELS = {
    "indigenous": "Indigenous peoples",
    "women": "Women",
    "black": "Black history",
    "slavery": "Slavery",
    "climate": "Climate & environment",
    "labor_ccc": "Labor & the New Deal",
    "lgbtq": "LGBTQ+ history",
    "japanese_american": "Japanese American incarceration",
    "latino": "Latino & Hispanic heritage",
}
REVIEW_STATUSES = ("legacy-unsourced", "draft", "reviewed", "published")
LICENSES = ("PD-USGov-NPS", "PD-USGov", "PD-LOC-HABS-HAER", "PD-old", "CC0")
LICENSE_LABELS = {
    "PD-USGov-NPS": "Public domain (U.S. Government work)",
    "PD-USGov": "Public domain (U.S. Government work)",
    "PD-LOC-HABS-HAER": "Public domain (Library of Congress, HABS/HAER/HALS)",
    "PD-old": "Public domain",
    "CC0": "Public domain (CC0)",
}
BANNED = ("is one of hundreds of", "466+", "under review", "TODO")
ALLOWED_TAGS = {"p", "a", "em", "strong", "ul", "li", "br"}

PLACEHOLDER = "NPSHistory.com keeps the administrative histories"
PARK_LOC_RE = re.compile(r'<div class="park-location">\s*([A-Z]{4})\b')
HIST_P_RE = re.compile(r'park-history-section.*?<p style="font-size:15px;line-height:1\.75;color:#b8b8c0;margin-bottom:20px">(.*?)</p>', re.S)
H1_RE = re.compile(r"<h1>(.*?)</h1>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
P_RE = re.compile(r"<p(?:\s[^>]*)?>(.*?)</p>", re.S | re.I)
HREF_RE = re.compile(r'<a\s[^>]*href="(https?://[^"]+)"', re.I)


# --------------------------------------------------------------------------- io

def load_sources() -> dict[str, dict]:
    out: dict[str, dict] = {}
    for f in sorted(SRC_DIR.glob("*.json")):
        rec = json.loads(f.read_text())
        code = rec.get("code") or f.stem
        if code != f.stem:
            raise ValueError(f"{f.name}: code field {code!r} does not match the file name")
        out[code] = rec
    return out


def compile_sources(sources: dict[str, dict]) -> dict:
    """The compiled file keeps what the site renders and drops authoring-only fields.
    A source file of the form {"code": X, "aliasOf": Y} makes X render Y's history
    (two map codes for one park unit, e.g. CACR and CARI for Cane River Creole)."""
    parks = {}
    for code, rec in sources.items():
        if rec.get("aliasOf"):
            continue
        parks[code] = {
            "name": rec.get("name"),
            "reviewStatus": rec.get("reviewStatus"),
            "lastReviewed": rec.get("lastReviewed"),
            "summary": rec.get("summary", ""),
            "sources": rec.get("sources", []),
            "themes": {k: {"html": v.get("html", ""), "sources": v.get("sources", [])}
                       for k, v in (rec.get("themes") or {}).items()},
            "photos": rec.get("photos", []),
            "npshistory": rec.get("npshistory", {}),
            "corrections": rec.get("corrections", []),
        }
    for code, rec in sources.items():
        target = rec.get("aliasOf")
        if target and target in parks:
            parks[code] = parks[target]
    return {"_meta": {"parks": len(parks), "themes": THEMES, "labels": THEME_LABELS}, "parks": parks}


def dumps_compiled(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"


# --------------------------------------------------------------------------- seed

def seed_from_pages(root: Path = ROOT, today: str | None = None) -> list[str]:
    """Create legacy-unsourced files from the hand-written paragraph on each parks/*.html page.
    Existing files are never overwritten."""
    today = today or dt.date.today().isoformat()
    npsh = json.loads(NPSH_INDEX.read_text())["parks"] if NPSH_INDEX.exists() else {}
    created: list[str] = []
    SRC_DIR.mkdir(parents=True, exist_ok=True)
    for f in sorted((root / "parks").glob("*.html")):
        html = f.read_text(errors="replace")
        if 'http-equiv="refresh"' in html:
            continue
        m = PARK_LOC_RE.search(html)
        if not m:
            continue
        code = m.group(1)
        target = SRC_DIR / f"{code}.json"
        if target.exists():
            continue
        hm = HIST_P_RE.search(html)
        name_m = H1_RE.search(html)
        name = htmllib.unescape(TAG_RE.sub("", name_m.group(1))).strip() if name_m else code
        para = hm.group(1).strip() if hm else ""
        legacy = bool(para) and not para.startswith(PLACEHOLDER)
        info = npsh.get(code, {})
        anchors = info.get("anchors", {})
        rec = {
            "code": code,
            "name": name,
            "entries": [],
            "reviewStatus": "legacy-unsourced" if legacy else "draft",
            "lastReviewed": today,
            "author": "parks-page-legacy" if legacy else "",
            "verifiedBy": "",
            "summary": f"<p>{para}</p>" if legacy else "",
            "themes": {},
            "facts": [],
            "photos": [],
            "photoStatus": "none-yet",
            "npshistory": {
                "indexUrl": info.get("url"),
                "adhiUrl": (anchors.get("adhi") or [{}])[0].get("u"),
                "hrsUrl": (anchors.get("hrs") or [{}])[0].get("u"),
                "ethnoUrls": [a["u"] for a in anchors.get("ethno", [])][:5],
                "brochureUrls": [a["u"] for a in anchors.get("brochure", [])][:3],
                "docCount": info.get("doc_total", 0),
            },
            "wayback": {"main": f"https://web.archive.org/web/20250119/https://www.nps.gov/{code.lower()}/index.htm"},
            "corrections": [],
        }
        target.write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n")
        created.append(code)
    return created


# --------------------------------------------------------------------------- validate

def validate(rec: dict) -> list[str]:
    """Return a list of problems; empty means the record is acceptable for its reviewStatus."""
    problems: list[str] = []
    code = rec.get("code", "?")
    if rec.get("aliasOf"):
        extra = set(rec) - {"code", "aliasOf", "note"}
        if extra:
            problems.append(f"{code}: an alias file may only hold code, aliasOf and note (found {sorted(extra)})")
        return problems
    status = rec.get("reviewStatus")
    if status not in REVIEW_STATUSES:
        problems.append(f"{code}: reviewStatus {status!r} not in {REVIEW_STATUSES}")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(rec.get("lastReviewed", ""))):
        problems.append(f"{code}: lastReviewed must be YYYY-MM-DD")
    for key in rec.get("themes") or {}:
        if key not in THEMES:
            problems.append(f"{code}: unknown theme {key!r}")
    blocks = [("summary", rec.get("summary", ""))] + [(f"themes.{k}", v.get("html", "")) for k, v in (rec.get("themes") or {}).items()]
    for label, html in blocks:
        for tag in set(re.findall(r"</?([a-zA-Z0-9]+)", html)):
            if tag.lower() not in ALLOWED_TAGS:
                problems.append(f"{code}: {label} uses disallowed tag <{tag}>")
        for banned in BANNED:
            if banned in html:
                problems.append(f"{code}: {label} contains banned text {banned!r}")
    if status == "published":
        if not rec.get("verifiedBy") or rec.get("verifiedBy") == rec.get("author"):
            problems.append(f"{code}: published parks need a verifiedBy different from author")
        if not rec.get("facts"):
            problems.append(f"{code}: published parks need a facts[] ledger")
        all_sources = {s.get("url") for t in (rec.get("themes") or {}).values() for s in t.get("sources", [])}
        all_sources |= {s.get("url") for s in rec.get("sources", [])}
        for i, fact in enumerate(rec.get("facts") or []):
            if not fact.get("claim") or not fact.get("sourceUrl") or not fact.get("locator"):
                problems.append(f"{code}: facts[{i}] needs claim, sourceUrl and locator")
            elif fact["sourceUrl"] not in all_sources and not fact["sourceUrl"].startswith("https://npshistory.com/"):
                problems.append(f"{code}: facts[{i}] cites a URL that is not in any sources[] list")
        for label, html in blocks:
            if not html:
                continue
            for j, para in enumerate(P_RE.findall(html)):
                if not HREF_RE.search(para):
                    problems.append(f"{code}: {label} paragraph {j + 1} has no inline citation")
                if re.search(r"https?://[a-z.]*(wikipedia|britannica)\.", para, re.I) and len(HREF_RE.findall(para)) == 1:
                    problems.append(f"{code}: {label} paragraph {j + 1} cites only Wikipedia/Britannica")
        for key, theme in (rec.get("themes") or {}).items():
            if not theme.get("sources"):
                problems.append(f"{code}: themes.{key} has no sources[]")
            inline = set(HREF_RE.findall(theme.get("html", "")))
            listed = {s.get("url") for s in theme.get("sources", [])}
            missing = inline - listed
            if missing:
                problems.append(f"{code}: themes.{key} cites {sorted(missing)} inline but not in sources[]")
        words = len(TAG_RE.sub(" ", rec.get("summary", "")).split())
        if not 80 <= words <= 400:
            problems.append(f"{code}: summary is {words} words (want 80-400)")
        for i, ph in enumerate(rec.get("photos") or []):
            for field in ("file", "caption", "credit", "license", "sourceUrl", "imageUrl", "evidenceUrl", "capturedAt"):
                if not ph.get(field):
                    problems.append(f"{code}: photos[{i}] missing {field}")
            if ph.get("themeKey") and ph["themeKey"] not in (rec.get("themes") or {}):
                problems.append(f"{code}: photos[{i}] themeKey {ph['themeKey']!r} has no matching theme section")
            if ph.get("license") not in LICENSES:
                problems.append(f"{code}: photos[{i}] license {ph.get('license')!r} not in {LICENSES}")
            if re.search(r"courtesy|©|copyright|all rights reserved", str(ph.get("credit", "")), re.I):
                problems.append(f"{code}: photos[{i}] credit {ph.get('credit')!r} is not a public-domain credit")
            f = ROOT / str(ph.get("file", ""))
            if ph.get("file") and not f.exists():
                problems.append(f"{code}: photos[{i}] file {ph['file']} does not exist")
            elif ph.get("file") and f.stat().st_size > 250 * 1024:
                problems.append(f"{code}: photos[{i}] file {ph['file']} exceeds 250 KB")
    return problems


# --------------------------------------------------------------------------- render

def _esc(s: str) -> str:
    return htmllib.escape(str(s or ""), quote=True)


def photo_figure(ph: dict) -> str:
    lic = LICENSE_LABELS.get(ph.get("license"), ph.get("license", ""))
    return (f'<figure class="ph-photo"><img src="/{_esc(ph["file"])}" alt="{_esc(ph["caption"])}" loading="lazy"'
            + (f' width="{int(ph["width"])}" height="{int(ph["height"])}"' if ph.get("width") and ph.get("height") else "") + '>'
            f'<figcaption>{_esc(ph["caption"])} &middot; <span class="ph-credit">Photo: {_esc(ph["credit"])} &middot; '
            f'{_esc(lic)} &middot; <a href="{_esc(ph["sourceUrl"])}" target="_blank" rel="noopener">source &#8599;</a></span></figcaption></figure>')


def render_block(rec: dict, mode: str = "page") -> str:
    """The Option-A 'Dossier' block: photo -> summary -> theme sections -> sources -> archive link.
    mode='page' is the parks/*.html card body; mode='modal' is the markup index.html builds.
    Only published parks get the full block; everything else gets the legacy paragraph (if any)
    plus the NPSHistory link so the card never regresses."""
    status = rec.get("reviewStatus")
    npsh = rec.get("npshistory") or {}
    index_url = npsh.get("indexUrl")
    parts: list[str] = []
    if status == "published":
        # Photos without a themeKey lead the section; a photo tagged with a theme sits inside it.
        for ph in rec.get("photos") or []:
            if not ph.get("themeKey"):
                parts.append(photo_figure(ph))
        # Citation numbering is derived here (summary sources first, then themes in THEMES order),
        # and the inline [n] markers are rewritten to match, so authors never hand-number.
        seen: list[dict] = []
        def add(src: dict) -> None:
            if src.get("url") and not any(x["url"] == src["url"] for x in seen):
                seen.append({"url": src["url"], "title": src.get("title", src["url"])})
        for s in rec.get("sources", []):
            add(s)
        theme_keys = [k for k in THEMES if (rec.get("themes") or {}).get(k, {}).get("html")]
        for key in theme_keys:
            for s in rec["themes"][key].get("sources", []):
                add(s)
        for key in theme_keys:
            for url in HREF_RE.findall(rec["themes"][key]["html"]):
                add({"url": url})
        for url in HREF_RE.findall(rec.get("summary", "")):
            add({"url": url})
        number = {s["url"]: i + 1 for i, s in enumerate(seen)}
        def renumber(html: str) -> str:
            return re.sub(r'(<a\s[^>]*href="(https?://[^"]+)"[^>]*class="cite"[^>]*>)\[[^\]]*\](</a>)',
                          lambda m: f"{m.group(1)}[{number.get(m.group(2), '?')}]{m.group(3)}", html)
        parts.append(f'<div class="ph-summary">{renumber(rec.get("summary", ""))}</div>')
        for key in theme_keys:
            figs = "".join(photo_figure(ph) for ph in rec.get("photos") or [] if ph.get("themeKey") == key)
            parts.append(f'<section class="ph-theme"><h4>{_esc(THEME_LABELS[key])}</h4>{figs}{renumber(rec["themes"][key]["html"])}</section>')
        if seen:
            parts.append('<h4 class="ph-h">Sources</h4><ol class="ph-sources">' + "".join(
                f'<li><a href="{_esc(s["url"])}" target="_blank" rel="noopener">{_esc(s["title"])}</a></li>' for s in seen) + "</ol>")
        if rec.get("corrections"):
            last = rec["corrections"][-1]
            parts.append(f'<p class="ph-updated">Updated {_esc(last.get("date"))}: {_esc(last.get("note"))}</p>')
    elif rec.get("summary"):
        parts.append(f'<div class="ph-summary ph-legacy">{rec["summary"]}</div>')
    if index_url:
        n = npsh.get("docCount") or 0
        label = f"Documentary record: {n} documents on NPSHistory.com" if n else "Documentary record on NPSHistory.com"
        parts.append(f'<div class="ph-row"><a href="{_esc(index_url)}" target="_blank" rel="noopener">{label} &#8599;</a></div>')
    return "".join(parts)


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--compile", action="store_true", help="write data/parkHistory.json from data/park_history/*.json")
    ap.add_argument("--check", action="store_true", help="validate sources and fail if the compiled file is stale")
    ap.add_argument("--seed-from-pages", action="store_true", help="create legacy files from parks/*.html history paragraphs")
    ap.add_argument("--render", metavar="CODE", help="print the HTML block for one park")
    args = ap.parse_args(argv)

    if args.seed_from_pages:
        created = seed_from_pages()
        print(f"seeded {len(created)} park files: {', '.join(created)}")
    sources = load_sources() if SRC_DIR.exists() else {}
    problems = [p for rec in sources.values() for p in validate(rec)]
    if args.render:
        rec = sources.get(args.render.upper())
        if not rec:
            print(f"no data/park_history/{args.render.upper()}.json", file=sys.stderr)
            return 1
        print(render_block(rec))
        return 0
    compiled = dumps_compiled(compile_sources(sources))
    if args.compile:
        COMPILED.write_text(compiled)
        print(f"wrote {COMPILED} ({len(sources)} parks)")
    if args.check:
        for p in problems:
            print("problem:", p)
        stale = not COMPILED.exists() or COMPILED.read_text() != compiled
        if stale:
            print("data/parkHistory.json is stale; run: python scripts/build_park_history.py --compile")
        return 1 if (problems or stale) else 0
    if problems and not args.compile:
        for p in problems:
            print("problem:", p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
