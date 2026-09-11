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

const fs = require('fs');
const path = require('path');
const { defineConfig, devices } = require('@playwright/test');

const PORT = 4173;

// Issue #211 -- resolve a Python executable that actually exists on the
// machine running the gate, instead of hardcoding `python3`. CI (Linux)
// always has `python3` on PATH (via actions/setup-python), so that path is
// unchanged. The owner's Windows PC has neither `python3` nor a bare
// `python` reliably on PATH, but does have (a) the project venv, when one
// has been created (`.venv\Scripts\python.exe`), and (b) the `py` launcher,
// which every python.org Windows installer registers and which this repo
// already treats as its canonical Windows Python invocation (see `py -3`
// throughout tests/*.py docstrings and .claude/rules/testing.md).
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
  testDir: './tests/playwright',
  fullyParallel: true,
  // Issue #211 -- against this harness's plain http.server, default
  // parallelism proved unstable off-CI (connection refused/timeouts on the
  // owner's Windows PC); `--workers=1` passed 116/116. CI's existing
  // default-parallel behavior is already proven green and stays untouched.
  workers: process.env.CI ? undefined : 1,
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
    command: `${resolveServerPythonCommand()} -m http.server ${PORT} --directory web --bind 127.0.0.1`,
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
