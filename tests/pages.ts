import { readdirSync, readFileSync } from 'node:fs';
import { join } from 'node:path';

const ROOT = join(__dirname, '..');

/** Root-level files that are drafts/tools, not public pages. */
const EXCLUDED = new Set([
  'logo-concepts.html',
  'logo-concepts-v2.html',
  'test-takeaction.html',
]);

/**
 * Every public page on the site as a URL path: root-level `*.html` plus
 * `parks/*.html`. Dated news archives and the email template are excluded.
 */
export function publicPages(): string[] {
  const root = readdirSync(ROOT)
    .filter((f) => f.endsWith('.html') && !EXCLUDED.has(f))
    .map((f) => `/${f}`);
  const parks = readdirSync(join(ROOT, 'parks'))
    .filter((f) => f.endsWith('.html'))
    // pages kept only to redirect an old URL (e.g. lower-delaware-wsr.html) are not public pages
    .filter((f) => !readFileSync(join(ROOT, 'parks', f), 'utf8').includes('http-equiv="refresh"'))
    .map((f) => `/parks/${f}`);
  return [...root, ...parks].sort();
}

/** Public pages whose markup contains the shared `.topnav-links` header. */
export function headerPages(): string[] {
  return publicPages().filter((p) =>
    readFileSync(join(ROOT, p), 'utf8').includes('class="topnav-links"'),
  );
}
