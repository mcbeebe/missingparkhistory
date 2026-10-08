# NPSHistory.com audit

`scripts/npshistory_audit.py` compares every park unit on the map with what
[NPSHistory.com](https://npshistory.com/) — an independent, public-domain archive of
National Park Service publications — holds for it, and ranks the gaps. It is the
first step of the per-park "Park History" program: the output tells authors which
parks to write first and which administrative histories, historic resource studies,
ethnographic overviews and climate studies to read.

## Outputs

| File | What it is |
|---|---|
| `data/npshistory_index.json` | Per-code inventory for authors: resolved NPSHistory URL, establishment dates, document counts by category and theme, and the classified documents (title, URL, year, categories, themes). Only documents that matched a category or theme are kept. |
| `data/npshistory_audit.json` | The mapping table: one row per canonical park code with MPH's current state (narrative kind, topics, photos, park page, Wayback health, topic-page case studies), NPSHistory's holdings, per-theme gap grades and a priority tier. Sorted by `gapScore`. |
| `--csv PATH` / `--xlsx PATH` | The same table for spreadsheets (XLSX adds a theme × tier pivot, a "Missing & Aliases" sheet and the rubric). |

## Running it

```bash
python scripts/npshistory_audit.py                       # full run; cached pages are reused
python scripts/npshistory_audit.py --refresh             # re-validate the cache (conditional GETs)
python scripts/npshistory_audit.py --offline             # never touch the network
python scripts/npshistory_audit.py --codes MORA,CAWO -v  # a few parks, verbose
python scripts/npshistory_audit.py --xlsx ~/Desktop/NPSHistory_Mapping_Analysis.xlsx
```

Pages are cached under `.cache/npshistory/` (gitignored). A cold run fetches ~440
pages at about one per second (≈10 minutes). NPSHistory is a volunteer archive that
blocks non-browser clients, so the script identifies as a browser and keeps the rate
low; never loop it.

## How codes are resolved

NPSHistory URLs are **discovered**, not assumed: the home page's park `<select>`
(`Name (CODE)` → URL) and the anchors on `park_histories.htm` are read first, then a
park-name match catches code mismatches (MPH `CACR` = NPSHistory `CARI`). Composite MPH
codes such as `GWMP,THIS` are split into one row per unit. `data/npshistory_aliases.json`
lists the few exceptions: NPS administrative units with no park page (`SERO`, `CBPO`,
`ANCH`, `WEAR`, `NEPH`, `MWAC`, `FAIR`, `NRSS`), FWS/BLM sites, umbrella codes skipped
when picking an entry's primary unit, and one BLM-hosted override.

## How documents are classified

`data/npshistory_themes.json` holds the keyword rules — edit it, not the script.
Each document's `title | citation | group header` is matched against category rules
(administrative history, HRS, ethnographic, cultural landscape, HSR, National
Register/HABS/HAER, brochure, handbook, foundation document, planning, newspaper,
climate). Themes (indigenous, women, black, slavery, climate, labor_ccc, lgbtq,
japanese_american, latino) are matched on `title | group` only, because citations carry
author names. Each rule has a `not` pattern that is blanked out before matching, which is
how "Stonewall Jackson" stays out of LGBTQ and "Nisqually Glacier" stays out of
Indigenous. `tests/python/test_npshistory_audit.py` pins these cases.

Counts are title-based and therefore a **floor**: an administrative history usually
discusses Indigenous history, labor and women without saying so in its title.

## The rubric

- **MPH theme level**: 0 = no topic tag and no keyword in the narrative / flagged text;
  1 = tag or keyword mention; 2 = a published Park History theme block.
- **NPSHistory theme level**: 0 = nothing; 1 = 1–2 documents; 2 = 3+ documents or an
  anchor study.
- **Gap**: `P1` expected, sources exist, MPH has nothing, worst status is severity 3
  (content removed / revised / ordered); `P2` same without severity 3; `P3` MPH only
  mentions it; `NA` MPH mentions it but NPSHistory has nothing (source from nps.gov /
  Wayback / other U.S.-government works); `OK` otherwise.
- **gapScore** = severity × (3·P1 + 2·P2 + P3) + 2 if the narrative is boilerplate
  + 2 if a topic page uses the park as a case study + 1 if a `parks/` page exists.
- **tier** 1 = severity 3, or topic-page case study, or severity ≥ 2 with a boilerplate
  narrative; 2 = custom narrative with open P2/P3 gaps; 3 = everything else.

## Refreshing

Re-run after `data/parkData.json` changes (new statuses move parks between tiers) or
quarterly to pick up new NPSHistory documents. Commit the two JSON outputs with the
change; the XLSX lives outside the repo.
