#!/usr/bin/env python3
"""Watch the Save Our Signs (SOS) Censorship Tracker for changes.

The tracker is a public Google Sheet maintained by Save Our Signs (UMN):
    https://docs.google.com/spreadsheets/d/1ulzIcpjpyTKLa52DClUkUlcazJPdAryK0B0oKmA9TF8/

This script:
  1. Discovers the sheet's visible tabs (name -> gid) from the public HTML view.
  2. Exports every tab as CSV (no auth needed; the sheet is "anyone with the link").
  3. Normalises each tab into keyed records so row re-ordering is not a "change".
  4. Writes a snapshot JSON (data/sos_tracker_snapshot.json by default).
  5. Diffs against the previous snapshot and prints a Markdown change report
     (added / removed / changed rows, per tab, with the cells that changed).

Exit codes: 0 = no changes, 3 = changes detected, 1 = error.  The non-zero
"changes" code lets a GitHub Actions step decide whether to open an issue/PR.

Usage:
    python scripts/sos_tracker_watch.py                 # diff + update snapshot
    python scripts/sos_tracker_watch.py --dry-run       # diff only, keep old snapshot
    python scripts/sos_tracker_watch.py --report out.md # also write the report to a file
    python scripts/sos_tracker_watch.py --baseline      # (re)create snapshot, no diff
    python scripts/sos_tracker_watch.py --coverage      # per-park tracker vs. site report (quarterly)
    python scripts/sos_tracker_watch.py --coverage --from-snapshot  # same, from the saved snapshot

Only the standard library is used so the script runs anywhere.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

SHEET_ID = "1ulzIcpjpyTKLa52DClUkUlcazJPdAryK0B0oKmA9TF8"
HTMLVIEW = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/htmlview"
EXPORT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={{gid}}"

# Known tabs as of 2026-10-06 (gid -> short name).  Discovery adds anything new.
KNOWN_TABS = {
    "689733930": "ABOUT",
    "1460906999": "NPS signs removed or modified",
    "484100168": "Non-signs confirmed removed/modified",
    "140530881": "Flagged for review or ordered to remove",
    "1443371538": "Related non-NPS reports",
    "279510859": "Related lawsuits and legislation",
}

# Columns that identify a row (used to build a stable key).  Anything not
# listed falls back to a hash of the first three non-empty cells.
KEY_COLUMNS = {
    "NPS signs removed or modified": ["alpha_code", "Name of subsite, if applicable", "Title of sign, if known", "Date reported", "Item Description"],
    "Non-signs confirmed removed/modified": ["alpha_code", "Name of subsite, if applicable", "Title, if known", "Date reported", "Item Description"],
    "Flagged for review or ordered to remove": ["Name of NPS site", "Name of subsite, if applicable", "Date reported", "Title of sign, if known"],
    "Related non-NPS reports": ["Agency", "Name of site", "Date reported"],
    "Related lawsuits and legislation": ["Title", "Number"],
}

UA = {"User-Agent": "MissingParkHistory-SOS-watch/1.0 (+https://missingparkhistory.org)"}


def fetch(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def discover_tabs() -> dict[str, str]:
    """Return {gid: name}.  Names come from KNOWN_TABS; unknown gids get a placeholder."""
    tabs = dict(KNOWN_TABS)
    try:
        html = fetch(HTMLVIEW).decode("utf-8", "replace")
        for gid in set(re.findall(r"gid=(\d+)", html)):
            tabs.setdefault(gid, f"(new tab gid {gid})")
    except Exception as exc:  # discovery is best-effort
        print(f"warn: tab discovery failed ({exc}); using known tabs only", file=sys.stderr)
    return tabs


def header_row(rows: list[list[str]]) -> int:
    """Index of the header row.

    The tabs start with 1-2 banner rows (notes, the 'TOTAL CENSORED SIGNS'
    counter) before the real header, so take the row among the first five with
    the most non-empty cells; ties go to the earliest row.
    """
    best, best_n = 0, -1
    for i, r in enumerate(rows[:5]):
        n = sum(1 for c in r if c.strip())
        if n > best_n:
            best, best_n = i, n
    return best


def normalise_tab(name: str, raw: bytes) -> tuple[list[str], dict[str, dict[str, str]], dict]:
    rows = list(csv.reader(io.StringIO(raw.decode("utf-8-sig", "replace"))))
    if not rows:
        return [], {}, {}
    h = header_row(rows)
    header = [c.strip() for c in rows[h]]
    # keep de-duplicated header names (Google exports "Column 4", "Column 5" ... for blanks)
    seen: dict[str, int] = {}
    cols = []
    for c in header:
        c = c or "blank"
        seen[c] = seen.get(c, 0) + 1
        cols.append(c if seen[c] == 1 else f"{c} ({seen[c]})")
    records: dict[str, dict[str, str]] = {}
    keycols = KEY_COLUMNS.get(name, [])
    for r in rows[h + 1:]:
        if not any(c.strip() for c in r):
            continue
        rec = {cols[i]: (r[i].strip() if i < len(r) else "") for i in range(len(cols))}
        rec = {k: v for k, v in rec.items() if v}  # drop empty cells
        if not rec:
            continue
        parts = [rec.get(k, "") for k in keycols] if keycols else []
        if not keycols or not any(parts):
            parts = [v for v in list(rec.values())[:3]]
        base = " | ".join(p.replace("\n", " ")[:120] for p in parts)
        key = base
        n = 2
        while key in records:  # identical keys (e.g. repeated "Bottle Filling Station") get a suffix
            key = f"{base} #{n}"
            n += 1
        records[key] = rec
    meta = {"rows": len(records), "columns": cols}
    # the banner cells above the header carry the SOS headline totals
    for r in rows[:h]:
        for c in r:
            m = re.search(r"TOTAL CENSORED SIGNS", c)
            if m:
                meta["total_label"] = c.strip()
            if re.search(r"Number of NPS sites with censored signs", c):
                meta["sites_label"] = c.strip()
        for c in r:
            if c.strip().isdigit():
                meta.setdefault("banner_numbers", []).append(int(c.strip()))
    # "Number of NPS sites with censored signs:\n41 ..." keeps its number inside the text cell
    m = re.search(r"censored signs:\s*(\d+)", meta.get("sites_label", ""))
    if m:
        meta.setdefault("banner_numbers", []).append(int(m.group(1)))
    return cols, records, meta


def build_snapshot() -> dict:
    tabs = discover_tabs()
    snap = {"fetched_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "sheet_id": SHEET_ID, "tabs": {}}
    for gid, name in sorted(tabs.items(), key=lambda kv: kv[1]):
        raw = fetch(EXPORT.format(gid=gid))
        cols, records, meta = normalise_tab(name, raw)
        snap["tabs"][name] = {"gid": gid, "sha1": hashlib.sha1(raw).hexdigest(), "meta": meta, "records": records}
    return snap


def diff_snapshots(old: dict, new: dict) -> tuple[bool, str]:
    out: list[str] = []
    changed_any = False
    out.append(f"# SOS Censorship Tracker — change report\n")
    out.append(f"Previous snapshot: {old.get('fetched_at', 'none')}  \nCurrent snapshot: {new['fetched_at']}\n")
    for name, tab in new["tabs"].items():
        o = old.get("tabs", {}).get(name)
        if o is None:
            changed_any = True
            out.append(f"## {name}\n**New tab** ({tab['meta'].get('rows', 0)} rows).\n")
            continue
        if o.get("sha1") == tab["sha1"]:
            continue
        orec, nrec = o.get("records", {}), tab["records"]
        added = [k for k in nrec if k not in orec]
        removed = [k for k in orec if k not in nrec]
        changed = [k for k in nrec if k in orec and nrec[k] != orec[k]]
        banner_old, banner_new = o.get("meta", {}).get("banner_numbers"), tab["meta"].get("banner_numbers")
        if not (added or removed or changed or banner_old != banner_new):
            continue  # export bytes differ (ordering/whitespace) but content is identical
        changed_any = True
        out.append(f"## {name}  ({len(orec)} → {len(nrec)} rows)\n")
        if banner_old != banner_new:
            out.append(f"- Banner totals changed: {banner_old} → {banner_new}")
        for k in added:
            r = nrec[k]
            out.append(f"- **ADDED** `{k}`")
            for col in ("What was removed or modified", "Link to confirmation news report", "Where was it reported/confirmed?", "Reason for Removal", "Status", "Information and Documents"):
                if r.get(col):
                    out.append(f"    - {col}: {r[col][:300].replace(chr(10), ' ')}")
        for k in removed:
            out.append(f"- **REMOVED** `{k}`")
        for k in changed:
            out.append(f"- **CHANGED** `{k}`")
            a, b = orec[k], nrec[k]
            for col in sorted(set(a) | set(b)):
                if a.get(col, "") != b.get(col, ""):
                    out.append(f"    - {col}: {a.get(col, '∅')[:160].replace(chr(10), ' ')} → {b.get(col, '∅')[:160].replace(chr(10), ' ')}")
        out.append("")
    for name in old.get("tabs", {}):
        if name not in new["tabs"]:
            changed_any = True
            out.append(f"## {name}\n**Tab disappeared from the public view.**\n")
    if not changed_any:
        out.append("No changes since the previous snapshot.\n")
    return changed_any, "\n".join(out)


# ---------------------------------------------------------------- coverage (quarterly reconciliation)
def _yes(v: str) -> bool:
    return (v or "").strip().lower().startswith("yes")


_DESIG = r"\b(national|historical|historic|park|site|monument|memorial|preserve|seashore|lakeshore|recreation|area|battlefield|military|trail|parkway|and|of|the)\b"


def _norm(name: str) -> str:
    """Park name without punctuation, apostrophes or designation words, for matching."""
    name = re.sub(r"['\u2019]", "", name.lower())
    name = re.sub(r"[^a-z0-9]+", " ", name)
    return re.sub(r"\s+", " ", re.sub(_DESIG, " ", name)).strip()


def _sign_count(signs: list) -> int:
    n = 0
    for s in signs or []:
        m = re.search(r"\((\d+) signs\)$", s.get("title", ""))
        n += int(m.group(1)) if m else 1
    return n


def coverage(snapshot: dict, root: Path = Path(".")) -> tuple[str, int]:
    """Per park: what the tracker lists vs. what the site shows. Returns (markdown, problems)."""
    pd = json.loads((root / "data/parkData.json").read_text())
    idx = (root / "index.html").read_text()
    pages = {m.group(1): m.group(2) for m in re.finditer(r'([A-Z]{4}):\{name:"[^"]*",entries:\d+,photos:\d+,slug:"([^"]*)"\}', idx)}
    tabs = snapshot["tabs"]
    track: dict[str, dict] = {}
    def row(code):
        return track.setdefault(code, {"signs": 0, "press": 0, "filing": 0, "photos": 0, "nonsigns": 0, "flagged": 0, "names": set()})
    for rec in tabs.get("NPS signs removed or modified", {}).get("records", {}).values():
        code = rec.get("alpha_code", "").strip()
        if not code: continue
        r = row(code); r["signs"] += 1; r["names"].add(rec.get("Name of NPS site", ""))
        r["press"] += _yes(rec.get("Confirmed removed/modified by news reports?", ""))
        r["filing"] += _yes(next((v for k, v in rec.items() if k.startswith("Was this sign")), ""))
        r["photos"] += any(rec.get(k) for k in rec if k.endswith("Photo - URL") or k.startswith("Missing Sign Photo"))
    for rec in tabs.get("Non-signs confirmed removed/modified", {}).get("records", {}).values():
        code = rec.get("alpha_code", "").strip()
        if code: row(code)["nonsigns"] += 1
    by_name = {}
    for v in pd.values():
        by_name.setdefault(_norm(v["park"]), v["code"])
    unmatched = []
    for rec in tabs.get("Flagged for review or ordered to remove", {}).get("records", {}).values():
        name = _norm(rec.get("Name of NPS site", ""))
        code = by_name.get(name) or next((c for n, c in by_name.items() if name and (n.startswith(name) or name.startswith(n))), None)
        if code: row(code)["flagged"] += 1
        elif name and "parks" not in name: unmatched.append(rec.get("Name of NPS site", ""))
    site: dict[str, dict] = {}
    for k, v in pd.items():
        s = site.setdefault(v["code"], {"entries": [], "confirmed": False, "filing": False, "ordered": False, "signs": 0, "sources": 0, "statuses": set()})
        s["entries"].append(k); s["statuses"].add(v["status"])
        s["confirmed"] |= bool(v.get("confirmedRemoved")); s["filing"] |= bool(v.get("filingRemoved"))
        s["ordered"] |= bool(v.get("orderedToRemove")); s["signs"] += _sign_count(v.get("sosSignNames"))
        s["sources"] += len([x for x in v.get("sosSources") or [] if isinstance(x, dict)])
    codes = sorted(set(track) | {c for c, s in site.items() if s["confirmed"] or s["filing"]})
    lines = ["| Park | Tracker: signs (press / filing / photos) | Non-signs | Flagged | Site status | Site signs | Sources | Page | Check |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    problems = []
    for code in codes:
        t = track.get(code, {"signs": 0, "press": 0, "filing": 0, "photos": 0, "nonsigns": 0, "flagged": 0})
        s = site.get(code)
        notes = []
        removed_rows = t["signs"] + t["nonsigns"]
        if not s:
            notes.append("no site entry")
        else:
            removed = s["confirmed"] or s["filing"]
            if removed_rows and not removed:
                notes.append("tracker lists removals; site does not show them")
            if (t["press"] or t["photos"]) and t["signs"] and not s["confirmed"]:
                notes.append("press/photo-confirmed in tracker; site not Confirmed Removed")
            if t["signs"] > s["signs"]:
                notes.append(f"sign list short ({s['signs']} of {t['signs']})")
            if t["flagged"] and not (s["ordered"] or removed):
                notes.append("flagged in tracker; not marked ordered")
            if removed and code not in pages:
                notes.append("no park page")
            if s["confirmed"] and not removed_rows and not t["flagged"]:
                notes.append("info: confirmed on site from other sources")
        real = [n for n in notes if not n.startswith("info:")]
        if real: problems.append((code, real))
        status = ", ".join(sorted(s["statuses"]))[:60] if s else "\u2014"
        lines.append(f"| {code} | {t['signs']} ({t['press']} / {t['filing']} / {t['photos']}) | {t['nonsigns']} | {t['flagged']} | {status} | "
                     f"{s['signs'] if s else 0} | {s['sources'] if s else 0} | {'yes' if code in pages else 'no'} | {'; '.join(notes) or 'ok'} |")
    out = [f"# SOS tracker coverage \u2014 snapshot {snapshot.get('fetched_at', '?')}", "",
           f"{len(codes)} parks compared; {len(problems)} need attention.", ""]
    if problems:
        out += ["## Needs attention", ""] + [f"- **{c}**: {'; '.join(n)}" for c, n in problems] + [""]
    if unmatched:
        out += ["## Flagged-tab sites not matched to a park", ""] + [f"- {u}" for u in sorted(set(unmatched))] + [""]
    out += ["## All parks", ""] + lines
    return "\n".join(out) + "\n", len(problems)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--snapshot", default="data/sos_tracker_snapshot.json", help="snapshot path (default: data/sos_tracker_snapshot.json)")
    ap.add_argument("--report", help="write the Markdown change report here as well as stdout")
    ap.add_argument("--dry-run", action="store_true", help="diff but do not overwrite the snapshot")
    ap.add_argument("--baseline", action="store_true", help="write a fresh snapshot without diffing")
    ap.add_argument("--coverage", action="store_true", help="print a per-park tracker vs. site report instead of diffing")
    ap.add_argument("--from-snapshot", action="store_true", help="with --coverage: use the saved snapshot, no download")
    args = ap.parse_args()

    path = Path(args.snapshot)
    if args.coverage:
        try:
            snap = json.loads(path.read_text()) if args.from_snapshot else build_snapshot()
        except Exception as exc:
            print(f"error: could not load the tracker: {exc}", file=sys.stderr)
            return 1
        text, problems = coverage(snap)
        print(text)
        if args.report:
            Path(args.report).write_text(text)
        return 0
    try:
        new = build_snapshot()
    except Exception as exc:
        print(f"error: could not fetch the tracker: {exc}", file=sys.stderr)
        return 1

    if args.baseline or not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(new, indent=1, ensure_ascii=False))
        rows = {n: t["meta"].get("rows", 0) for n, t in new["tabs"].items()}
        print(f"Baseline snapshot written to {path}: {rows}")
        return 0

    old = json.loads(path.read_text())
    changed, report = diff_snapshots(old, new)
    print(report)
    if args.report:
        Path(args.report).write_text(report)
    if changed and not args.dry_run:
        path.write_text(json.dumps(new, indent=1, ensure_ascii=False))
        print(f"\nSnapshot updated: {path}")
    return 3 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
