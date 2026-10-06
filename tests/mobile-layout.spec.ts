import { test, expect, type Page } from '@playwright/test';
import { publicPages, headerPages } from './pages';

const PHONE = { width: 390, height: 844 };

test.use({ viewport: PHONE, isMobile: true, hasTouch: true, deviceScaleFactor: 2 });

/** Loads a page and waits for layout to settle (fonts, deferred scripts). */
async function open(page: Page, path: string): Promise<void> {
  await page.goto(path, { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
}

/**
 * Lists visible elements whose box extends past either side of the viewport and
 * which are not inside a horizontally clipping/scrolling container. This catches
 * overflow that never shows up in document scroll width, e.g. inside a
 * `position: fixed` header, where content is silently cut off.
 */
async function overflowCulprits(page: Page): Promise<string[]> {
  return page.evaluate(() => {
    const vw = document.documentElement.clientWidth;
    const clipped = (el: Node): boolean => {
      for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
        const ox = getComputedStyle(p).overflowX;
        if (ox !== 'visible') return true;
      }
      return false;
    };
    const describe = (el: Element): string => {
      const id = el.id ? `#${el.id}` : '';
      const cls = typeof el.className === 'string' && el.className.trim()
        ? '.' + el.className.trim().split(/\s+/).join('.')
        : '';
      return `${el.tagName.toLowerCase()}${id}${cls}`;
    };
    const out: string[] = [];
    for (const el of Array.from(document.body.querySelectorAll('*'))) {
      const r = el.getBoundingClientRect();
      if (r.width === 0 || r.height === 0) continue;
      if (r.right <= vw + 1 && r.left >= -1) continue;
      // Visually-hidden helpers (skip links, sr-only text) are intentionally off-screen.
      if (r.right <= 0 || r.width <= 1 || r.height <= 1) continue;
      const cs = getComputedStyle(el);
      if (cs.visibility === 'hidden' || cs.opacity === '0' || clipped(el)) continue;
      out.push(`${describe(el)} left=${Math.round(r.left)} right=${Math.round(r.right)}`);
    }
    // Unbroken text (e.g. long URLs) can spill out of a box that itself fits.
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    const range = document.createRange();
    for (let n = walker.nextNode(); n; n = walker.nextNode()) {
      const parent = n.parentElement;
      if (!parent || !n.textContent!.trim() || clipped(n)) continue;
      range.selectNodeContents(n);
      const r = range.getBoundingClientRect();
      if (r.width === 0 || r.right <= vw + 1) continue;
      if (getComputedStyle(parent).visibility === 'hidden') continue;
      out.push(`text in ${describe(parent)} right=${Math.round(r.right)}: "${n.textContent!.trim().slice(0, 40)}"`);
    }
    return out.slice(0, 10);
  });
}

test.describe('no horizontal overflow at 390px', () => {
  for (const path of publicPages()) {
    test(path, async ({ page }) => {
      await open(page, path);
      const { scrollWidth, clientWidth } = await page.evaluate(() => ({
        scrollWidth: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth),
        clientWidth: document.documentElement.clientWidth,
      }));
      expect(clientWidth, 'layout viewport should be device width (meta viewport)').toBe(PHONE.width);
      const culprits = await overflowCulprits(page);
      expect(scrollWidth, `page is wider than viewport; culprits:\n${culprits.join('\n')}`)
        .toBeLessThanOrEqual(clientWidth);
      expect(culprits, 'elements extend past the viewport edge').toEqual([]);
    });
  }
});

test.describe('shared header collapses into a menu on phones', () => {
  for (const path of headerPages()) {
    test(path, async ({ page }) => {
      await open(page, path);
      const nav = page.locator('nav.topnav');
      const brand = nav.locator('.topnav-brand');
      const toggle = nav.locator('.nav-toggle');
      const links = nav.locator('.topnav-links');

      // Bar is a single row: brand on one line, menu button beside it.
      await expect(toggle).toBeVisible();
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      await expect(links).toBeHidden();
      const navBox = (await nav.boundingBox())!;
      const brandBox = (await brand.boundingBox())!;
      const toggleBox = (await toggle.boundingBox())!;
      expect(navBox.height).toBeLessThanOrEqual(64);
      expect(brandBox.height, 'site title must not wrap').toBeLessThanOrEqual(32);
      expect(brandBox.x + brandBox.width).toBeLessThanOrEqual(toggleBox.x);
      expect(toggleBox.x + toggleBox.width).toBeLessThanOrEqual(PHONE.width);

      // Opening the menu shows every link fully inside the viewport, unclipped.
      await toggle.click();
      await expect(toggle).toHaveAttribute('aria-expanded', 'true');
      await expect(links).toBeVisible();
      const menuBg = await links.evaluate((el) => getComputedStyle(el).backgroundColor);
      expect(menuBg, 'menu panel must be opaque so page text does not show through').toMatch(/^rgb\(/);
      const boxes = await links.locator('a').evaluateAll((as) =>
        as.map((a) => {
          const r = a.getBoundingClientRect();
          return { text: a.textContent!.trim(), left: r.left, right: r.right, clipped: a.scrollWidth > a.clientWidth + 1 };
        }),
      );
      expect(boxes.length).toBeGreaterThan(3);
      for (const b of boxes) {
        expect(b.left, `${b.text} left edge`).toBeGreaterThanOrEqual(0);
        expect(b.right, `${b.text} right edge`).toBeLessThanOrEqual(PHONE.width);
        expect(b.clipped, `${b.text} text clipped`).toBe(false);
      }
      const active = links.locator('a.active');
      if (await active.count()) {
        const ab = (await active.first().boundingBox())!;
        expect(ab.height, 'active pill should be one line').toBeLessThanOrEqual(48);
      }

      // Escape closes the menu and returns focus to the button.
      await page.keyboard.press('Escape');
      await expect(links).toBeHidden();
      await expect(toggle).toHaveAttribute('aria-expanded', 'false');
      await expect(toggle).toBeFocused();
    });
  }
});
