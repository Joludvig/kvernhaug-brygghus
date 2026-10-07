// Bryggeskole stage UI progress real-runtime Playwright config -- the
// SEEDED, read-only stage UI browser check (stage-progress-smoke.spec.js),
// isolated from every other browser spec.
//
// That spec asserts exact learner-progress text (which modules are "not
// started", "in progress" or "worked through", and the per-stage module
// count), so it needs one known learner history and a web server that no
// other spec writes to. Before this config existed, it would have shared
// playwright.bryggeskole-grid.config.js's single server and the checkout's
// default mastery file with specs that answer questions, and nothing seeded
// the history it expects.
//
// Isolation:
// - its own port and its own webServer (never reused);
// - its own fresh temp KVERNHAUG_BRYGGESKOLE_STATE_DIR, seeded exactly once
//   in the main Playwright process by
//   tests/playwright_streamlit/seed_stage_progress_state.py (the production
//   mastery API; fail-closed, never the real data/ directory). Workers
//   re-load this config with the directory already in their environment,
//   so they neither create nor seed another one.
//
// The spec only reads state. Specs that answer questions run elsewhere
// (playwright.bryggeskole-stage-final.config.js, the grid config).
'use strict';

const childProcess = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { defineConfig, devices } = require('@playwright/test');
const { resolveStreamlitPythonCommand } = require('./tests/playwright_streamlit/streamlit_runtime');

const PORT = 8528;

// Same validated resolver as the other Streamlit runtime configs -- no
// silent `py -3` fallback (see streamlit_runtime.js).
const STREAMLIT_PYTHON = resolveStreamlitPythonCommand();

const STATE_DIR_ENV = 'KBH_PW_STAGE_PROGRESS_STATE_DIR';

function seededStateDir() {
  if (process.env[STATE_DIR_ENV]) {
    return process.env[STATE_DIR_ENV];
  }
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'kbh-stage-progress-state-'));
  childProcess.execSync(`${STREAMLIT_PYTHON} tests/playwright_streamlit/seed_stage_progress_state.py`, {
    cwd: __dirname,
    env: { ...process.env, KVERNHAUG_BRYGGESKOLE_STATE_DIR: dir },
    stdio: 'pipe',
  });
  process.env[STATE_DIR_ENV] = dir;
  return dir;
}

const STATE_DIR = seededStateDir();

module.exports = defineConfig({
  testDir: './tests/playwright_streamlit',
  testMatch: '**/stage-progress-smoke.spec.js',
  fullyParallel: true,
  workers: process.env.CI ? undefined : 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-bryggeskole-stage-progress' }]] : 'list',
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
    // Never reuse: an already-running server on this port could be reading
    // learner state from somewhere other than the seeded dir above.
    reuseExistingServer: false,
    env: { ...process.env, KVERNHAUG_BRYGGESKOLE_STATE_DIR: STATE_DIR },
    timeout: 60_000,
  },
  // Same projects as playwright.bryggeskole-grid.config.js.
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
