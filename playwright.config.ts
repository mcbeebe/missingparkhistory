import { defineConfig, devices } from '@playwright/test';

const PORT = 4173;
const HTTPS_PROXY = process.env.HTTPS_PROXY || process.env.https_proxy;

export default defineConfig({
  testDir: 'tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    ...devices['Desktop Chrome'],
    // Sandboxed dev environments reach CDNs only through an HTTPS proxy.
    ...(HTTPS_PROXY
      ? { proxy: { server: HTTPS_PROXY, bypass: '127.0.0.1,localhost' }, ignoreHTTPSErrors: true }
      : {}),
  },
  webServer: {
    // The site is plain static files served from the repo root (GitHub Pages).
    command: `python3 -m http.server ${PORT} --bind 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}/about.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
    stdout: 'ignore',
    stderr: 'ignore',
  },
});
