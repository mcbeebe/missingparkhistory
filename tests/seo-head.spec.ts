import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { test, expect } from './fixtures';
import { publicPages } from './pages';

// Head-tag hygiene for every public page: one H1, title/description, a self-referencing
// canonical, Open Graph + Twitter card, and an indexable robots directive.
// Drafts (logo concepts, test page) must stay out of search results.

const ROOT = join(__dirname, '..');
const SITE = 'https://missingparkhistory.org';
const DRAFTS = ['logo-concepts.html', 'logo-concepts-v2.html', 'test-takeaction.html'];

for (const path of publicPages()) {
  test(`SEO head: ${path}`, async ({ page }) => {
    await page.goto(path, { waitUntil: 'domcontentloaded' });
    const head = await page.evaluate(() => {
      const meta = (sel: string) => document.querySelector<HTMLMetaElement>(sel)?.content?.trim() ?? '';
      return {
        h1: document.querySelectorAll('h1').length,
        title: document.title.trim(),
        description: meta('meta[name="description"]'),
        canonical: document.querySelector<HTMLLinkElement>('link[rel="canonical"]')?.getAttribute('href') ?? '',
        ogTitle: meta('meta[property="og:title"]'),
        ogDescription: meta('meta[property="og:description"]'),
        ogImage: meta('meta[property="og:image"]'),
        twitterCard: meta('meta[name="twitter:card"]'),
        robots: meta('meta[name="robots"]'),
      };
    });
    expect(head.h1, 'exactly one <h1>').toBe(1);
    expect(head.title, 'title').not.toBe('');
    expect(head.description, 'meta description').not.toBe('');
    // index.html is served at the site root, so its canonical is the bare domain.
    const own = path === '/index.html' ? `${SITE}/` : `${SITE}${path}`;
    expect(head.canonical, 'canonical').toBe(own);
    expect(head.ogTitle, 'og:title').not.toBe('');
    expect(head.ogDescription, 'og:description').not.toBe('');
    expect(head.ogImage, 'og:image').toMatch(/^https:\/\/missingparkhistory\.org\/.+\.(png|jpe?g)$/);
    expect(head.twitterCard, 'twitter:card').not.toBe('');
    expect(head.robots, 'robots').toContain('index');
    expect(head.robots, 'robots').not.toContain('noindex');
  });
}

test('draft pages are noindex and not in the sitemap', () => {
  const sitemap = readFileSync(join(ROOT, 'sitemap.xml'), 'utf8');
  for (const file of DRAFTS) {
    const html = readFileSync(join(ROOT, file), 'utf8');
    expect(html, file).toMatch(/<meta name="robots" content="[^"]*noindex[^"]*"/);
    expect(sitemap, file).not.toContain(file);
  }
});

test('park pages give every photo explicit dimensions', () => {
  // Static check across all park pages: width/height reserve space so lazy images don't shift layout.
  const bad: string[] = [];
  for (const path of publicPages().filter((p) => p.startsWith('/parks/'))) {
    const html = readFileSync(join(ROOT, path), 'utf8');
    for (const tag of html.match(/<img [^>]*>/g) ?? []) {
      if (tag.includes('logo.svg')) continue;
      if (!/ width="\d+"/.test(tag) || !/ height="\d+"/.test(tag)) bad.push(`${path}: ${tag.slice(0, 120)}`);
    }
  }
  // One SOS source file is an HTML error page saved as .jpg; its dimensions cannot be read.
  expect(bad.filter((b) => !b.includes('acad-wetlands-tripod-two-acadia-is-changing-so-are-we-sage-backgr'))).toEqual([]);
});
