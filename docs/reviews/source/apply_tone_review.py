#!/usr/bin/env python3
"""Apply the approved Tone & Sensitivity Review v1.0 edits, with citations.

Each edit in tone-review-v1.0.json swaps an exact `current_html` for
`proposed_html`, either in a map entry's narrative (data/parkData.json) or in a
topic page. Before swapping, a citation is appended to the new paragraph:

  * a linked tag per published source, e.g. [NPS] or [Smithsonian];
  * [NPS review record] when the fact comes only from the internal NPS review
    record (the flagged text shown on each entry), linked to the methodology
    page that explains where that record comes from.

Park pages are generated from parkData.json, so run
`python scripts/build_park_pages.py` afterwards.

Usage: python docs/reviews/source/apply_tone_review.py [--check]
  --check  exit 1 unless every edit is already applied (used by the tests)
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
EDITS = Path(__file__).with_name("tone-review-v1.0.json")
PARK_DATA = ROOT / "data" / "parkData.json"
RECORD_URL = "/data-methodology.html#where-the-data-starts"

LABELS = {
    "nps.gov": "NPS", "home.nps.gov": "NPS", "npshistory.com": "NPSHistory.com",
    "en.wikipedia.org": "Wikipedia", "jhnewsandguide.com": "Jackson Hole News&amp;Guide",
    "smithsonianmag.com": "Smithsonian", "bozemandailychronicle.com": "Bozeman Daily Chronicle",
    "wbhm.org": "WBHM", "bia.gov": "Interior Dept.", "spokesman.com": "Spokesman-Review",
    "nbcmontana.com": "NBC Montana", "presidency.ucsb.edu": "American Presidency Project",
    "archive.archaeology.org": "Archaeology", "dh.durangoherald.com": "Durango Herald",
    "gazette.com": "Colorado Springs Gazette", "kqed.org": "KQED", "historynet.com": "HistoryNet",
    "891khol.org": "KHOL",
}


def label_for(url: str) -> str:
    host = urlparse(url).netloc.lower()
    host = host[4:] if host.startswith("www.") else host
    return LABELS.get(host, host)


def citations(edit: dict) -> str:
    """Citation tags for one edit: published sources first (Wikipedia only when
    nothing better backs the claim), else the NPS review record."""
    urls, seen = [], set()
    for s in edit.get("sources", []):
        u = s.get("url", "")
        if u.startswith("http") and u not in seen:
            seen.add(u)
            urls.append((u, s.get("note", "")))
    if any(label_for(u) != "Wikipedia" for u, _ in urls):
        urls = [(u, n) for u, n in urls if label_for(u) != "Wikipedia"]
    tags = []
    labels_used: dict[str, int] = {}
    for u, note in urls:
        lab = label_for(u)
        labels_used[lab] = labels_used.get(lab, 0) + 1
        if labels_used[lab] > 1:
            lab = f"{lab} {labels_used[lab]}"
        title = html.escape(re.sub(r"\s+", " ", note).split(". Confirmed via")[0][:180], quote=True)
        tags.append(f'<a href="{html.escape(u, quote=True)}" target="_blank" rel="noopener" class="cite" '
                    f'title="{title}">[{lab}]</a>')
    uses_record = any(not s.get("url", "").startswith("http") and s.get("url", "") not in ("", "n/a")
                      for s in edit.get("sources", []))
    if uses_record:
        tags.append(f'<a href="{RECORD_URL}" class="cite" title="The internal NPS review record for this '
                    f'entry, shown in full under What the Administration Ordered Changed">[NPS review record]</a>')
    return " ".join(tags)


def with_citations(edit: dict) -> str:
    new = edit["proposed_html"]
    cites = citations(edit)
    if not new.strip() or not cites:
        return new
    idx = new.rfind("</p>")
    if idx == -1:
        return f"{new} {cites}"
    return f"{new[:idx]} {cites}{new[idx:]}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    edits = json.loads(EDITS.read_text(encoding="utf-8"))
    data = json.loads(PARK_DATA.read_text(encoding="utf-8"))
    pages: dict[Path, str] = {}
    problems = []
    for e in edits:
        new = with_citations(e)
        if e["field"] == "narrative":
            targets = [(k, data[k]["narrative"]) for k in e["keys"]]
            for k, text in targets:
                if new and new in text and e["current_html"] not in text:
                    continue
                if args.check or text.count(e["current_html"]) != 1:
                    problems.append(f"edit {e['id']}: key {k} not applied / current text not found once")
                    continue
                data[k]["narrative"] = text.replace(e["current_html"], new)
        else:
            path = ROOT / e["file"]
            text = pages.setdefault(path, path.read_text(encoding="utf-8"))
            if (new and new in text and e["current_html"] not in text) or (not new.strip() and e["current_html"] not in text):
                continue
            if args.check or text.count(e["current_html"]) != 1:
                problems.append(f"edit {e['id']}: {e['file']} not applied / current text not found once")
                continue
            pages[path] = text.replace(e["current_html"], new)
    if problems:
        print("\n".join(problems))
        return 1
    if not args.check:
        PARK_DATA.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        for path, text in pages.items():
            path.write_text(text, encoding="utf-8")
        print(f"applied {len(edits)} edits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
