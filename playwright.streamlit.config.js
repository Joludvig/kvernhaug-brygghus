// Bryggeskole SVG real-runtime Playwright config (issue #378 Chief review,
// PR #379) -- separate, deliberately narrow config from the root
// playwright.config.js (which serves the static web/ site only, per its
// own header comment, and never starts Streamlit).
//
// This config starts the actual `streamlit run` process against the
// minimal dedicated harness in tests/playwright_streamlit/harness_app.py,
// so tests/playwright_streamlit/*.spec.js can inspect the real rendered
// Streamlit/browser DOM for the three Bryggeskole SVG visuals -- the
// exact gap the Playwright Critical Browser Gate (playwright.config.js)
// cannot cover, since that gate only ever serves web/ via a static file
// server and never starts Streamlit at all.
//
// Deliberately not merged into playwright.config.js / the Browser Gate
// workflow: a different app entirely (Streamlit, not the static web/
// site) needs a different webServer command and a much longer startup
// timeout -- keeping it a separate, narrowly-scoped config avoids
// broadening that gate's documented, already-reviewed scope.
'use strict';

const fs = require('fs');
const path = require('path');
const { defineConfig, devices } = require('@playwright/test');

const PORT = 8523;

// Same Python-executable resolution as playwright.config.js (issue
// #211): prefer a project venv if one exists, else fall back to the
// platform's canonical python3/py launcher.
function resolveServerPythonCommand() {
  if (process.platform === 'win32') {
    const venvPython = path.join('.venv', 'Scripts', 'python.exe');
    if (fs.existsSync(venvPython)) {
      return venvPython;
    }
    return 'py -3';
  }
  const venvPython = path.join('.venv', 'bin', 'python3');
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }
  return 'python3';
}

module.exports = defineConfig({
  testDir: './tests/playwright_streamlit',
  fullyParallel: true,
  workers: process.env.CI ? undefined : 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-streamlit' }]] : 'list',
  timeout: 30_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command:
      `${resolveServerPythonCommand()} -m streamlit run tests/playwright_streamlit/harness_app.py ` +
      `--server.headless true --server.port ${PORT} --server.address 127.0.0.1 ` +
      '--browser.gatherUsageStats false',
    url: `http://127.0.0.1:${PORT}/`,
    reuseExistingServer: !process.env.CI,
    // Streamlit's own startup (importing streamlit/plotly/altair etc.)
    // is slower than the plain static file server the root config uses.
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
