---
name: nps-news-updater
description: >
  Daily updater skill for the MissingParkHistory.org News & Press page.
  Use this skill whenever the user asks to update, refresh, or add new articles
  to the NPS censorship news timeline. Also trigger when the user mentions
  "update the news page", "check for new NPS articles", "refresh the timeline",
  "add new press coverage", "daily news update", or any reference to keeping
  the MissingParkHistory.org news/press section current. This skill handles
  web research, article curation, HTML insertion, QA, and git commit.
---

# NPS News & Press Daily Updater

This skill maintains the chronological news timeline on the MissingParkHistory.org
News & Press page (`news-and-press.html`). It searches for new reporting on NPS
sign censorship, SO 3431, EO 14253, and related litigation, then inserts new
article cards into the HTML file in the correct chronological position.

## When to Run

- **Daily**: Ideally once per day, or on-demand when the user requests.
- **Breaking news**: Immediately when major developments occur (court rulings,
  new removals, legislative action, new lawsuits).

## Workflow

### Step 1: Research New Coverage

Run multiple web searches to find articles published since the last update date
shown in the update-banner element. Suggested queries:

```
"NPS sign removal" OR "national park censorship" [current month/year]
"SO 3431" OR "Secretary Order 3431" [current month/year]
"national park exhibit removed" [current month/year]
NPCA "national parks" lawsuit [current month/year]
"Democracy Forward" "national parks" [current month/year]
"MissingParkHistory" OR "Save Our Signs" [current month/year]
national park "executive order" history signs [current week]
```

Also check these key sources directly via web_fetch:
- https://www.npca.org/news
- https://www.nationalparkstraveler.org
- https://democracyforward.org/news
- https://www.sierraclub.org/press-releases
- https://www.outsideonline.com/outdoor-adventure/environment/

### Step 2: Evaluate and Curate

For each candidate article, assess:
1. **Relevance**: Must be directly about NPS sign/exhibit censorship, SO 3431,
   EO 14253, related litigation, or preservation/resistance efforts.
2. **Novelty**: Is it genuinely new information, or a rehash of existing coverage?
3. **Source quality**: Prioritize original reporting from major outlets (WaPo, NYT,
   NPR, AP, PBS) and domain-specific sources (NPCA, Outside, NPS Traveler,
   Democracy Forward). Include notable regional coverage.
4. **Deduplication**: Check against existing entries in the HTML file.

### Step 3: Classify and Tag

Assign each new article exactly ONE primary tag:

| Tag Class | CSS Class | Use When |
|-----------|-----------|----------|
| Executive Order / Secretary's Order | tag-order | New orders, directives, memos |
| Removal | tag-removal | Confirmed sign/exhibit removals |
| Resistance | tag-resistance | Advocacy, preservation efforts, public pushback |
| Lawsuit | tag-lawsuit | New filings, legal motions, FOIA suits |
| Leak | tag-leak | Leaked documents, databases, internal communications |
| Court Ruling | tag-court | Judge rulings, injunctions, orders |

### Step 4: Generate Article Cards

For each new article, create an HTML card following this exact template:

```html
<article class="article-card" data-tags="[tag-class]">
  <div class="article-date">
    <div class="month-day">[Mon DD]</div>
    <div class="date-detail">[YYYY]</div>
  </div>
  <div class="article-body">
    <div class="article-meta">
      <span class="article-source">[SOURCE NAME]</span>
      <span class="article-tag [tag-css-class]">[TAG LABEL]</span>
    </div>
    <h3><a href="[URL]" target="_blank">[HEADLINE]</a></h3>
    <p class="article-summary">[2-4 sentence paraphrased summary. Include
    key facts, named parties, and significance. Bold key terms with strong tags.]</p>
    <a href="[URL]" class="read-more" target="_blank">Read at [Source] &rarr;</a>
  </div>
</article>
```

**Writing guidelines for summaries:**
- Paraphrase entirely — never quote articles directly
- Include specific names, dates, and numbers
- Note the significance or why it matters
- Keep to 2-4 sentences (mobile-friendly)
- Use strong tags for key terms sparingly

### Step 5: Insert into HTML

1. Open `news-and-press.html`
2. Find the correct year section (create a new year-marker div if needed)
3. Insert the new card in chronological order within that year section
4. Update the update-banner div:
   - Set the date to today
   - Update the article count
   - Update the litigation status if changed

### Step 6: Update Statistics

Review and update the hero stats if needed:
- **Items Flagged**: Update if new leak data changes the count
- **Parks Affected**: Update if new parks are confirmed
- **Active Lawsuits**: Update count
- **Court-Ordered Restorations**: Update count

Also update the Key Background cards if there are major new developments.

### Step 7: QA/QC

Before committing, verify:
- All links work (no 404s)
- Dates are accurate and in chronological order
- Tags are correct and filter buttons work
- No duplicate entries
- Summaries are factual and sourced (no fabricated claims)
- HTML is valid (no unclosed tags)
- The update banner date is set to today

### Step 8: Git Commit

```bash
cd /path/to/missingparkhistory-news
git add news-and-press.html
git commit -m "news: add [N] articles through [date]

- [Brief description of each new article]
- Updated stats: [any stat changes]
- Sources: [list primary sources]"
```

### Step 9: Archive

Move the previous version to an Archive folder before saving the new one:
```bash
mkdir -p Archive
cp news-and-press.html Archive/news-and-press_$(date +%Y%m%d).html
```

## Key Search Terms to Monitor

These terms and entities should be checked regularly:

**Orders and Policy:**
Executive Order 14253, Secretary's Order 3431, Secretary's Order 3416,
Jessica Bowron (acting NPS Director), Doug Burgum national parks

**Litigation:**
NPCA v Department of Interior, Democracy Forward national parks,
Philadelphia President's House lawsuit, Sierra Club FOIA Interior Department,
preliminary injunction national parks

**Preservation and Resistance:**
MissingParkHistory.org, SaveOurSigns.org, Save Our Signs project,
National Parks Traveler censorship, Resistance Rangers

**Removals and Specific Sites:**
NPS sign removal [any park name], interpretive sign removed,
Grand Canyon exhibit, Glacier climate sign, Independence Hall slavery,
Selma to Montgomery Civil Rights, Stonewall NPS

## Error Handling

- If no new articles are found, report that to the user and update only the
  banner date to confirm the check was performed.
- If search results are ambiguous, flag them for user review rather than
  auto-inserting.
- If a source URL is paywalled, note it in the card and prefer non-paywalled
  coverage of the same story.
