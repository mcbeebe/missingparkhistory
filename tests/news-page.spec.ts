import { test, expect } from '@playwright/test';

test.describe('News & Press page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/news-and-press.html');
  });

  test('has the elements the daily news bot edits', async ({ page }) => {
    // update_banner() rewrites the <time> and "N articles tracked"; insert_card()
    // needs the year markers; ensure_month_options() needs the month <select>.
    const updated = page.locator('.publish-date');
    await expect(updated.locator('time[datetime]')).toHaveCount(1);
    const cards = await page.locator('.article-card').count();
    await expect(updated).toContainText(`${cards} articles tracked`);
    await expect(page.locator('.year-marker h2').first()).toHaveText(/^\d{4}$/);
    await expect(page.locator('select#filterMonth option')).not.toHaveCount(0);
  });

  test('topic filter shows only matching cards and hides empty years', async ({ page }) => {
    const total = await page.locator('.article-card').count();
    await page.locator('.filter-btn[data-filter="court"]').click();
    const visible = page.locator('.article-card:not(.hidden)');
    const n = await visible.count();
    expect(n).toBeGreaterThan(0);
    expect(n).toBeLessThan(total);
    const tags = await visible.evaluateAll((els) => els.map((e) => (e as HTMLElement).dataset.tags));
    for (const t of tags) expect(t).toContain('court');
    await expect(page.locator('#resultsCount')).toHaveText(`Showing ${n} of ${total} articles`);
  });

  // From June to October 2026 the page ended with a "None" year heading over 13
  // cards that had no data-month/data-source and sat out of date order.
  test('every year heading is a 4-digit year', async ({ page }) => {
    const years = await page.locator('.year-marker h2').allTextContents();
    expect(years.length).toBeGreaterThan(0);
    expect(years.filter((y) => !/^\d{4}$/.test(y.trim()))).toEqual([]);
  });

  test('every card has a month and a source the filters can select', async ({ page }) => {
    const optionValues = async (select: string) =>
      new Set(
        await page.locator(`${select} option`).evaluateAll((os) => os.map((o) => (o as HTMLOptionElement).value)),
      );
    const months = await optionValues('#filterMonth');
    const sources = await optionValues('#filterSource');
    const cards = await page.locator('.article-card').evaluateAll((els) =>
      els.map((el) => ({
        title: el.querySelector('h3')?.textContent?.trim() ?? '',
        month: (el as HTMLElement).dataset.month ?? '',
        source: (el as HTMLElement).dataset.source ?? '',
      })),
    );
    expect(cards.length).toBeGreaterThan(200);
    const unfilterable = cards.filter(
      (c) => !/^\d{4}-\d{2}$/.test(c.month) || !months.has(c.month) || c.source === 'all' || !sources.has(c.source),
    );
    expect(unfilterable).toEqual([]);
  });

  test('cards run newest first, each under its own year heading', async ({ page }) => {
    const cards = await page.locator('.timeline-section').evaluate((section) => {
      let heading = '';
      const out: { title: string; heading: string; date: string }[] = [];
      for (const el of Array.from(section.children)) {
        if (el.classList.contains('year-marker')) heading = el.textContent?.trim() ?? '';
        if (!el.classList.contains('article-card')) continue;
        // Same order as scripts/resort_cards.py: data-month, then the day in the
        // "Mon D" label (0 for labels with no day, e.g. "Jun" or "Jun–Sep").
        const day = el.querySelector('.month-day')?.textContent?.match(/\d{1,2}/);
        out.push({
          title: el.querySelector('h3')?.textContent?.trim() ?? '',
          heading,
          date: `${(el as HTMLElement).dataset.month}-${String(day ? Number(day[0]) : 0).padStart(2, '0')}`,
        });
      }
      return out;
    });
    expect(cards.length).toBe(await page.locator('.article-card').count());
    expect(cards.filter((c) => c.date.slice(0, 4) !== c.heading)).toEqual([]);
    expect(cards.slice(1).filter((c, i) => c.date > cards[i].date)).toEqual([]);
  });

  test('month and source filters combine, and Clear resets everything', async ({ page }) => {
    const total = await page.locator('.article-card').count();
    const month = await page.locator('.article-card').first().getAttribute('data-month');
    await page.selectOption('#filterMonth', month!);
    const shown = await page.locator('.article-card:not(.hidden)').evaluateAll((els) =>
      els.map((e) => (e as HTMLElement).dataset.month),
    );
    expect(new Set(shown)).toEqual(new Set([month]));
    await page.selectOption('#filterSource', 'other');
    await page.locator('#clearFilters').click();
    await expect(page.locator('.article-card.hidden')).toHaveCount(0);
    await expect(page.locator('.article-card')).toHaveCount(total);
    await expect(page.locator('.filter-btn.active')).toHaveAttribute('data-filter', 'all');
  });
});
