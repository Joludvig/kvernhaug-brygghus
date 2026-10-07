// Contract tests for tests/playwright_streamlit/streamlit_runtime.js -- the
// validated Python/Streamlit resolver used by the Streamlit real-runtime
// Playwright configs.
//
// Background: the configs used to fall back silently to `py -3` when a
// worktree had no .venv; on the owner PC that was Streamlit 1.57 (below
// requirements.txt's minimum), which renders a different radio DOM and
// produced a false #401 browser-QA failure.
//
// Interpreter probing is stubbed (no extra Python/Streamlit installs);
// the real probe is only exercised against interpreters that must FAIL.
// Plain Node (fs, path, assert) -- same pattern as the other tests/js files.
//
// Kjøres med:
//     node tests/js/test_streamlit_runtime_guard.js
//
// Exit code 0 = alle tester bestått. Exit code 1 = minst én feilet.

'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const rt = require(path.join(ROOT, 'tests', 'playwright_streamlit', 'streamlit_runtime.js'));

const REQS = 'streamlit>=1.59,<2.0\nplotly>=5.18\n';
const REPO = path.join(path.sep, 'repo');
const WIN_VENV = path.join(REPO, '.venv', 'Scripts', 'python.exe');
const POSIX_VENV = path.join(REPO, '.venv', 'bin', 'python3');

// Builds resolver options with a stub filesystem and a stub probe that
// records which interpreter command it was asked to inspect.
function oppsett({ env = {}, platform = 'win32', finnes = [], svar = {} } = {}) {
  const probet = [];
  const logg = [];
  const options = {
    env: { ...env },
    platform,
    repoRoot: REPO,
    requirementsText: REQS,
    existsSync: (p) => finnes.includes(p),
    probe: (cmd) => {
      probet.push(cmd);
      return Object.prototype.hasOwnProperty.call(svar, cmd) ? svar[cmd] : null;
    },
    log: (m) => logg.push(m),
  };
  return { options, probet, logg };
}

function rt159(exe = 'C:\\x\\python.exe') {
  return { executable: exe, python: '3.12.10', streamlit: '1.59.0' };
}

const tests = [];
function test(navn, fn) { tests.push([navn, fn]); }

// --- minimum version source --------------------------------------------

test('minimum is read from the real requirements.txt', () => {
  const tekst = fs.readFileSync(path.join(ROOT, 'requirements.txt'), 'utf8');
  const min = rt.readMinStreamlitVersion(tekst);
  assert.match(min, /^\d+\.\d+/);
  assert.ok(tekst.includes(`streamlit>=${min}`));
});

test('requirements without a streamlit>= line fails clearly', () => {
  assert.throws(() => rt.readMinStreamlitVersion('plotly>=5.18\n'), /minimum Streamlit version/);
  const { options } = oppsett({ finnes: [WIN_VENV], svar: { [WIN_VENV]: rt159() } });
  options.requirementsText = 'plotly>=5.18\n';
  assert.throws(() => rt.resolveStreamlitPythonCommand(options), rt.StreamlitRuntimeError);
});

test('version comparison is numeric and ignores pre-release suffixes', () => {
  assert.strictEqual(rt.compareVersions('1.59.2', '1.59'), 1);
  assert.strictEqual(rt.compareVersions('1.59.0', '1.59'), 0);
  assert.strictEqual(rt.compareVersions('1.57.0', '1.59'), -1);
  assert.strictEqual(rt.compareVersions('1.100.0', '1.59'), 1);
  assert.strictEqual(rt.compareVersions('1.60.0rc1', '1.59'), 1);
});

// --- resolution order --------------------------------------------------

test('explicit KBH_STREAMLIT_PYTHON wins over an existing .venv', () => {
  const eksplisitt = 'D:\\scratch\\venv159\\Scripts\\python.exe';
  const { options, probet } = oppsett({
    env: { KBH_STREAMLIT_PYTHON: eksplisitt },
    finnes: [WIN_VENV],
    svar: { [eksplisitt]: rt159(eksplisitt), [WIN_VENV]: rt159(WIN_VENV) },
  });
  assert.strictEqual(rt.resolveStreamlitPythonCommand(options), `"${eksplisitt}"`);
  assert.deepStrictEqual(probet, [eksplisitt]);
});

test('worktree .venv is used when present (win32 and POSIX)', () => {
  const win = oppsett({ finnes: [WIN_VENV], svar: { [WIN_VENV]: rt159(WIN_VENV) } });
  assert.strictEqual(rt.resolveStreamlitPythonCommand(win.options), `"${WIN_VENV}"`);
  const posix = oppsett({ platform: 'linux', finnes: [POSIX_VENV], svar: { [POSIX_VENV]: rt159(POSIX_VENV) } });
  assert.strictEqual(rt.resolveStreamlitPythonCommand(posix.options), `"${POSIX_VENV}"`);
});

test('missing .venv outside CI fails fast and never probes py -3 / system Python', () => {
  for (const platform of ['win32', 'linux']) {
    const { options, probet } = oppsett({
      platform,
      svar: { 'py -3': rt159(), py: rt159(), python: rt159(), python3: rt159() },
    });
    assert.throws(
      () => rt.resolveStreamlitPythonCommand(options),
      (e) => e instanceof rt.StreamlitRuntimeError
        && /Refusing to fall back to system Python/.test(e.message)
        && /KBH_STREAMLIT_PYTHON/.test(e.message)
        && /\.venv/.test(e.message),
    );
    assert.deepStrictEqual(probet, [], 'no interpreter may be probed without an explicit/venv/CI source');
  }
});

test('CI without .venv uses the workflow-installed PATH python, still validated', () => {
  const posix = oppsett({ platform: 'linux', env: { CI: 'true' }, svar: { python3: rt159('/opt/py/bin/python3') } });
  assert.strictEqual(rt.resolveStreamlitPythonCommand(posix.options), '"/opt/py/bin/python3"');
  assert.deepStrictEqual(posix.probet, ['python3']);

  const gammel = oppsett({ platform: 'linux', env: { CI: 'true' }, svar: { python3: { ...rt159(), streamlit: '1.57.0' } } });
  assert.throws(() => rt.resolveStreamlitPythonCommand(gammel.options), /Unsupported Streamlit runtime: 1\.57\.0/);
});

// --- version validation ------------------------------------------------

test('supported runtimes are accepted (1.59.0, 1.59.2, 1.61.1)', () => {
  for (const v of ['1.59.0', '1.59.2', '1.61.1']) {
    const { options } = oppsett({ finnes: [WIN_VENV], svar: { [WIN_VENV]: { ...rt159(WIN_VENV), streamlit: v } } });
    assert.strictEqual(rt.resolveStreamlitPythonCommand(options), `"${WIN_VENV}"`, v);
  }
});

test('Streamlit below the minimum is rejected with an actionable message', () => {
  const { options } = oppsett({ finnes: [WIN_VENV], svar: { [WIN_VENV]: { ...rt159(WIN_VENV), streamlit: '1.57.0' } } });
  assert.throws(
    () => rt.resolveStreamlitPythonCommand(options),
    (e) => e instanceof rt.StreamlitRuntimeError
      && e.message.startsWith('Unsupported Streamlit runtime: 1.57.0')
      && e.message.includes('Repository requires >=1.59')
      && e.message.includes(WIN_VENV)
      && e.message.includes('Python 3.12.10')
      && e.message.includes('Set KBH_STREAMLIT_PYTHON'),
  );
});

test('missing Streamlit is rejected', () => {
  const { options } = oppsett({ finnes: [WIN_VENV], svar: { [WIN_VENV]: { ...rt159(WIN_VENV), streamlit: null } } });
  assert.throws(
    () => rt.resolveStreamlitPythonCommand(options),
    /Streamlit is not installed in .*Repository requires >=1\.59\. Set KBH_STREAMLIT_PYTHON/,
  );
});

test('an interpreter that cannot be run is rejected', () => {
  const { options } = oppsett({ env: { KBH_STREAMLIT_PYTHON: 'C:\\nope\\python.exe' } });
  assert.throws(
    () => rt.resolveStreamlitPythonCommand(options),
    /Cannot run Python interpreter from KBH_STREAMLIT_PYTHON: C:\\nope\\python\.exe/,
  );
});

test('the runtime is announced once per run (workers inherit env)', () => {
  const { options, logg } = oppsett({ finnes: [WIN_VENV], svar: { [WIN_VENV]: rt159(WIN_VENV) } });
  rt.resolveStreamlitPythonCommand(options);
  rt.resolveStreamlitPythonCommand(options);
  assert.strictEqual(logg.length, 1);
  assert.match(logg[0], /Streamlit 1\.59\.0 \/ Python 3\.12\.10/);
});

// --- real probe (only interpreters that must fail) ---------------------

test('probe output parsing', () => {
  assert.deepStrictEqual(
    rt.parseProbeOutput('noise\n{"executable": "/p", "python": "3.12.1", "streamlit": "1.59.2"}\n'),
    { executable: '/p', python: '3.12.1', streamlit: '1.59.2' },
  );
  assert.strictEqual(rt.parseProbeOutput('{"executable": "/p", "python": "3.12.1", "streamlit": null}').streamlit, null);
  assert.strictEqual(rt.parseProbeOutput('Python was not found'), null);
  assert.strictEqual(rt.parseProbeOutput(''), null);
});

test('real probe returns null for a non-existent or non-Python executable', () => {
  assert.strictEqual(rt.probeInterpreter(path.join(ROOT, 'does-not-exist', 'python.exe')), null);
  // Node is a real executable but not Python: `node -c <script>` fails.
  assert.strictEqual(rt.probeInterpreter(process.execPath), null);
});

// --- configs actually use the guard ------------------------------------

test('every Streamlit runtime config uses the guard and has no silent fallback', () => {
  for (const navn of ['playwright.streamlit.config.js', 'playwright.bryggeskole-grid.config.js', 'playwright.bryggeskole-quiz-contrast.config.js',
    'playwright.bryggeskole-stage-progress.config.js', 'playwright.bryggeskole-stage-final.config.js']) {
    const tekst = fs.readFileSync(path.join(ROOT, navn), 'utf8');
    assert.ok(tekst.includes("require('./tests/playwright_streamlit/streamlit_runtime')"), navn);
    assert.match(tekst, /command:\s*\n?\s*`\$\{STREAMLIT_PYTHON\} -m streamlit run /, navn);
    assert.ok(!tekst.includes("'py -3'"), `${navn} must not fall back to py -3`);
    assert.ok(!/return\s+'python3?'/.test(tekst), `${navn} must not fall back to PATH python`);
  }
});

let feilet = 0;
for (const [navn, fn] of tests) {
  try {
    fn();
    console.log(`  ok  ${navn}`);
  } catch (e) {
    feilet += 1;
    console.log(`  FAIL ${navn}\n       ${e.stack.split('\n').slice(0, 3).join('\n       ')}`);
  }
}
console.log(`\n${tests.length - feilet}/${tests.length} passed`);
process.exit(feilet ? 1 : 0);
