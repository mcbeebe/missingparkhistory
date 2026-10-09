# Tone review: MissingParkHistory.org (draft)

_Draft for the site owner, prepared 2026-10-09. No files in the repo were changed._

## Summary

- **Reviewed:** all 446 entries in `data/parkData.json` (narrative, flagged text, topics, SOS context), the four topic pages (`indigenous-history-censorship.html`, `slavery-history-censorship.html`, `civil-rights-censorship.html`, `climate-censorship.html`), and the Park History blocks (`ph-summary` / `ph-theme`) on the 20 park pages that have them.
- **Issues with a proposed rewrite:** 43 sections, 65 mechanical edits (see `tone-review-draft.json`).
  - **High: 8.** Grand Teton, Emmett Till, Fort Sumter & Fort Moultrie, Grand Canyon, Yosemite, Virgin Islands, Glacier, Sand Creek.
  - **Medium: 23.** Includes 3 topic-page fixes.
  - **Low: 12.**
  - A further set of **Low notes without rewrites** (grouped at the end) covers thin entries, mechanical quote artifacts and data-tagging errors.
- **Reviewed and fine:** the Park History blocks, the civil rights topic page (apart from small inconsistencies), and most of the script-flagged candidates (listed at the end).

### What the problems have in common

1. **Stock “Why this matters” paragraphs.** About 78 entries use a park-specific scenery or visitor-count closing line. In entries where the flagged text is about killing, enslavement or dispossession, the closing line moves straight to geology or “conservation vision” (Grand Teton, Grand Canyon, Yosemite, Virgin Islands, Fort Sumter, Glacier, Olympic, Redwood, Mesa Verde, Muir Woods).
2. **The wrong template.** The Indigenous-land template (“Long before X became a national park, this land was home to Indigenous peoples … tribal consultation”) appears on entries that have nothing to do with it, most seriously **Emmett Till** (a 1955 lynching), plus Dayton Aviation (the Wounded Knee timeline entry) and Charles Young Buffalo Soldiers. The Civil War/slavery template appears on Palo Alto (the U.S.–Mexican War). The civil-rights “people are still alive” template appears on Belmont-Paul (1917 suffragists).
3. **Auto-extracted “quotes” that are not the flagged text.** The “content that includes the language: …” paragraphs often quote reviewer labels or fragments (“Revised Text:”, “from the sentence:”, “Location: Hoh Visitor Center (HVC-1)”, “LEGACY NPS REGION”, “within right reason”). Some quote the reviewers’ proposed softer rewording as if it were the targeted text (Harpers Ferry, Golden Spike). Several times this hides the hard history: “genocidal” at Piscataway, the enslaved dockworkers on the National Mall, Hannah and Isaac Till at Morristown, and the McIntosh lynching at Gateway Arch.
4. **Mislabelled quotes.** “From the internal review records:” introduces sign text at Grand Teton, National Mall, Great Smoky Mountains, River Raisin and Cumberland. Suggested labels: “The removed sign read:” or “From the flagged wayside text:”.

### Method

- A Python triage script (kept in the scratchpad, not the repo) put every “Why this matters” paragraph into one of these groups:
  - the generic “466+ sites” template (252 entries);
  - the generic “network of 400 parks” template (30);
  - topic templates: slavery, Indigenous, civil rights, environment, language, primary sources (78 in total);
  - park-specific custom text (78);
  - no “Why this matters” paragraph (8).
- The script also searched the narrative body, the quote and `whatTheyWantChanged` for about 40 hard-history terms, plus a second, broader list. It flagged “internal review records” labels, `&quot;` artifacts and truncations.
- Every custom or no-paragraph entry, every labelled quote, and every keyword hit was then read by hand. That covers about 180 entries, including all 21 candidates from the earlier triage. The generic “466+ sites” and “400 parks” templates are bland, but they don't undercut anything. I did not flag them unless the entry had other problems.
- **Fact checking.** `nps.gov` and most news sites could not be fetched from this environment (DNS failure). WebSearch did work, so facts marked “verified online” were checked against the search engine’s summaries of the cited pages, not by reading the pages directly. Where I could not search, I relied on facts already in the repo: the entry’s own flagged text, the SOS context, or the sourced Park History blocks, which cite NPS and npshistory.com documents. Those sources are marked “from repo”. One claim could not be verified at all and is marked as such.
- **Tone of the rewrites.** Plain and factual. Each rewrite names the people harmed, is 2–4 sentences long, and drops the visitor-count sentence in hard-history entries.
- **How to apply the edits.** Park pages (`parks/*.html`) are generated from `data/parkData.json` by `scripts/build_park_pages.py`. Apply narrative edits to `parkData.json` and then rebuild the pages, or apply the same `current_html` → `proposed_html` swap to both. The JSON lists every file that contains each `current_html`. Topic-page edits are direct HTML edits.

### Facts I could not fully verify

- Sand Creek topic page: “first unit of the National Park System to label American troops as perpetrators.” I found no source and recommend deleting the sentence (item 61).
- Mesa Verde “26 present-day tribes”: this comes from a Durango Herald quote of the park curator, as summarized by search, not from an NPS page.
- Fort Sumter “approximately 40 percent”: this comes only from the park foundation-document theme quoted in the entry’s flagged text.
- Every nps.gov claim marked “verified” rests on search summaries, because nps.gov itself was unreachable.
- Muir Woods: the search summary did not name which founder worked on anti-Asian policy, so the rewrite does not name William Kent.
- Virgin Islands: the claims that the park covers 7,500 acres and includes “Saint Croix” look wrong next to the site’s own Park History block, but I left them for the owner to check.

## High severity

### 1. Grand Teton National Park

- **Severity:** High
- **Data keys:** 720
- **Files:** data/parkData.json, parks/grand-teton-np.html
- **JSON items:** 1, 2

#### narrative, quote paragraph (label + stray &quot;)

**Problem:** The quote is labelled “From the internal review records,” but it is the text of the removed sign itself (the flagged record quotes the full panel, headed “How do we acknowledge the good and bad of a historic figure?”). A stray &quot; and three spaces are left inside the closing quote.

**Current:**

```html
<p>From the internal review records: &ldquo;In January 1870, Doane participated in what is now known as the Marias Massacre, at which, the U.S. Army killed over 170 Piegan Blackfeet, including many women, elders, and children. Doane wrote fondly about this attack and bragged about it for the rest of his life.   &quot;&rdquo;</p>
```

**Proposed:**

```html
<p>The removed sign, headed &ldquo;How do we acknowledge the good and bad of a historic figure?&rdquo;, read in part: &ldquo;In January 1870, Doane participated in what is now known as the Marias Massacre, at which, the U.S. Army killed over 170 Piegan Blackfeet, including many women, elders, and children. Doane wrote fondly about this attack and bragged about it for the rest of his life.&rdquo;</p>
```

**Sources:**
- data/parkData.json key 720, whatTheyWantChanged (from repo): Repo: the flagged record reproduces the full sign text with heading; this is what the quote comes from.
- https://www.jhnewsandguide.com/news/environmental/after-trump-order-teton-park-removes-sign-about-explorer-who-massacred-native-americans/article_f92471a3-c937-46ec-b549-280a6cc8d3f3.html (verified online (WebSearch result summary)): Jackson Hole News&Guide, Jan 28 2026: sign about Doane and the massacre removed from Craig Thomas Discovery and Visitor Center. Confirmed via WebSearch result summary (page itself not fetchable).

#### narrative, “Why this matters” paragraph

**Problem:** The narrative quotes the Army’s killing of over 170 Piegan Blackfeet, many of them women, elders and children, and then moves straight to “the raw power of mountain geology” and a visitor count, with no reference to the massacre, the Blackfeet, or why the sign mattered.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Grand Tetons showcase the raw power of mountain geology—where uplift and erosion created one of Earth's most dramatic landscapes. Over 3.3 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Doane&rsquo;s expedition reports helped lead to the creation of the parks in this region, and the same man took part in the Marias Massacre and boasted of it for the rest of his life. The Blackfeet are among the tribes Grand Teton lists as traditionally associated with the park. The removed sign did not ask visitors to condemn or excuse him; it asked them to hold both parts of his story at once. We need that honesty to acknowledge our past and move forward.</p>
```

**Sources:**
- data/parkData.json key 720, whatTheyWantChanged (from repo): Repo: sign text says Doane’s journal notes and reports “played a role in future decisions to establish national parks in this area” and that he bragged about the massacre “for the rest of his life.”
- https://npshistory.com/publications/foundation-documents/grte-fd-2017.pdf (from repo): Grand Teton Foundation Document (2017), Appendix C: Blackfeet listed among traditionally associated tribes. Cited in parks/grand-teton-np.html; not fetched online.
- https://www.nps.gov/yell/learn/news/22022.htm (from repo): NPS Yellowstone release (June 2022) on renaming Mount Doane: Doane led an attack on Piegan Blackfeet, at least 173 killed, he bragged of it. Cited in parks/grand-teton-np.html; nps.gov could not be fetched from this environment (DNS failure).

### 2. Emmett Till and Mamie Till-Mobley National Monument

- **Severity:** High
- **Data keys:** 352
- **Files:** data/parkData.json
- **JSON items:** 3, 4

#### narrative, intro paragraph

**Problem:** The entry uses the Indigenous-land template (“Long before … became a national park, this land was home to Indigenous peoples … tribal consultation”). The monument marks the 1955 lynching of a 14-year-old Black boy; the narrative never says who Emmett Till was or what was done to him. The entry is also tagged “Indigenous & Native History” instead of “Civil Rights & Racial Justice”, so it is missing from the civil rights page and counted on the Indigenous page.

**Current:**

```html
<p>Long before <strong>Emmett Till and Mamie Till-Mobley NM</strong> became a national park, this land was home to Indigenous peoples whose connection to it spans thousands of years. The interpretive materials now being reviewed tell their story — often developed through years of formal tribal consultation, as required by federal law.</p>
```

**Proposed:**

```html
<p><strong>Emmett Till and Mamie Till-Mobley NM</strong> remembers Emmett Till, a 14-year-old Black boy from Chicago who was abducted, tortured and killed in Mississippi in August 1955, and his mother, Mamie Till-Mobley, who held an open-casket funeral so the country could see what had been done to her son. Its three sites are Graball Landing on the Tallahatchie River, where his body is believed to have been pulled from the water; the Tallahatchie County courthouse in Sumner, where an all-white jury acquitted the two men charged; and Roberts Temple Church of God in Christ in Chicago, where his funeral was held.</p>
```

**Sources:**
- https://www.smithsonianmag.com/smart-news/emmett-till-mother-national-monument-180982600/ (verified online (WebSearch result summary)): Monument established July 25, 2023; three sites. Confirmed via WebSearch summary.
- https://wbhm.org/2023/emmett-till-is-being-memorialized-with-3-national-monuments-heres-where-theyll-be-located (verified online (WebSearch result summary)): Graball Landing, Sumner courthouse (all-white jury acquitted), Roberts Temple. Confirmed via WebSearch summary.
- https://en.wikipedia.org/wiki/Emmett_Till_and_Mamie_Till-Mobley_National_Monument (verified online (WebSearch result summary)): Background: 14-year-old, abducted, tortured, killed Aug 1955; open-casket funeral. Confirmed via WebSearch summary.

#### narrative, “Why this matters” paragraph

**Problem:** The “Why this matters” text talks about tribal consultation and “tribal nations whose ancestors lived on this land,” which has nothing to do with this site and leaves Emmett Till’s murder unacknowledged.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Indigenous history presented at Emmett Till and Mamie Till-Mobley NM was developed through formal tribal consultation — a legal requirement under federal law. The language being reviewed was often specifically requested by tribal nations whose ancestors lived on this land for thousands of years. Revising it without renewed consultation would violate both the spirit and the letter of that process.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The flagged exhibit, &ldquo;Let the World See,&rdquo; was created with the Till family and local partners, and park staff told reviewers that without it the new site &ldquo;would be almost completely devoid of interpretation.&rdquo; Mamie Till-Mobley asked the nation to look at what happened to her son. Reviewing that exhibit for content that might disparage Americans puts her request itself under review.</p>
```

**Sources:**
- data/parkData.json key 352, whatTheyWantChanged (from repo): Repo: exhibit created with the Emmett Till and Mamie Till-Mobley Institute, Emmett Till Interpretive Center, the Till family and the Children’s Museum of Indianapolis; quote “would be almost completely devoid of interpretation.”
- https://www.smithsonianmag.com/smart-news/emmett-till-mother-national-monument-180982600/ (verified online (WebSearch result summary)): Open-casket funeral and her activism. Confirmed via WebSearch summary.

### 3. Fort Sumter and Fort Moultrie National Historical Park

- **Severity:** High
- **Data keys:** 568
- **Files:** data/parkData.json, parks/fort-sumter-and-fort-moultrie-nhp.html
- **JSON items:** 5, 6

#### narrative, “confirmed removed” paragraph

**Problem:** The paragraph says the content was removed “with no public record of what was changed or why,” but the entry’s own flagged record names the material: about nine panels from the African Passages exhibit at Fort Moultrie.

**Current:**

```html
<p>The content at Fort Sumter and Fort Moultrie NHP has been <strong>confirmed removed</strong>. What was once publicly accessible historical interpretation — developed over years by professional historians and park staff — has been taken down with no public record of what was changed or why.</p>
```

**Proposed:**

```html
<p>The content at Fort Sumter and Fort Moultrie NHP has been <strong>confirmed removed</strong>. The flagged items include about nine panels, text and images, from the <em>African Passages</em> exhibit at the Fort Moultrie Visitor Center.</p>
```

**Sources:**
- data/parkData.json key 568, whatTheyWantChanged (from repo): Repo: “approximately 9 panels from the African Passages exhibit at the Fort Moultrie Visitor Center to review including text and images.”

#### narrative, “Why this matters” paragraph

**Problem:** The flagged exhibit is about the slave trade (the park’s foundation-document theme says about 40% of enslaved Africans brought to America disembarked here), but “Why this matters” is a generic Civil War line (“the moment the nation fractured”) plus a visitor count, and never mentions slavery or the people who were brought here.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Fort Sumter marks the moment the nation fractured—where political crisis became military conflict that defined American history. Over 500,000 people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Fort Sumter is where the Civil War began. Across the harbor, the park&rsquo;s foundation document notes, Gadsden&rsquo;s Wharf and the quarantine stations on Sullivan&rsquo;s Island were where approximately 40 percent of all enslaved Africans transported to America disembarked. The <em>African Passages</em> exhibit tells their story, and links the slave trade to the war that started here.</p>
```

**Sources:**
- data/parkData.json key 568, whatTheyWantChanged (from repo): Repo: quotes the park Foundation Document interpretive theme: “former sites of Gadsden’s Wharf and quarantine stations on Sullivan’s Island, where approximately 40% of all enslaved Africans transported to America disembarked.” Not verified online.

### 4. Grand Canyon National Park

- **Severity:** High
- **Data keys:** 792
- **Files:** data/parkData.json, parks/grand-canyon-np.html
- **JSON items:** 7

**Location:** narrative, “Why this matters” paragraph

**Problem:** The removed exhibit said federal officials “pushed tribes off their land” to establish the park. The narrative ends by praising “Roosevelt’s conservation vision” as treasure-preserving, which is the exact framing the removed text corrected, and never mentions the Havasupai or other tribes.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Grand Canyon exemplifies Roosevelt's conservation vision—protecting natural wonders not as resources to exploit but as treasures to preserve. Over 4.5 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Protecting the canyon kept out mining and development, but it also displaced people who already lived there. Havasupai families farmed Ha&rsquo;a Gyoh, below the South Rim, until Park Service policies forced them out in the 1920s; the 1975 Grand Canyon National Park Enlargement Act returned land to the tribe. The removed exhibit said plainly that federal officials &ldquo;pushed tribes off their land&rdquo; to establish the park, and visitors deserve both halves of that story.</p>
```

**Sources:**
- https://www.nps.gov/grca/learn/news/indian-garden-officially-renamed-to-havasupai-gardens.htm (from repo): NPS 2022 release: Havasupai forced out of Ha’a Gyoh by Park Service policies in the 1920s. Cited in parks/grand-canyon-np.html; nps.gov not fetchable here.
- https://npshistory.com/publications/grca/adhi.pdf (from repo): Anderson, Polishing the Jewel (NPS admin history), ch. 5: 1975 Enlargement Act returned land to the Havasupai. Cited in parks/grand-canyon-np.html.
- https://www.bia.gov/as-ia/opa/online-press-release/land-near-grand-canyon-restored-havasupai-indians (verified online (WebSearch result summary)): 1975 Interior press release on land restored to the Havasupai. Confirmed via WebSearch summary.
- https://www.spokesman.com/stories/2026/jan/27/more-history-exhibits-pulled-from-national-parks-i/ (verified online (WebSearch result summary)): Syndicated Washington Post story quoting removed text “pushed tribes off their land.” Confirmed via WebSearch summary.

### 5. Yosemite National Park

- **Severity:** High
- **Data keys:** 827
- **Files:** data/parkData.json, parks/yosemite-np.html
- **JSON items:** 8, 9

#### narrative, “content targeted” paragraph (garbled quote)

**Problem:** The “quoted language” is a fragment of a reviewer list (“work of the Army.\n3) Adapting to New Life wayside: review sentence”), not sign text. It hides what was actually flagged: waysides on the Miwok, the Army’s “punitive” work and the sentence “vast numbers of their population were wiped out.”

**Current:**

```html
<p>Among the content targeted: <em>&ldquo;work of the Army.
3) Adapting to New Life wayside: review sentence&rdquo;</em> — language that the administration has flagged for review under its directive to review historically accurate interpretive materials.</p>
```

**Proposed:**

```html
<p>The flagged waysides include &ldquo;Miwoks and Meadows,&rdquo; which quotes Maria Lebrado; a history wayside describing the &ldquo;punitive&rdquo; work of the Army; the sentence &ldquo;vast numbers of their population were wiped out&rdquo; on the &ldquo;Adapting to New Life&rdquo; wayside; and a paragraph about Koomine Village on &ldquo;The First People&rdquo; wayside.</p>
```

**Sources:**
- data/parkData.json key 827, whatTheyWantChanged (from repo): Repo: list of four flagged waysides and the items to review.

#### narrative, “Why this matters” paragraph

**Problem:** Every flagged item concerns the Ahwahneechee/Miwok and what was done to them, but “Why this matters” is about glacial geology and “unparalleled beauty,” and the intro tells the park’s origin only through Muir and Johnson.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Yosemite exemplifies the power of glacial geology—where massive ice sheets sculpted a landscape of unparalleled beauty. Over 5 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Yosemite Valley was home to the Ahwahneechee long before it was a park. In 1851 the state-authorized Mariposa Battalion burned their villages and food stores to drive them onto reservations, and in 1907 the Army took Koomine, the valley&rsquo;s largest village, as a camp and forced out its residents. The flagged waysides are where visitors learn that the valley&rsquo;s story did not begin with John Muir.</p>
```

**Sources:**
- https://npshistory.com/publications/yose/hrs1.pdf (from repo): Greene, Yosemite Historic Resource Study Vol. 1 (NPS 1987): Mariposa Battalion authorized by Gov. McDougal, burned dwellings and food caches; 1907 Army took Koomine and forced residents out. Cited in parks/yosemite-np.html; not fetched online.
- https://en.wikipedia.org/wiki/Mariposa_County,_California (verified online (WebSearch result summary)): Mariposa Battalion mustered Jan 1851, burned villages. Confirmed via WebSearch summary (secondary).

### 6. Virgin Islands National Park

- **Severity:** High
- **Data keys:** 235
- **Files:** data/parkData.json, parks/virgin-islands-np.html
- **JSON items:** 10, 11

#### narrative, “Why this matters” paragraph

**Problem:** Signs removed at Annaberg told the history of enslavement on St. John (Carl Francis, born into slavery there in 1800; the 1733 revolt). The entry is tagged Slavery, yet “Why this matters” is about coral reefs and a visitor count and does not mention slavery at all.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Virgin Islands protects tropical marine ecosystems—coral reefs and beaches that sustain biodiversity and human communities. Over 600,000 people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The plantation ruins in this park were built and worked by enslaved Africans under Danish rule. The signs removed from Annaberg in 2026 told the stories of people like Carl Francis, born into slavery there in 1800, and of the 1733 Akwamu revolt, which the Park Service calls the first time enslaved people took control of a colony. They were developed with local historians and the community, who had worked for years to see that history told.</p>
```

**Sources:**
- data/parkData.json key 235, sosContext (from repo): Repo (Save Our Signs context): Annaberg signs removed by Feb 4 2026, Carl Francis, 1733 revolt, community engagement and local historians.
- https://www.nps.gov/viis/learn/historyculture/the-1733-akwamu-insurrection.htm (from repo): NPS: 1733 Akwamu insurrection, first time enslaved people took control of a colony. Cited in parks/virgin-islands-np.html; nps.gov not fetchable here.
- https://npshistory.com/publications/foundation-documents/viis-fd-2016.pdf (from repo): VIIS Foundation Document 2016: plantation economy under Danish rule built with forced labor of enslaved Africans. Cited in parks/virgin-islands-np.html.

#### narrative, intro paragraph (factual)

**Problem:** Factual error found while reviewing: the intro says Congress established the park “in 1980”; the site’s own Park History block (citing NPS) says August 2, 1956. (The next sentence also places the park on “Saint Croix and Saint John”; the Park History block describes it as St. John plus Hassel Island. Owner should check that sentence and its 7,500-acre figure; not changed here.)

**Current:**

```html
<p>In 1980, Congress established Virgin Islands National Park
```

**Proposed:**

```html
<p>On August 2, 1956, Congress established Virgin Islands National Park
```

**Sources:**
- https://npshistory.com/publications/viis/index.htm (from repo): NPSHistory.com VIIS archive page: established August 2, 1956. Cited in parks/virgin-islands-np.html; not fetched online.

### 7. Glacier National Park

- **Severity:** High
- **Data keys:** 783
- **Files:** data/parkData.json, parks/glacier-np.html
- **JSON items:** 12, 13

#### narrative, “confirmed removed” paragraph

**Problem:** Glacier removed a sign and brochures about the 1870 Marias (Baker) Massacre of Piikáni (Piegan Blackfeet). The narrative does not mention it at all and says there is “no public record of what was changed or why,” although the Blackfeet Tribal Business Council publicly described what was removed.

**Current:**

```html
<p>The content at Glacier NP has been <strong>confirmed removed</strong>. What was once publicly accessible historical interpretation — developed over years by professional historians and park staff — has been taken down with no public record of what was changed or why.</p>
```

**Proposed:**

```html
<p>The content at Glacier NP has been <strong>confirmed removed</strong>. Along with climate exhibits, the park took down a sign and brochures about the Marias Massacre &mdash; also called the Baker Massacre &mdash; of January 23, 1870, when U.S. Army troops attacked a winter camp of Piikáni (Piegan Blackfeet) and killed 173 or more people, mostly women, children and elders. The Blackfeet Tribal Business Council said materials documenting the massacre had been &ldquo;specifically targeted for removal.&rdquo;</p>
```

**Sources:**
- https://www.bozemandailychronicle.com/news/in-glacier-feds-are-quietly-scrubbing-information-on-climate-change-native-history/article_1b60e3b9-90b5-5fa0-8dca-39d038ab5fda.html (verified online (WebSearch result summary)): Sign and brochures about the Baker Massacre removed; Blackfeet Tribal Business Council statement. Confirmed via WebSearch summary.
- https://www.nbcmontana.com/news/working-for-you/tribes-national-park-advocates-upset-about-potential-changes-to-historic-displays (verified online (WebSearch result summary)): Tribal reaction. Confirmed via WebSearch summary.
- https://npshistory.com/publications/glac/eo.pdf (from repo): Reeves & Peacock ethnographic overview of Glacier (NPS 2001): Jan 23 1870, Col. E. M. Baker attacked a winter camp of Piikáni, 173 or more killed, mostly women, children and elders. Cited in parks/glacier-np.html.
- data/parkData.json key 783, sosContext (from repo): Repo: “a sign about the mass slaughter of the Piegan Blackfeet were also ordered removed.”

#### narrative, “Why this matters” paragraph

**Problem:** “Why this matters” covers only climate (“fragility of the American wilderness”) and a visitor count. The park’s Indigenous history, including the removed massacre sign and the 1895 purchase of these mountains from the Blackfeet, is absent; the intro credits Grinnell only with a nickname.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Glacier exemplifies the fragility of the American wilderness—where visible climate change impacts reveal the planet's transformation. Over 2.9 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Glacier&rsquo;s shrinking ice is the clearest view of climate change many visitors will ever have. These mountains are also the Piikáni&rsquo;s most sacred place; the government bought them from the Blackfeet in 1895, and they became part of the park in 1910. Removing both the climate exhibits and the account of the Marias Massacre leaves visitors with the scenery but not the people and forces that shaped it.</p>
```

**Sources:**
- https://npshistory.com/publications/glac/eo.pdf (from repo): Ethnographic overview: mountains the Piikáni’s most sacred place; Sept 1895 commission (Grinnell among them) bought the mountain lands; strip became part of park in 1910. Cited in parks/glacier-np.html.
- https://npshistory.com/publications/glac/glacier-retreat-2017.pdf (from repo): USGS 2017: ~150 glaciers in 1850, 26 active in 2015. Cited in parks/glacier-np.html.

### 8. Sand Creek Massacre National Historic Site

- **Severity:** High
- **Data keys:** 1062
- **Files:** data/parkData.json, parks/sand-creek-massacre-nhs.html
- **JSON items:** 14, 15

#### narrative, intro paragraph

**Problem:** The intro is the generic “Long before … became a national park, this land was home to Indigenous peoples” template. At a site created to remember a massacre, the narrative never says what happened at Sand Creek or who was killed.

**Current:**

```html
<p>Long before <strong>Sand Creek Massacre NHS</strong> became a national park, this land was home to Indigenous peoples whose connection to it spans thousands of years. The interpretive materials now being reviewed tell their story — often developed through years of formal tribal consultation, as required by federal law.</p>
```

**Proposed:**

```html
<p>At dawn on November 29, 1864, about 675 soldiers of the 1st and 3rd Colorado Volunteer Cavalry under Col. John Chivington attacked a camp of Cheyenne and Arapaho people at Sand Creek and killed more than 230 of them, mostly women, children and elders. <strong>Sand Creek Massacre NHS</strong> exists to remember them, and its waysides were developed through the tribal consultation its enabling law requires.</p>
```

**Sources:**
- https://www.nps.gov/places/sand-creek-massacre-national-historic-site.htm (verified online (WebSearch result summary)): NPS: ~675 soldiers of the 1st and 3rd Regiments, Colorado Volunteer Cavalry, killed more than 230 Cheyenne and Arapaho. Confirmed via WebSearch summary (page not fetchable).
- https://www.nps.gov/articles/sandcreek.htm (verified online (WebSearch result summary)): NPS article: approximately 230 Cheyenne and Arapaho women, children and elderly. Confirmed via WebSearch summary.
- data/parkData.json key 1062, whatTheyWantChanged (from repo): Repo: all waysides went through tribal consultation required by Public Law 106-465.

#### narrative, “Why this matters” paragraph

**Problem:** Generic consultation template; it does not reflect what was flagged (the panel was submitted because Chivington’s photo is often vandalized) or acknowledge the people killed.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Indigenous history presented at Sand Creek Massacre NHS was developed through formal tribal consultation — a legal requirement under federal law. The language being reviewed was often specifically requested by tribal nations whose ancestors lived on this land for thousands of years. Revising it without renewed consultation would violate both the spirit and the letter of that process.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The &ldquo;Night March to Sand Creek&rdquo; panel was submitted because Chivington&rsquo;s photograph on it is a frequent target of vandalism, and the park plans to move the picture somewhere less exposed. Whatever changes are made should go back through consultation with the Cheyenne and Arapaho, as every wayside here already has. At a place created to remember a massacre, the account of what happened must not be softened along the way.</p>
```

**Sources:**
- data/parkData.json key 1062, whatTheyWantChanged (from repo): Repo: vandalism of Chivington photo, planned FY26 replacement and relocation, consultation under PL 106-465.


## Medium severity

### 9. Lassen Volcanic National Park (entry text describes Lava Beds NM)

- **Severity:** Medium
- **Data keys:** 967
- **Files:** data/parkData.json
- **JSON items:** 16

**Location:** narrative, “Why this matters” paragraph (plus data mismatch)

**Problem:** “…and tragic indigenous history” tacks the Modoc War onto a geology sentence as an aside. Separately, the entry is keyed to Lassen Volcanic (code LAVO, Lassen coordinates) while the text describes Lava Beds NM, and its first sentence mixes the two (Roosevelt proclaimed Lassen Peak NM in 1907; Lava Beds NM was proclaimed by Coolidge on Nov 21, 1925). The flagged text is empty, so the owner must decide which park this entry is for; the rewrite below assumes Lava Beds.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Lava Beds demonstrates volcanic geology in all its forms—from gentle lava flows to explosive cinder cones—and tragic indigenous history. Over 100,000 people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The lava beds hold both a geological record and the site of the Modoc War, when Kintpuash (Captain Jack) and his people held out in the lava stronghold rather than return to a reservation. After the war, Kintpuash and three other Modoc men were hanged, and 163 Modocs were sent as prisoners of war to Indian Territory, where their numbers fell by a third. Both stories are part of what visitors come here to understand.</p>
```

**Sources:**
- https://www.nps.gov/labe/learn/historyculture/modoc-war.htm (verified online (WebSearch result summary)): NPS Modoc War page: Oct 3 1873 Captain Jack, Schonchin John, Black Jim, Boston Charley hanged; 163 Modocs sent as POWs to Quapaw Agency, Oklahoma; population dropped by a third. Confirmed via WebSearch summary.
- https://npshistory.com/publications/labe/brochures/modoc-war.pdf (verified online (WebSearch result summary)): NPS brochure on the stronghold. Confirmed via WebSearch summary.
- https://www.npshistory.com/publications/foundation-documents/labe-fd-overview.pdf (verified online (WebSearch result summary)): Lava Beds proclaimed by Coolidge Nov 21 1925. Confirmed via WebSearch summary.
- https://www.presidency.ucsb.edu/documents/proclamation-754-setting-aside-lassen-peak-national-monument-california (verified online (WebSearch result summary)): Lassen Peak NM proclaimed by Roosevelt May 6 1907. Confirmed via WebSearch summary.

### 10. Dayton Aviation Heritage National Historical Park

- **Severity:** Medium
- **Data keys:** 701
- **Files:** data/parkData.json
- **JSON items:** 17, 18

#### narrative, intro paragraph

**Problem:** Wrong template: the Indigenous-land/tribal-consultation intro is applied to a timeline entry about the 1890 Wounded Knee massacre at an aviation park. The massacre then appears only as a bare quote.

**Current:**

```html
<p>Long before <strong>Dayton Aviation Heritage National Historical Park</strong> became a national park, this land was home to Indigenous peoples whose connection to it spans thousands of years. The interpretive materials now being reviewed tell their story — often developed through years of formal tribal consultation, as required by federal law.</p>
```

**Proposed:**

```html
<p>At <strong>Dayton Aviation Heritage National Historical Park</strong>, one entry in a timeline exhibit marks the 1890 massacre at Wounded Knee. Park staff told reviewers the entry was &ldquo;not likely in conflict&rdquo; with the order but asked for further review.</p>
```

**Sources:**
- data/parkData.json key 701, whatTheyWantChanged (from repo): Repo: “This exhibit is part of a timeline and is not likely in conflict with SO3431, however further review is requested. Text: 1890s, 1890 Wounded Knee.”

#### narrative, “Why this matters” paragraph

**Problem:** Tribal-consultation template that does not fit this site and does not acknowledge the Lakota people killed.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Indigenous history presented at Dayton Aviation Heritage National Historical Park was developed through formal tribal consultation — a legal requirement under federal law. The language being reviewed was often specifically requested by tribal nations whose ancestors lived on this land for thousands of years. Revising it without renewed consultation would violate both the spirit and the letter of that process.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The entry is one line, and it states a documented fact: U.S. troops killed Lakota men, women and children at Wounded Knee in 1890. A timeline that keeps the year but drops the people who were killed would not be more neutral, only less true.</p>
```

**Sources:**
- data/parkData.json key 701, whatTheyWantChanged (from repo): Repo: flagged text “More than 200 Lakota men, women, and children were massacred by U.S. troops...”

### 11. Olympic National Park

- **Severity:** Medium
- **Data keys:** 535
- **Files:** data/parkData.json
- **JSON items:** 19, 20

#### narrative, flagged-language paragraph (artifacts)

**Problem:** Three of the four “quoted” items are location labels (“Location: Hoh Visitor Center (HVC-1),” etc.), not sign text. The real flagged text, about the Klallam, Hoh and Quileute and salmon, is left out.

**Current:**

```html
<p>The administration has flagged for review content that includes the language: <em>&ldquo;Entrepreneurs built two dams in the early 1900s to power growth on the Olympic Peninsula. A century later the dams were removed and the Elwha Valley began to heal.&rdquo;</em>, <em>&ldquo;Location: Hoh Visitor Center (HVC-1),&rdquo;</em>, <em>&ldquo;Location: Hoh Visitor Center (HVC-2),&rdquo;</em>, and <em>&ldquo;Location: Hoh Visitor Center (HVC-3),&rdquo;</em>.</p>
```

**Proposed:**

```html
<p>The administration has flagged for review content that includes the language: <em>&ldquo;Entrepreneurs built two dams in the early 1900s to power growth on the Olympic Peninsula. A century later the dams were removed and the Elwha Valley began to heal.&rdquo;</em> Other flagged panels say the dams &ldquo;blocked the migration of salmon&rdquo; and disrupted &ldquo;the culture of the resident Klallam tribe for 100 years,&rdquo; and that the Hoh and Quileute &ldquo;pursue traditional activities along their ancestral rivers,&rdquo; where &ldquo;environmental changes pose new challenges to age-old traditions.&rdquo;</p>
```

**Sources:**
- data/parkData.json key 535, whatTheyWantChanged (from repo): Repo: texts of AU-1, AU-2, HVC-1 panels.

#### narrative, “Why this matters” paragraph

**Problem:** The flagged panels concern harm to the Klallam people and to the salmon the Hoh and Quileute depend on; “Why this matters” calls the park “pristine” and gives a visitor count.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Olympic preserves one of Earth's most pristine rainforests—a landscape shaped by abundant water, ancient trees, and diverse wildlife. Over 3 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Olympic&rsquo;s rivers are not only scenery; they are the home waters of the Klallam and the ancestral rivers of the Hoh and Quileute, whose lives are tied to the salmon that run in them. The flagged panels explain how the Elwha dams cut those runs for a century and how a warming climate now threatens them again. Removing that context leaves visitors with the view but not the people who depend on it.</p>
```

**Sources:**
- data/parkData.json key 535, whatTheyWantChanged (from repo): Repo: AU-2 (dams blocked salmon, disrupted Klallam culture 100 years), HVC-1 (Hoh and Quileute, ancestral rivers, salmon central to tribal life), HVC-2 (shrinking glaciers, warmer rivers threaten salmon).

### 12. Redwood National and State Parks

- **Severity:** Medium
- **Data keys:** 491
- **Files:** data/parkData.json
- **JSON items:** 21

**Location:** narrative, “Why this matters” paragraph

**Problem:** The flagged items are the bookstore’s books on local tribal histories (including one on the desecration of Native graves), but “Why this matters” is only about tall trees and a visitor count. The intro also puts the Yurok, Chilula and Tolowa in the past tense.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Redwoods preserve the largest living organisms on Earth—ancient giants that have towered over human history for thousands of years. Over 1 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Yurok, Tolowa and Chilula peoples lived on the lands inside these parks long before the redwoods were protected, and the Park Service says their traditional lifeways continue today. The flagged books are the park bookstore&rsquo;s shelf of tribal histories. Pulling them would leave visitors with the trees but not the people who have always lived among them.</p>
```

**Sources:**
- https://www.nps.gov/redw/learn/park-facts.htm (verified online (WebSearch result summary)): NPS park facts: Yurok, Tolowa and Chilula historically lived on park lands; lifeways continue today. Confirmed via WebSearch summary.
- https://www.npshistory.com/publications/foundation-documents/redw-fd-overview.pdf (verified online (WebSearch result summary)): Foundation document overview: Chilula, Hupa, Tolowa and Yurok connected to the land since time immemorial. Confirmed via WebSearch summary.
- data/parkData.json key 491, whatTheyWantChanged (from repo): Repo: list of flagged books.

### 13. Mesa Verde National Park

- **Severity:** Medium
- **Data keys:** 647
- **Files:** data/parkData.json
- **JSON items:** 22, 23, 24

#### narrative, intro paragraphs (terminology)

**Problem:** The intro uses “Anasazi,” a Navajo-derived term that Pueblo nations object to, and repeats the outdated “mysteriously abandoning” framing.

**Current:**

```html
ancestral Puebloans (Anasazi), who built
```

**Proposed:**

```html
ancestral Puebloans, who built
```

**Sources:**
- https://archive.archaeology.org/0607/news/insider.html (verified online (WebSearch result summary)): Archaeology magazine: shift away from “Anasazi” since the 1990s after Hopi and other Pueblo tribes raised objections with NPS. Confirmed via WebSearch summary.
- https://en.wikipedia.org/wiki/Ancestral_Puebloans (verified online (WebSearch result summary)): Contemporary Pueblos view “Anasazi” as derogatory. Confirmed via WebSearch summary (secondary).

#### narrative, second paragraph

**Problem:** “Mysteriously abandoning” suggests the people vanished; their descendants are today’s Pueblo peoples, and drought and conflict are the usual explanations.

**Current:**

```html
The ancestral Puebloans inhabited the region from 600 to 1300 CE before mysteriously abandoning the cliff dwellings and relocating south.
```

**Proposed:**

```html
Ancestral Puebloans lived here from about 600 to 1300 CE, then moved south, most likely because of prolonged drought and conflict; 26 present-day tribes count them as ancestors.
```

**Sources:**
- https://dh.durangoherald.com/?p=199629 (verified online (WebSearch result summary)): Durango Herald: Mesa Verde curator Tara Travis says the correct term is ancestral Puebloans because 26 modern tribes are their descendants; drought and conflict as causes. Confirmed via WebSearch summary; the figure 26 comes from this secondhand source, not an NPS page.

#### narrative, “Why this matters” paragraph

**Problem:** One flagged panel describes Ute Mountain Ute land being cut back “under continued pressure from white settlements”; “Why this matters” mentions only a “pre-Columbian civilization” and a visitor count.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Mesa Verde preserves the tangible evidence of a sophisticated pre-Columbian civilization—a window into indigenous American achievement. Over 500,000 people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Mesa Verde preserves the homes of the ancestors of today&rsquo;s Pueblo peoples, and it borders the homeland of the Ute Mountain Ute Tribe, whose lands were reduced again and again &ldquo;under continued pressure from white settlements,&rdquo; as one flagged panel puts it. The flagged waysides tell both stories, along with the more frequent, more destructive fires now reshaping the mesa.</p>
```

**Sources:**
- data/parkData.json key 647, whatTheyWantChanged (from repo): Repo: MEVE-603 “The Ute Homeland” (historic and ongoing connection of the Ute Mountain Ute Tribe to ancestral lands in the park; reservation reductions); MEVE-601 fire panel.
- https://gazette.com/2021/09/21/the-other-mesa-verde-colorados-lesser-known-no-less-wondrous-tribal-park-9841d632-0ff2-11ec-b6f5-3f2527825a18/ (verified online (WebSearch result summary)): Ute Mountain Tribal Park lies within the Ute Mountain Ute Reservation, adjacent to the national park. Confirmed via WebSearch summary.

### 14. Morristown National Historical Park

- **Severity:** Medium
- **Data keys:** 795
- **Files:** data/parkData.json, parks/morristown-nhp.html
- **JSON items:** 25, 26

#### narrative, “content targeted” paragraph (artifact)

**Problem:** The “targeted language” is just the label “Revised Text:”. The actual item is a proposed rewrite that replaces “enslaved” and “enslavers” on a panel about Hannah and Isaac Till.

**Current:**

```html
<p>Among the content targeted: <em>&ldquo;Revised Text:&rdquo;</em> — language that the administration has flagged for review under its directive to review historically accurate interpretive materials.</p>
```

**Proposed:**

```html
<p>For a new wayside not yet fabricated, suggested SO 3431 edits would change &ldquo;The Ford family enslaved at least three people&rdquo; to &ldquo;The Ford family relied on at least three such individuals,&rdquo; and &ldquo;Their enslavers were Reverend John Mason and Captain John Johnson&rdquo; to &ldquo;They were owned by Reverend John Mason and Captain John Johnson.&rdquo;</p>
```

**Sources:**
- data/parkData.json key 795, whatTheyWantChanged (from repo): Repo: existing and revised text.

#### narrative, “Why this matters” paragraph

**Problem:** The flagged panel is about enslaved people at Washington’s headquarters, but “Why this matters” is only about soldiers’ cold and hunger and never mentions slavery or Hannah and Isaac Till.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Morristown NHP preserves the story of the Continental Army's most desperate hour — when the Revolution nearly ended not from British bullets but from cold, hunger, and despair. The interpretive materials here tell a story of survival that is central to understanding how American independence was won. Over 350,000 people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Soldiers were not the only people who lived through that winter here. Hannah and Isaac Till, held in slavery by Reverend John Mason and Captain John Johnson, were rented by George Washington to work at the Ford Mansion, and the Ford family enslaved at least three people on this farm. The suggested edits keep the facts but trade &ldquo;enslavers&rdquo; for &ldquo;owned by,&rdquo; wording that puts the slaveholders&rsquo; claim of ownership ahead of the people held.</p>
```

**Sources:**
- data/parkData.json key 795, whatTheyWantChanged (from repo): Repo: panel text naming Hannah and Isaac Till, their enslavers, Washington renting them, Fords enslaving at least three people.

### 15. National Mall and Memorial Parks

- **Severity:** Medium
- **Data keys:** 368
- **Files:** data/parkData.json, parks/national-mall.html
- **JSON items:** 27

**Location:** narrative, quote paragraph

**Problem:** Staff asked “Is the word ‘enslaved’ ok here?” about a wayside. The quote shown (“built in 1806 for $2,000…”) is the one part of the sign that leaves out the enslaved dockworkers, so the excerpt erases the very thing that was questioned. It is also sign text labelled as “internal review records.”

**Current:**

```html
<p>From the internal review records: &ldquo;built in 1806 for $2,000. It remained the bustling heart of the city&rdquo;</p>
```

**Proposed:**

```html
<p>On the &ldquo;Working Waterfront&rdquo; wayside, staff asked reviewers: &ldquo;Is the word &lsquo;enslaved&rsquo; ok here?&rdquo; The sentence in question reads: &ldquo;You might hear the shouts of hundreds of dockworkers, many of them enslaved people until the end of the Civil War in 1865.&rdquo;</p>
```

**Sources:**
- data/parkData.json key 368, whatTheyWantChanged (from repo): Repo: question and full wayside text.

### 16. Independence National Historical Park (Liberty Bell Center panels)

- **Severity:** Medium
- **Data keys:** 442
- **Files:** data/parkData.json, parks/independence-nhp.html
- **JSON items:** 28, 29, 30

#### narrative, flagged-language paragraph

**Problem:** The “ordered revised” language shown is just the bell’s inscription and the words “Liberty Bell,” which misrepresents the flag: the panels explain that abolitionists named the bell and describe slavery, Washington’s slaveholding and post-Reconstruction racism.

**Current:**

```html
<p>The administration has ordered revised content that includes the language: <em>&ldquo;Proclaim Liberty Throughout All the Land Unto All the Inhabitants Thereof,&rdquo;</em>, and <em>&ldquo;Liberty Bell.&rdquo;</em>.</p>
```

**Proposed:**

```html
<p>The park submitted Liberty Bell Center panels explaining how abolitionists adopted the bell and its inscription, &ldquo;Proclaim Liberty Throughout All the Land Unto All the Inhabitants Thereof,&rdquo; as a symbol and gave it the name &ldquo;Liberty Bell.&rdquo; The panels also mention George Washington holding enslaved people while serving as president in Philadelphia and, in the park&rsquo;s description, call out the systemic and violent racism and sexism of the post-Reconstruction era.</p>
```

**Sources:**
- data/parkData.json key 442, whatTheyWantChanged (from repo): Repo: park description of the two panel groups.

#### narrative, “physically removed” paragraph (conflation)

**Problem:** This paragraph describes the President’s House removal and court-ordered restoration (entry 439), not these Liberty Bell Center panels, which are listed as flagged for review.

**Current:**

```html
<p>In a remarkable turn, the content at Independence NHP was <strong>physically removed</strong> by the administration, only to be <strong>restored by federal court order</strong> after legal challenges. This is among the few known cases where removed NPS content has been returned to public view.</p>
```

**Proposed:**

```html
<p>Elsewhere in the park, the President&rsquo;s House exhibit was <strong>physically removed</strong> and then partly <strong>restored by federal court order</strong>; see the separate President&rsquo;s House entry.</p>
```

**Sources:**
- data/parkData.json keys 439 and 442 (from repo): Repo: 439 is the President’s House (removed, partially restored); 442 status is “FLAGGED FOR REVIEW.”

#### narrative, “Why this matters” paragraph

**Problem:** Generic founding-era line plus visitor count; it drops the abolition and slavery content that was flagged.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Independence National Historical Park preserves the physical spaces where the American republic was born and its governing documents were debated. Over 2.5 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The bell got its name from people fighting slavery, and the panels flagged here say so. The park&rsquo;s own brochure notes that the Constitution drafted in Independence Hall failed to adequately address slavery. Telling visitors who named the Liberty Bell, and why, is part of telling the founding honestly.</p>
```

**Sources:**
- https://npshistory.com/publications/inde/index.htm (from repo): INDE brochure (2018): Constitution “failed to adequately address slavery”; anti-slavery groups named the bell in the 1830s. Cited in parks/independence-nhp.html.
- https://npshistory.com/publications/inde/shs-liberty-bell.pdf (from repo): Paige, Liberty Bell special history study: abolitionist annual first named the bell in print in 1839. Cited in parks/independence-nhp.html.

### 17. Muir Woods National Monument

- **Severity:** Medium
- **Data keys:** 389
- **Files:** data/parkData.json, parks/muir-woods-nm.html
- **JSON items:** 31

**Location:** narrative, “Why this matters” paragraph

**Problem:** The removed 2021 annotations named the Coast Miwok and Southern Pomo, said their land was taken, and described the anti-Asian politics and eugenics views of figures in the park’s founding story. The narrative praises “local preservationists” and ends on “majesty of old-growth redwoods,” saying nothing about what the notes added.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Muir Woods preserves the majesty of old-growth redwoods—among Earth's tallest and most ancient living organisms. Over 2 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Park staff added notes to the &ldquo;Saving Muir Woods&rdquo; timeline in 2021 because the original sign was, in their words, &ldquo;true but incomplete.&rdquo; The notes named the Coast Miwok and Southern Pomo as the land&rsquo;s original caretakers, said their lands were taken from them, and described the anti-Asian politics and eugenics views of figures in the park&rsquo;s founding story. Removing the notes returns the sign to the version staff had already judged incomplete.</p>
```

**Sources:**
- https://www.kqed.org/news/12049405/muir-woods-national-monument-exhibit-removal-trump-executive-order-national-parks-history-under-construction-sticky-notes (verified online (WebSearch result summary)): KQED: 2021 sticky notes removed; poster called original sign “true but incomplete”; Coast Miwok and Southern Pomo; founder’s anti-Asian policies; Gifford Pinchot eugenics. Confirmed via WebSearch summary. The summary did not name William Kent, so the rewrite does not either.

### 18. Piscataway Park

- **Severity:** Medium
- **Data keys:** 354
- **Files:** data/parkData.json
- **JSON items:** 32, 33

#### narrative, “content targeted” paragraph (artifact) + “Why this matters”

**Problem:** The “targeted language” is the fragment “from the sentence:”. The real item is a recommendation to delete the word “genocidal” from “genocidal colonial policies.” The generic “Why this matters” never mentions the Piscataway.

**Current:**

```html
<p>Among the content targeted: <em>&ldquo;from the sentence:&rdquo;</em> — language that the administration has flagged for review under its directive to review historically accurate interpretive materials.</p>
```

**Proposed:**

```html
<p>The flagged item is a single word: reviewers recommended removing &ldquo;genocidal&rdquo; from the phrase &ldquo;genocidal colonial policies.&rdquo;</p>
```

**Sources:**
- data/parkData.json key 354, whatTheyWantChanged (from repo): Repo: “Recommend removing the word ‘genocidal’ from the sentence: ‘genocidal colonial policies.’”

#### narrative, “Why this matters” paragraph

**Problem:** Generic network template; does not name the people the phrase is about.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Piscataway Park is one of 466+ National Park Service sites where historically accurate interpretive content has been flagged under Secretary's Order 3431. Over 300 million people visit national parks each year. For many — especially schoolchildren — these visits are their first and deepest encounter with American history.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Park Service describes the Accokeek Creek site in Piscataway Park as home to the Potomac Valley&rsquo;s Indigenous people for thousands of years, among them the Piscataway, whose descendants still live nearby. The phrase under review describes what colonial policy did to them. Deleting one word does not change that history; it only makes it harder to name.</p>
```

**Sources:**
- https://www.nps.gov/places/accokeek-creek.htm (verified online (WebSearch result summary)): NPS: Accokeek Creek site home to Potomac Valley Indigenous inhabitants for thousands of years; Piscataway, whose ancestors/descendants still live nearby. Confirmed via WebSearch summary.
- https://www.nps.gov/articles/piscataway.htm (verified online (WebSearch result summary)): NPS article on Piscataway Park. Confirmed via WebSearch summary.

### 19. Lowell National Historical Park

- **Severity:** Medium
- **Data keys:** 714
- **Files:** data/parkData.json, parks/lowell-nhp.html
- **JSON items:** 34

**Location:** narrative, “Why this matters” paragraph

**Problem:** The quote is about a film describing “burning Native Americans,” but the slavery template that follows never mentions Native Americans (or the indentured servants also covered in the flagged films), so the violence quoted is raised and dropped.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The history of slavery at Lowell National Historical Park was suppressed for generations. The materials now being targeted represent decades of work by historians, descendants of enslaved people, and community advocates to ensure these stories are finally told. Removing them would re-erase history that has only recently been acknowledged.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Lowell&rsquo;s mills ran on cotton grown by enslaved people, and the flagged films also address the treatment of Native Americans, including an image from the <em>Lowell Offering</em> with a description of Native people being burned, and the lives of indentured servants. These are hard parts of the industrial story the park exists to tell. Pulling the films takes them out of what visitors see.</p>
```

**Sources:**
- data/parkData.json key 714, whatTheyWantChanged (from repo): Repo: flagged videos (critique of slave owners; Lowell Offering description of burning Native Americans; treatment of Native Americans; images of enslaved people; indentured servants).

### 20. Harpers Ferry National Historical Park

- **Severity:** Medium
- **Data keys:** 813
- **Files:** data/parkData.json, parks/harpers-ferry-nhp.html
- **JSON items:** 35

**Location:** narrative, flagged-language paragraph (mislabelled quotes)

**Problem:** Two of the four “ordered revised” quotes are the park’s proposed softer rewordings, not the original text, so the paragraph presents the sanitized versions as what was targeted and hides the before/after.

**Current:**

```html
<p>The administration has ordered revised content that includes the language: <em>&ldquo;target practice.&rdquo;</em>, <em>&ldquo;They threw his body into the river and continued to fire shots at it.&rdquo;</em>, <em>&ldquo;a drunken mob murders&rdquo;</em>, and <em>&ldquo;Some townspeople, enraged by the mayor&#x27;s death, kill William Thompson and toss his body into the Potomac.&rdquo;</em>.</p>
```

**Proposed:**

```html
<p>Park staff flagged handouts saying townspeople used the body of a dead raider for &ldquo;target practice&rdquo; and that &ldquo;a drunken mob murders&rdquo; raider William Thompson, and proposed softer wording: &ldquo;They threw his body into the river and continued to fire shots at it,&rdquo; and &ldquo;Some townspeople, enraged by the mayor&rsquo;s death, kill William Thompson and toss his body into the Potomac.&rdquo; A Civil War driving tour that quotes secession documents on the cause of secession was also flagged.</p>
```

**Sources:**
- data/parkData.json key 813, whatTheyWantChanged (from repo): Repo: original phrases and the park’s suggested rewordings; driving tour quoting secession documents.

### 21. Gateway Arch National Park

- **Severity:** Medium
- **Data keys:** 888
- **Files:** data/parkData.json
- **JSON items:** 36

**Location:** narrative, flagged-language paragraph

**Problem:** The flagged panel is about the 1836 lynching of Francis McIntosh and four executions, but the narrative never mentions a lynching. It quotes the reviewer’s phrase “within right reason” as if it were exhibit text, and shows a racist period phrase with no context.

**Current:**

```html
<p>The administration has flagged for review content that includes the language: <em>&ldquo;within right reason&rdquo;</em>, and <em>&ldquo;impudent free negroes to be cautious.&rdquo;</em>.</p>
```

**Proposed:**

```html
<p>The flagged gallery includes a panel on the 1836 lynching of Francis McIntosh, a free Black man burned to death by a white mob in St. Louis, and on the &ldquo;Four Executions&rdquo; of the same era. It uses period sources and language, including the phrase &ldquo;impudent free negroes to be cautious.&rdquo; Park staff told reviewers the panel is historically accurate and &ldquo;within right reason&rdquo; as context for Dred and Harriet Scott&rsquo;s fight for freedom.</p>
```

**Sources:**
- data/parkData.json key 888, whatTheyWantChanged (from repo): Repo: “McIntosh Lynching and Four Executions panel”; staff view that it is historically accurate and “within right reason.”
- https://en.wikipedia.org/wiki/Lynching_of_Francis_McIntosh (verified online (WebSearch result summary)): Free Black man, burned to death by a white mob in St. Louis, April 1836. Confirmed via WebSearch summary (secondary).
- https://www.nps.gov/articles/000/free-people-of-color-in-st-louis.htm (verified online (WebSearch result summary)): NPS article placing the lynching at today’s Kiener Plaza. Confirmed via WebSearch summary.

### 22. Great Falls Park

- **Severity:** Medium
- **Data keys:** 779
- **Files:** data/parkData.json
- **JSON items:** 37, 38

#### narrative, intro paragraph

**Problem:** The intro calls the flagged items “books and publications sold in the park bookstore,” but the record says they are two visitor center signs. The flagged sign tells how Captain Pointer’s Black descendants were forced off their land by discriminatory eminent domain; the narrative never says so, and “Why this matters” is generic.

**Current:**

```html
<p>At <strong>Great Falls Park</strong>, the administration has flagged books and publications sold in the park bookstore for review under Secretary's Order 3431. Among the titles targeted: <em>Struggle, Resilience, Hope</em>, <em>A Story Untold</em>. These works, selected by park staff and partner organizations for their educational value, are now under scrutiny.</p>
```

**Proposed:**

```html
<p>At <strong>Great Falls Park</strong>, staff submitted two visitor center signs for review, &ldquo;Struggle, Resilience, Hope&rdquo; and &ldquo;A Story Untold.&rdquo; Under the heading &ldquo;Discrimination and Displacement,&rdquo; the first tells how the descendants of Captain Pointer lost their homes: in 1928 Joseph Harris and Mary Moten were forced to sell their family farm, Dry Meadows, by eminent domain to build a school serving a whites-only housing development.</p>
```

**Sources:**
- data/parkData.json key 779, whatTheyWantChanged (from repo): Repo: “We are submitting 2 signs for review” and the full sign text.

#### narrative, “Why this matters” paragraph

**Problem:** Generic network template; does not acknowledge the family’s displacement.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Great Falls Park is part of a network of over 400 national parks that serve as America's classrooms. The interpretive materials here were developed by subject-matter experts to help visitors understand the full story of this place. When historically accurate content is removed, the public loses access to its own history.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The sign names a Black family pushed off its land by the discriminatory use of eminent domain, and it links that loss to redlining and gentrification, which it says still affect the community today. This is documented local history, and it belongs at the park where the family&rsquo;s story is told.</p>
```

**Sources:**
- data/parkData.json key 779, whatTheyWantChanged (from repo): Repo: sign text on eminent domain, redlining, gentrification.

### 23. Charles Young Buffalo Soldiers National Monument

- **Severity:** Medium
- **Data keys:** 611
- **Files:** data/parkData.json
- **JSON items:** 39, 40

#### narrative, intro paragraph

**Problem:** Wrong template: the intro and “Why this matters” describe Indigenous land and tribal consultation. The flagged panels are about segregation and discrimination in the Army against Black soldiers, and against Native Americans; Charles Young is never mentioned.

**Current:**

```html
<p>Long before <strong>Charles Young Buffalo Soldiers NM</strong> became a national park, this land was home to Indigenous peoples whose connection to it spans thousands of years. The interpretive materials now being reviewed tell their story — often developed through years of formal tribal consultation, as required by federal law.</p>
```

**Proposed:**

```html
<p><strong>Charles Young Buffalo Soldiers NM</strong> preserves the Ohio home of Charles Young, the third African American graduate of West Point and the highest-ranking Black officer in the U.S. Army until his death in 1922, and tells the story of the Buffalo Soldiers, the Black regiments formed after the Civil War.</p>
```

**Sources:**
- https://www.nps.gov/chyo/learn/news/historichousereopens.htm (verified online (WebSearch result summary)): NPS: third African American West Point graduate; highest-ranking African American officer until his death in 1922. Confirmed via WebSearch summary.
- https://npshistory.com/publications/yose/invisible-men.pdf (not verified online): Buffalo Soldiers regiments formed after the Civil War (cited in parks/yosemite-np.html).

#### narrative, “Why this matters” paragraph

**Problem:** Tribal-consultation template unrelated to the flagged content.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Indigenous history presented at Charles Young Buffalo Soldiers NM was developed through formal tribal consultation — a legal requirement under federal law. The language being reviewed was often specifically requested by tribal nations whose ancestors lived on this land for thousands of years. Revising it without renewed consultation would violate both the spirit and the letter of that process.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The flagged panels describe the segregation and ostracism Black soldiers faced in the U.S. Army, racial discrimination, and discrimination against Native Americans. Young built his career in spite of that prejudice. Visitors cannot understand what he achieved without knowing what he was up against.</p>
```

**Sources:**
- data/parkData.json key 611, whatTheyWantChanged (from repo): Repo: “detailed accounts of segregation and ostracism in the U.S. Army, race discrimination, … discrimination against Native Americans, and racial prejudice.”

### 24. Trail of Tears National Historic Trail

- **Severity:** Medium
- **Data keys:** 513
- **Files:** data/parkData.json
- **JSON items:** 41

**Location:** narrative, “Why this matters” paragraph

**Problem:** An entry for the Trail of Tears never mentions forced removal, the Cherokee, or the deaths; it carries only the generic “466+ sites … 300 million visitors” template. (No flagged text is recorded, so the rewrite adds context only.)

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Trail of Tears NHT is one of 466+ National Park Service sites where historically accurate interpretive content has been flagged under Secretary's Order 3431. Over 300 million people visit national parks each year. For many — especially schoolchildren — these visits are their first and deepest encounter with American history.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The Trail of Tears National Historic Trail commemorates the removal of the Cherokee from their homelands in 1838&ndash;39, when the U.S. government forced more than 16,000 people west at gunpoint to Indian Territory; thousands died. The trail crosses nine states, and the Park Service administers it in partnership with others, including the Cherokee Nation and the Eastern Band of Cherokee Indians. Any change to how it is interpreted touches a forced removal both nations still carry.</p>
```

**Sources:**
- https://www.nps.gov/trte/getinvolved/upload/Comprehensive-Management-Plan-508.pdf (verified online (WebSearch result summary)): NPS TRTE plan: 1838–39 removal at gunpoint, more than 16,000 removed; deaths estimated in the thousands. Confirmed via WebSearch summary.
- https://www.nps.gov/articles/trailoftears.htm (verified online (WebSearch result summary)): NPS: nine states; partnership administration. Confirmed via WebSearch summary.

### 25. Palo Alto Battlefield National Historical Park

- **Severity:** Medium
- **Data keys:** 270
- **Files:** data/parkData.json
- **JSON items:** 42

**Location:** narrative, “Why this matters” paragraph (wrong war)

**Problem:** Template error: says the site is students’ first encounter with “the realities of the Civil War — including its root cause in slavery.” Palo Alto is a U.S.–Mexican War battlefield, and the flagged text is about the invasion of Mexico and manifest destiny.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Palo Alto Battlefield National Historical Park commemorates events that shaped the course of American history. The interpretation here has been developed by professional historians over decades and reflects scholarly consensus. For the thousands of students who visit each year, this is often their first direct encounter with the realities of the Civil War — including its root cause in slavery.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Palo Alto was the first major battle of the U.S.&ndash;Mexican War, a war that ended in 1848 with Mexico ceding more than half its territory to the United States. The flagged brochure and film describe that war from more than one side, including the American belief in a &ldquo;manifest destiny to conquer the continent&rdquo; and the &ldquo;invasion of Mexico.&rdquo; Those are the park&rsquo;s own words for a war that reshaped both nations.</p>
```

**Sources:**
- https://www.nps.gov/parkhistory/online_books/paal/thunder-cannon/abstract.htm (verified online (WebSearch result summary)): NPS: first major engagement of the Mexican–American War. Confirmed via WebSearch summary.
- https://en.wikipedia.org/wiki/Treaty_of_Guadalupe_Hidalgo (verified online (WebSearch result summary)): Treaty of Guadalupe Hidalgo (1848): Mexico ceded about 55% of its territory. Confirmed via WebSearch summary.
- data/parkData.json key 270, whatTheyWantChanged (from repo): Repo: flagged film and brochure text.

### 26. Belmont-Paul Women's Equality National Monument

- **Severity:** Medium
- **Data keys:** 386
- **Files:** data/parkData.json, parks/belmont-paul-womens-equality-nm.html
- **JSON items:** 43

**Location:** narrative, “Why this matters” paragraph (factual)

**Problem:** The civil-rights template says these events “occurred within living memory” and the people who “marched, sat in, and sacrificed are still alive.” The flagged wayside is about the Silent Sentinels of 1917, who are not alive; it also skips the jailing and force-feeding the narrative itself describes.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> The women's equality history documented at Belmont-Paul Women's Equality NM is not a matter of opinion — it is the factual record of how Americans fought for the rights promised by our founding documents. These events occurred within living memory. The people who marched, sat in, and sacrificed are still alive to tell their stories.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> More than 90 of the Silent Sentinels were jailed for picketing the White House in 1917, many at the Occoquan Workhouse, where they were beaten and force-fed during hunger strikes. The publicity helped turn public and congressional opinion. Steps from that workhouse now stand in front of the monument, and the flagged wayside explains why.</p>
```

**Sources:**
- data/parkData.json key 386, whatTheyWantChanged (from repo): Repo: wayside text (90+ jailed, Occoquan, beaten and force-fed, publicity changed opinion, steps donated 1998 and placed on the grounds).

### 27. Golden Spike National Historical Park

- **Severity:** Medium
- **Data keys:** 887
- **Files:** data/parkData.json
- **JSON items:** 44, 45

#### narrative, flagged-language paragraph + truncated “Why this matters”

**Problem:** The second “targeted” quote is the reviewers’ suggested replacement, not exhibit text, so the paragraph hides the before/after. “Why this matters” cuts the quote off mid-word (“becau”).

**Current:**

```html
<p>The administration has flagged for review content that includes the language: <em>&ldquo;Today many ethnic minorities in the United States continue to face discrimination and violence because of their race, challenging our founding principle that all people &#x27;are created equal&#x27;.&rdquo;</em>, and <em>&ldquo;The legacy of exclusion and discrimination continues to impact many communities in the United States, reminding us of the ongoing work needed to fully realize the founding principle that all people are created equal.&rdquo;</em>.</p>
```

**Proposed:**

```html
<p>Park staff flagged one sentence on an exhibit panel: <em>&ldquo;Today many ethnic minorities in the United States continue to face discrimination and violence because of their race, challenging our founding principle that all people &#x27;are created equal&#x27;.&rdquo;</em> They suggested replacing it with: <em>&ldquo;The legacy of exclusion and discrimination continues to impact many communities in the United States, reminding us of the ongoing work needed to fully realize the founding principle that all people are created equal.&rdquo;</em></p>
```

**Sources:**
- data/parkData.json key 887, whatTheyWantChanged (from repo): Repo: original sentence and “suggested revision.”

#### narrative, “Why this matters” (truncation artifact)

**Problem:** Quote truncated mid-word.

**Current:**

```html
continue to face discrimination and violence becau&rdquo;</em>
```

**Proposed:**

```html
continue to face discrimination and violence because of their race&rdquo;</em>
```

**Sources:**
- data/parkData.json key 887, whatTheyWantChanged (from repo): Repo: full sentence.

### 28. Colonial National Historical Park

- **Severity:** Medium
- **Data keys:** 484
- **Files:** data/parkData.json, parks/colonial-nhp.html
- **JSON items:** 46, 47

#### narrative, intro sentence (factual) + “Why this matters”

**Problem:** Calls Jamestown “the first permanent European settlement in North America” (St. Augustine, 1565, is older; Jamestown was the first permanent English one). “Why this matters” frames Jamestown only as where “independence and democracy first took root,” erasing the Powhatan peoples and the beginning of slavery, both of which the park’s own brochure and foundation document put at the center.

**Current:**

```html
English settlers landed to create the first permanent European settlement in North America.
```

**Proposed:**

```html
English settlers landed in the Powhatan Paramount Chiefdom to create the first permanent English settlement in North America.
```

**Sources:**
- https://npshistory.com/publications/foundation-documents/colo-fd-2018.pdf (from repo): COLO Foundation Document (2018): Powhatan Paramount Chiefdom; English landed inside Wahunsenacawh’s chiefdom. Cited in parks/colonial-nhp.html.
- https://npshistory.com/publications/casa/index.htm (not verified online): parks/castillo-de-san-marcos-nm.html Park History block: St. Augustine (1565) is the oldest permanent European settlement in the continental U.S. Source [1] on that page; not fetched online.

#### narrative, “Why this matters” paragraph

**Problem:** Triumphalist framing that leaves out the Powhatan peoples and slavery.

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Colonial marks the beginning of English North America—where the continent's trajectory toward independence and democracy first took root. Over 1.2 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Jamestown&rsquo;s legacy, in the park&rsquo;s own words, includes representative government but also slavery: the first elected assembly in English-speaking North America met here in 1619, the same year 20 to 30 captive Africans were sold at nearby Point Comfort. The colony was planted in the homeland of the Powhatan peoples, whose conflict with the English shaped its first decades. Visitors need all three parts of that story.</p>
```

**Sources:**
- https://npshistory.com/publications/colo/index.htm (from repo): COLO brochure (2018): 1619 assembly; 20–30 captive Africans sold at Point Comfort; legacy includes representative government but also slavery. Cited in parks/colonial-nhp.html.
- https://npshistory.com/publications/foundation-documents/colo-fd-2018.pdf (from repo): Foundation document on Powhatan–colonist conflict. Cited in parks/colonial-nhp.html.

### 29. Indigenous history topic page (Grand Teton card)

- **Severity:** Medium
- **Data keys:** n/a (topic page)
- **Files:** indigenous-history-censorship.html
- **JSON items:** 48, 49

#### Grand Teton detail paragraph

**Problem:** States the Marias Massacre was carried out by “a 675-man Army force.” 675 is the Sand Creek figure; accounts of the Marias attack describe about 200 soldiers under Maj. Eugene Baker.

**Current:**

```html
in which a 675-man Army force attacked a peaceful Piegan Blackfeet village
```

**Proposed:**

```html
in which U.S. Army troops under Major Eugene Baker attacked a peaceful Piegan Blackfeet village
```

**Sources:**
- https://en.wikipedia.org/wiki/Marias_Massacre (verified online (WebSearch result summary)): Force of roughly 200 cavalry plus mounted infantry under Baker; 173–217 killed. Confirmed via WebSearch summary (secondary).
- https://historynet.com/montana-territory-massacre-blood-snow/ (verified online (WebSearch result summary)): “200 dismounted U.S. cavalrymen.” Confirmed via WebSearch summary.

#### Grand Teton renaming paragraph

**Problem:** Says the sign “was removed under the same directive that prompted the renaming effort.” The renaming happened in 2022; the removal followed the 2025 order. The sentence is factually wrong and muddles the point.

**Current:**

```html
The Grand Teton exhibit panel that asked visitors to reckon with Doane's legacy was removed under the same directive that prompted the renaming effort &mdash; effectively reversing the park's own attempt at honest historical interpretation.
```

**Proposed:**

```html
The Grand Teton exhibit panel that asked visitors to reckon with Doane&rsquo;s legacy came down in January 2026. Park staff told KHOL it was removed to comply with Secretary&rsquo;s Order 3431; the Interior Department called it routine sign maintenance. Either way, it reversed the park&rsquo;s own attempt at honest historical interpretation.
```

**Sources:**
- https://891khol.org/removed-grand-teton-sign-doesnt-have-to-be-reinstalled-higher-court-rules/ (verified online (WebSearch result summary)): KHOL: park employees said sign removed for compliance with SO 3431; Interior spokesperson called it routine sign maintenance. Confirmed via WebSearch summary.
- https://www.jhnewsandguide.com/news/environmental/after-trump-order-teton-park-removes-sign-about-explorer-who-massacred-native-americans/article_f92471a3-c937-46ec-b549-280a6cc8d3f3.html (verified online (WebSearch result summary)): JH News&Guide, Jan 28 2026. Confirmed via WebSearch summary.

### 30. Indigenous history topic page (Sand Creek card)

- **Severity:** Medium
- **Data keys:** n/a (topic page)
- **Files:** indigenous-history-censorship.html
- **JSON items:** 50

**Location:** Sand Creek detail paragraph

**Problem:** Death toll contradicts the same page (“over 200” in the card, “more than 200” below, “Approximately 150” here) and the NPS figure (more than 230). The troops were the 1st and 3rd Colorado, not only the Third. The quoted committee line ends in “the veriest savage,” a racist trope repeated without comment.

**Current:**

```html
Colonel John Chivington led 675 soldiers of the Third Colorado Cavalry in an attack on a Cheyenne and Arapaho village that was flying both an American flag and a white flag of truce, signaling its protected status under an agreement with Fort Lyon. Approximately 150 people were killed &mdash; about two-thirds of them women and children. Soldiers mutilated bodies and burned the village. Congress's <a href="https://en.wikipedia.org/wiki/Sand_Creek_massacre" target="_blank" rel="noopener">Joint Committee on the Conduct of the War</a> later called it "a foul and dastardly massacre which would have disgraced the veriest savage."
```

**Proposed:**

```html
Colonel John Chivington led about 675 soldiers of the 1st and 3rd Colorado Volunteer Cavalry in an attack on a Cheyenne and Arapaho village that was flying both an American flag and a white flag of truce, signaling its protected status under an agreement with Fort Lyon. More than 230 people were killed, according to the National Park Service, most of them women, children and elders. Soldiers mutilated bodies and burned the village. Congress&rsquo;s <a href="https://en.wikipedia.org/wiki/Sand_Creek_massacre" target="_blank" rel="noopener">Joint Committee on the Conduct of the War</a> later condemned it as &ldquo;a foul and dastardly massacre.&rdquo;
```

**Sources:**
- https://www.nps.gov/places/sand-creek-massacre-national-historic-site.htm (verified online (WebSearch result summary)): NPS: ~675 soldiers of 1st and 3rd Colorado; more than 230 killed. Confirmed via WebSearch summary.
- https://www.nps.gov/articles/sandcreek.htm (verified online (WebSearch result summary)): NPS: ~230 women, children and elderly. Confirmed via WebSearch summary.

### 31. Climate topic page (Glacier card)

- **Severity:** Medium
- **Data keys:** n/a (topic page)
- **Files:** climate-censorship.html
- **JSON items:** 51

**Location:** Glacier card, last paragraph

**Problem:** The killing of Piegan Blackfeet is mentioned as an aside (“a sign about the mass slaughter … was also ordered removed”) and used to make a point about topics overlapping, without naming the massacre, the date, or the people killed.

**Current:**

```html
A sign about the mass slaughter of the Piegan Blackfeet was also ordered removed, showing how climate censorship and Indigenous history erasure often overlap at the same parks.
```

**Proposed:**

```html
Glacier also removed a sign and brochures about the Marias Massacre of January 23, 1870, when U.S. Army troops attacked a winter camp of Piikáni (Piegan Blackfeet) on the Marias River and killed 173 or more people, mostly women, children and elders. The Blackfeet Tribal Business Council said materials documenting the massacre had been specifically targeted for removal.
```

**Sources:**
- https://www.bozemandailychronicle.com/news/in-glacier-feds-are-quietly-scrubbing-information-on-climate-change-native-history/article_1b60e3b9-90b5-5fa0-8dca-39d038ab5fda.html (verified online (WebSearch result summary)): Sign and brochures on the Baker/Marias Massacre removed; Blackfeet Tribal Business Council statement. Confirmed via WebSearch summary.
- https://npshistory.com/publications/glac/eo.pdf (from repo): Glacier ethnographic overview: Jan 23 1870, 173 or more killed, mostly women, children and elders. Cited in parks/glacier-np.html.


## Low severity

### 32. Manzanar National Historic Site

- **Severity:** Low
- **Data keys:** 840
- **Files:** data/parkData.json
- **JSON items:** 52, 53, 54

#### narrative, intro paragraphs (terminology)

**Problem:** Uses “internment camps” and “internees,” wartime euphemisms the NPS terminology guidance advises against, next to the more accurate “concentration camps” and “incarcerated” used elsewhere in the same entry.

**Current:**

```html
forcibly relocating 120,000 Japanese Americans to internment camps, including Manzanar
```

**Proposed:**

```html
forcing some 120,000 Japanese Americans from their homes and into incarceration camps, including Manzanar
```

**Sources:**
- https://home.nps.gov/articles/000/terminology-and-the-mass-incarceration-of-japanese-americans-during-world-war-ii.htm (verified online (WebSearch result summary)): NPS terminology article (Nov 2023): avoid government euphemisms; “concentration camp” and “incarceration” accepted. Confirmed via WebSearch summary.

#### narrative, second paragraph (terminology)

**Problem:** Same terminology issue.

**Current:**

```html
Manzanar held over 10,000 internees at its peak
```

**Proposed:**

```html
Manzanar held over 10,000 people at its peak
```

**Sources:**
- https://home.nps.gov/articles/000/terminology-and-the-mass-incarceration-of-japanese-americans-during-world-war-ii.htm (verified online (WebSearch result summary)): As above.

#### narrative, second paragraph (terminology)

**Problem:** Same terminology issue.

**Current:**

```html
fired into a crowd of protesting internees
```

**Proposed:**

```html
fired into a crowd of protesting incarcerees
```

**Sources:**
- https://home.nps.gov/articles/000/terminology-and-the-mass-incarceration-of-japanese-americans-during-world-war-ii.htm (verified online (WebSearch result summary)): As above.

### 33. Haleakalā National Park

- **Severity:** Low
- **Data keys:** 924
- **Files:** data/parkData.json
- **JSON items:** 55

**Location:** narrative, second paragraph

**Problem:** The entry is mostly about Hawaii National Park and Kīlauea, not Haleakalā. It presents Lorrin Thurston only as a hotel investor who championed the park, without noting that he led the 1893 overthrow of the Hawaiian Kingdom. Ideally the entry is rewritten around Haleakalā; at minimum, add the context.

**Current:**

```html
Lorrin Thurston, grandson of missionary Asa Thurston, was a driving force behind the park's establishment after investing in local hotels.
```

**Proposed:**

```html
Lorrin Thurston, grandson of missionary Asa Thurston and a leader of the 1893 overthrow of the Hawaiian Kingdom, was a driving force behind the park&rsquo;s establishment after investing in local hotels.
```

**Sources:**
- https://en.wikipedia.org/wiki/Lorrin_A._Thurston (verified online (WebSearch result summary)): Thurston was the Committee of Safety’s unofficial leader in the 1893 overthrow; lobbied 1906–1916 for the volcano park. Confirmed via WebSearch summary (secondary; no NPS page found).

### 34. Hawai'i Volcanoes National Park

- **Severity:** Low
- **Data keys:** 480
- **Files:** data/parkData.json
- **JSON items:** 56

**Location:** narrative, “Why this matters” paragraph

**Problem:** The flagged wayside uses “geological and cultural storytelling” and is under review for disparaging people “from the colonial era”; “Why this matters” covers only geology plus a visitor count. (Topics also list Japanese American Incarceration and Labor History with no text supporting them.)

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Hawaii Volcanoes reveals the planet's living geology—where molten rock and gas continue to literally create the landscape. Over 2 million people visit this site each year.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> Kīlauea is one of Earth&rsquo;s most active volcanoes and a place of deep cultural significance for Native Hawaiians; the flagged wayside interprets the 1959 Kīlauea Iki eruption &ldquo;through geological and cultural storytelling.&rdquo; A review for content that might disparage people &ldquo;from the colonial era&rdquo; puts the Hawaiian side of that story at risk.</p>
```

**Sources:**
- data/parkData.json key 480, narrative (from repo): Repo: quote from review record; narrative already states Halemaʻumaʻu holds cultural significance for Hawaiian people.

### 35. Rock Creek Park

- **Severity:** Low
- **Data keys:** 820
- **Files:** data/parkData.json, parks/rock-creek-park.html
- **JSON items:** 57

**Location:** narrative, “Why this matters” paragraph

**Problem:** Leads with a visitor count and softens a white supremacist senator to a “flawed historical figure.”

**Current:**

```html
<p class="context-box"><strong>Why this matters:</strong> Rock Creek Park is one of the oldest and largest urban parks in the U.S., visited by over 2 million people each year. The removed wayside addressed the legacy of Senator Newlands and the community’s ongoing dialogue about how we memorialize flawed historical figures.</p>
```

**Proposed:**

```html
<p class="context-box"><strong>Why this matters:</strong> The removed &ldquo;What&rsquo;s in a Name?&rdquo; wayside, developed with the local community, told visitors that Senator Francis Newlands held white supremacist views and asked them to weigh how the fountain at Chevy Chase Circle should remember him. Rock Creek Park is one of the oldest urban parks in the country, and that conversation belongs in it.</p>
```

**Sources:**
- data/parkData.json key 820, whatTheyWantChanged and sosContext (from repo): Repo: wayside on Newlands’ racist/white supremacist views, community input, installed c. 2022.

### 36. Theodore Roosevelt National Park

- **Severity:** Low
- **Data keys:** 1069
- **Files:** data/parkData.json, parks/theodore-roosevelt-np.html
- **JSON items:** 58

**Location:** narrative, “content targeted” paragraph (artifact)

**Problem:** The “targeted language,” “LEGACY NPS REGION,” is an administrative note about the park’s region, not content.

**Current:**

```html
<p>Among the content targeted: <em>&ldquo;LEGACY NPS REGION&rdquo;</em> — language that the administration has flagged for review under its directive to review historically accurate interpretive materials.</p>
```

**Proposed:**

```html
<p>The flagged item is one page of the park&rsquo;s Junior Ranger book: three illustrations and the last two sentences of a paragraph, which staff proposed either removing or editing.</p>
```

**Sources:**
- data/parkData.json key 1069, whatTheyWantChanged (from repo): Repo: Junior Ranger Book page 6, three illustrations and last two sentences.

### 37. Antietam National Battlefield

- **Severity:** Low
- **Data keys:** 710
- **Files:** data/parkData.json, parks/antietam-nb.html
- **JSON items:** 59

**Location:** narrative, quote paragraph

**Problem:** Of five flagged waysides the narrative quotes the most trivial (a sycamore “with no beauty and grandeur reference”) and omits the one the park flagged for addressing the “Lost Cause narrative.”

**Current:**

```html
<p>From the internal review records: &ldquo;Witness to History: natural resource (historic Burnside Sycamore) with no beauty and grandeur reference.&rdquo;</p>
```

**Proposed:**

```html
<p>Among the waysides submitted: &ldquo;History or Memory,&rdquo; which the park lists under &ldquo;Lost Cause narrative,&rdquo; and several on armies &ldquo;causing destruction to civilian property.&rdquo;</p>
```

**Sources:**
- data/parkData.json key 710, whatTheyWantChanged (from repo): Repo: list of five flagged waysides.

### 38. Indigenous history topic page (Grand Teton card)

- **Severity:** Low
- **Data keys:** n/a (topic page)
- **Files:** indigenous-history-censorship.html
- **JSON items:** 60

**Location:** Grand Teton photo caption

**Problem:** “An explorer known for leading a massacre” overstates his role (Baker commanded; NPS says Doane led an attack within it) and misspells his middle name (“Cheney”; the sign and NPS use “Cheyney”).

**Current:**

```html
It described Gustavus Cheney Doane, an explorer known for leading a massacre of Piegan Blackfeet people.
```

**Proposed:**

```html
It described Gustavus Cheyney Doane, an Army officer and explorer who took part in the Marias Massacre of Piegan Blackfeet people.
```

**Sources:**
- data/parkData.json key 720, whatTheyWantChanged (from repo): Repo: sign text “Gustavus Cheyney Doane … participated in what is now known as the Marias Massacre.”
- https://www.nps.gov/yell/learn/news/22022.htm (from repo): NPS Yellowstone release (June 2022) on renaming Mount Doane: Doane led an attack on Piegan Blackfeet, at least 173 killed, he bragged of it. Cited in parks/grand-teton-np.html; nps.gov could not be fetched from this environment (DNS failure).

### 39. Indigenous history topic page (Sand Creek card)

- **Severity:** Low
- **Data keys:** n/a (topic page)
- **Files:** indigenous-history-censorship.html
- **JSON items:** 61

**Location:** Sand Creek establishment paragraph

**Problem:** “It is the first unit of the National Park System to label American troops as perpetrators rather than heroes” is an unsourced superlative. Could not verify; recommend sourcing it or removing the sentence.

**Current:**

```html
 It is the first unit of the National Park System to label American troops as perpetrators rather than heroes.
```

**Proposed:**

_(delete the sentence)_

**Sources:**
- n/a (could not verify): Could not verify online; no source found in repo.

### 40. Slavery topic page (Fort Sumter paragraph)

- **Severity:** Low
- **Data keys:** n/a (topic page)
- **Files:** slavery-history-censorship.html
- **JSON items:** 62

**Location:** “What’s Being Removed” prose

**Problem:** Frames the Fort Sumter/Moultrie slavery removals only as “the very site where the Civil War began,” leaving out that the removed exhibit concerns the place where about 40% of enslaved Africans brought to America disembarked. (Also on this page: “eight enslaved people” vs “nine” elsewhere; “Doug Bergum” should be “Burgum”; the 1733 revolt is said to have held the island “nearly nine months” here, “for months” lower down, and about six months in the Virgin Islands Park History block.)

**Current:**

```html
five entries about slavery have been flagged and five confirmed removed &mdash; at the very site where the Civil War began.
```

**Proposed:**

```html
five entries about slavery have been flagged and five confirmed removed &mdash; including the <em>African Passages</em> exhibit about Sullivan&rsquo;s Island, where, the park&rsquo;s foundation document notes, approximately 40 percent of all enslaved Africans transported to America disembarked.
```

**Sources:**
- data/parkData.json key 568, whatTheyWantChanged (from repo): Repo: African Passages panels; foundation-document theme on 40%.

### 41. Cumberland Island NS / Cumberland Gap NHP

- **Severity:** Low
- **Data keys:** 290
- **Files:** data/parkData.json, parks/cumberland-gap-nhp.html, parks/cumberland-island-ns.html
- **JSON items:** 63

**Location:** narrative, quote label

**Problem:** Same labelling problem as Grand Teton: the quoted passage is the text of the sign/exhibit itself (it appears verbatim in the flagged record), but it is introduced as “From the internal review records.”

**Current:**

```html
<p>From the internal review records: &ldquo;European Colonial Occupation:
```

**Proposed:**

```html
<p>From the flagged wayside text: &ldquo;European Colonial Occupation:
```

**Sources:**
- data/parkData.json key 290, whatTheyWantChanged (from repo): Repo: the flagged record quotes the sign text verbatim.

### 42. Great Smoky Mountains National Park

- **Severity:** Low
- **Data keys:** 502
- **Files:** data/parkData.json, parks/great-smoky-mountains-np.html
- **JSON items:** 64

**Location:** narrative, quote label

**Problem:** Same labelling problem as Grand Teton: the quoted passage is the text of the sign/exhibit itself (it appears verbatim in the flagged record), but it is introduced as “From the internal review records.”

**Current:**

```html
<p>From the internal review records: &ldquo;(A Sacred Ancestral Connection:
```

**Proposed:**

```html
<p>From the flagged wayside text: &ldquo;(A Sacred Ancestral Connection:
```

**Sources:**
- data/parkData.json key 502, whatTheyWantChanged (from repo): Repo: the flagged record quotes the sign text verbatim.

### 43. River Raisin National Battlefield Park

- **Severity:** Low
- **Data keys:** 683
- **Files:** data/parkData.json, parks/river-raisin-nb-park.html
- **JSON items:** 65

**Location:** narrative, quote label

**Problem:** Same labelling problem as Grand Teton: the quoted passage is the text of the sign/exhibit itself (it appears verbatim in the flagged record), but it is introduced as “From the internal review records.”

**Current:**

```html
<p>From the internal review records: &ldquo;Text in Question: Facing
```

**Proposed:**

```html
<p>From the flagged exhibit text: &ldquo;Facing
```

**Sources:**
- data/parkData.json key 683, whatTheyWantChanged (from repo): Repo: the flagged record quotes the sign text verbatim.

## Low-severity notes without a rewrite

These are real but minor, or they need data the repo does not have.

- **Data and tagging errors.**
  - Emmett Till (352) is tagged “Indigenous & Native History” and “Labor History”. Change the tag to “Civil Rights & Racial Justice” so the entry appears on the civil rights page; right now it is counted on the Indigenous page.
  - Key 967 is labelled Lassen Volcanic (code LAVO), but its text describes Lava Beds.
  - Haleakalā (924) describes Hawaii National Park and Kīlauea, not Haleakalā.
  - Cumberland (290) merges Cumberland Island NS (Georgia) and Cumberland Gap NHP (Kentucky/Tennessee/Virginia).
  - Pictured Rocks (195) calls the park “Pigeon River area”.
  - Manassas (291) is tagged “LGBTQ+ History” with no supporting text.
- **Thin generic entries at hard-history sites.** These have no flagged text, only the “466+ sites” template: Washita Battlefield (954), Big Hole (744), Nez Perce (745), Tule Lake (968), Honouliuli (911), Kalaupapa (301), Little Rock Central High (454), Fort Smith (972) and Andersonville (516). None of them is offensive, but each one leaves a massacre, incarceration, forced isolation or segregation site without a single sentence about what happened there. When there is time, add one sourced sentence per site (as done for Trail of Tears, item 41). Gateway (249) is similar: the removed display named slavery, “massacres of Indians” and the wartime camps, but the narrative gives only the reviewer’s logistics note.
- **Wrong template on non-hard-history content.** The Indigenous template appears on Fort McHenry (833, a War of 1812 staff note about Madison), Cowpens (400, a Revolutionary War curriculum) and Fort Matanzas (226, a bookstore title).
- **Other quote artifacts.**
  - Carl Sandburg (134) quotes the reviewer’s word “disparaging”.
  - Andrew Johnson (345) lists “prejudicial” twice.
  - Chickamauga (455) quotes mid-sentence fragments.
  - Fort Pulaski (623) lists only titles; “Embedded in Brick” is about bricks made by enslaved workers, which the narrative never says.
  - Fredericksburg (719) quotes “American culture”.
  - Arches (757) and Canyonlands (768) have doubled quote marks (`&ldquo;&quot;`).
  - Glacier (783), Big Bend (1037) and Pictured Rocks (195) quote the order’s own criteria (“matters unrelated to the beauty, abundance, or grandeur”) as if they were the flagged sign text.
  - Hawai'i Volcanoes (480) lists topics (Japanese American Incarceration, Labor) that nothing in the entry supports.
- **Intro framing, optional.**
  - Grand Teton’s intro credits “conservationists” whose imagination was captured in 1872. Its Park History block already handles the Shoshone and Doane well.
  - Glacier’s intro credits Grinnell only for the “Crown of the Continent” nickname, though he also negotiated the 1895 purchase of the mountains from the Blackfeet.
  - Redwood’s intro uses the past tense for the Yurok, Chilula and Tolowa.
  - Glacier Bay (587) calls the park “pristine Alaskan wilderness” shaped by Tlingit and Haida “for centuries” (also past tense). It has no flagged text, so I made no rewrite.
  - Santa Monica Mountains (822) says the content was “eliminated”, but the park’s note says the sign was sun-damaged.
- **Topic-page nits.**
  - Indigenous page: cites entry IDs that no longer exist in the data (#848 Yosemite, #987 Grand Canyon). It says Grand Canyon gets “over 6 million visitors per year”, but the park page says about 4.5 million on average, with 6 million in 2016. It dates a Yosemite removal to 1906, while the park page says 1907.
  - Slavery page: “eight” enslaved people vs “nine”; “Doug Bergum” should be “Burgum”; the 1733 revolt lasted “nearly nine months” in one place and “for months” in another, while the park page says six months; it uses “internment” for the Gateway display.
  - Civil rights page: “53” vs “52” House Democrats. The Medgar Evers card says “3 entries confirmed removed”, but the entry’s own update says the brochures were returned hours after press coverage, while replacement edits were still planned. The phrase “in a 15-minute frenzy” is slightly sensational.

## Reviewed and fine

- **Minidoka (899).** The narrative and closing paragraph name the incarceration plainly. The patriotism line is respectful.
- **Hampton (828).** It says plainly that the house was “built on the foundation of human bondage”.
- **Western Arctic Parklands (659, 949).** False positive: “klan” matched inside “Parklands”. The generic template is fine.
- **Manassas (291).** The “War Over Memory” entry has no hard-history content to drop. Only the topic tag is odd (see notes above).
- **Gettysburg (403), Kennesaw (107), Vicksburg (263), Shiloh (821), Richmond (941).** Battle summaries with no flagged hard-history text. “High Water Mark” is quoted as a phrase.
- **Death Valley (422).** No flagged text. It names the Timbisha and does not erase them.
- **Everglades (681).** The flagged text is about development and drainage, and the narrative matches it.
- **Pinnacles (917), Petrified Forest (579), Crater Lake (861), Bryce (873), Zion (892), Arches (757), Kenai Fjords (754), North Cascades (409).** Geology or climate entries with no hard history.
- **Little Bighorn (152), Delaware Water Gap (109), Gulf Islands (142), Grant (303), Reconstruction Era (310), President's House (439), Great Smoky Mountains (502; label noted in item 64), Ocmulgee (716), Castillo (204), Tallgrass (850), Homestead (644), Scotts Bluff (1047), Edgar Allan Poe (709), Jimmy Carter (732), Timucuan (155), Fort Raleigh (170), Lewis & Clark (730), Badlands (901), Stonewall (923), Pipestone (650), Cane River (1070).** These name the people and the harm, and their closing paragraphs fit the content.
- **Fort Frederica (256).** The closing paragraph is generic (“documented, factual history of colonial Georgia”) but does not undercut the slavery content above it.
- **Rock Creek (820).** Mostly fine; only the closing line is softened (item 57).
- **FWS entries (FWS-001 to FWS-011).** Accurate and appropriately framed.
- **Park History blocks** (20 pages, including Grand Teton, Yosemite, Glacier, Grand Canyon, Colonial, Virgin Islands, Independence, Castillo, Fort Raleigh, Christiansted, Arlington House and Gateway). These are well sourced and name the harm and the people plainly. Two passages quote sources with “last of” or “extirpated” framing (Gateway: “the last known Canarsie person”; Fort Raleigh: the foundation document’s “extirpated”). Both are attributed. Consider a clause noting that descendant communities exist, but I don't consider them errors.
- **Civil rights topic page.** Tone is good; it has only the small inconsistencies listed above.
