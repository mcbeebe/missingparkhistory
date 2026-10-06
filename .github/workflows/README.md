# GitHub Actions — Daily NPS News Update

This workflow runs **daily at 8 AM Pacific (15:00 UTC)** on GitHub's servers —
no local computer required.

## One-time setup

1. **Add the Anthropic API key as a repo secret**
   - In GitHub: *Settings → Secrets and variables → Actions → New repository secret*
   - Name: `ANTHROPIC_API_KEY`
   - Value: your key (starts with `sk-ant-...`)

2. **Verify workflow permissions**
   - *Settings → Actions → General → Workflow permissions*
   - Select **"Read and write permissions"** (so the bot can push commits)
   - Check **"Allow GitHub Actions to create and approve pull requests"** is not required, but fine either way

3. **Push this workflow to GitHub**
   ```bash
   git add .github/workflows/ scripts/
   git commit -m "ci: add daily news updater GitHub Action"
   git push origin main
   ```

4. **Test it manually first**
   - Go to *Actions → Daily NPS News Update → Run workflow*
   - Try `dry_run = true` first to preview what it would add.
   - Then `dry_run = false, force = true` to let it commit once.

5. **Disable the Cowork scheduled task** (so you don't get duplicate runs):
   - Ask Claude in Cowork: *"Disable the nps-news-daily-update scheduled task"*.

## What the workflow does

- Runs `scripts/update_news.py`
- The script calls the Anthropic API (Claude Sonnet 4.5) with the native
  `web_search` tool enabled — no Serper or scraping needed
- Claude returns structured JSON of qualifying new articles
- Python renders HTML cards, inserts them at the top of the correct year
  section in `news-and-press.html`, and updates the banner
- Previous version is copied to `News and Press/Archive/news-and-press_YYYYMMDD.html`
- Commit is pushed as `NPS News Bot <bot@missingparkhistory.org>`

### Weekly jobs

Two jobs run whenever they are **7+ days stale** (not just on Mondays), and
retry on each daily run until they succeed:

- **Where the Fight Stands** (home-page news pop-up in `index.html`): a
  two-paragraph synthesis + three badges, written from articles *published or
  added* since the last refresh. Stamp: `<!-- news-bot:synthesis-updated DATE -->`.
- **Timeline** (`timeline.html`, newest first): up to 3 milestone events per
  week, each required to cite an article already tracked on the News & Press
  page (anything else is discarded). Stamp: `<!-- news-bot:timeline-updated DATE -->`.

- **Status page** (`status.html`, "Where the Issue Stands Now"): the same
  weekly synthesis is also written into the page's `<div class="nd-synthesis">`
  block, and a separate weekly pass rewrites the **four fronts** (lanes) and the
  **case board** from structured JSON. Every changed lane or case must cite an
  article already tracked on the News & Press page or it is discarded; items
  the model marks unchanged keep their existing HTML. The lanes and cases live
  between `<!-- status-bot:lanes-start/end -->` and
  `<!-- status-bot:cases-start/end -->`; the "Updated" date in the hero
  (`<time id="statusUpdated">`) follows. Stamp:
  `<!-- news-bot:status-updated DATE -->`. The verdict strip and the stat tiles
  are hand-edited and never touched by the bot.

To stop the bot editing a section, add its freeze comment on its own:
`news-bot:freeze-synthesis` / `news-bot:freeze-digest` (in `index.html`),
`news-bot:freeze-timeline` (in `timeline.html`) or `news-bot:freeze-status`
(in `status.html`; `freeze-synthesis` in `index.html` also freezes the copy of
the synthesis on the status page). Run *Actions → Daily NPS News
Update → Run workflow* with **force_synthesis = true** to run both weekly jobs
immediately.

## Cost

Each run uses ~1 Claude API call with up to 12 web searches. Expected cost
well under **$0.10/day**. Set a monthly budget on your Anthropic account if
you want a hard cap.

## Troubleshooting

- **Workflow didn't fire at 8 AM sharp** — GitHub cron can delay up to ~15
  minutes under load. This is normal.
- **`ANTHROPIC_API_KEY` not set** — double-check the secret name (exact match,
  no typos, no trailing whitespace).
- **Push fails with 403** — check repo *Settings → Actions → General* has
  "Read and write permissions" enabled.
- **Claude returns invalid JSON** — check the run log; the script prints the
  first 500 chars of the response. If this becomes a pattern, tighten the
  `CURATION_PROMPT` in `scripts/update_news.py`.

## Running locally (manual test)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
pip install -r scripts/requirements.txt
python scripts/update_news.py --dry-run
```

---

# GitHub Actions — Layout tests

`layout-tests.yml` runs on every pull request and on pushes to `main`. It
serves the repo as static files and uses Playwright (headless Chromium) to
check every public page (root `*.html` + `parks/*.html`):

- **No horizontal overflow at 390px** (iPhone-width) — including content that
  is silently clipped inside the fixed header, and long unbroken text.
- **Shared header** (`nav.topnav`, styled by `/site-nav.css` and driven by
  `/site-nav.js`) collapses into a working menu whenever its links don't fit,
  and shows the full link row on desktop.

Run locally: `npm install && npm test` (needs Python 3 for the static server).
