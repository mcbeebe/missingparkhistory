#!/usr/bin/env python3
"""Generate parks/<slug>.html for every park in data/park_pages.json.

All park pages share one template (scripts/park_page_template.html, carved from the
current hand-made template) and one stylesheet (/park-page.css).  Content comes from:

  data/parkData.json      the map records (status, narrative, flagged text, SOS signs,
                          court-filing detail, news sources, before/after photos)
  data/manifestData.json  photo folders (images/<id>/)
  data/parkHistory.json   the sourced Park History block (scripts/build_park_history.py)
  data/park_pages.json    the registry: stable slug per code + raw entry IDs whose photo
                          folders belong to the park (kept from the pre-dedup dataset)

The same registry drives the `parksWithPages` table in index.html (--update-index), so
the map's "See all N entries" links never drift from the pages that exist.

Usage:
    python scripts/build_park_pages.py                 # write all pages
    python scripts/build_park_pages.py --check         # exit 1 if any page on disk is stale
    python scripts/build_park_pages.py --update-index  # also rewrite parksWithPages in index.html
    python scripts/build_park_pages.py --only MORA     # one park
"""
from __future__ import annotations

import argparse
import html as htmllib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
PARKS = ROOT / "parks"
TEMPLATE = ROOT / "scripts" / "park_page_template.html"
SITE = "https://missingparkhistory.org"

sys.path.insert(0, str(ROOT / "scripts"))
import build_park_history as bph  # noqa: E402

SIGN_STATUS = {"removed": "removed", "restored": "restored", "partial": "partially restored",
               "ordered": "ordered to remove", "filing": "removed per NPS court filing"}
NON_GENERAL = "General Historical Content"


def esc(s) -> str:
    return str(s if s is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def load() -> dict:
    return {
        "parkData": json.loads((DATA / "parkData.json").read_text()),
        "manifest": json.loads((DATA / "manifestData.json").read_text()),
        "history": json.loads((DATA / "parkHistory.json").read_text()).get("parks", {}) if (DATA / "parkHistory.json").exists() else {},
        "registry": json.loads((DATA / "park_pages.json").read_text())["pages"],
        "template": TEMPLATE.read_text(),
    }


def entries_for(code: str, park_data: dict) -> list[tuple[str, dict]]:
    out = []
    for eid, rec in park_data.items():
        codes = [c.strip() for c in str(rec.get("code", "")).split(",")]
        if code in codes:
            out.append((eid, rec))
    return sorted(out, key=lambda x: (x[1].get("code") != code, int(re.sub(r"\D", "", x[0]) or 0)))


def photos_for(ids: list[str], manifest: dict) -> list[tuple[str, dict]]:
    return [(i, p) for i in ids for p in manifest.get(i, [])]


def photo_src(eid: str, p: dict) -> str:
    """manifestData.json stores files as 'images/<id>/<name>' (older rows: bare names)."""
    f = str(p.get("file", ""))
    return "/" + f.lstrip("/") if f.startswith("images/") else f"/images/{eid}/{f}"


# --------------------------------------------------------------------------- fragments

def status_label(rec: dict) -> str:
    return str(rec.get("status", "FLAGGED FOR REVIEW"))


def hero(code: str, name: str, entries: list[tuple[str, dict]], photo_count: int) -> str:
    state = entries[0][1].get("state", "") if entries else ""
    badges = []
    for _, r in entries:
        b = (status_label(r), r.get("badgeClass", "badge-flagged"))
        if b not in badges:
            badges.append(b)
    topics = sorted({t for _, r in entries for t in (r.get("topics") or [])})
    return (
        '<div class="park-hero">\n'
        f'<div class="breadcrumb"><a href="/">Map</a> &rarr; {esc(name)}</div>\n'
        f'<h1>{esc(name)}</h1>\n'
        f'<div class="park-location">{esc(code)} &middot; {esc(state)}</div>\n'
        '<div class="status-badges">\n' + "".join(f'<span class="badge {esc(c)}">{esc(s)}</span>\n' for s, c in badges) + '</div>\n'
        '<div class="stats-row">\n'
        f'<div class="stat-chip"><strong>{len(entries)}</strong> {"entry" if len(entries) == 1 else "entries"}</div>\n'
        f'<div class="stat-chip"><strong>{photo_count}</strong> {"photo" if photo_count == 1 else "photos"}</div>\n'
        f'<div class="stat-chip"><strong>{len(topics)}</strong> {"topic" if len(topics) == 1 else "topics"}</div>\n'
        '</div>\n'
        '<div class="topic-pills">\n' + "".join(f'<span class="topic-pill">{esc(t)}</span>\n' for t in topics) + '</div>\n'
        '</div>\n'
    )


def history_card(code: str, name: str, hist: dict | None) -> str:
    published = bool(hist) and hist.get("reviewStatus") == "published"
    body = bph.render_block(hist) if hist else ""
    badge = "Sourced" if published else "NPSHistory.com"
    if not body:
        body = f'<p>NPSHistory.com keeps the administrative histories, handbooks and reports for {esc(name)}.</p>'
    return (
        f'<!-- park-history:start {code} -->\n'
        '<div class="park-history-section" style="margin-top:0;margin-bottom:40px;padding:32px;background:rgba(16,16,28,0.6);border:1px solid #2a2a3a;border-radius:16px">\n'
        '<div style="display:flex;align-items:center;gap:12px;margin-bottom:20px">\n'
        '<h2 style="font-size:14px;letter-spacing:2px;text-transform:uppercase;color:#6d9eeb;margin:0;font-family:-apple-system,sans-serif;font-weight:700">Park History</h2>\n'
        f'<span style="display:inline-block;padding:3px 10px;border-radius:4px;font-size:10px;font-weight:700;letter-spacing:0.5px;text-transform:uppercase;background:rgba(109,158,235,0.15);color:#6d9eeb;font-family:-apple-system,sans-serif;border:1px solid rgba(109,158,235,0.3)">{badge}</span>\n'
        '</div>\n'
        f'{body}\n'
        '</div>\n'
        '<!-- park-history:end -->\n'
    )


def entry_card(code: str, eid: str, r: dict, manifest: dict) -> str:
    photos = manifest.get(eid, [])
    status = status_label(r)
    media = r.get("media") or "Interpretive materials"
    parts = ['<div class="entry-card">\n<div class="entry-card-header">\n',
             f'<span class="entry-id">Entry #{esc(eid)}</span>\n',
             f'<span class="badge {esc(r.get("badgeClass", "badge-flagged"))}">{esc(status)}</span>\n</div>\n',
             f'<h3>{esc(status.title() if status.isupper() and len(status) > 24 else status)}: {esc(media)}</h3>\n',
             f'<div class="entry-meta">\n<span>{esc(media)}</span>\n<span>{len(photos)} {"photo" if len(photos) == 1 else "photos"}</span>\n</div>\n']
    if photos:
        parts.append('<div class="entry-photos">\n')
        for p in photos[:2]:
            parts.append(f'<div class="entry-photo"><img src="{esc(photo_src(eid, p))}" alt="{esc(p.get("name") or media)}" loading="lazy"></div>\n')
        if len(photos) > 2:
            parts.append(f'<div class="entry-photo-more">+{len(photos) - 2} more</div>\n')
        parts.append('</div>\n')
    if r.get("flagNote"):
        parts.append(f'<div class="entry-flagged"><strong>Note</strong>{esc(r["flagNote"])}</div>\n')
    parts.append(f'<div class="entry-narrative">{r.get("narrative", "")}</div>\n')
    topics = r.get("topics") or []
    if topics:
        parts.append('<div class="entry-topics">\n' + "".join(f'<span class="topic-pill">{esc(t)}</span>\n' for t in topics) + '</div>\n')
    signs = r.get("sosSignNames") or []
    if signs:
        parts.append('<div class="entry-flagged"><strong>Signs removed or changed (Save Our Signs tracker)</strong><ul>'
                     + "".join(f'<li>&ldquo;{esc(s.get("title"))}&rdquo; &mdash; {esc(SIGN_STATUS.get(s.get("status"), s.get("status") or "removed"))}</li>' for s in signs)
                     + '</ul></div>\n')
    nonsign = r.get("sosNonSignItems") or []
    if nonsign:
        parts.append('<div class="entry-flagged"><strong>Other items removed or changed (Save Our Signs tracker)</strong><ul>'
                     + "".join(f'<li>{esc(x if isinstance(x, str) else x.get("title") or x.get("item"))}</li>' for x in nonsign) + '</ul></div>\n')
    filing = r.get("filingDetail") or []
    if filing:
        src = r.get("filingSource") or "NPS court filing"
        items = []
        for d in filing:
            bits = [esc(d.get("item", ""))]
            if d.get("rows") and int(d.get("rows") or 0) > 1:
                bits[0] += f' (&times;{int(d["rows"])})'
            if d.get("reason"):
                bits.append(f'reason: {esc(d["reason"])}')
            if d.get("location"):
                bits.append(f'now: {esc(d["location"])}')
            items.append("<li>" + "; ".join(bits) + "</li>")
        parts.append(f'<div class="entry-flagged"><strong>What the Park Service told the court ({esc(src)})</strong><ul>{"".join(items)}</ul></div>\n')
    if r.get("orderedContext"):
        parts.append(f'<div class="entry-flagged"><strong>Ordered to remove</strong>{esc(r["orderedContext"])}</div>\n')
    if r.get("whatTheyWantChanged"):
        parts.append(f'<div class="entry-flagged"><strong>Exact Text Targeted for Removal</strong>{r["whatTheyWantChanged"]}</div>\n')
    parts.append(f'<a class="view-map-link" href="/?id={esc(eid)}&park={esc(code)}">View on map &rarr;</a>\n</div>\n')
    return "".join(parts)


def sos_photos(entries: list[tuple[str, dict]]) -> str:
    pairs = []
    for _, r in entries:
        for p in r.get("sosPhotoUrls") or []:
            for label, key in (("before", "before"), ("after", "after"), ("restored", "restored")):
                if p.get(key):
                    pairs.append((p.get("title", ""), label, p[key]))
    if not pairs:
        return ""
    cards = "".join(
        f'<div class="sos-pair"><img src="/{esc(path)}" alt="{esc(title)} &mdash; {label}" loading="lazy"><div class="sos-pair-title">{esc(title)}</div>'
        f'<span class="sos-label sos-label-{label}" style="margin-bottom:10px">{label}</span></div>' for title, label, path in pairs)
    return ('<div class="section-heading">Signs Documented by Save Our Signs</div>\n'
            f'<div class="sos-pairs">{cards}</div>\n'
            '<p style="font-size:11px;color:#666;font-family:-apple-system,sans-serif;margin:-6px 0 24px">Photos courtesy Save Our Signs (public domain)</p>\n')


def archive_photos(legacy_ids: list[str], manifest: dict) -> str:
    photos = photos_for(legacy_ids, manifest)
    if not photos:
        return ""
    shown = photos[:18]
    items = "".join(f'<a href="{esc(photo_src(i, p))}" target="_blank" rel="noopener"><img src="{esc(photo_src(i, p))}" alt="{esc(p.get("name") or "Archived photograph")}" loading="lazy"></a>' for i, p in shown)
    more = f'<div class="more">+{len(photos) - len(shown)} more</div>' if len(photos) > len(shown) else ""
    return (f'<div class="section-heading">Archive Photographs ({len(photos)})</div>\n'
            '<p style="font-size:13px;color:#888;font-family:-apple-system,sans-serif;margin-bottom:12px">Photographs attached to this park\'s records in the leaked NPS review database.</p>\n'
            f'<div class="archive-photos">{items}{more}</div>\n')


def lawsuits(entries: list[tuple[str, dict]]) -> str:
    out = []
    seen = set()
    for _, r in entries:
        items = []
        if r.get("sosLawsuit"):
            items.append(r["sosLawsuit"])
        items += r.get("sosLawsuits") or []
        for l in items:
            key = l.get("url") or l.get("title")
            if key in seen:
                continue
            seen.add(key)
            out.append(f'<div class="lawsuit-box"><div class="lawsuit-title">{esc(l.get("title"))}</div><div class="lawsuit-detail">{esc(l.get("detail"))}</div>'
                       + (f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">View court filing &rarr;</a>' if l.get("url") else "") + '</div>\n')
    return ('<div class="section-heading">Related Lawsuit</div>\n' + "".join(out)) if out else ""


def news_sources(entries: list[tuple[str, dict]]) -> str:
    seen = set()
    items = []
    for _, r in entries:
        for s in r.get("sosSources") or []:
            if not s.get("url") or s["url"] in seen:
                continue
            seen.add(s["url"])
            items.append(f'<a class="news-source-item" href="{esc(s["url"])}" target="_blank" rel="noopener">\n<div class="news-source-icon">&#128240;</div>\n<div class="news-source-details">'
                         f'<span class="news-source-pub">{esc(s.get("pub"))}</span><span class="news-source-title">{esc(s.get("title"))}</span><span class="news-source-date">{esc(s.get("date"))}</span></div>\n</a>\n')
    if not items:
        return ""
    return '<div class="news-sources-section">\n<div class="news-sources-header">\n<h2>News Sources</h2>\n<span class="verified-badge">Verified</span>\n</div>\n' + "".join(items) + '</div>\n'


# --------------------------------------------------------------------------- page

def describe(name: str, entries: list[tuple[str, dict]], photo_count: int) -> tuple[str, str]:
    n = len(entries)
    statuses = sorted({status_label(r).lower() for _, r in entries})
    desc = f'{n} {"entry" if n == 1 else "entries"} at {name}: {", ".join(statuses)}. {photo_count} photograph{"" if photo_count == 1 else "s"} documenting censorship under SO 3431.'
    tw = f'{n} {"entry" if n == 1 else "entries"} flagged or removed. {photo_count} photo{"" if photo_count == 1 else "s"} documenting what\'s being erased.'
    return desc, tw


def render_page(code: str, data: dict) -> str:
    reg = data["registry"][code]
    entries = entries_for(code, data["parkData"])
    hist = data["history"].get(code)
    name = (hist or {}).get("name") or (entries[0][1].get("park") if entries else code)
    live_ids = [e for e, _ in entries]
    legacy_ids = [i for i in reg.get("legacyEntryIds", []) if i not in live_ids]
    photo_count = len(photos_for(live_ids + legacy_ids, data["manifest"]))
    slug = reg["slug"]
    url = f"{SITE}/parks/{slug}.html"
    desc, tw = describe(name, entries, photo_count)
    og_image = f"{SITE}/og-parks/{slug}.png" if (ROOT / "og-parks" / f"{slug}.png").exists() else f"{SITE}/og-image.png"
    json_ld = json.dumps({"@context": "https://schema.org", "@type": "Article", "name": f"{name} — Missing Park History", "url": url, "description": desc,
                          "author": {"@type": "Organization", "name": "Missing Park History Project"},
                          "about": {"@type": "LandmarksOrHistoricalBuildings", "name": name}}, ensure_ascii=False)
    body = (hero(code, name, entries, photo_count)
            + history_card(code, name, hist)
            + f'<div class="section-heading">Flagged Entries ({len(entries)})</div>\n'
            + "".join(entry_card(code, eid, r, data["manifest"]) for eid, r in entries)
            + sos_photos(entries)
            + archive_photos(legacy_ids, data["manifest"])
            + lawsuits(entries)
            + news_sources(entries))
    page = data["template"]
    for k, v in {"TITLE": esc(f"{name} — The Missing History of Our National Parks"), "DESCRIPTION": esc(desc), "TW_DESCRIPTION": esc(tw),
                 "CANONICAL": url, "OG_TITLE": esc(f"{name} — Missing Park History"), "OG_IMAGE": og_image, "JSON_LD": json_ld,
                 "BODY": body.rstrip("\n"), "ENTRY_COUNT": str(len(data["parkData"]))}.items():
        page = page.replace("{{" + k + "}}", v)
    return page


def parks_with_pages_literal(data: dict) -> str:
    items = []
    for code in sorted(data["registry"]):
        reg = data["registry"][code]
        entries = entries_for(code, data["parkData"])
        if not entries:
            continue
        hist = data["history"].get(code)
        name = (hist or {}).get("name") or entries[0][1].get("park")
        ids = [e for e, _ in entries] + [i for i in reg.get("legacyEntryIds", []) if i not in {e for e, _ in entries}]
        photos = len(photos_for(ids, data["manifest"]))
        items.append(f'{code}:{{name:{json.dumps(name, ensure_ascii=False)},entries:{len(entries)},photos:{photos},slug:"{reg["slug"]}"}}')
    return "parksWithPages={" + ",".join(items) + "}"


def update_index(data: dict) -> bool:
    p = ROOT / "index.html"
    html = p.read_text()
    new = parks_with_pages_literal(data)
    m = re.search(r"parksWithPages=\{.*?\}\}", html, re.S)
    if not m:
        raise RuntimeError("parksWithPages table not found in index.html")
    if m.group(0) == new:
        return False
    p.write_text(html[:m.start()] + new + html[m.end():])
    return True


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="compare generated pages with disk; exit 1 if stale")
    ap.add_argument("--update-index", action="store_true", help="rewrite parksWithPages in index.html")
    ap.add_argument("--only", help="comma-separated codes")
    args = ap.parse_args(argv)
    data = load()
    codes = [c.strip().upper() for c in args.only.split(",")] if args.only else sorted(data["registry"])
    stale = []
    written = 0
    for code in codes:
        if code not in data["registry"]:
            print(f"warn: {code} not in data/park_pages.json", file=sys.stderr)
            continue
        out = PARKS / f"{data['registry'][code]['slug']}.html"
        html = render_page(code, data)
        if args.check:
            if not out.exists() or out.read_text() != html:
                stale.append(out.name)
        else:
            if not out.exists() or out.read_text() != html:
                out.write_text(html)
                written += 1
    if args.check:
        idx_stale = parks_with_pages_literal(data) not in (ROOT / "index.html").read_text()
        for s in stale:
            print("stale:", s)
        if idx_stale:
            print("stale: index.html parksWithPages (run --update-index)")
        return 1 if (stale or idx_stale) else 0
    print(f"{written} page(s) written, {len(codes) - written} unchanged")
    if args.update_index:
        print("index.html parksWithPages", "updated" if update_index(data) else "unchanged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
