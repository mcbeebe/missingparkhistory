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
