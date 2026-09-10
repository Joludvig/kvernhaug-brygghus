// Playwright Critical Browser Gate (issue #200) -- config only.
//
// Serves web/ with a deterministic local static server (Python's
// stdlib http.server -- already a project dependency, no extra Node
// package needed just to serve static files) so tests run against the
// checked-out PR head, never production (https://kvernhaugbrygghus.no).
//
// Matrix required by issue #200: Chromium + Firefox x desktop 1280x900 +
// mobile 390x844. NO vs EN is a per-test concern (tests navigate to
// either the NO page or its /en/ mirror), not a separate project, so it
// does not multiply the project matrix here.
'use strict';

const { defineConfig, devices } = require('@playwright/test');

const PORT = 4173;

module.exports = defineConfig({
  testDir: './tests/playwright',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: `python3 -m http.server ${PORT} --directory web --bind 127.0.0.1`,
    url: `http://127.0.0.1:${PORT}/index.html`,
    reuseExistingServer: !process.env.CI,
    timeout: 30_000,
  },
  projects: [
    {
      name: 'chromium-desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } },
    },
    {
      name: 'chromium-mobile',
      use: { ...devices['Desktop Chrome'], viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true },
    },
    {
      name: 'firefox-desktop',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1280, height: 900 } },
    },
    {
      name: 'firefox-mobile',
      // Firefox does not support Playwright's mobile-emulation device
      // descriptors (isMobile/hasTouch are Chromium-only) -- viewport-only
      // emulation, which is all the 390x844 requirement in issue #200 asks for.
      use: { ...devices['Desktop Firefox'], viewport: { width: 390, height: 844 } },
    },
  ],
});
