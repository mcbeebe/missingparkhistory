import { test, expect, type Page } from '@playwright/test';

// The home page search box on phones: it must not trigger iOS Safari's focus zoom
// (any text box under 16px does), and its results must sit above the floating
// Take Action / Subscribe buttons rather than under them.
const PHONE_WIDTHS = [360, 390, 430];

/**
 * Loads the home page without the map's CDN scripts, closes the news pop-up, and
 * fills the results list with `count` fake parks (the real list needs the map data).
 */
async function openWithResults(page: Page, width: number, count = 8) {
  await page.setViewportSize({ width, height: 844 });
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
  await page.evaluate((n) => {
    (window as unknown as { ndClose?: () => void }).ndClose?.();
    document.getElementById('loadOverlay')?.remove();
    const w = window as unknown as { opened?: string[] };
    w.opened = [];
    const list = document.getElementById('searchResults')!;
    list.innerHTML = Array.from({ length: n }, (_, i) =>
      `<div class="search-result" onclick="window.opened.push('p${i}')"><div class="sr-park">Park ${i}</div><div class="sr-meta">CODE · ST · FLAGGED</div></div>`,
    ).join('');
    list.classList.add('active');
  }, count);
}

/** Points inside the visible results list whose top-most element is not part of it. */
function coveredPoints(page: Page) {
  return page.evaluate(() => {
    const list = document.getElementById('searchResults')!;
    const r = list.getBoundingClientRect();
    const bottom = Math.min(r.bottom, window.innerHeight) - 4;
    const covered: string[] = [];
    for (let y = r.top + 4; y < bottom; y += 12) {
      for (let x = r.left + 4; x < r.right - 4; x += 12) {
        const el = document.elementFromPoint(x, y);
        if (el && !list.contains(el)) covered.push(`${Math.round(x)},${Math.round(y)} ${el.className || el.tagName}`);
      }
    }
    return covered;
  });
}

test.describe('home page search on phones', () => {
  for (const width of PHONE_WIDTHS) {
    test(`search text is at least 16px at ${width}px (no iOS focus zoom)`, async ({ page }) => {
      await openWithResults(page, width);
      const size = await page.locator('#searchInput').evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
      expect(size).toBeGreaterThanOrEqual(16);
    });

    test(`nothing floats over the results while typing at ${width}px`, async ({ page }) => {
      await openWithResults(page, width);
      await page.locator('#searchInput').focus();
      // The list really does run under the buttons' position, so this is a real check.
      const overlapsButton = await page.evaluate(() => {
        const r = document.getElementById('searchResults')!.getBoundingClientRect();
        const b = document.querySelector('.take-action-btn')!.getBoundingClientRect();
        return r.bottom > b.top && r.top < b.bottom;
      });
      expect(overlapsButton).toBe(true);
      expect(await coveredPoints(page)).toEqual([]);
    });
  }

  test('results stay on top after the keyboard closes while the list is open', async ({ page }) => {
    await openWithResults(page, 390);
    await page.locator('#searchInput').evaluate((el) => (el as HTMLInputElement).blur());
    expect(await coveredPoints(page)).toEqual([]);
  });

  test('the list fits on screen above the bottom buttons', async ({ page }) => {
    await openWithResults(page, 390, 15);
    const { listBottom, barTop } = await page.evaluate(() => ({
      listBottom: document.getElementById('searchResults')!.getBoundingClientRect().bottom,
      barTop: document.querySelector('.mobile-bottom-bar')!.getBoundingClientRect().top,
    }));
    expect(listBottom).toBeLessThan(barTop);
  });

  test('the keyboard shows a Search key; Return opens the first result and Escape closes the list', async ({ page }) => {
    await openWithResults(page, 390);
    const input = page.locator('#searchInput');
    await expect(input).toHaveAttribute('enterkeyhint', 'search');
    await input.focus();
    await input.press('Enter');
    expect(await page.evaluate(() => (window as unknown as { opened: string[] }).opened)).toEqual(['p0']);

    await page.evaluate(() => document.getElementById('searchResults')!.classList.add('active'));
    await input.focus();
    await input.press('Escape');
    await expect(page.locator('#searchResults')).toBeHidden();
  });

  test('desktop search keeps its compact size', async ({ page }) => {
    await openWithResults(page, 1280);
    const size = await page.locator('#searchInput').evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
    expect(size).toBe(13);
  });
});
