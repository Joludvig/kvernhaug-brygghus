// Bryggeskole module-grid real-runtime Playwright config (issue #394) --
// separate, deliberately narrow config, same pattern as
// playwright.streamlit.config.js (issue #378/#379).
//
// This config starts the actual `streamlit run` process against the
// existing AppTest fixture harness
// (tests/fixtures/streamlit_harness/bryggeskole_harness.py -- already the
// production render_bryggeskole_panel() call, previously only exercised
// via streamlit.testing.v1.AppTest, which does not produce a real
// browser DOM/CSS layout at all), so tests/playwright_streamlit/module-
// grid-responsive.spec.js can measure genuine flex-wrap/column-count/
// text-line layout at several real viewport widths -- the exact gap
// unit tests on the CSS string can't cover (a passing CSS-string
// assertion proves nothing about whether the browser actually wraps).
//
// Deliberately a separate config/port from playwright.streamlit.config.js
// (which boots a different, SVG-only harness) so the two webServers never
// collide and each spec file only ever talks to the harness it needs.
'use strict';

const { defineConfig, devices } = require('@playwright/test');
const { resolveStreamlitPythonCommand } = require('./tests/playwright_streamlit/streamlit_runtime');

const PORT = 8525;

// Same validated resolver as playwright.streamlit.config.js -- no silent
// `py -3` fallback (see streamlit_runtime.js).
const STREAMLIT_PYTHON = resolveStreamlitPythonCommand();

module.exports = defineConfig({
  testDir: './tests/playwright_streamlit',
  // nav-buttons-responsive.spec.js (issue #398 responsive follow-up)
  // uses the same harness, so it shares this config/port.
  // stage-selector-smoke.spec.js (stage UI S3) uses it too.
  testMatch: ['**/module-grid-responsive.spec.js', '**/nav-buttons-responsive.spec.js', '**/stage-selector-smoke.spec.js'],
  fullyParallel: true,
  workers: process.env.CI ? undefined : 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-bryggeskole-grid' }]] : 'list',
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command:
      `${STREAMLIT_PYTHON} -m streamlit run tests/fixtures/streamlit_harness/bryggeskole_harness.py ` +
      `--server.headless true --server.port ${PORT} --server.address 127.0.0.1 ` +
      '--browser.gatherUsageStats false',
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
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
      use: { ...devices['Desktop Firefox'], viewport: { width: 390, height: 844 } },
    },
  ],
});
