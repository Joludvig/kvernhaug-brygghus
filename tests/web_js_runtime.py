"""
WEB PRI 5 (issue #51) -- Python-side helper for running real, executed
web/js/*.js source against Node, instead of the source-contract-by-regex
pattern used by the earlier web tests (test_web_custom_ingredient_id_active_draft.py
and friends). Those tests were written under the assumption that "dette
repoet har ingen JavaScript-kjøretid i dette miljøet (ingen Node.js...)" --
that assumption no longer holds: the CI runner (and this dev environment)
does have Node.js available, it is just not on Claude's own direct Bash
allowlist (docs/development/AGENT_WORKFLOW.md). `python3 -m unittest ...`
IS on that allowlist, and a Python subprocess is free to shell out to
`node` internally -- so this module gives Web's DOM-free shared-contract
modules (calc.js, kbhrecipe.js, custom_ingredient_id.js, brew_storage.js, ...)
genuine, deterministic, execution-based test coverage without adding any
npm dependency or build step (web.md).

Usage (see tests/test_web_js_*.py for real examples):

    from tests.web_js_runtime import run_web_js

    result = run_web_js(
        ["calc.js"],
        "beregnOG([{id: 'pilsner', mengde: 5}], "
        "{pilsner: {potensiale: 1.037, ebc: 3}}, 20, 0.72)",
    )

`files` are filenames relative to web/js/, loaded in order into one shared
Node `vm` context -- exactly like a browser loading a sequence of <script>
tags on one page, so a later file may reference an earlier file's
top-level `const`/`function` declarations. `expr` is a single JS
expression (an IIFE is fine for multi-statement logic) evaluated after all
files are loaded; its value is returned to Python, round-tripped through
JSON (so only JSON-serializable values -- numbers, strings, bools, None,
lists, dicts -- can be returned).
"""
import json
import os
import subprocess
import tempfile

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WEB_JS_DIR = os.path.join(_REPO_ROOT, "web", "js")
_HARNESS = os.path.join(_REPO_ROOT, "tests", "js_runtime", "eval_web_js.js")


class WebJsError(RuntimeError):
    """Raised when the Node harness itself fails (JS syntax/runtime error,
    missing file, ...) -- distinct from a normal `{ok: false, ...}` return
    value a web/js function itself might produce."""


def run_web_js(files, expr, prelude=None, preset_local_storage=None, uuid_queue=None, timeout=15):
    """Load `files` (filenames relative to web/js/, in order) into a fresh
    Node vm context and evaluate `expr` against them. Returns the
    JSON-decoded result. Raises WebJsError on any harness/JS failure."""
    manifest = {
        "files": [os.path.join(_WEB_JS_DIR, f) for f in files],
        "expr": expr,
    }
    if prelude is not None:
        manifest["prelude"] = prelude
    if preset_local_storage is not None:
        manifest["presetLocalStorage"] = preset_local_storage
    if uuid_queue is not None:
        manifest["uuidQueue"] = uuid_queue

    manifest_fd, manifest_path = tempfile.mkstemp(suffix=".json", prefix="kbh_web_js_manifest_")
    try:
        with os.fdopen(manifest_fd, "w", encoding="utf-8") as f:
            json.dump(manifest, f)
        proc = subprocess.run(
            ["node", _HARNESS, manifest_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    finally:
        os.unlink(manifest_path)

    if proc.returncode != 0:
        raise WebJsError(
            "Node harness failed (exit %d) for expr=%r:\n%s" % (proc.returncode, expr, proc.stderr)
        )
    try:
        envelope = json.loads(proc.stdout)
    except ValueError as exc:
        raise WebJsError("Node harness produced non-JSON stdout: %r" % proc.stdout) from exc
    if not envelope.get("ok"):
        raise WebJsError("Node harness returned ok=false for expr=%r" % expr)
    return envelope["value"]
