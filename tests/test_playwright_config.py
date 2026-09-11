"""
Regression tests for playwright.config.js (issue #211: make the Playwright
Critical Browser Gate runnable on the owner Windows PC without a manually
prestarted server, and without destabilizing it off-CI).

Plain string-/regex-based inspection of the config SOURCE TEXT (not
executed JS -- this suite is Python/unittest, and the config is Node/
CommonJS), matching the existing convention in
tests/test_agent_bridge_permission_config.py and
tests/test_ci_test_gate_workflow.py. Proves:

- the webServer command no longer hardcodes a bare, unconditional
  `python3` -- it resolves an available Python executable, preferring the
  project venv, falling back to the repo's own documented Windows
  convention (`py -3`, see .claude/rules/testing.md) on win32 and to the
  original, still-proven-green `python3` on POSIX/CI;
- local (non-CI) concurrency is explicitly bounded to the value proven
  stable in the issue's own owner-PC evidence (`--workers=1`), while CI's
  already-green default-parallel behavior is left untouched;
- the required Chromium/Firefox x desktop/mobile matrix is unchanged.

Run by the normal suite (`py -3 -m unittest discover -s tests -b`).
"""
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CONFIG = os.path.join(_REPO_ROOT, "playwright.config.js")


def _read_config():
    with open(_CONFIG, encoding="utf-8") as f:
        return f.read()


class TestPlaywrightConfigExists(unittest.TestCase):
    def test_config_file_exists(self):
        self.assertTrue(
            os.path.isfile(_CONFIG),
            "Expected playwright.config.js to exist.",
        )


class TestServerPythonResolution(unittest.TestCase):
    def test_does_not_hardcode_bare_python3_command(self):
        tekst = _read_config()
        self.assertNotRegex(
            tekst,
            r"command:\s*`python3 -m http\.server",
            "webServer.command must not hardcode an unconditional "
            "`python3` -- it must resolve an available Python executable "
            "(see resolveServerPythonCommand).",
        )

    def test_resolver_function_defined_and_used_in_webserver_command(self):
        tekst = _read_config()
        self.assertIn("function resolveServerPythonCommand", tekst)
        self.assertRegex(
            tekst,
            r"command:\s*`\$\{resolveServerPythonCommand\(\)\}",
            "webServer.command must build its Python invocation from "
            "resolveServerPythonCommand().",
        )

    def test_windows_branch_prefers_project_venv(self):
        tekst = _read_config()
        self.assertIn("'win32'", tekst)
        self.assertIn("'Scripts'", tekst)
        self.assertIn("'python.exe'", tekst)

    def test_windows_branch_falls_back_to_repo_documented_py_launcher(self):
        # 'py -3' is this repo's own documented Windows Python convention
        # (see .claude/rules/testing.md, tests/*.py docstrings) -- not a
        # bare 'python', which is not reliably on PATH on the owner's PC
        # per the issue's own evidence.
        tekst = _read_config()
        self.assertIn("'py -3'", tekst)

    def test_posix_branch_still_prefers_venv_then_python3(self):
        tekst = _read_config()
        self.assertIn("'bin'", tekst)
        self.assertRegex(
            tekst,
            r"return\s+'python3';",
            "The POSIX/CI fallback must remain the exact, already-proven-"
            "green 'python3' invocation.",
        )


class TestLocalConcurrencyBounded(unittest.TestCase):
    def test_workers_bounded_off_ci_only(self):
        tekst = _read_config()
        self.assertRegex(
            tekst,
            r"workers:\s*process\.env\.CI\s*\?\s*undefined\s*:\s*1\s*,",
            "Local (non-CI) runs must be bounded to --workers=1, the "
            "value proven stable in the issue's own owner-PC evidence, "
            "while CI's already-green default concurrency stays untouched.",
        )


class TestMatrixUnchanged(unittest.TestCase):
    _REQUIRED_PROJECT_NAMES = (
        "chromium-desktop",
        "chromium-mobile",
        "firefox-desktop",
        "firefox-mobile",
    )

    def test_all_four_required_projects_present(self):
        tekst = _read_config()
        for name in self._REQUIRED_PROJECT_NAMES:
            self.assertIn(
                f"name: '{name}'", tekst,
                f"Expected the required project {name!r} to remain in "
                "the matrix -- this issue must not narrow browser/"
                "viewport coverage.",
            )

    def test_desktop_and_mobile_viewports_unchanged(self):
        tekst = _read_config()
        self.assertIn("width: 1280, height: 900", tekst)
        self.assertIn("width: 390, height: 844", tekst)

    def test_serves_from_web_directory_on_the_same_port(self):
        tekst = _read_config()
        self.assertIn("const PORT = 4173;", tekst)
        self.assertIn("--directory web", tekst)


if __name__ == "__main__":
    unittest.main()
