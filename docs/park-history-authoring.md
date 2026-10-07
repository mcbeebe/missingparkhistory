# Writing a park history

Every park unit on the map gets a `data/park_history/<CODE>.json` file: a sourced history
of the site itself — its grandeur, the peoples who lived with it, what happened there and
what is changing — not an inventory of what the archive holds. `scripts/build_park_history.py`
compiles these files into `data/parkHistory.json`, which the map modal and the park pages
render as the "Park History" section.

Accuracy is the top priority. A single wrong fact on a censorship-tracking site is worse
than a missing one. The rules below are enforced by `tests/python/test_park_history.py`
where they can be, and by a human/agent verifier where they cannot.

## Where to start

1. Open `data/npshistory_index.json` → `parks[CODE]`. It lists the archive page, the
   administrative history (`anchors.adhi`), historic resource study (`hrs`), ethnographic
   studies (`ethno`), cultural landscape inventories, and the documents matched to each theme.
2. Read, in this order: the archive page's overview prose (the NPS brochure text) and
   establishment block; the administrative history's HTML chapters (prefer `adhi/index.htm`
   chapter pages — 300-page PDFs exceed fetch limits); the HRS; the ethnographic overview;
   the climate/glacier reports' summary pages; any theme-specific article.
3. Read the park's map entry in `data/parkData.json` (`whatTheyWantChanged`, `sosSignNames`,
   `filingDetail`) so the history speaks to what was flagged or removed.
4. Fetch npshistory.com with a browser User-Agent (bare curl gets 403). Scanned PDFs have
   no text layer; read them page by page with a PDF viewer and cite page numbers.

## What to write

- **Summary** (2–3 paragraphs, 150–300 words): the place first. Scale, landscape, what it
  protects, how long people have been there, when and why it became a park, what the Park
  Service itself says is at stake there.
- **Theme sections** (60–160 words each, only for themes the sources support):
  `indigenous`, `women`, `black`, `slavery`, `climate`, `labor_ccc`, `lgbtq`,
  `japanese_american`, `latino`. Tell the human story with specifics — names, dates, numbers —
  and let the documents' own conclusions carry the weight ("Catton argues…", "the 2016 report
  finds…").
- **Voice**: the site's — factual, number-dense, plain sentences, ending on what it means.
  Paraphrase; never quote more than a short phrase. Use present-day tribal names as the
  nations use them, and say so when a source uses an older spelling ("Yakima (today's Yakama
  Nation)"). Date old sources whose language is dated. No euphemism for slavery,
  incarceration or removal. Never say what the Park Service "intended" unless a document does.
- **Hedge what the source hedges**: "archaeological findings suggest", "according to guide
  Leonard Longmire's 1933 reminiscence". Interpretive claims get `"interpretive": true` in
  the ledger and an attribution in the prose.

## Sourcing rules

- Allowed: NPS documents on NPSHistory.com → nps.gov (live, or a Wayback snapshot dated
  2025-01-19 or earlier when the live page was altered) → other U.S. Government works
  (LOC, USGS, NARA) → journal articles archived on NPSHistory. **Never a sole source:**
  Wikipedia, Britannica, news reports, or memory. If you cannot point to it in a document
  you opened, it does not go in.
- Every `<p>` carries at least one inline citation:
  `<a href="…" target="_blank" rel="noopener" class="cite">[n]</a>`. Each theme's
  `sources[]` lists every URL cited in its HTML.
- **Fact ledger** — one `facts[]` row per date, number, name or interpretive statement:
  `{"claim": …, "sourceUrl": …, "locator": "chapter / footnote / page"}`. This is what the
  verifier checks line by line.
- HTML allowed in text: `p a em strong ul li br` only. Banned strings: the old boilerplate
  ("is one of hundreds of…", "466+"), "under review", "TODO".

## Photos (Phase E)

1–2 per park, public domain only, copied into `images/history/<code>/` at ≤ 250 KB:
nps.gov images credited "NPS Photo" → NPS Flickr / Harpers Ferry Center items marked public
domain → Library of Congress HABS/HAER/HALS → NPSHistory's own NPS hero photo → Wikimedia
Commons files tagged `PD-USGov-NPS`, `PD-USGov`, `PD-old` or `CC0`. CC BY / CC BY-SA are
excluded. Record `credit` verbatim, `license`, `sourceUrl`, `imageUrl`, `evidenceUrl`,
`capturedAt`. No qualifying photo → `photos: []`, `photoStatus: "none-found"`.

## Review states

`draft` → `reviewed` → `published`. Only `published` renders in the map modal.

- `draft`: author has run `python scripts/build_park_history.py --check` clean.
- `reviewed`: a **different** agent or person has opened every cited source and ticked every
  `facts[]` row and photo credit; name them in `verifiedBy`; corrections applied.
- `published`: set only by the project owner (or a delegated lead) after a spot-check.
- `legacy-unsourced`: paragraphs seeded from the old hand-written park pages. They render on
  the park pages only, never in the modal, and are replaced when the park is authored.

Post-publication fixes go in `corrections[]` with a date and note; the page shows
"Updated <date>".

## Commands

```bash
python scripts/build_park_history.py --seed-from-pages   # once: legacy paragraphs -> files
python scripts/build_park_history.py --compile           # after any edit
python scripts/build_park_history.py --check             # what CI runs
python scripts/build_park_history.py --render MORA       # eyeball the HTML block
python -m unittest discover -s tests/python
```
