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

  test('each date label matches its data-date', async ({ page }) => {
    // "Sep 30, 2026" for an exact day, "Sep 2026" for a month (data-date on the 1st).
    await page.goto('/timeline.html');
    const pairs = await page.locator('.timeline-event').evaluateAll((els) =>
      els.map((el) => [(el as HTMLElement).dataset.date ?? '', el.querySelector('.event-date')?.textContent ?? '']),
    );
    const mon = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const mismatched = pairs.filter(([iso, label]) => {
      const [y, m, d] = iso.split('-').map(Number);
      const allowed = [`${mon[m - 1]} ${d}, ${y}`, ...(d === 1 ? [`${mon[m - 1]} ${y}`] : [])];
      return !allowed.includes(label.trim());
    });
    expect(mismatched).toEqual([]);
  });

  test('external event links open safely in a new tab', async ({ page }) => {
    await page.goto('/timeline.html');
    const unsafe = await page.locator('a.event-link[href^="http"]').evaluateAll((els) =>
      els
        .filter((a) => a.getAttribute('target') !== '_blank' || !/\bnoopener\b/.test(a.getAttribute('rel') ?? ''))
        .map((a) => a.getAttribute('href')),
    );
    expect(unsafe).toEqual([]);
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

  test.describe('on a phone', () => {
    test.use({ viewport: { width: 390, height: 844 } });

    test('event dots stay round instead of being squeezed by the card', async ({ page }) => {
      await page.goto('/timeline.html');
      const dots = await page.locator('.timeline-event .event-dot').evaluateAll((els) =>
        els.slice(0, 5).map((el) => {
          const r = el.getBoundingClientRect();
          return { width: r.width, height: r.height };
        }),
      );
      expect(dots).toHaveLength(5);
      for (const [i, d] of dots.entries()) {
        expect(d.height, `dot ${i + 1} should be visible`).toBeGreaterThan(0);
        expect(Math.abs(d.width - d.height), `dot ${i + 1} is ${d.width}×${d.height}px`)
          .toBeLessThanOrEqual(0.5);
      }
    });
  });
});
