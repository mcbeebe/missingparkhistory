# MissingParkHistory.org — News & Press

A chronological news timeline tracking coverage of NPS sign censorship under Executive Order 14253 and Secretary's Order 3431.

## Files

| File | Purpose |
|------|---------|
| `news-and-press.html` | The news timeline page (drop into your site) |
| `daily_updater.py` | Automated Python script that searches for new articles daily |
| `.github/workflows/daily-update.yml` | GitHub Actions workflow for daily auto-updates |
| `skills/nps-news-updater/SKILL.md` | Claude skill for manual updates via conversation |
| `requirements.txt` | Python dependencies |

## Setup: Automated Daily Updates

### 1. Push to GitHub
```bash
git remote add origin git@github.com:YOUR_USERNAME/missingparkhistory-news.git
git push -u origin master
```

### 2. Add Repository Secrets
In GitHub → Settings → Secrets and variables → Actions:

| Secret | Required | Source |
|--------|----------|--------|
| `ANTHROPIC_API_KEY` | Yes | [console.anthropic.com](https://console.anthropic.com/) |
| `SERPER_API_KEY` | Optional | [serper.dev](https://serper.dev/) — free tier gives 2,500 searches/month |

### 3. How It Works
- **Schedule**: Runs daily at 8:00 AM Pacific
- **Manual trigger**: Click "Run workflow" in GitHub Actions tab
- **Process**: Searches → Claude evaluates relevance → generates article cards → inserts into HTML → git commits
- **Archive**: Previous versions auto-saved to `Archive/` folder

### 4. Local Testing
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export SERPER_API_KEY="..."  # optional

# Preview without modifying files
python daily_updater.py --dry-run

# Run the update
python daily_updater.py

# Force even if already updated today
python daily_updater.py --force
```

## Manual Updates via Claude

If you prefer to update manually through conversation, use the skill at `skills/nps-news-updater/SKILL.md`. Just tell Claude:
- "Update the news page"
- "Check for new NPS articles"
- "Refresh the timeline"

## Currently Tracking

- **28 articles** from March 2025 – March 2026
- **Sources**: Washington Post, NPR, PBS, NBC, Newsweek, Outside, NPCA, Sierra Club, Democracy Forward, OAH, NOTUS, regional outlets
- **Topics**: EO 14253, SO 3431, SO 3416, sign removals, lawsuits, leaked databases, court orders, citizen preservation efforts

## License

Content curation and code: MIT. Article summaries are original paraphrased writing. All linked articles remain property of their respective publishers.
