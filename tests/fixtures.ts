import { test as base } from '@playwright/test';

export { expect } from '@playwright/test';
export type { Page } from '@playwright/test';

/** Hosts that serve the site's analytics scripts or receive its beacons (GA4 and Umami Cloud). */
export const ANALYTICS_HOSTS = [
  'googletagmanager.com',
  'google-analytics.com',
  'analytics.google.com',
  'cloud.umami.is',
  'api-gateway.umami.dev',
];

/** Matches any URL on an analytics host or one of its subdomains. */
export const ANALYTICS_URL = new RegExp(
  `^https?://([^/]+\\.)?(${ANALYTICS_HOSTS.map((h) => h.replace(/\./g, '\\.')).join('|')})(?::\\d+)?(/|$)`,
);

/**
 * Drop-in replacement for Playwright's `test` that blocks every analytics request,
 * so test runs (locally and in CI) never show up as visitors in GA or Umami.
 * Every spec must import `test` from here, not from `@playwright/test`;
 * tests/analytics.spec.ts enforces that.
 */
export const test = base.extend<{ blockAnalytics: void }>({
  blockAnalytics: [
    async ({ context }, use) => {
      await context.route(ANALYTICS_URL, (route) => route.abort('blockedbyclient'));
      await use();
    },
    { auto: true },
  ],
});
