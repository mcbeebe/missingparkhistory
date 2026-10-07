# Watching the Save Our Signs Censorship Tracker

Save Our Signs (University of Minnesota) maintains the public tracker this site cites as
"Data: SOS Removal Tracker". It is a Google Sheet:
<https://docs.google.com/spreadsheets/d/1ulzIcpjpyTKLa52DClUkUlcazJPdAryK0B0oKmA9TF8/>.
SOS is cited as a **source**, never as a verifier of this site's data (their request, March 2026).

## What runs automatically

`.github/workflows/sos-tracker-watch.yml` runs `scripts/sos_tracker_watch.py` every Monday at
08:30 Pacific (after the daily news job). The script exports every visible tab as CSV, keys each
row by `alpha_code | subsite | title | date | item description` so re-ordering is not a change,
and diffs against `data/sos_tracker_snapshot.json`.

When anything changed it opens:

- a **pull request** that updates the snapshot (the audit trail; merge it after triage), and
- an **issue** labelled `sos-tracker` whose body is the change report (added / removed /
  changed rows with the cells that changed, new or vanished tabs, and the banner totals such as
  "102 signs / 41 sites").

Run it by hand any time:

```bash
python scripts/sos_tracker_watch.py --dry-run          # print the diff, keep the snapshot
python scripts/sos_tracker_watch.py --report out.md    # also write the report to a file
python scripts/sos_tracker_watch.py --baseline         # re-baseline after a manual review
```

Exit codes: 0 no changes, 3 changes, 1 the sheet could not be fetched.

## Triage checklist (per `sos-tracker` issue)

1. Map each changed row to its `data/parkData.json` entry: `alpha_code` first, then the sheet's
   "related response ID" through `data/sos_id_aliases.json` (SOS uses the leaked-dataset IDs,
   some of which this site consolidated away).
2. Decide the status:
   - press- or photo-confirmed ("Confirmed removed/modified by news reports?" = yes, or SOS
     before/after photos) → `CONFIRMED REMOVED`, `confirmedRemoved: true`;
   - listed only in the NPS court filing (Doc. 49-2, June 17, 2026) → the "Removed — per NPS
     court filing" badge, `filingRemoved: true`, copy the purple columns into `filingDetail`;
   - on the "Flagged for review or ordered to remove" tab → `orderedToRemove: true`.
3. Add the sheet's confirmation link to `sosSources`, its photo URLs to `sosPhotoUrls`
   (copy the images into `images/<entry>/` with the credit "Photo: Save Our Signs, public
   domain"), and the sign title to `sosSignNames` with the row's `sosRowKey`.
4. If the banner totals moved, update the tiles on `status.html` and the home-page stat strip;
   add a timeline milestone for anything the sheet marks as a new event; the news bot handles
   article cards.
5. Open the change as a PR against `main` (3-way merge content pages onto `origin/main`), let
   CI pass, merge, and close the issue with the PR link.

## What usually changes

New rows after a court filing or a major newspaper story; "Confirmed by news" flipping to yes;
new before/after photo URLs; "Item Current Location" moving between *At the park*, *Discarded*
and restored; new tabs (the old-format tab is hidden, not deleted); additions to the lawsuits tab.

## Quarterly

On the first day of each quarter the same workflow runs
`python scripts/sos_tracker_watch.py --coverage` and files the result as an
`sos-tracker` issue: one row per park comparing the tracker's sign rows (press-
confirmed, court filing, with photos), non-sign rows and flagged rows with the
site's status, sign list, sources and park page, plus a "Needs attention" list.
Run it any time from the Actions tab (`coverage = true`) or locally:

```bash
python scripts/sos_tracker_watch.py --coverage                   # fresh download
python scripts/sos_tracker_watch.py --coverage --from-snapshot   # saved snapshot
```

Known, expected flags: Independence lists fewer signs than the tracker because
the tracker counts each two-panel set as two rows; parks confirmed from other
sources (Stonewall, Golden Gate, the BLM monuments) have no tracker rows.
Re-read the full gap analysis
([`docs/sos-tracker-gap-analysis-2026-10-06.md`](sos-tracker-gap-analysis-2026-10-06.md))
when the report shows a pattern rather than one-off rows.
