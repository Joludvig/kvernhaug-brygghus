// Shared Python/Streamlit runtime resolver for the Streamlit real-runtime
// Playwright configs (playwright.streamlit.config.js,
// playwright.bryggeskole-grid.config.js).
//
// Why: those configs used to fall back silently to `py -3` / `python3`
// when the worktree had no .venv. On the owner PC `py -3` resolved to
// Streamlit 1.57 -- below the repo minimum in requirements.txt -- whose
// radio DOM differs from supported versions, so a browser QA run reported
// a false #401 contrast failure. A browser test must never silently run
// the app on an unsupported Streamlit.
//
// Resolution order (first hit wins, then ALWAYS validated):
//   1. KBH_STREAMLIT_PYTHON (explicit interpreter path/command).
//   2. <repo>/.venv interpreter, if it exists. Worktrees conventionally
//      junction/symlink their .venv to the owner checkout's venv, so this
//      covers the shared venv without hardcoding any machine path.
//   3. CI only (process.env.CI): `python3` (POSIX) / `python` (win32) on
//      PATH -- the CI workflow sets up Python and runs
//      `pip install -r requirements.txt` before the Streamlit gates.
//   4. Otherwise: fail fast. Never an arbitrary system Python.
//
// Validation: the chosen interpreter is probed (executable, Python
// version, installed Streamlit version via importlib.metadata -- no
// streamlit import, no install) and must have Streamlit >= the minimum
// read from requirements.txt (`streamlit>=X`), the single source of truth.
//
// Not used by playwright.config.js: that config only serves web/ through
// `python -m http.server` and needs no Streamlit at all.
'use strict';

const childProcess = require('child_process');
const fs = require('fs');
const path = require('path');

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const ENV_VAR = 'KBH_STREAMLIT_PYTHON';

const PROBE_SCRIPT = [
  'import json, sys',
  'try:',
  '    from importlib.metadata import version, PackageNotFoundError',
  '    try:',
  '        st = version("streamlit")',
  '    except PackageNotFoundError:',
  '        st = None',
  'except Exception:',
  '    st = None',
  'print(json.dumps({"executable": sys.executable, "python": sys.version.split()[0], "streamlit": st}))',
].join('\n');

class StreamlitRuntimeError extends Error {}

function readMinStreamlitVersion(requirementsText) {
  const m = /^\s*streamlit\s*>=\s*([0-9]+(?:\.[0-9]+)*)/im.exec(requirementsText || '');
  if (!m) {
    throw new StreamlitRuntimeError(
      'Cannot determine the minimum Streamlit version: requirements.txt has no `streamlit>=X` line.',
    );
  }
  return m[1];
}

// Numeric release parts only ("1.60.0rc1" -> [1, 60, 0]).
function versionParts(v) {
  return String(v).split('.').map((p) => parseInt(p, 10)).filter((n) => !Number.isNaN(n));
}

function compareVersions(a, b) {
  const pa = versionParts(a);
  const pb = versionParts(b);
  for (let i = 0; i < Math.max(pa.length, pb.length); i += 1) {
    const d = (pa[i] || 0) - (pb[i] || 0);
    if (d !== 0) return d < 0 ? -1 : 1;
  }
  return 0;
}

function parseProbeOutput(stdout) {
  const line = String(stdout || '').trim().split(/\r?\n/).pop();
  let data;
  try {
    data = JSON.parse(line);
  } catch (e) {
    return null;
  }
  if (!data || typeof data.executable !== 'string' || !data.executable) return null;
  return { executable: data.executable, python: data.python || null, streamlit: data.streamlit || null };
}

function probeInterpreter(command) {
  try {
    const stdout = childProcess.execFileSync(command, ['-c', PROBE_SCRIPT], {
      encoding: 'utf8',
      timeout: 30_000,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    });
    return parseProbeOutput(stdout);
  } catch (e) {
    return null;
  }
}

function venvPython(repoRoot, platform) {
  return platform === 'win32'
    ? path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(repoRoot, '.venv', 'bin', 'python3');
}

function pickCandidate({ env, platform, repoRoot, existsSync }) {
  if (env[ENV_VAR]) {
    return { command: env[ENV_VAR], source: ENV_VAR };
  }
  const venv = venvPython(repoRoot, platform);
  if (existsSync(venv)) {
    return { command: venv, source: '.venv' };
  }
  if (env.CI) {
    return { command: platform === 'win32' ? 'python' : 'python3', source: 'CI PATH' };
  }
  return null;
}

const HINT = `Set ${ENV_VAR} to a Python with the repo requirements installed, or use the repository .venv.`;

// Returns the shell-ready interpreter command for a webServer command line,
// or throws StreamlitRuntimeError with an actionable message.
function resolveStreamlitPythonCommand(options = {}) {
  const env = options.env || process.env;
  const platform = options.platform || process.platform;
  const repoRoot = options.repoRoot || REPO_ROOT;
  const existsSync = options.existsSync || fs.existsSync;
  const probe = options.probe || probeInterpreter;
  const requirementsText = options.requirementsText !== undefined
    ? options.requirementsText
    : fs.readFileSync(path.join(repoRoot, 'requirements.txt'), 'utf8');
  const log = options.log || ((msg) => console.log(msg));

  const minVersion = readMinStreamlitVersion(requirementsText);
  const candidate = pickCandidate({ env, platform, repoRoot, existsSync });
  if (!candidate) {
    throw new StreamlitRuntimeError(
      `No Streamlit runtime: no ${ENV_VAR} and no ${path.relative(repoRoot, venvPython(repoRoot, platform))} in ${repoRoot}. `
      + `Refusing to fall back to system Python. ${HINT}`,
    );
  }

  const info = probe(candidate.command);
  if (!info) {
    throw new StreamlitRuntimeError(
      `Cannot run Python interpreter from ${candidate.source}: ${candidate.command}. ${HINT}`,
    );
  }
  const where = `${info.executable} (Python ${info.python || '?'}, from ${candidate.source})`;
  if (!info.streamlit) {
    throw new StreamlitRuntimeError(
      `Streamlit is not installed in ${where}. Repository requires >=${minVersion}. ${HINT}`,
    );
  }
  if (compareVersions(info.streamlit, minVersion) < 0) {
    throw new StreamlitRuntimeError(
      `Unsupported Streamlit runtime: ${info.streamlit} in ${where}. Repository requires >=${minVersion}. ${HINT}`,
    );
  }

  // Playwright loads the config in the runner and again in every worker
  // (workers inherit env), so announce the runtime only once per run.
  if (!env.KBH_STREAMLIT_RUNTIME_ANNOUNCED) {
    log(`[streamlit-runtime] Streamlit ${info.streamlit} / Python ${info.python} -- ${info.executable} (from ${candidate.source})`);
    env.KBH_STREAMLIT_RUNTIME_ANNOUNCED = '1';
  }
  return `"${info.executable}"`;
}

module.exports = {
  ENV_VAR,
  StreamlitRuntimeError,
  compareVersions,
  parseProbeOutput,
  pickCandidate,
  probeInterpreter,
  readMinStreamlitVersion,
  resolveStreamlitPythonCommand,
};
