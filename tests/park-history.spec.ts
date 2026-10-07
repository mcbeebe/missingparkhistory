import { test, expect, type Page } from '@playwright/test';

// The map modal's "Park History" section is built by buildParkHistoryHTML() from
// data/parkHistory.json. Published parks get the sourced block; parks with only an
// NPSHistory archive page get a single link; non-NPS entries get nothing.

type W = Window & {
  parkData: Record<string, unknown>;
  parkHistory: Record<string, unknown>;
  openPanel: (id: string) => void;
  buildParkHistoryHTML: (t: unknown, id: string) => string;
  ndClose?: () => void;
};

async function openHome(page: Page) {
  await page.setViewportSize({ width: 1200, height: 900 });
  await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) => r.abort());
  await page.goto('/index.html', { waitUntil: 'domcontentloaded' });
  await page.waitForFunction(() => {
    const w = window as unknown as W;
    return w.parkData && Object.keys(w.parkData).length > 0 && typeof w.buildParkHistoryHTML === 'function';
  });
  await page.evaluate(() => {
    (window as unknown as W).ndClose?.();
    document.getElementById('loadOverlay')?.remove();
  });
}

const PUBLISHED = {
  name: 'Mount Rainier National Park',
  reviewStatus: 'published',
  lastReviewed: '2026-10-07',
  summary:
    '<p>Summary sentence. <a href="https://npshistory.com/publications/mora/index.htm" target="_blank" rel="noopener" class="cite">[9]</a></p>',
  sources: [{ url: 'https://npshistory.com/publications/mora/index.htm', title: 'Archive overview' }],
  themes: {
    climate: {
      html: '<p>Glacier sentence. <a href="https://npshistory.com/publications/mora/nisqually-glacier-changes-1.pdf" target="_blank" rel="noopener" class="cite">[x]</a></p>',
      sources: [{ url: 'https://npshistory.com/publications/mora/nisqually-glacier-changes-1.pdf', title: 'Stevens et al. 2016' }],
    },
    indigenous: {
      html: '<p>People sentence. <a href="https://npshistory.com/publications/mora/adhi/chap1.htm" target="_blank" rel="noopener" class="cite">[x]</a></p>',
      sources: [{ url: 'https://npshistory.com/publications/mora/adhi/chap1.htm', title: 'Catton 1996 ch. 1' }],
    },
  },
  photos: [],
  npshistory: { indexUrl: 'https://npshistory.com/publications/mora/index.htm', docCount: 572 },
  corrections: [],
};

test('a published park renders the sourced Dossier block with derived citation numbers', async ({ page }) => {
  await openHome(page);
  const html = await page.evaluate((rec) => {
    const w = window as unknown as W;
    w.parkHistory['MORA'] = rec;
    return w.buildParkHistoryHTML(w.parkData['131'], '131');
  }, PUBLISHED);
  expect(html).toContain('class="panel-section ph-section"');
  expect(html).not.toContain('undefined');
  // summary source is [1]; themes follow the fixed theme order: indigenous [2], climate [3]
  expect(html).toContain('class="cite">[1]</a>');
  expect(html).toContain('Indigenous peoples</h4><p>People sentence. <a href="https://npshistory.com/publications/mora/adhi/chap1.htm" target="_blank" rel="noopener" class="cite">[2]</a>');
  expect(html).toContain('Climate &amp; environment</h4><p>Glacier sentence.');
  expect(html).toContain('class="cite">[3]</a>');
  expect(html).toMatch(/<ol class="ph-sources">(<li><a href="https?:\/\/[^"]+" target="_blank" rel="noopener">[^<]+<\/a><\/li>){3}<\/ol>/);
  expect(html).toContain('572 documents on NPSHistory.com');
  expect(html).toContain('/about.html#credits');
});

test('the modal shows the block when a published park is opened', async ({ page }) => {
  await openHome(page);
  await page.evaluate((rec) => {
    const w = window as unknown as W;
    w.parkHistory['MORA'] = rec;
    try { w.openPanel('131'); } catch { /* map library is blocked in this harness */ }
  }, PUBLISHED);
  const section = page.locator('#panelContent .ph-section');
  await expect(section).toHaveCount(1);
  await expect(section.locator('.section-title')).toContainText('Park History');
  await expect(section.locator('.ph-sources a[href^="http"][target="_blank"][rel~="noopener"]')).toHaveCount(3);
  // long source URLs must not widen the panel
  const overflow = await page.evaluate(() => {
    const p = document.getElementById('sidePanel')!;
    return p.scrollWidth > p.clientWidth + 1;
  });
  expect(overflow).toBe(false);
});

test('a park with only an archive page gets the single documentary-record link', async ({ page }) => {
  await openHome(page);
  const html = await page.evaluate(() => {
    const w = window as unknown as W;
    w.parkHistory['WRST'] = { reviewStatus: 'draft', summary: '', themes: {}, npshistory: { indexUrl: 'https://npshistory.com/publications/wrst/index.htm', docCount: 156 } };
    return w.buildParkHistoryHTML(w.parkData['156'], '156');
  });
  expect(html).toContain('ph-row');
  expect(html).toContain('156 documents on NPSHistory.com');
  expect(html).not.toContain('ph-sources');
  expect(html).not.toContain('ph-summary');
});

test('non-NPS entries and parks without data render nothing', async ({ page }) => {
  await openHome(page);
  const out = await page.evaluate(() => {
    const w = window as unknown as W;
    const fws = Object.entries(w.parkData).find(([, v]) => (v as { agency?: string }).agency === 'FWS');
    const fwsHtml = fws ? w.buildParkHistoryHTML(fws[1], fws[0]) : '';
    delete w.parkHistory['ZZZZ'];
    const none = w.buildParkHistoryHTML({ code: 'ZZZZ', park: 'Nowhere' }, 'x');
    return { fwsHtml, none };
  });
  expect(out.fwsHtml).toBe('');
  expect(out.none).toBe('');
});

test('the compiled data file is served and keyed by park code', async ({ page }) => {
  await openHome(page);
  const keys = await page.evaluate(() => Object.keys((window as unknown as W).parkHistory));
  expect(keys.length).toBeGreaterThan(50);
  expect(keys).toContain('MORA');
  expect(keys.every((k) => /^[A-Z]{4}$/.test(k))).toBe(true);
});
