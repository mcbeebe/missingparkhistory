import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { test, expect, ANALYTICS_URL, type Page } from './fixtures';

// Test runs must never count as visitors. Two layers keep them out:
//   1. tests/fixtures.ts blocks analytics requests in every test;
//   2. the pages themselves only report from the live hostname (GA guard, Umami data-domains).

const ROOT = join(__dirname, '..');
const SKIP_DIRS = new Set(['node_modules', '.git', 'playwright-report', 'test-results']);
const LIVE_HOSTS = 'missingparkhistory.org,www.missingparkhistory.org';
const GA_GUARD =
  "if (location.hostname === 'missingparkhistory.org' || location.hostname === 'www.missingparkhistory.org') {";

function htmlFiles(dir = ROOT): string[] {
  return readdirSync(dir).flatMap((name) => {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) return SKIP_DIRS.has(name) ? [] : htmlFiles(p);
    return name.endsWith('.html') ? [p] : [];
  });
}

/** Records analytics requests a page attempts and any that actually got a response. */
function watchAnalytics(page: Page) {
  const attempted: string[] = [];
  const answered: string[] = [];
  page.on('request', (r) => { if (ANALYTICS_URL.test(r.url())) attempted.push(r.url()); });
  page.on('response', (r) => { if (ANALYTICS_URL.test(r.url())) answered.push(r.url()); });
  return { attempted, answered };
}

test.describe('analytics stay out of test runs', () => {
  test('every spec imports test from ./fixtures', () => {
    const specs = readdirSync(__dirname).filter((f) => f.endsWith('.spec.ts'));
    expect(specs.length).toBeGreaterThan(1);
    for (const f of specs) {
      const src = readFileSync(join(__dirname, f), 'utf8');
      expect(src, `${f} must not import from @playwright/test`).not.toMatch(/from ['"]@playwright\/test['"]/);
      expect(src, `${f} must import test from ./fixtures`).toMatch(/from ['"]\.\/fixtures['"]/);
    }
  });

  test('the fixture pattern matches GA and Umami URLs only', () => {
    for (const url of [
      'https://www.googletagmanager.com/gtag/js?id=G-EK392KLRFB',
      'https://region1.google-analytics.com/g/collect?v=2',
      'https://analytics.google.com/g/collect',
      'https://cloud.umami.is/script.js',
      'https://cloud.umami.is/api/send',
      'https://api-gateway.umami.dev/api/send',
    ]) expect(ANALYTICS_URL.test(url), url).toBe(true);
    for (const url of [
      'http://127.0.0.1:4173/about.html',
      'https://missingparkhistory.org/about.html',
      'https://fonts.googleapis.com/css2?family=Inter',
      'https://notgoogletagmanager.com/x',
      'https://example.com/?u=https://cloud.umami.is/',
    ]) expect(ANALYTICS_URL.test(url), url).toBe(false);
  });

  test('every page guards its analytics tags to the live hostname', () => {
    const files = htmlFiles();
    let ga = 0;
    let umami = 0;
    for (const file of files) {
      const rel = relative(ROOT, file);
      const html = readFileSync(file, 'utf8');
      // Booleans, so a failure names the file instead of printing the whole page.
      expect(/<script[^>]*src="https:\/\/www\.googletagmanager\.com/.test(html),
        `${rel}: gtag.js must be loaded by the hostname guard, not a <script src>`).toBe(false);
      expect(html.includes('your-umami-id'), `${rel}: leftover placeholder analytics tag`).toBe(false);
      if (html.includes('googletagmanager.com/gtag/js')) {
        ga++;
        expect(html.includes(GA_GUARD), `${rel}: GA must only load on the live hostname`).toBe(true);
      }
      for (const tag of html.match(/<script[^>]*cloud\.umami\.is[^>]*>/g) ?? []) {
        umami++;
        expect(tag, `${rel}: Umami tag needs data-domains`).toContain(`data-domains="${LIVE_HOSTS}"`);
      }
    }
    // Guards against the scan silently matching nothing.
    expect(ga).toBeGreaterThan(100);
    expect(umami).toBeGreaterThan(100);
  });

  for (const path of ['/about.html', '/index.html']) {
    test(`${path} on the test server sends nothing to analytics`, async ({ page }) => {
      const seen = watchAnalytics(page);
      await page.route(/^https?:\/\/(?!127\.0\.0\.1|localhost)/, (r) =>
        ANALYTICS_URL.test(r.request().url()) ? r.fallback() : r.abort(),
      );
      await page.goto(path, { waitUntil: 'load' });
      expect(await page.evaluate(() => typeof (window as unknown as { gtag?: unknown }).gtag)).toBe('function');
      expect(await page.locator('script[src*="googletagmanager.com"]').count()).toBe(0);
      expect(seen.attempted.filter((u) => u.includes('googletagmanager'))).toEqual([]);
      expect(seen.answered).toEqual([]);
    });
  }

  test('on the live hostname the page still loads GA and Umami (requests blocked by the fixture)', async ({ page }) => {
    const seen = watchAnalytics(page);
    // Serve the repo's about.html as if it came from the live site; abort everything else external.
    await page.route(/^https?:\/\/(?!missingparkhistory\.org\/)/, (r) =>
      ANALYTICS_URL.test(r.request().url()) ? r.fallback() : r.abort(),
    );
    await page.route(/^https:\/\/missingparkhistory\.org\//, (r) => {
      const path = new URL(r.request().url()).pathname;
      return path.endsWith('.html') || path.endsWith('.js') || path.endsWith('.css')
        ? r.fulfill({ path: join(ROOT, path) })
        : r.abort();
    });
    await page.goto('https://missingparkhistory.org/about.html', { waitUntil: 'load' });
    await expect(page.locator('script[src*="googletagmanager.com/gtag/js?id=G-EK392KLRFB"]')).toHaveCount(1);
    await expect.poll(() => seen.attempted.some((u) => u.includes('googletagmanager.com/gtag/js'))).toBe(true);
    await expect.poll(() => seen.attempted.some((u) => u.startsWith('https://cloud.umami.is/script.js'))).toBe(true);
    expect(seen.answered).toEqual([]);
  });
});
