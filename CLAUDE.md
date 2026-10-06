# Project guidance for Claude

## Workflow

- After completing a set of changes, **always commit and open a pull request** —
  don't leave work only committed/pushed without a PR. This is the default for
  every task unless the user says otherwise.
- Develop on the feature branch assigned for the session; never push directly to
  `main`.
- This is a static HTML site (GitHub Pages, served from `main`). There is no
  build step — pages are plain `.html` files with inline `<style>`/`<script>`.

## Shared header

Most content pages share the same top navigation (`.topnav` / `.topnav-links`).
When changing nav links or header behavior, update all pages that contain
`<div class="topnav-links">` so the header stays consistent. Every header page
carries the same link list, in the same order; the canonical list lives in
`tests/nav-consistency.spec.ts` and the test fails if any page drifts. The
current page's link gets `class="active" aria-current="page"`. `index.html` (the
map/home page) uses a different banner design and does not share this header.

Responsive/menu behavior lives in two shared files, not in each page:
`/site-nav.css` (linked at the end of `<head>`) and `/site-nav.js` (loaded
synchronously right after `</nav>`). The script adds the menu button and
collapses the links whenever they don't fit. New header pages need both tags;
don't add per-page hamburger CSS or buttons.

## Tests

`npm install && npm test` runs Playwright layout checks on every public page
(no horizontal overflow at 390px; header collapses correctly). CI runs the same
on every PR (`.github/workflows/layout-tests.yml`). Run it before opening a PR
that touches layout or the header.
