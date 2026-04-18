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
