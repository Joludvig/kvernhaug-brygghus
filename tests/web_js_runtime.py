"""
WEB PRI 5 (issue #51) -- Python-side helper for running real, executed
web/js/*.js source against Node.

BLOCKED (Chief review, PR #53, on head 56dcab8): this module's original
implementation shelled out to `node` from inside an allowed
`python3 -m unittest ...` process. Chief's review found that a Bash-
allowlist circumvention -- `docs/development/AGENT_WORKFLOW.md` defines
the allowlist as the minimum explicit command set and states only listed
commands are allowed; tunneling `node` (not itself allowlisted) through an
allowed Python subprocess defeats that control rather than extending it.
`run_web_js` below therefore now refuses to run at all. Re-enabling it
requires a separate, explicitly reviewed Bridge permission-model change
(e.g. adding a scoped `node` rule to `--allowedTools`) -- not a Web-test
PR reintroducing the same subprocess call. See the PR #53 review thread
for the full required-change discussion.

Usage (see tests/test_web_js_*.py for real examples; all of them are
currently `@unittest.skip`-ped pending the permission-model change above):

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
import os

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WEB_JS_DIR = os.path.join(_REPO_ROOT, "web", "js")
_HARNESS = os.path.join(_REPO_ROOT, "tests", "js_runtime", "eval_web_js.js")

_BLOCKED_REASON = (
    "run_web_js() is blocked: it would shell out to `node`, which is not on "
    "the Claude Agent Bridge's --allowedTools list (docs/development/"
    "AGENT_WORKFLOW.md). Doing so from an allowed `python3 -m unittest ...` "
    "process was flagged by Chief review (PR #53) as a Bash-allowlist "
    "circumvention. Re-enabling this requires a separate, explicitly "
    "reviewed Bridge permission-model change -- see this module's docstring."
)


class WebJsError(RuntimeError):
    """Raised when the Node harness itself fails (JS syntax/runtime error,
    missing file, ...) -- distinct from a normal `{ok: false, ...}` return
    value a web/js function itself might produce."""


def run_web_js(files, expr, prelude=None, preset_local_storage=None, uuid_queue=None, timeout=15):
    """Blocked -- see module docstring and `_BLOCKED_REASON`. Raises
    unconditionally instead of shelling out to `node`."""
    raise WebJsError(_BLOCKED_REASON)
