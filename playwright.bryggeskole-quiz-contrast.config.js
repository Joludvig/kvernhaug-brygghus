// Bryggeskole quiz answer-contrast real-runtime Playwright config (issue
// #401) -- separate, deliberately narrow config, same pattern as
// playwright.streamlit.config.js (#378/#379) and
// playwright.bryggeskole-grid.config.js (#394).
//
// Starts the real `streamlit run` process against the existing
// production-panel harness (tests/fixtures/streamlit_harness/
// bryggeskole_harness.py) so tests/playwright_streamlit/quiz-answer-
// contrast.spec.js can answer a real quiz question and measure the
// browser's own computed text/background colours of the locked answer
// options -- the gap the AppTest/CSS-string tests in
// tests/test_ui_bryggeskole_panel.py cannot cover (they passed while a
// real Chromium on a different Streamlit version still rendered the
// answers at rgba(49, 51, 63, 0.4), ~2.6:1).
//
// Answering a question writes mastery state, so the webServer always runs
// with KVERNHAUG_BRYGGESKOLE_STATE_DIR pointed at a fresh temp dir --
// never the real data/bryggeskole_mastery_state.json.
//
// KBH_STREAMLIT_PYTHON optionally overrides the Python interpreter, so the
// same spec can be run against a different installed Streamlit version
// (the #401 regression was Streamlit-version-dependent DOM).
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { defineConfig, devices } = require('@playwright/test');

const PORT = 8527;

// Same Python-executable resolution as playwright.config.js / issue #211.
function resolveServerPythonCommand() {
  if (process.env.KBH_STREAMLIT_PYTHON) {
    return `"${process.env.KBH_STREAMLIT_PYTHON}"`;
  }
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

const STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'kbh-quiz-contrast-state-'));

module.exports = defineConfig({
  testDir: './tests/playwright_streamlit',
  testMatch: '**/quiz-answer-contrast.spec.js',
  fullyParallel: true,
  workers: process.env.CI ? undefined : 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-bryggeskole-quiz-contrast' }]] : 'list',
  timeout: 45_000,
  use: {
    baseURL: `http://127.0.0.1:${PORT}`,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command:
      `${resolveServerPythonCommand()} -m streamlit run tests/fixtures/streamlit_harness/bryggeskole_harness.py ` +
      `--server.headless true --server.port ${PORT} --server.address 127.0.0.1 ` +
      '--browser.gatherUsageStats false',
    url: `http://127.0.0.1:${PORT}/`,
    // Never reuse: an already-running server on this port could be writing
    // mastery state somewhere other than the temp dir above.
    reuseExistingServer: false,
    env: { ...process.env, KVERNHAUG_BRYGGESKOLE_STATE_DIR: STATE_DIR },
    timeout: 60_000,
  },
  // Light and dark: Streamlit picks its default theme from the browser's
  // prefers-color-scheme, so this covers both built-in themes.
  projects: [
    {
      name: 'chromium-light',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 }, colorScheme: 'light' },
    },
    {
      name: 'chromium-dark',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 }, colorScheme: 'dark' },
    },
    {
      name: 'firefox-light',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1280, height: 900 }, colorScheme: 'light' },
    },
    {
      name: 'firefox-dark',
      use: { ...devices['Desktop Firefox'], viewport: { width: 1280, height: 900 }, colorScheme: 'dark' },
    },
  ],
});
