import { test, expect, type Page } from '@playwright/test';
import { headerPages } from './pages';

/** Bounding rects of the nav bar's links, toggle and brand, plus collapse state. */
async function headerState(page: Page) {
  return page.evaluate(() => {
    const nav = document.querySelector('nav.topnav')!;
    const rect = (el: Element | null) => (el ? el.getBoundingClientRect().toJSON() as DOMRect : null);
    return {
      collapsed: nav.classList.contains('nav-collapsed'),
      vw: document.documentElement.clientWidth,
      nav: rect(nav)!,
      brand: rect(nav.querySelector('.topnav-brand'))!,
      toggleVisible: getComputedStyle(nav.querySelector('.nav-toggle')!).display !== 'none',
      links: Array.from(nav.querySelectorAll('.topnav-links a')).map((a) => ({
        text: a.textContent!.trim(),
        ...a.getBoundingClientRect().toJSON(),
      })) as Array<DOMRect & { text: string }>,
    };
  });
}

// Wide enough for the full row on every page (~1,290px max): links stay inline.
test.describe('desktop 1440px: header shows inline links', () => {
  test.use({ viewport: { width: 1440, height: 900 } });
  for (const path of headerPages()) {
    test(path, async ({ page }) => {
      await page.goto(path, { waitUntil: 'load' });
      const s = await headerState(page);
      expect(s.collapsed).toBe(false);
      expect(s.toggleVisible).toBe(false);
      expect(s.nav.height).toBeLessThanOrEqual(64);
      for (const l of s.links) {
        expect(l.right, `${l.text} fits`).toBeLessThanOrEqual(s.vw);
        expect(l.top, `${l.text} on the bar`).toBeLessThan(s.nav.bottom);
        expect(l.left, `${l.text} clear of brand`).toBeGreaterThanOrEqual(s.brand.right);
      }
    });
  }
});

// Every width either shows the full row without clipping, or collapses.
for (const width of [700, 768, 1024, 1280]) {
  test.describe(`${width}px: header never clips`, () => {
    test.use({ viewport: { width, height: 900 } });
    for (const path of headerPages()) {
      test(path, async ({ page }) => {
        await page.goto(path, { waitUntil: 'load' });
        const s = await headerState(page);
        expect(s.brand.height, 'site title on one line').toBeLessThanOrEqual(32);
        if (s.collapsed) {
          expect(s.toggleVisible).toBe(true);
        } else {
          for (const l of s.links) {
            expect(l.right, `${l.text} fits`).toBeLessThanOrEqual(s.vw);
            expect(l.left, `${l.text} clear of brand`).toBeGreaterThanOrEqual(s.brand.right);
          }
        }
      });
    }
  });
}

test.describe('menu behaviour', () => {
  const path = '/voices.html';

  test('re-evaluates on resize and closes when expanding to desktop', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    const toggle = page.locator('.nav-toggle');
    await toggle.click();
    await expect(page.locator('nav.topnav')).toHaveClass(/nav-open/);
    await page.setViewportSize({ width: 1440, height: 900 });
    await expect(page.locator('nav.topnav')).not.toHaveClass(/nav-collapsed/);
    await expect(page.locator('nav.topnav')).not.toHaveClass(/nav-open/);
    await expect(toggle).toBeHidden();
    await page.setViewportSize({ width: 390, height: 844 });
    await expect(toggle).toBeVisible();
    await expect(page.locator('.topnav-links')).toBeHidden();
  });

  test('clicking outside the menu closes it', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    await page.locator('.nav-toggle').click();
    await expect(page.locator('.topnav-links')).toBeVisible();
    await page.mouse.click(200, 800);
    await expect(page.locator('.topnav-links')).toBeHidden();
    await expect(page.locator('.nav-toggle')).toHaveAttribute('aria-expanded', 'false');
  });

  test('menu button is labelled and controls the link list', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    const toggle = page.getByRole('button', { name: 'Open menu' });
    await expect(toggle).toHaveAttribute('aria-controls', 'site-nav-links');
    await toggle.click();
    await expect(page.getByRole('button', { name: 'Close menu' })).toBeVisible();
    await expect(page.locator('#site-nav-links')).toBeVisible();
  });

  test('keyboard: Enter opens, links are reachable with Tab', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(path);
    await page.locator('.nav-toggle').focus();
    await page.keyboard.press('Enter');
    await page.keyboard.press('Tab');
    const focused = await page.evaluate(() => document.activeElement?.closest('.topnav-links') !== null);
    expect(focused).toBe(true);
  });
});

test.describe('without JavaScript', () => {
  test.use({ javaScriptEnabled: false, viewport: { width: 390, height: 844 }, isMobile: true });
  test('links scroll inside the bar instead of overflowing the page', async ({ page }) => {
    await page.goto('/voices.html');
    const s = await page.evaluate(() => {
      const links = document.querySelector('.topnav-links')!;
      return {
        overflowX: getComputedStyle(links).overflowX,
        right: links.getBoundingClientRect().right,
        scrollable: links.scrollWidth > links.clientWidth,
        docWidth: document.documentElement.scrollWidth,
      };
    });
    expect(s.overflowX).toBe('auto');
    expect(s.right).toBeLessThanOrEqual(390);
    expect(s.scrollable).toBe(true);
    expect(s.docWidth).toBeLessThanOrEqual(390);
  });
});
