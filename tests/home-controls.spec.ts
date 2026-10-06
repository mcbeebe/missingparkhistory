import { test, expect, type Page } from '@playwright/test';

// The home page floats its buttons, comments strip, filters and legend over the
// map. At every width none of them may cover the title box's text or each other.
const WIDTHS = [360, 390, 430, 600, 601, 650, 700, 768, 820, 900, 901, 1024, 1100, 1101, 1150, 1151, 1280, 1366, 1440, 1920];

const CONTROLS = [
  '.take-action-btn', '.sub-btn', '.about-page-btn', '.topics-dropdown', '.phu-btn', '.news-btn',
  '.mobile-about-btn', '.mobile-news-btn', '.mobile-topics-dropdown', '.desktop-last-updated', '.legend',
];

/**
 * Loads the home page without the map's CDN scripts (the controls are placed by
 * their own inline script), closes the news pop-up, and removes the map's loading
 * veil, which only lifts once the map library has loaded.
 */
async function openHome(page: Page, width: number) {
  await page.setViewportSize({ width, height: width <= 600 ? 844 : 900 });
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
  await page.evaluate(() => {
    (window as unknown as { ndClose?: () => void }).ndClose?.();
    document.getElementById('loadOverlay')?.remove();
  });
}

/** Every covered title line and every overlapping pair of controls, as readable strings. */
function collisions(page: Page) {
  return page.evaluate((selectors) => {
    const box = (el: Element | null) => {
      if (!el) return null;
      const cs = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      return cs.display !== 'none' && cs.visibility !== 'hidden' && r.width > 0 && r.height > 0 ? r : null;
    };
    const hit = (a: DOMRect, b: DOMRect) =>
      a.left < b.right - 1 && b.left < a.right - 1 && a.top < b.bottom - 1 && b.top < a.bottom - 1;
    const controls: Array<[string, DOMRect]> = [];
    for (const s of selectors) {
      const r = box(document.querySelector(s));
      if (r) controls.push([s, r]);
    }
    for (const el of Array.from(document.querySelectorAll('.controls-bar > *'))) {
      const r = box(el);
      if (r) controls.push([`.controls-bar > .${el.classList[0]}`, r]);
    }
    const lines: Array<[string, DOMRect]> = [];
    const walker = document.createTreeWalker(document.querySelector('.title-banner')!, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.textContent!.trim() || !box(node.parentElement)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const r of Array.from(range.getClientRects())) if (r.width > 0) lines.push([node.textContent!.trim().slice(0, 24), r]);
    }
    const found: string[] = [];
    for (const [text, r] of lines) for (const [name, c] of controls) if (hit(r, c)) found.push(`"${text}" under ${name}`);
    for (let i = 0; i < controls.length; i++) {
      for (let j = i + 1; j < controls.length; j++) {
        const [a, ra] = controls[i], [b, rb] = controls[j];
        if (a.startsWith('.controls-bar') && b.startsWith('.controls-bar')) continue; // stacked by flexbox
        if (hit(ra, rb)) found.push(`${a} overlaps ${b}`);
      }
    }
    return [...new Set(found)];
  }, CONTROLS);
}

test.describe('home page controls', () => {
  for (const width of WIDTHS) {
    test(`nothing covers the title or another control at ${width}px`, async ({ page }) => {
      await openHome(page, width);
      await expect(page.locator('.title-banner h1')).toBeVisible();
      expect(await collisions(page)).toEqual([]);
    });
  }

  test('tablet widths stack every button in one right-hand column', async ({ page }) => {
    await openHome(page, 768);
    const boxes = await page.evaluate(() =>
      ['.take-action-btn', '.sub-btn', '.about-page-btn', '.topics-dropdown', '.phu-btn', '.news-btn'].map((s) => {
        const r = document.querySelector(s)!.getBoundingClientRect();
        return { s, left: Math.round(r.left), right: Math.round(r.right), top: r.top, bottom: r.bottom };
      }),
    );
    for (const b of boxes) expect(b.right, `${b.s} hugs the right edge`).toBe(768 - 12);
    expect(new Set(boxes.map((b) => b.left)).size, 'one column width').toBe(1);
    for (let i = 1; i < boxes.length; i++) expect(boxes[i].top, `${boxes[i].s} below ${boxes[i - 1].s}`).toBeGreaterThan(boxes[i - 1].bottom);
    const title = await page.locator('.title-banner').boundingBox();
    expect(title!.x, 'title box clear of the map zoom buttons').toBeGreaterThanOrEqual(48);
    expect(title!.x + title!.width, 'title box clear of the column').toBeLessThanOrEqual(boxes[0].left);
  });

  test('on phones About, News and Topics can all be tapped', async ({ page }) => {
    await openHome(page, 390);
    const covered = await page.evaluate(() =>
      ['.mobile-about-btn', '.mobile-news-btn', '.mobile-topics-btn'].filter((s) => {
        const el = document.querySelector(s)!;
        const r = el.getBoundingClientRect();
        return !el.contains(document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2));
      }),
    );
    expect(covered).toEqual([]);
    await page.locator('.mobile-topics-btn').click();
    const menu = await page.locator('.mobile-topics-menu').boundingBox();
    expect(menu!.x).toBeGreaterThanOrEqual(0);
    expect(menu!.x + menu!.width).toBeLessThanOrEqual(390);
  });
});
