#!/usr/bin/env python3
"""Audit MissingParkHistory.org park records against NPSHistory.com.

NPSHistory.com (npshistory.com) is an independent, public-domain archive of
National Park Service publications: administrative histories, historic
resource studies, ethnographic overviews, cultural landscape inventories,
brochures, National Register nominations, glacier/climate studies, park
newspapers.  Every park has an archive page at
    https://npshistory.com/publications/<code>/index.htm

This script answers, for every park unit on the map (data/parkData.json):
  * what does MPH currently say about it (boilerplate vs. custom narrative,
    topics, photos, park page, Wayback link health)?
  * what does NPSHistory hold for it (document counts by category, and by
    sensitive-history theme: Indigenous, women, Black history, slavery,
    climate, labor/CCC, LGBTQ+, Japanese American incarceration, Latino)?
  * where are the gaps, and in what order should they be filled?

Steps:
  1. Resolve each MPH code to its NPSHistory page.  URLs are discovered from
     NPSHistory's own park index (home-page <select> + park_histories.htm
     anchors), then by park-name match; data/npshistory_aliases.json covers
     the rest (admin units with no page, FWS/BLM codes, one BLM override).
  2. Fetch every park page politely (browser User-Agent -- the site 403s bare
     clients -- ~1 request/second, 3 retries, on-disk cache in .cache/).
  3. Parse the document list and classify each title with the keyword rules
     in data/npshistory_themes.json.
  4. Score MPH's current coverage per code and compute theme gaps.
  5. Write data/npshistory_index.json (per-code NPSHistory inventory for
     authors) and data/npshistory_audit.json (the mapping table), plus
     optional CSV / XLSX.

Usage:
    python scripts/npshistory_audit.py                    # full run (uses cache when present)
    python scripts/npshistory_audit.py --refresh          # re-validate cached pages (conditional GETs)
    python scripts/npshistory_audit.py --offline          # never touch the network
    python scripts/npshistory_audit.py --codes MORA,CAWO  # a few parks (quick check)
    python scripts/npshistory_audit.py --csv out.csv --xlsx out.xlsx

Only the standard library is required; openpyxl is imported only for --xlsx.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html as htmllib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
CACHE = ROOT / ".cache" / "npshistory"

HOME = "https://npshistory.com/"
PARK_INDEX = "https://npshistory.com/park_histories.htm"
PUB = "https://npshistory.com/publications/{code}/index.htm"

# The site returns 403 to non-browser clients; identify as a browser and be polite.
UA = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

THEMES = ["indigenous", "women", "black", "slavery", "climate",
          "labor_ccc", "lgbtq", "japanese_american", "latino"]
CATEGORIES = ["adhi", "hrs", "ethno", "cli_clr", "hsr", "nrhp", "brochure",
              "handbook", "foundation", "planning", "newspaper", "climate"]

BOILERPLATE = "is one of hundreds of National Park Service sites"
PLACEHOLDER = "NPSHistory.com keeps the administrative histories"

# How bad is the park's worst status?  1 = flagged only, 2 = action pending, 3 = content gone/altered.
SEVERITY = {
    "FLAGGED FOR REVIEW": 1,
    "CONTENT UNDER FURTHER REVIEW": 2,
    "NEEDS REPAIR / REPLACEMENT": 2,
    "OTHER — SEE NOTE": 2,
    "ACTION REQUIRED": 2,
}
DEFAULT_SEVERITY = 3  # CONFIRMED REMOVED, REMOVED PER NPS COURT FILING, REVISE, ORDERED TO REMOVE, ...

TOPIC_PAGES = ["climate-censorship.html", "indigenous-history-censorship.html",
               "slavery-history-censorship.html", "civil-rights-censorship.html",
               "presidents-house.html"]


# --------------------------------------------------------------------------- fetch

def _cache_paths(url: str) -> tuple[Path, Path]:
    h = hashlib.sha1(url.encode()).hexdigest()
    return CACHE / f"{h}.html", CACHE / f"{h}.meta.json"


class Fetcher:
    """Cached, rate-limited GET.  Returns (body, http_status, final_url)."""

    def __init__(self, offline: bool = False, refresh: bool = False, delay: float = 1.0,
                 retries: int = 3, verbose: bool = False):
        self.offline, self.refresh, self.delay, self.retries, self.verbose = offline, refresh, delay, retries, verbose
        self.last = 0.0
        self.network_calls = 0

    def _wait(self) -> None:
        gap = self.delay + random.uniform(0, 0.4) - (time.time() - self.last)
        if gap > 0:
            time.sleep(gap)
        self.last = time.time()

    def get(self, url: str) -> tuple[bytes, int, str]:
        body_p, meta_p = _cache_paths(url)
        meta = json.loads(meta_p.read_text()) if meta_p.exists() else {}
        cached = body_p.exists()
        if self.offline or (cached and not self.refresh):
            if cached:
                return body_p.read_bytes(), int(meta.get("status", 200)), meta.get("final_url", url)
            if meta.get("status") in (404, 410):  # remembered miss
                return b"", int(meta["status"]), url
            return b"", 0, url
        headers = dict(UA)
        if cached and meta.get("etag"):
            headers["If-None-Match"] = meta["etag"]
        if cached and meta.get("last_modified"):
            headers["If-Modified-Since"] = meta["last_modified"]
        for attempt in range(self.retries):
            self._wait()
            self.network_calls += 1
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as r:
                    body = r.read()
                    meta = {"status": r.status, "final_url": r.geturl(), "etag": r.headers.get("ETag"),
                            "last_modified": r.headers.get("Last-Modified"),
                            "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
                    CACHE.mkdir(parents=True, exist_ok=True)
                    body_p.write_bytes(body)
                    meta_p.write_text(json.dumps(meta))
                    if self.verbose:
                        print(f"  GET {r.status} {url} ({len(body)} B)", file=sys.stderr)
                    return body, r.status, r.geturl()
            except urllib.error.HTTPError as exc:
                if exc.code == 304 and cached:
                    return body_p.read_bytes(), 200, meta.get("final_url", url)
                if exc.code in (403, 404, 410) or attempt == self.retries - 1:
                    CACHE.mkdir(parents=True, exist_ok=True)
                    meta_p.write_text(json.dumps({"status": exc.code, "final_url": url,
                                                  "fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}))
                    if self.verbose:
                        print(f"  GET {exc.code} {url}", file=sys.stderr)
                    return b"", exc.code, url
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                if attempt == self.retries - 1:
                    print(f"warn: {url}: {exc}", file=sys.stderr)
                    return b"", 0, url
            time.sleep(2 ** attempt)
        return b"", 0, url


# --------------------------------------------------------------------------- resolve

OPTION_RE = re.compile(r'<option value="([^"]+)">\s*([^<]*?)\s*</option>', re.I)
CODE_IN_NAME_RE = re.compile(r"\(([A-Z]{4})\)\s*$")
ANCHOR_RE = re.compile(r'<a name="([a-z0-9_-]+)"></a>\s*<span class="park">(?:<a href="([^"]+)"[^>]*>)?([^<]+)', re.I)

ABBREV = [
    ("National Historical Park and Preserve", "NHP & Pres"),
    ("National Historical Park & Ecological Preserve", "NHP & EPres"),
    ("National Park and Preserve", "NP & Pres"),
    ("National Park & Preserve", "NP & Pres"),
    ("National Monument and Preserve", "NM & Pres"),
    ("National Monument & Preserve", "NM & Pres"),
    ("National Monument and Historic Shrine", "NM & HS"),
    ("National Historical Park", "NHP"),
    ("National Historic Site", "NHS"),
    ("National Historical Reserve", "NHR"),
    ("National Battlefield Park", "NBP"),
    ("National Battlefield Site", "NBS"),
    ("National Military Park", "NMP"),
    ("National Memorial Parkway", "Mem Pkwy"),
    ("National Memorial", "NMem"),
    ("National Battlefield", "NB"),
    ("National Monument", "NM"),
    ("National Seashore", "NS"),
    ("National Lakeshore", "NL"),
    ("National Recreation Area", "NRA"),
    ("National Preserve", "NPres"),
    ("National Historic Trail", "NHT"),
    ("National Scenic Trail", "NST"),
    ("National Scenic Riverway", "NSR"),
    ("National Scenic River", "NSR"),
    ("National Wild and Scenic River", "NWSR"),
    ("Wild and Scenic River", "WSR"),
    ("National River and Recreation Area", "NRRA"),
    ("National Heritage Area", "NHA"),
    ("National Reserve", "NRes"),
    ("National Parkway", "Pkwy"),
    ("National Park", "NP"),
    ("Parkway", "Pkwy"),
]


def _norm(name: str) -> str:
    s = htmllib.unescape(name)
    for long, short in ABBREV:
        s = re.sub(re.escape(long), short, s, flags=re.I)
    s = s.replace("&", "and").replace("'", "").replace("’", "")
    s = re.sub(r"[^a-z0-9]+", " ", s.lower()).strip()
    return s


def parse_home_options(html: str) -> tuple[dict[str, dict], list[dict]]:
    """code -> {name, url} for coded parks; list of {name, url} for uncoded entries."""
    coded: dict[str, dict] = {}
    uncoded: list[dict] = []
    for url, name in OPTION_RE.findall(html):
        name = htmllib.unescape(name.strip())
        if not url.startswith("http") or not name or name.startswith("Select"):
            continue
        m = CODE_IN_NAME_RE.search(name)
        if m:
            coded.setdefault(m.group(1), {"name": name[: m.start()].strip(), "url": url})
        else:
            uncoded.append({"name": name, "url": url})
    return coded, uncoded


def parse_park_index_anchors(html: str) -> dict[str, dict]:
    """anchor (lowercase code) -> {name, url|None}."""
    out: dict[str, dict] = {}
    for anchor, href, name in ANCHOR_RE.findall(html):
        url = urllib.parse.urljoin(PARK_INDEX, href) if href else None
        out.setdefault(anchor.lower(), {"name": htmllib.unescape(name.strip()), "url": url})
    return out


def canonical_codes(park_data: dict) -> dict[str, list[str]]:
    """Split composite codes ('GWMP,THIS') into one row per unit code -> [entry ids]."""
    out: dict[str, list[str]] = {}
    for eid, rec in park_data.items():
        for code in str(rec.get("code", "")).split(","):
            code = code.strip()
            if code:
                out.setdefault(code, []).append(eid)
    return out


def primary_code(code_field: str, umbrella: list[str]) -> str:
    parts = [c.strip() for c in str(code_field).split(",") if c.strip()]
    for c in parts:
        if c not in umbrella:
            return c
    return parts[0] if parts else ""


def resolve(code: str, mph_name: str, aliases: dict, coded: dict, anchors: dict) -> dict:
    """Return {kind, url, npsh_code, npsh_name}.  kind in
    park | heritage-anchor | override | name-match | guess | no-page | non-nps."""
    if code in aliases.get("non_nps", []):
        return {"kind": "non-nps", "url": None, "npsh_code": None, "npsh_name": None}
    if code in aliases.get("no_page", []):
        return {"kind": "no-page", "url": None, "npsh_code": None, "npsh_name": None}
    if code in aliases.get("overrides", {}):
        return {"kind": "override", "url": aliases["overrides"][code], "npsh_code": code, "npsh_name": None}
    if code in coded:
        return {"kind": "park", "url": coded[code]["url"], "npsh_code": code, "npsh_name": coded[code]["name"]}
    a = anchors.get(code.lower())
    if a:
        url = a["url"] or f"{PARK_INDEX}#{code.lower()}"
        return {"kind": "park" if a["url"] else "heritage-anchor", "url": url, "npsh_code": code, "npsh_name": a["name"]}
    # Name match (handles code mismatches such as MPH MAWA vs. NPSHistory MALW).
    hint = aliases.get("name_hints", {}).get(code)
    wanted = {_norm(hint)} if hint else set()
    if mph_name:
        wanted.add(_norm(mph_name))
    for ncode, info in coded.items():
        if _norm(info["name"]) in wanted:
            return {"kind": "name-match", "url": info["url"], "npsh_code": ncode, "npsh_name": info["name"]}
    return {"kind": "guess", "url": PUB.format(code=code.lower()), "npsh_code": code, "npsh_name": None}


# --------------------------------------------------------------------------- parse park page

TITLE_RE = re.compile(r"<title>\s*Park Archives:\s*(.*?)\s*</title>", re.I | re.S)
EST_RE = re.compile(r'<p class="style3-18">\s*Establishment\s*</p>\s*<p class="style3-14">(.*?)</p>', re.I | re.S)
CREDIT_RE = re.compile(r'<p class="credit">(.*?)</p>', re.I | re.S)
PHOTO_RE = re.compile(r'<img src="([^"]*index\.jpg)"[^>]*>.*?<div class="image-credit">(.*?)</div>', re.I | re.S)
DOCS_ANCHOR = re.compile(r'name="documents"', re.I)
P_RE = re.compile(r'<p class="(hangingindent2?)">(.*?)</p>', re.I | re.S)
A_RE = re.compile(r'<a href="([^"]+)"[^>]*>(.*?)</a>', re.I | re.S)
FONT_RE = re.compile(r'<font size="-2">(.*?)</font>', re.I | re.S)
TAG_RE = re.compile(r"<[^>]+>")
YEAR_RE = re.compile(r"\b(1[6-9]\d\d|20\d\d)\b")
EDITION_RE = re.compile(r"(PDF|HTML( edition)?|Google Books|Archive\.org|HathiTrust|IRMA|map|large print|Part \d+|Vol(ume)?\.? \d+|\d{4}|[A-Z])", re.I)


def _text(fragment: str) -> str:
    return re.sub(r"\s+", " ", htmllib.unescape(TAG_RE.sub(" ", fragment))).strip()


def parse_park_page(html: str, page_url: str) -> dict:
    out: dict = {"name": None, "established": [], "intro_words": 0, "intro": "", "photo": None, "photo_credit": None, "docs": []}
    m = TITLE_RE.search(html)
    if m:
        out["name"] = _text(m.group(1))
    m = EST_RE.search(html)
    if m:
        out["established"] = [_text(x) for x in re.split(r"<br\s*/?>", m.group(1)) if _text(x)]
    pm = PHOTO_RE.search(html)
    cm = CREDIT_RE.search(html)
    if pm:
        out["photo"] = urllib.parse.urljoin(page_url, pm.group(1))
        out["photo_credit"] = _text(pm.group(2))
    if pm and cm and cm.start() > pm.end():
        intro = " ".join(_text(p) for p in re.findall(r"<p(?:\s[^>]*)?>(.*?)</p>", html[pm.end():cm.start()], re.I | re.S))
        out["intro_words"] = len(intro.split())
        out["intro"] = intro
    am = DOCS_ANCHOR.search(html)
    if not am:
        return out
    group = None
    for cls, inner in P_RE.findall(html[am.end():]):
        cite_m = FONT_RE.search(inner)
        cite = re.sub(r"[;,]?\s*\)$", ")", _text(A_RE.sub("", cite_m.group(1)))) if cite_m else ""
        # Links inside the citation are alternate editions ("HTML edition", "PDF"), not documents.
        alt_urls = [urllib.parse.urljoin(page_url, h) for h, _ in A_RE.findall(cite_m.group(1))] if cite_m else []
        body_html = FONT_RE.sub(" ", inner)
        links = A_RE.findall(body_html)
        label = re.sub(r"(\s*[,;]\s*)+", ", ", _text(A_RE.sub(" ", body_html))).strip(" ,;:")
        if cls.lower() == "hangingindent":
            group = label if not links else None
        if not links:
            continue
        for href, link_text in links:
            title = _text(link_text)
            if not title:
                continue
            if EDITION_RE.fullmatch(title) and out["docs"] and not re.search(r"[A-Za-z]{2}", label):
                out["docs"][-1].setdefault("alt_urls", []).append(urllib.parse.urljoin(page_url, href))
                continue
            if len(links) > 1 and re.search(r"[A-Za-z]{2}", label):
                title = f"{label.rstrip(': ')}: {title}"
            years = YEAR_RE.findall(cite) or YEAR_RE.findall(title)
            doc = {
                "title": title,
                "url": urllib.parse.urljoin(page_url, href),
                "cite": cite,
                "group": group if cls.lower() == "hangingindent2" else "",
                "year": int(years[-1]) if years else None,
            }
            if alt_urls and len(links) == 1:
                doc["alt_urls"] = alt_urls
            out["docs"].append(doc)
    return out


# --------------------------------------------------------------------------- classify

class Classifier:
    def __init__(self, cfg: dict):
        self.categories = {k: self._compile(v) for k, v in cfg["categories"].items()}
        self.themes = {k: self._compile(v) for k, v in cfg["themes"].items()}
        self.tag_to_theme = cfg.get("topic_tag_to_theme", {})

    @staticmethod
    def _compile(rule: dict):
        pos = re.compile(rule["any"], re.I)
        neg = re.compile(rule["not"], re.I) if rule.get("not") else None
        return pos, neg

    @staticmethod
    def _hits(text: str, rules: dict) -> list[str]:
        out = []
        for key, (pos, neg) in rules.items():
            t = neg.sub(" ", text) if neg else text
            if pos.search(t):
                out.append(key)
        return out

    def doc(self, d: dict) -> tuple[list[str], list[str]]:
        """Categories look at title + citation + group (series names live in the citation);
        themes look at title + group only, because citations carry author names ("Gay Hunter")."""
        full = f"{d.get('title', '')} | {d.get('cite', '')} | {d.get('group', '')}"
        tg = f"{d.get('title', '')} | {d.get('group', '')}"
        return self._hits(full, self.categories), self._hits(tg, self.themes)

    def text_themes(self, text: str) -> list[str]:
        return self._hits(text, self.themes)

    def theme_counts(self, text: str) -> dict[str, int]:
        out = {}
        for key, (pos, neg) in self.themes.items():
            t = neg.sub(" ", text) if neg else text
            n = len(pos.findall(t))
            if n:
                out[key] = n
        return out


ANCHOR_CATEGORIES = ("adhi", "hrs", "foundation")  # park-wide studies; CLIs/HSRs are about one structure
PARK_THEME_MIN_HITS = 2  # a theme must be mentioned at least this often in the archive page's overview
DESIGNATION_RE = re.compile(r"\b(National|Historical?|Park|Site|Monument|Memorial|Preserve|Reserve|Seashore|Lakeshore|Recreation|Area|"
                            r"Battlefield|Military|Trail|Scenic|River|Riverway|Parkway|Heritage|and|&|of|the)\b", re.I)


def self_name_pattern(park_name: str | None) -> re.Pattern | None:
    """Regex for the park's own name and its stem (name minus designation words), so that a
    document titled 'Amache newsletter, Spring' is not counted as a Japanese American source
    just because the park is Amache."""
    if not park_name:
        return None
    stem = re.sub(r"\s+", " ", DESIGNATION_RE.sub(" ", park_name)).strip()
    parts = [re.escape(park_name)]
    if len(stem) >= 4:
        parts.append(re.escape(stem))
    return re.compile("|".join(parts), re.I)


def park_wide_themes(clf: Classifier, park_name: str | None, park_text: str) -> list[str]:
    """Themes the park itself is about: named in the park's name, or mentioned repeatedly in the
    archive page's overview prose.  Climate is excluded (overviews mention glaciers and sea level
    too freely for that to mean the park is 'about' climate)."""
    named = set(clf.text_themes(park_name or ""))
    counts = clf.theme_counts(park_text or "")
    out = {t for t, n in counts.items() if n >= PARK_THEME_MIN_HITS} | named
    return [t for t in THEMES if t in out and t != "climate"]


def summarize_docs(docs: list[dict], clf: Classifier, park_name: str | None = None, park_text: str = "",
                   keep_per_key: int = 5) -> dict:
    cats = {c: 0 for c in CATEGORIES}
    themes = {t: 0 for t in THEMES}
    anchors: dict[str, list[dict]] = {}
    classified: list[dict] = []
    self_re = self_name_pattern(park_name)
    # A park that is itself about a theme (the archive page's overview prose says "Japanese American
    # incarceration" for Amache, "women's rights" for Belmont-Paul) makes its anchor studies sources
    # for that theme even when their titles don't say so.
    park_themes = park_wide_themes(clf, park_name, park_text)
    for d in docs:
        d2 = dict(d)
        if self_re:
            d2["title"] = self_re.sub(" ", d["title"])
            d2["group"] = self_re.sub(" ", d.get("group", "") or "")
        c_hits, t_hits = clf.doc(d2)
        if park_themes and any(c in ANCHOR_CATEGORIES for c in c_hits):
            t_hits = sorted(set(t_hits) | set(park_themes), key=THEMES.index)
        for c in c_hits:
            cats[c] = cats.get(c, 0) + 1
        for t in t_hits:
            themes[t] = themes.get(t, 0) + 1
        # Keep the documents an author would open; park newspapers are counted but not listed.
        if t_hits or any(c != "newspaper" for c in c_hits):
            compact = {"t": d["title"], "u": d["url"], "y": d["year"], "c": c_hits, "th": t_hits}
            if d.get("alt_urls"):
                compact["alt"] = d["alt_urls"]
            classified.append(compact)
            for key in c_hits + t_hits:
                lst = anchors.setdefault(key, [])
                if len(lst) < keep_per_key:
                    lst.append({"t": d["title"], "u": d["url"], "y": d["year"]})
    return {"doc_total": len(docs), "categories": cats, "themes": themes, "anchors": anchors, "docs": classified}


# --------------------------------------------------------------------------- MPH side

PWP_RE = re.compile(r'([A-Z]{4}):\{name:"((?:[^"\\]|\\.)*)",entries:(\d+),photos:(\d+),slug:"([^"]+)"\}')
PARK_LOC_RE = re.compile(r'<div class="park-location">\s*([A-Z]{4})\b')
HIST_P_RE = re.compile(r'park-history-section.*?<p style="font-size:15px;line-height:1\.75;color:#b8b8c0;margin-bottom:20px">(.*?)</p>', re.S)


def load_mph(root: Path) -> dict:
    park_data = json.loads((root / "data" / "parkData.json").read_text())
    manifest = json.loads((root / "data" / "manifestData.json").read_text()) if (root / "data" / "manifestData.json").exists() else {}
    index_html = (root / "index.html").read_text(errors="replace") if (root / "index.html").exists() else ""
    pwp = {c: {"name": n, "entries": int(e), "photos": int(p), "slug": s} for c, n, e, p, s in PWP_RE.findall(index_html)}
    pages: dict[str, dict] = {}
    for f in sorted((root / "parks").glob("*.html")) if (root / "parks").exists() else []:
        html = f.read_text(errors="replace")
        if 'http-equiv="refresh"' in html:
            continue
        m = PARK_LOC_RE.search(html)
        if not m:
            continue
        code = m.group(1)
        hm = HIST_P_RE.search(html)
        kind = "none"
        if hm:
            kind = "placeholder" if _text(hm.group(1)).startswith(PLACEHOLDER) else "custom"
        pages.setdefault(code, {"slug": f.stem, "history": kind, "history_chars": len(_text(hm.group(1))) if hm else 0})
    slug_to_code = {v["slug"]: k for k, v in pages.items()}
    slug_to_code.update({v["slug"]: k for k, v in pwp.items()})
    id_to_code = {eid: str(rec.get("code", "")) for eid, rec in park_data.items()}
    case_studies: dict[str, set] = {}
    for page in TOPIC_PAGES:
        p = root / page
        if not p.exists():
            continue
        html = p.read_text(errors="replace")
        codes: set[str] = set()
        for c in re.findall(r"[?&](?:amp;)?park=([A-Z]{4})", html):
            codes.add(c)
        for eid in re.findall(r"[?&](?:amp;)?id=(\d+)", html):
            if eid in id_to_code:
                codes.update(x.strip() for x in id_to_code[eid].split(","))
        for slug in re.findall(r"parks/([a-z0-9-]+)\.html", html):
            if slug in slug_to_code:
                codes.add(slug_to_code[slug])
        for c in codes:
            case_studies.setdefault(c, set()).add(page.replace(".html", ""))
    park_history = {}
    ph = root / "data" / "parkHistory.json"
    if ph.exists():
        try:
            park_history = json.loads(ph.read_text())
        except json.JSONDecodeError:
            park_history = {}
    return {"park_data": park_data, "manifest": manifest, "pwp": pwp, "pages": pages,
            "case_studies": case_studies, "park_history": park_history}


def mph_theme_level(code: str, entries: list[dict], mph: dict, clf: Classifier) -> dict[str, int]:
    """0 = nothing, 1 = tag or keyword mention, 2 = published Park History theme block."""
    levels = {t: 0 for t in THEMES}
    ph = mph["park_history"].get(code) or {}
    if ph.get("reviewStatus") == "published":
        for t in (ph.get("themes") or {}):
            if t in levels:
                levels[t] = 2
    for rec in entries:
        for tag in rec.get("topics", []) or []:
            t = clf.tag_to_theme.get(tag)
            if t and levels[t] < 1:
                levels[t] = 1
        text = " ".join([
            _text(rec.get("narrative", "") or ""),
            _text(rec.get("whatTheyWantChanged", "") or ""),
            " ".join(s.get("title", "") for s in rec.get("sosSignNames", []) or []),
            " ".join(f"{d.get('item', '')} {d.get('reason', '')}" for d in rec.get("filingDetail", []) or []),
        ])
        for t in clf.text_themes(text):
            if levels[t] < 1:
                levels[t] = 1
    return levels


def score_code(code: str, eids: list[str], mph: dict, clf: Classifier, aliases: dict) -> dict:
    entries = [mph["park_data"][e] for e in eids]
    statuses = [str(r.get("status", "")) for r in entries]
    sev = max(SEVERITY.get(s, DEFAULT_SEVERITY) for s in statuses) if statuses else 1
    worst = max(statuses, key=lambda s: SEVERITY.get(s, DEFAULT_SEVERITY)) if statuses else ""
    narratives = [r.get("narrative", "") or "" for r in entries]
    kinds = ["boilerplate" if BOILERPLATE in n else ("custom" if _text(n) else "none") for n in narratives]
    narrative_kind = "custom" if "custom" in kinds else ("boilerplate" if "boilerplate" in kinds else "none")
    topics = sorted({t for r in entries for t in (r.get("topics") or []) if t != "General Historical Content"})
    manifest_photos = sum(len(mph["manifest"].get(str(r.get("folderId") or e), [])) for e, r in zip(eids, entries))
    image_count = sum(int(r.get("imageCount") or 0) for r in entries)
    page = mph["pages"].get(code) or {}
    wayback_ok = all(("," not in str(r.get("code", ""))) and (f"/{code.lower()}/" in str((r.get("wayback") or {}).get("main", "")))
                     for r in entries)
    agency = next((r.get("agency") for r in entries if r.get("agency")), "NPS")
    return {
        "code": code,
        "park": entries[0].get("park", "") if entries else "",
        "agency": agency,
        "state": entries[0].get("state", "") if entries else "",
        "entryIds": eids,
        "entryCount": len(eids),
        "worstStatus": worst,
        "severity": sev,
        "confirmedRemoved": any(r.get("confirmedRemoved") for r in entries),
        "filingRemoved": any(r.get("filingRemoved") for r in entries),
        "orderedToRemove": any(r.get("orderedToRemove") for r in entries),
        "topicsNonGeneral": topics,
        "narrativeKind": narrative_kind,
        "narrativeChars": max((len(_text(n)) for n in narratives), default=0),
        "manifestPhotos": manifest_photos,
        "imageCountField": image_count,
        "parkPageSlug": page.get("slug") or (mph["pwp"].get(code) or {}).get("slug"),
        "parkPageHistoryKind": page.get("history", "none"),
        "waybackOk": wayback_ok,
        "topicPageCaseStudy": sorted(mph["case_studies"].get(code, [])),
        "mphThemeLevel": mph_theme_level(code, entries, mph, clf),
    }


# --------------------------------------------------------------------------- gaps

def gap_for(mph_level: int, npsh_count: int, npsh_anchor: bool, severity: int) -> str:
    npsh_level = 0 if npsh_count == 0 else (2 if npsh_count >= 3 or npsh_anchor else 1)
    expected = mph_level >= 1 or npsh_level >= 1
    if not expected or mph_level == 2:
        return "OK"
    if npsh_level == 0:
        return "NA"  # MPH mentions it but NPSHistory has nothing: source elsewhere
    if mph_level == 0:
        return "P1" if severity == 3 else "P2"
    return "P3"


def build_row(score: dict, res: dict, http: int, inv: dict | None) -> dict:
    row = dict(score)
    row.update({
        "npshResolution": res["kind"],
        "npshUrl": res["url"],
        "npshCode": res.get("npsh_code"),
        "npshName": (inv or {}).get("name") or res.get("npsh_name"),
        "npshHttp": http,
        "npshDocTotal": (inv or {}).get("doc_total", 0),
        "npshEstablished": "; ".join((inv or {}).get("established", [])),
        "npshIntroWords": (inv or {}).get("intro_words", 0),
        "npshPhoto": (inv or {}).get("photo"),
    })
    cats = (inv or {}).get("categories", {})
    anchors = (inv or {}).get("anchors", {})
    for c in CATEGORIES:
        row[f"{c}Count"] = cats.get(c, 0)
    for c in ("adhi", "hrs", "cli_clr", "foundation"):
        row[f"{c}Url"] = anchors.get(c, [{}])[0].get("u") if anchors.get(c) else None
    row["ethnoUrls"] = [a["u"] for a in anchors.get("ethno", [])]
    themes = (inv or {}).get("themes", {})
    p1 = p2 = p3 = 0
    for t in THEMES:
        mph_l = score["mphThemeLevel"].get(t, 0)
        n = themes.get(t, 0)
        anchor = bool(anchors.get("adhi")) and t == "indigenous" and n > 0 or (t == "indigenous" and cats.get("ethno", 0) > 0)
        gap = gap_for(mph_l, n, anchor, score["severity"])
        row[f"{t}_mph"] = mph_l
        row[f"{t}_npsh"] = n
        row[f"{t}_gap"] = gap
        p1 += gap == "P1"
        p2 += gap == "P2"
        p3 += gap == "P3"
    boiler = score["narrativeKind"] == "boilerplate"
    case = bool(score["topicPageCaseStudy"])
    row["gapScore"] = score["severity"] * (3 * p1 + 2 * p2 + p3) + 2 * boiler + 2 * case + (1 if score["parkPageSlug"] else 0)
    if res["kind"] in ("non-nps", "no-page"):
        tier = 3
    elif score["severity"] == 3 or case or (score["severity"] >= 2 and boiler):
        tier = 1
    elif score["narrativeKind"] == "custom" and (p2 or p3):
        tier = 2
    else:
        tier = 3
    row["tier"] = tier
    notes = []
    if res["kind"] == "non-nps":
        notes.append("FWS/BLM site: no NPSHistory park page")
    if res["kind"] == "no-page":
        notes.append("NPS administrative/regional unit: no NPSHistory park page")
    if res["kind"] == "name-match":
        notes.append(f"NPSHistory uses code {res.get('npsh_code')}")
    if res["kind"] == "guess" and http != 200:
        notes.append("unresolved on NPSHistory (guessed URL failed)")
    if boiler:
        notes.append("narrative is boilerplate")
    if not score["waybackOk"]:
        notes.append("Wayback link broken/composite code")
    if score["manifestPhotos"] and not score["imageCountField"]:
        notes.append(f"{score['manifestPhotos']} photos in manifest but imageCount=0")
    row["notes"] = "; ".join(notes)
    return row


# --------------------------------------------------------------------------- outputs

COLUMNS = (["code", "park", "agency", "state", "entryIds", "entryCount", "worstStatus", "severity",
            "confirmedRemoved", "filingRemoved", "orderedToRemove", "topicsNonGeneral", "narrativeKind",
            "narrativeChars", "manifestPhotos", "imageCountField", "parkPageSlug", "parkPageHistoryKind",
            "waybackOk", "topicPageCaseStudy", "npshResolution", "npshUrl", "npshCode", "npshName", "npshHttp",
            "npshDocTotal", "npshEstablished", "npshIntroWords", "npshPhoto"]
           + [f"{c}Count" for c in CATEGORIES] + ["adhiUrl", "hrsUrl", "cli_clrUrl", "foundationUrl", "ethnoUrls"]
           + [f"{t}_{k}" for t in THEMES for k in ("mph", "npsh", "gap")]
           + ["gapScore", "tier", "notes"])


def _cell(v):
    if isinstance(v, (list, tuple)):
        return "; ".join(str(x) for x in v)
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    return v


def write_csv(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(r.get(k)) for k in COLUMNS})


def write_xlsx(rows: list[dict], path: Path, meta: dict) -> None:
    """Mapping table + a formula-driven theme x tier pivot + resolution exceptions + the rubric."""
    from openpyxl import Workbook  # optional dependency, local use only
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    base = Font(name="Arial", size=10)
    bold = Font(name="Arial", size=10, bold=True)
    wb = Workbook()
    ws = wb.active
    ws.title = "Mapping"
    ws.append(COLUMNS)
    for r in rows:
        ws.append([_cell(r.get(k)) for k in COLUMNS])
    fills = {"P1": PatternFill("solid", fgColor="F8CBAD"), "P2": PatternFill("solid", fgColor="FFE699"),
             "P3": PatternFill("solid", fgColor="FFF2CC"), "NA": PatternFill("solid", fgColor="D9D9D9"),
             "OK": PatternFill("solid", fgColor="E2EFDA")}
    gap_cols = [i for i, c in enumerate(COLUMNS) if c.endswith("_gap")]
    tier_idx = COLUMNS.index("tier")
    for row in ws.iter_rows(min_row=1):
        for cell in row:
            cell.font = base
    for row in ws.iter_rows(min_row=2):
        for ci in gap_cols:
            if row[ci].value in fills:
                row[ci].fill = fills[row[ci].value]
        if row[tier_idx].value == 1:
            row[tier_idx].fill = fills["P1"]
        elif row[tier_idx].value == 2:
            row[tier_idx].fill = fills["P2"]
    for cell in ws[1]:
        cell.font = bold
        cell.alignment = Alignment(wrap_text=True, vertical="top")
    widths = {"park": 38, "npshName": 30, "npshUrl": 44, "notes": 48, "topicsNonGeneral": 28,
              "npshEstablished": 30, "worstStatus": 26, "ethnoUrls": 40, "entryIds": 14}
    for i, c in enumerate(COLUMNS, 1):
        ws.column_dimensions[get_column_letter(i)].width = widths.get(c, 11 if len(c) < 12 else 16)
    ws.freeze_panes = "C2"
    ws.auto_filter.ref = ws.dimensions
    last = len(rows) + 1

    def col(name: str) -> str:
        return get_column_letter(COLUMNS.index(name) + 1)

    # Theme x tier pivot driven by COUNTIFS over the Mapping sheet, so filters/edits there flow through.
    pv = wb.create_sheet("Theme Gaps")
    pv.append(["theme", "tier", "P1", "P2", "P3", "NA", "OK", "parks with NPSHistory sources", "parks with MPH coverage"])
    tier_rng = f"Mapping!${col('tier')}$2:${col('tier')}${last}"
    for t in THEMES:
        gap_rng = f"Mapping!${col(t + '_gap')}$2:${col(t + '_gap')}${last}"
        npsh_rng = f"Mapping!${col(t + '_npsh')}$2:${col(t + '_npsh')}${last}"
        mph_rng = f"Mapping!${col(t + '_mph')}$2:${col(t + '_mph')}${last}"
        for tier in (1, 2, 3):
            r = pv.max_row + 1
            pv.append([t, tier] + [f'=COUNTIFS({tier_rng},$B{r},{gap_rng},"{g}")' for g in ("P1", "P2", "P3", "NA", "OK")]
                      + [f'=COUNTIFS({tier_rng},$B{r},{npsh_rng},">0")', f'=COUNTIFS({tier_rng},$B{r},{mph_rng},">0")'])
    r = pv.max_row + 1
    pv.append(["all themes", "all"] + [f"=SUM({c}2:{c}{r - 1})" for c in "CDEFGHI"])
    for row in pv.iter_rows():
        for cell in row:
            cell.font = base
    for cell in pv[1]:
        cell.font = bold
    for cell in pv[r]:
        cell.font = bold
    pv.column_dimensions["A"].width = 20
    pv.column_dimensions["H"].width = 30
    pv.column_dimensions["I"].width = 26
    pv.freeze_panes = "A2"

    mx = wb.create_sheet("Missing & Aliases")
    mx.append(["code", "park", "agency", "npshResolution", "npshCode", "npshUrl", "npshHttp", "notes"])
    for r_ in rows:
        if r_["npshResolution"] != "park" or r_["npshHttp"] != 200:
            mx.append([r_["code"], r_["park"], r_["agency"], r_["npshResolution"], r_.get("npshCode"), r_.get("npshUrl"), r_["npshHttp"], r_["notes"]])
    for row in mx.iter_rows():
        for cell in row:
            cell.font = base
    for cell in mx[1]:
        cell.font = bold
    for c, w in zip("ABCDEFGH", (8, 40, 8, 16, 10, 48, 9, 50)):
        mx.column_dimensions[c].width = w

    md = wb.create_sheet("Method & Rubric")
    lines = [
        ["Generated", meta["generated_at"]],
        ["Source data", "data/parkData.json (MissingParkHistory.org) vs. npshistory.com park archive pages, fetched by scripts/npshistory_audit.py"],
        ["Rows", f"{len(rows)} canonical park codes (composite MPH codes split; FWS/BLM included and marked)"],
        ["Fill colours", "P1 red, P2 amber, P3 pale amber, NA grey, OK green; tier 1 red, tier 2 amber"],
        [""],
        ["MPH theme level", "0 = no topic tag and no keyword in narrative/flagged text; 1 = tag or keyword mention; 2 = published Park History theme block"],
        ["NPSHistory theme level", "0 = no documents matching the theme; 1 = 1-2 documents; 2 = 3+ documents or an anchor study (admin history / HRS / ethnographic overview)"],
        ["Gap P1", "theme expected, NPSHistory has sources, MPH has nothing, park's worst status is severity 3 (content removed/altered/ordered)"],
        ["Gap P2", "theme expected, NPSHistory has sources, MPH has nothing"],
        ["Gap P3", "MPH only mentions the theme; NPSHistory has sources to write a real section"],
        ["Gap NA", "MPH mentions the theme but NPSHistory has nothing on it: source from nps.gov / Wayback / other US-gov works"],
        ["Gap OK", "theme not expected for this park, or already published"],
        ["gapScore", "severity x (3*P1 + 2*P2 + P3) + 2 if narrative is boilerplate + 2 if a topic page uses the park as a case study + 1 if a parks/ page exists (computed by the script)"],
        ["tier", "1 = severity 3, or topic-page case study, or severity>=2 with boilerplate narrative; 2 = custom narrative with open P2/P3 gaps; 3 = everything else (incl. FWS/BLM and admin units)"],
        ["severity", "1 = FLAGGED FOR REVIEW; 2 = CONTENT UNDER FURTHER REVIEW / NEEDS REPAIR / OTHER / ACTION REQUIRED; 3 = removed, revised, ordered, pulled, censored"],
        ["Classification", "keyword rules in data/npshistory_themes.json applied to document title | citation | group header (themes: title | group only); 'not' patterns are blanked before matching"],
        ["Caveat", "document counts are title-based; a park may discuss a theme inside an administrative history whose title does not say so. Treat counts as a floor, not a verdict."],
        ["Theme Gaps sheet", "formulas (COUNTIFS) over the Mapping sheet; they recalculate if rows are edited"],
    ]
    for line in lines:
        md.append(line)
    md.column_dimensions["A"].width = 24
    md.column_dimensions["B"].width = 120
    for row in md.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.font = base
    for row in md.iter_rows(max_col=1):
        row[0].font = bold
    wb.save(path)


def print_summary(rows: list[dict]) -> None:
    n = len(rows)
    nps = [r for r in rows if r["agency"] == "NPS"]
    resolved = [r for r in nps if r["npshHttp"] == 200]
    print(f"\n{n} codes ({len(nps)} NPS); {len(resolved)} NPS codes resolved to a live NPSHistory page")
    for kind in ("park", "name-match", "heritage-anchor", "override", "guess", "no-page", "non-nps"):
        k = [r for r in rows if r["npshResolution"] == kind]
        if k:
            print(f"  {kind:16s} {len(k):4d}  e.g. {', '.join(r['code'] for r in k[:6])}")
    print(f"boilerplate narratives: {sum(1 for r in rows if r['narrativeKind'] == 'boilerplate')}; "
          f"custom: {sum(1 for r in rows if r['narrativeKind'] == 'custom')}")
    print(f"tiers: 1={sum(1 for r in rows if r['tier'] == 1)}  2={sum(1 for r in rows if r['tier'] == 2)}  3={sum(1 for r in rows if r['tier'] == 3)}")
    print("theme gaps (P1/P2/P3/NA):")
    for t in THEMES:
        c = {g: sum(1 for r in rows if r[f'{t}_gap'] == g) for g in ("P1", "P2", "P3", "NA")}
        print(f"  {t:18s} P1={c['P1']:3d} P2={c['P2']:3d} P3={c['P3']:3d} NA={c['NA']:3d}  "
              f"parks w/ NPSH sources={sum(1 for r in rows if r[f'{t}_npsh'] > 0)}")
    print(f"parks with an administrative history: {sum(1 for r in rows if r['adhiCount'])}; "
          f"with HRS: {sum(1 for r in rows if r['hrsCount'])}; with ethnographic docs: {sum(1 for r in rows if r['ethnoCount'])}")


# --------------------------------------------------------------------------- main

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--offline", action="store_true", help="never touch the network (cache only)")
    ap.add_argument("--refresh", action="store_true", help="re-validate cached pages with conditional GETs")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")
    ap.add_argument("--codes", help="comma-separated MPH codes to audit (default: all)")
    ap.add_argument("--limit", type=int, help="audit only the first N codes")
    ap.add_argument("--csv", type=Path, help="also write the table as CSV")
    ap.add_argument("--xlsx", type=Path, help="also write the table as XLSX (needs openpyxl)")
    ap.add_argument("--out-index", type=Path, default=DATA / "npshistory_index.json")
    ap.add_argument("--out-audit", type=Path, default=DATA / "npshistory_audit.json")
    ap.add_argument("--no-write", action="store_true", help="print the summary only")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    aliases = json.loads((DATA / "npshistory_aliases.json").read_text())
    clf = Classifier(json.loads((DATA / "npshistory_themes.json").read_text()))
    mph = load_mph(ROOT)
    fetcher = Fetcher(offline=args.offline, refresh=args.refresh, delay=args.delay, verbose=args.verbose)

    home_html = fetcher.get(HOME)[0].decode("utf-8", "replace")
    coded, uncoded = parse_home_options(home_html)
    anchors = parse_park_index_anchors(fetcher.get(PARK_INDEX)[0].decode("utf-8", "replace"))
    if not coded:
        print("error: could not read NPSHistory's park list (offline with empty cache?)", file=sys.stderr)
        return 1
    print(f"NPSHistory index: {len(coded)} coded parks, {len(uncoded)} uncoded entries, {len(anchors)} anchors", file=sys.stderr)

    codes = canonical_codes(mph["park_data"])
    wanted = [c.strip().upper() for c in args.codes.split(",")] if args.codes else list(codes)
    if args.limit:
        wanted = wanted[: args.limit]

    index_out: dict[str, dict] = {}
    rows: list[dict] = []
    for i, code in enumerate(wanted, 1):
        eids = codes.get(code, [])
        if not eids:
            print(f"warn: {code} is not in parkData.json", file=sys.stderr)
            continue
        score = score_code(code, eids, mph, clf, aliases)
        if score["agency"] != "NPS":
            res = {"kind": "non-nps", "url": None, "npsh_code": None, "npsh_name": None}
        else:
            res = resolve(code, score["park"], aliases, coded, anchors)
        inv: dict | None = None
        http = 0
        if res["url"] and "#" not in res["url"]:
            body, http, final = fetcher.get(res["url"])
            if body and http == 200:
                parsed = parse_park_page(body.decode("utf-8", "replace"), final)
                inv = {"name": parsed["name"], "established": parsed["established"], "intro_words": parsed["intro_words"],
                       "photo": parsed["photo"], "photo_credit": parsed["photo_credit"]}
                inv.update(summarize_docs(parsed["docs"], clf, parsed["name"] or score["park"], parsed["intro"]))
                inv["park_themes"] = park_wide_themes(clf, parsed["name"] or score["park"], parsed["intro"])
        elif res["url"]:
            http = 200  # heritage anchors live on the (already fetched) park index page
        index_out[code] = {"resolution": res["kind"], "url": res["url"], "npsh_code": res.get("npsh_code"), "http": http,
                           **({k: v for k, v in inv.items()} if inv else {})}
        rows.append(build_row(score, res, http, inv))
        if args.verbose or i % 25 == 0:
            print(f"[{i}/{len(wanted)}] {code} {res['kind']} http={http} docs={(inv or {}).get('doc_total', 0)}", file=sys.stderr)

    rows.sort(key=lambda r: (-r["gapScore"], r["code"]))
    meta = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "codes": len(rows), "network_calls": fetcher.network_calls,
            "themes": THEMES, "categories": CATEGORIES}
    if not args.no_write:
        args.out_index.parent.mkdir(parents=True, exist_ok=True)
        args.out_index.write_text(json.dumps({"_meta": meta, "parks": index_out}, ensure_ascii=False, separators=(",", ":")) + "\n")
        args.out_audit.write_text(json.dumps({"_meta": meta, "columns": COLUMNS, "rows": rows}, ensure_ascii=False, indent=0) + "\n")
        print(f"wrote {args.out_index} and {args.out_audit}", file=sys.stderr)
        if args.csv:
            write_csv(rows, args.csv)
            print(f"wrote {args.csv}", file=sys.stderr)
        if args.xlsx:
            write_xlsx(rows, args.xlsx, meta)
            print(f"wrote {args.xlsx}", file=sys.stderr)
    print_summary(rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
