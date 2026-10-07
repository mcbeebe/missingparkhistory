import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { headerPages } from './pages';

const ROOT = join(__dirname, '..');

/** The one link list every shared header must carry, in order. */
const CANONICAL = [
  ['/', 'Map'],
  ['/voices.html', 'Voices'],
  ['/about.html', 'About'],
  ['/data-methodology.html', 'Data'],
  ['/nps-censorship.html', 'Censorship'],
  ['/status.html', 'Status'],
  ['/help.html', 'Help'],
  ['/timeline.html', 'Timeline'],
  ['/legal-analysis.html', 'Legal'],
  ['/presidents-house.html', "President's House"],
  ['/news-and-press.html', 'News & Press'],
];

/** Parses the `.topnav-links` anchors straight from the HTML source. */
function navLinks(path: string) {
  const html = readFileSync(join(ROOT, path), 'utf8');
  const block = html.match(/<div class="topnav-links">([\s\S]*?)<\/div>/)![1];
  return [...block.matchAll(/<a\s+([^>]*)>([\s\S]*?)<\/a>/g)].map(([, attrs, text]) => ({
    href: attrs.match(/href="([^"]*)"/)![1],
    text: text.replace(/&amp;/g, '&').replace(/&#x?[0-9a-f]+;/gi, '').trim(),
    active: /class="[^"]*\bactive\b/.test(attrs),
    current: /aria-current="page"/.test(attrs),
  }));
}

test.describe('header link list is identical on every page', () => {
  for (const path of headerPages()) {
    test(path, () => {
      const links = navLinks(path);
      expect(links.map((l) => [l.href, l.text])).toEqual(CANONICAL);

      // At most one highlighted link; aria-current only on the page itself.
      expect(links.filter((l) => l.active).length).toBeLessThanOrEqual(1);
      for (const l of links) {
        expect(l.current, `${l.href} aria-current`).toBe(l.href === path);
        if (l.current) expect(l.active, `${l.href} highlighted`).toBe(true);
      }
    });
  }
});
