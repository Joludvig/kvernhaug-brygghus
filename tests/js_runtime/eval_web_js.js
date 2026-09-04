// WEB PRI 5 (issue #51) -- minimal, dependency-free Node harness that loads
// one or more web/js/*.js files as real, executed browser <script> tags
// (script-mode `vm` context, NOT jsdom/npm) and evaluates one final JS
// expression against them. No npm install, no build step, no jsdom -- see
// web.md's "no npm dependency without explicit approval" rule and
// docs/development/AGENT_WORKFLOW.md.
//
// Invoked as: node eval_web_js.js <manifest.json>, where the manifest is
// { files: [absolute paths, loaded in order], prelude, presetLocalStorage,
//   uuidQueue, expr }.
//
// BLOCKED (Chief review, PR #53, on head 56dcab8): the only caller,
// tests/web_js_runtime.py's run_web_js(), invoked this file as a `node`
// subprocess from inside an allowed `python3 -m unittest ...` process --
// found to be a Bridge Bash-allowlist circumvention (`node` itself is not
// on --allowedTools; see docs/development/AGENT_WORKFLOW.md). run_web_js()
// now refuses to run, so this harness is currently unreferenced. Kept
// as-is (not deleted) as reference for a future, separately reviewed
// Bridge permission-model change; do not wire it back up without that.
//
// Prints exactly one line of JSON to stdout on success:
//   {"ok":true,"value":<result of evaluating manifest.expr>}
// and exits non-zero with a message on stderr on any failure (missing
// manifest, JS syntax/runtime error, non-JSON-serializable result, ...).
'use strict';

const fs = require('fs');
const vm = require('vm');
const nodeCrypto = require('crypto');

function buildLocalStorage(preset) {
  const store = new Map(Object.entries(preset || {}));
  return {
    getItem(key) {
      return store.has(String(key)) ? store.get(String(key)) : null;
    },
    setItem(key, value) {
      store.set(String(key), String(value));
    },
    removeItem(key) {
      store.delete(String(key));
    },
    clear() {
      store.clear();
    },
    key(index) {
      return Array.from(store.keys())[index] ?? null;
    },
    get length() {
      return store.size;
    },
  };
}

function buildCrypto(uuidQueue) {
  const queue = Array.isArray(uuidQueue) ? uuidQueue.slice() : [];
  return {
    randomUUID() {
      return queue.length > 0 ? queue.shift() : nodeCrypto.randomUUID();
    },
    getRandomValues(typedArray) {
      return nodeCrypto.webcrypto.getRandomValues(typedArray);
    },
  };
}

function main() {
  const manifestPath = process.argv[2];
  if (!manifestPath) {
    process.stderr.write('eval_web_js.js: missing manifest path argument\n');
    process.exit(2);
  }
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));

  const sandbox = {
    console,
    JSON,
    Math,
    Date,
    Array,
    Object,
    String,
    Number,
    Boolean,
    RegExp,
    Map,
    Set,
    Promise,
    Symbol,
    Error,
    TypeError,
    RangeError,
    isFinite,
    isNaN,
    parseFloat,
    parseInt,
    localStorage: buildLocalStorage(manifest.presetLocalStorage),
    crypto: buildCrypto(manifest.uuidQueue),
  };
  sandbox.window = sandbox;
  sandbox.globalThis = sandbox;
  const context = vm.createContext(sandbox);

  if (manifest.prelude) {
    vm.runInContext(manifest.prelude, context, { filename: '<prelude>' });
  }

  for (const file of manifest.files || []) {
    const source = fs.readFileSync(file, 'utf8');
    vm.runInContext(source, context, { filename: file });
  }

  const rawResult = vm.runInContext(manifest.expr, context, { filename: '<expr>' });
  const value = rawResult === undefined ? null : rawResult;
  process.stdout.write(JSON.stringify({ ok: true, value }));
}

try {
  main();
} catch (err) {
  process.stderr.write(String((err && err.stack) || err) + '\n');
  process.exit(1);
}
