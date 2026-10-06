import { test, expect } from '@playwright/test';

// The home page's news pop-up opens on every visit. Its headline wraps with the
// viewport, so check that no line of it ever runs under the close (×) button.
test.describe('home news pop-up', () => {
  for (const width of [320, 360, 375, 390, 412, 428, 600, 768, 1024, 1440]) {
    test(`headline clears the close button at ${width}px`, async ({ page }) => {
      await page.setViewportSize({ width, height: 800 });
      await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
      const headline = page.locator('#ndOverlay .nd-header h2');
      await expect(headline).toBeVisible();
      const hits = await headline.evaluate((h2) => {
        const x = document.querySelector('#ndOverlay .nd-close')!.getBoundingClientRect();
        const range = document.createRange();
        range.selectNodeContents(h2);
        return Array.from(range.getClientRects())
          .filter((l) => l.right > x.left && l.left < x.right && l.bottom > x.top && l.top < x.bottom)
          .map((l) => `line ${Math.round(l.left)}–${Math.round(l.right)} vs × ${Math.round(x.left)}–${Math.round(x.right)}`);
      });
      expect(hits).toEqual([]);
    });
  }
});
