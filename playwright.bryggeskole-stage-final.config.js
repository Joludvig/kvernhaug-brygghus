// Bryggeskole stage UI final-matrix real-runtime Playwright config -- the
// stage UI browser matrix that WRITES learner history
// (stage-final-matrix.spec.js walks a lesson and answers its questions),
// isolated from every other browser spec.
//
// Its answers change what the overview shows (module status, stage counts,
// recommendations). On a shared server and state file, as in
// playwright.bryggeskole-grid.config.js before this config existed, they
// would leak into specs that assert exact progress text (the seeded
// stage-progress smoke), and with fullyParallel CI workers that is a race.
//
// Isolation:
// - its own port and its own webServer (never reused);
// - its own fresh temp KVERNHAUG_BRYGGESKOLE_STATE_DIR, never the checkout's
//   data/ directory and never shared with another config;
// - exactly one worker, in CI and locally: the matrix's own tests share this
//   one server and state file, so they always run one after another and
//   never write learner history concurrently. The spec is written for a
//   shared, growing history (it reads stage counts by pattern and may reopen
//   a finished session at its summary).
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { defineConfig, devices } = require('@playwright/test');
const { resolveStreamlitPythonCommand } = require('./tests/playwright_streamlit/streamlit_runtime');

const PORT = 8529;

// Same validated resolver as the other Streamlit runtime configs -- no
// silent `py -3` fallback (see streamlit_runtime.js).
const STREAMLIT_PYTHON = resolveStreamlitPythonCommand();

const STATE_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'kbh-stage-final-state-'));

module.exports = defineConfig({
  testDir: './tests/playwright_streamlit',
  testMatch: '**/stage-final-matrix.spec.js',
  // State-writing spec, one state file: serialized, never parallel workers.
  fullyParallel: false,
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [['list'], ['html', { open: 'never', outputFolder: 'playwright-report-bryggeskole-stage-final' }]] : 'list',
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
    // Never reuse: an already-running server on this port could be writing
    // learner state somewhere other than the temp dir above.
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
