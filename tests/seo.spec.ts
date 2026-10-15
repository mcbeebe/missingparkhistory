import { test, expect } from './fixtures';
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync, statSync } from 'node:fs';
import { dirname, join, normalize } from 'node:path';

// Search Console hygiene: published duplicates must point Google at the live page,
// and no page may link to an address on this site that doesn't exist (a 404).

const ROOT = join(__dirname, '..');
const SITE = 'https://missingparkhistory.org';
const NEWS_CANONICAL = `${SITE}/news-and-press.html`;

/** Every tracked .html file, as repo-relative paths. */
function trackedHtml(): string[] {
  return execFileSync('git', ['ls-files', '-z', '*.html'], { cwd: ROOT, encoding: 'utf8' })
    .split('\0')
    .filter(Boolean);
}

/** Drafts, templates and superseded material: tracked but not linked from the site. */
const UNPUBLISHED = /^(Archive\/|scripts\/|email\/|logo-concepts|test-takeaction)/;

/** Whether GitHub Pages serves something at this repo-relative path (file, .html, or folder index). */
function served(path: string): boolean {
  const isFile = (p: string) => existsSync(join(ROOT, p)) && statSync(join(ROOT, p)).isFile();
  return isFile(path) || isFile(`${path}.html`) || isFile(join(path, 'index.html'));
}

/**
 * Same-site link targets in an HTML file, as repo-relative paths. Links built in
 * JavaScript (containing `+`, `${` or quotes) are skipped; static hrefs only.
 */
function internalLinks(file: string): string[] {
  const html = readFileSync(join(ROOT, file), 'utf8');
  const out: string[] = [];
  for (const [, raw] of html.matchAll(/href="([^"#?]*)/g)) {
    let u = raw;
    if (/^https?:\/\//.test(u)) {
      if (!u.startsWith(SITE)) continue;
      u = u.slice(SITE.length) || '/';
    }
    if (!u || /^(mailto:|tel:|javascript:|data:)/.test(u) || /[+${}()'\s]/.test(u)) continue;
    const p = normalize(u.startsWith('/') ? u.slice(1) : join(dirname(file), u)).replace(/\/$/, '');
    if (p === '.' || p === '') continue;
    out.push(decodeURIComponent(p));
  }
  return out;
}

test.describe('Search Console hygiene', () => {
  test('every News & Press copy is noindex and points at the live page', () => {
    const copies = trackedHtml().filter((f) => f.startsWith('News and Press/'));
    expect(copies.length).toBeGreaterThan(100);
    const bad = copies.filter((f) => {
      const html = readFileSync(join(ROOT, f), 'utf8');
      const robots = [...html.matchAll(/<meta name="robots" content="([^"]*)"/g)].map((m) => m[1]);
      const canonical = [...html.matchAll(/<link rel="canonical" href="([^"]*)"/g)].map((m) => m[1]);
      return robots.join() !== 'noindex, follow' || canonical.join() !== NEWS_CANONICAL;
    });
    expect(bad, 'copies missing noindex/canonical').toEqual([]);
  });

  test('the live News & Press page stays indexable', () => {
    const html = readFileSync(join(ROOT, 'news-and-press.html'), 'utf8');
    expect(html).toContain('<meta name="robots" content="index, follow">');
    expect(html).not.toContain('noindex');
  });

  test('no published page links to a missing page on this site', () => {
    const broken: string[] = [];
    for (const file of trackedHtml().filter((f) => !UNPUBLISHED.test(f))) {
      for (const target of internalLinks(file)) {
        if (!served(target)) broken.push(`${file} -> /${target}`);
      }
    }
    expect(broken).toEqual([]);
  });

  test('Support links go to the project Ko-fi page, not a placeholder', () => {
    const bad = trackedHtml()
      .filter((f) => !UNPUBLISHED.test(f))
      .filter((f) => /href="https?:\/\/(www\.)?buymeacoffee\.com/.test(readFileSync(join(ROOT, f), 'utf8')));
    expect(bad).toEqual([]);
  });

  test('the link check catches a broken link (guards against a scan that matches nothing)', () => {
    expect(served('about')).toBe(true);
    expect(served('about.html')).toBe(true);
    expect(served('data')).toBe(false);
    expect(internalLinks('index.html').length).toBeGreaterThan(10);
  });
});
