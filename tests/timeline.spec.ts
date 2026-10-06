import { test, expect } from '@playwright/test';

test.describe('timeline page', () => {
  test('events are newest first and all dated', async ({ page }) => {
    await page.goto('/timeline.html');
    const dates = await page.locator('.timeline-event').evaluateAll((els) =>
      els.map((el) => (el as HTMLElement).dataset.date ?? ''),
    );
    expect(dates.length).toBeGreaterThan(40);
    for (const d of dates) expect(d).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    expect(dates).toEqual([...dates].sort().reverse());
  });

  test('every event from 2026-06-13 on cites a source', async ({ page }) => {
    await page.goto('/timeline.html');
    const missing = await page.locator('.timeline-event').evaluateAll((els) =>
      els
        .filter((el) => ((el as HTMLElement).dataset.date ?? '') >= '2026-06-13')
        .filter((el) => !el.querySelector('a.event-link[href^="http"]'))
        .map((el) => el.querySelector('.event-title')?.textContent),
    );
    expect(missing).toEqual([]);
  });

  test('type filters still show only matching events', async ({ page }) => {
    await page.goto('/timeline.html');
    await page.getByRole('button', { name: 'Legal Actions' }).click();
    const visibleTypes = await page.locator('.timeline-event:not(.hidden)').evaluateAll((els) =>
      [...new Set(els.map((el) => (el as HTMLElement).dataset.type))],
    );
    expect(visibleTypes).toEqual(['legal']);
    await page.getByRole('button', { name: 'All Events' }).click();
    await expect(page.locator('.timeline-event.hidden')).toHaveCount(0);
  });
});
