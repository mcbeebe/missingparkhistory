#!/usr/bin/env python3
"""Generate data/blockedFunding.json for the map's "Blocked funding" layer.

Source: data/source/nps-disapprovals-2026.csv, the NPS Financial Assistance
Submission Tracker (FAST) records of partner agreements Interior disapproved on
Aug 7, 2026 and that were still disapproved on Sep 9, 2026 (133 rows). The
Center for Western Priorities published the extract:
https://github.com/Center-for-Western-Priorities/2026-NPS-Agreement-Disapprovals
Titles and impact statements are NPS's own words and are kept verbatim.

Each agreement gets a `hist` flag for the map's "History & collections" lens.
The flag is our classification, not a field in the records. An agreement
counts if it was filed under a cultural-resources listing (15.946 / 15.955) or
its title names history, archives, archeology, museum, curation, heritage, or
Tribal work. The HIST_EXCLUDE / HIST_INCLUDE lists then correct that rule by
hand, by FAST ID. Edit those lists to change the classification and rerun.

Usage:
    python scripts/build_blocked_funding.py           # write the JSON
    python scripts/build_blocked_funding.py --check   # exit 1 if the JSON is stale
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source" / "nps-disapprovals-2026.csv"
PARKS = ROOT / "data" / "parkData.json"
OUT = ROOT / "data" / "blockedFunding.json"

HIST_LISTINGS = {"Cultural resources management", "MLK Historic Site preservation"}
HIST_TITLE = re.compile(r"archiv|archeolog|archaeolog|histor|museum|interpret|curat|cultural|heritage|tribal", re.I)

# Matched by the rule, but the work is not history or collections.
HIST_EXCLUDE = {
    "1674",  # CRMO GIS specialist
    "1956",  # ORCA cave (natural) interpretation interns
    "1981",  # GRSA sand-dune interpretation interns
    "2458",  # HPTC facilities-management interns
    "2558",  # GLCA general compliance and permitting
    "2723",  # SEKI GIS and data management
    "3042",  # EFMO hazard-tree removal
    "3144",  # DEVA abandoned mine lands
}
# Missed by the rule, but plainly history or collections work.
HIST_INCLUDE = {
    "1987",  # PWRO Preservation Partnerships Program support
    "2132",  # MANZ visitor services at Manzanar
    "2227",  # PETR National Register nomination
    "2346",  # NERO book and paper conservation internship
    "2407",  # NERO preservation assistance support
}

SOURCE_URL = "https://westernpriorities.org/resource/map-agreements-blocked-by-the-trump-administration-at-61-national-park-sites/"


def partner(name: str) -> str:
    low = name.lower()
    if "great basin" in low:
        return "Great Basin Institute"
    if "student conservation" in low:
        return "Student Conservation Association"
    if "experienced workforce" in low:
        return "National Experienced Workforce Solutions"
    return name.strip()


def is_hist(r: dict) -> bool:
    fid = r["fast_id"]
    if fid in HIST_EXCLUDE:
        return False
    if fid in HIST_INCLUDE:
        return True
    return r["program"] in HIST_LISTINGS or bool(HIST_TITLE.search(r["title"]))


def build() -> dict:
    with SRC.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if r["status"] == "Disapproved"]
    for fid in HIST_EXCLUDE | HIST_INCLUDE:
        if not any(r["fast_id"] == fid for r in rows):
            sys.exit(f"override FAST ID {fid} is not in {SRC.name}")

    coords: dict[str, tuple[float, float]] = {}
    for p in json.loads(PARKS.read_text(encoding="utf-8")).values():
        if p.get("code") and isinstance(p.get("lat"), (int, float)) and isinstance(p.get("lon"), (int, float)):
            coords.setdefault(p["code"], (p["lat"], p["lon"]))

    units: dict[str, dict] = {}
    for r in rows:
        u = units.setdefault(r["unit_code"], {
            "name": r["unit_name"], "type": r["unit_type"], "n": 0, "usd": 0,
            "hist_n": 0, "hist_usd": 0, "partners": [], "items": [],
        })
        exact = float(r["fed_funding_this_action"])
        usd = round(exact)
        h = is_hist(r)
        u["n"] += 1
        u["usd"] += exact
        if h:
            u["hist_n"] += 1
            u["hist_usd"] += exact
        p = partner(r["recipient"])
        if p not in u["partners"]:
            u["partners"].append(p)
        u["items"].append({
            "id": r["fast_id"], "title": r["title"], "usd": usd, "partner": p,
            "listing": r["assistance_listing"], "hist": h, "impact": r["project_impact"],
        })
    for u in units.values():
        u["items"].sort(key=lambda i: -i["usd"])
        u["partners"].sort()

    parks, offmap = {}, []
    for code, u in sorted(units.items()):
        if code in coords:
            u["lat"], u["lon"] = coords[code]
            parks[code] = u
        else:
            offmap.append({"code": code, "name": u["name"], "type": u["type"], "n": u["n"], "usd": u["usd"]})
    offmap.sort(key=lambda o: -o["usd"])

    def tot(us, k):
        return round(sum(u[k] for u in us))

    allu = list(units.values())
    meta = {
        "decided": "2026-08-07",
        "as_of": "2026-09-09",
        "n": tot(allu, "n"), "usd": tot(allu, "usd"),
        "hist_n": tot(allu, "hist_n"), "hist_usd": tot(allu, "hist_usd"),
        "map_units": len(parks), "map_n": tot(parks.values(), "n"), "map_usd": tot(parks.values(), "usd"),
        "offmap_n": tot(offmap, "n"), "offmap_usd": tot(offmap, "usd"),
        "source_url": SOURCE_URL,
    }
    # Totals above are summed from exact cents; round per unit only for display.
    for u in units.values():
        u["usd"], u["hist_usd"] = round(u["usd"]), round(u["hist_usd"])
    for o in offmap:
        o["usd"] = round(o["usd"])
    return {"meta": meta, "parks": parks, "offmap": offmap}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    text = json.dumps(build(), ensure_ascii=False, separators=(",", ":")) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != text:
            sys.exit(f"{OUT.relative_to(ROOT)} is stale; run scripts/build_blocked_funding.py")
        print("blockedFunding.json is current")
        return
    OUT.write_text(text, encoding="utf-8")
    m = json.loads(text)["meta"]
    print(f"wrote {OUT.relative_to(ROOT)}: {m['n']} agreements ${m['usd']:,}; history {m['hist_n']} ${m['hist_usd']:,}; "
          f"on map {m['map_units']} units {m['map_n']} ${m['map_usd']:,}; off map {m['offmap_n']} ${m['offmap_usd']:,}")


if __name__ == "__main__":
    main()
