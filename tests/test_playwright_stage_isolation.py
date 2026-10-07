"""
Stage UI browser-test isolation: the Bryggeskole Streamlit runtime
Playwright configs must never share a web server or a learner-state
directory between specs that depend on, or write, learner history.

The stage UI progress smoke asserts exact progress text from a seeded
history. The final matrix answers questions. On one shared server and
state file -- the checkout's default data/bryggeskole_mastery_state.json,
because the grid config set no state dir -- the matrix's answers changed
the progress smoke's expected statuses, and with fullyParallel CI workers
that was a race. Nothing seeded the progress smoke's history either.

These tests pin the isolation:
- the source text of the three configs (like tests/test_playwright_config.py,
  config files are inspected as text, not executed);
- the package.json scripts and the CI steps that run them;
- the test-only seed helper, run against a temp dir.
Test infrastructure only: no product behaviour is involved.

    python -m unittest tests.test_playwright_stage_isolation -v
"""
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest import mock

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_GRID = "playwright.bryggeskole-grid.config.js"
_PROGRESS = "playwright.bryggeskole-stage-progress.config.js"
_FINAL = "playwright.bryggeskole-stage-final.config.js"
_QUIZ = "playwright.bryggeskole-quiz-contrast.config.js"
_HARNESS_CONFIGS = (_GRID, _PROGRESS, _FINAL, _QUIZ)

_PROGRESS_SPEC = "stage-progress-smoke.spec.js"
_FINAL_SPEC = "stage-final-matrix.spec.js"
_SEED = os.path.join("tests", "playwright_streamlit", "seed_stage_progress_state.py")


def _read(name):
    with open(os.path.join(_REPO_ROOT, name), encoding="utf-8") as fh:
        return fh.read()


def _port(text):
    match = re.search(r"const PORT = (\d+);", text)
    return int(match.group(1)) if match else None


class TestEveryHarnessServerHasItsOwnStateDir(unittest.TestCase):
    def test_each_config_points_its_server_at_a_fresh_temp_state_dir(self):
        prefixes = []
        for name in _HARNESS_CONFIGS:
            text = _read(name)
            with self.subTest(name):
                self.assertIn("bryggeskole_harness.py", text)
                self.assertIn("env: { ...process.env, KVERNHAUG_BRYGGESKOLE_STATE_DIR: STATE_DIR }", text)
                match = re.search(r"fs\.mkdtempSync\(path\.join\(os\.tmpdir\(\), '([a-z-]+)'\)\)", text)
                self.assertIsNotNone(match, f"{name}: the state dir must be a fresh mkdtemp dir")
                prefixes.append(match.group(1))
                self.assertIn("reuseExistingServer: false", text)
        self.assertEqual(len(prefixes), len(set(prefixes)), f"state-dir prefixes must differ: {prefixes}")

    def test_each_config_has_its_own_port(self):
        ports = {name: _port(_read(name)) for name in _HARNESS_CONFIGS}
        self.assertNotIn(None, ports.values(), ports)
        self.assertEqual(len(set(ports.values())), len(ports), ports)
        # ... and none collides with the SVG harness config or the static web gate.
        self.assertNotIn(_port(_read("playwright.streamlit.config.js")), ports.values())
        self.assertNotIn(_port(_read("playwright.config.js")), ports.values())

    def test_no_config_points_at_the_checkout_data_dir(self):
        for name in _HARNESS_CONFIGS:
            with self.subTest(name):
                self.assertNotRegex(_read(name), r"KVERNHAUG_BRYGGESKOLE_STATE_DIR:\s*['\"]data")


class TestStatefulStageSpecsRunAlone(unittest.TestCase):
    def test_grid_config_ignores_both_stateful_specs(self):
        text = _read(_GRID)
        match = re.search(r"testIgnore:\s*\[([^\]]*)\]", text)
        self.assertIsNotNone(match, "grid config must have a testIgnore list")
        self.assertIn(f"'**/{_PROGRESS_SPEC}'", match.group(1))
        self.assertIn(f"'**/{_FINAL_SPEC}'", match.group(1))

    def test_progress_and_final_configs_match_only_their_own_spec(self):
        self.assertIn(f"testMatch: '**/{_PROGRESS_SPEC}',", _read(_PROGRESS))
        self.assertIn(f"testMatch: '**/{_FINAL_SPEC}',", _read(_FINAL))
        for name in (_GRID, _QUIZ, "playwright.streamlit.config.js", "playwright.config.js"):
            with self.subTest(name):
                text = _read(name)
                ignored = re.search(r"testIgnore:\s*\[([^\]]*)\]", text)
                ignored = ignored.group(1) if ignored else ""
                for spec in (_PROGRESS_SPEC, _FINAL_SPEC):
                    if spec in text:
                        self.assertIn(spec, ignored, f"{name} may name {spec} only to ignore it")

    def test_progress_config_seeds_once_with_the_seed_helper(self):
        text = _read(_PROGRESS)
        self.assertIn("tests/playwright_streamlit/seed_stage_progress_state.py", text)
        self.assertIn("process.env[STATE_DIR_ENV] = dir;", text)
        self.assertIn("if (process.env[STATE_DIR_ENV]) {", text)

    def test_final_config_does_not_seed(self):
        self.assertNotIn("seed_stage_progress_state", _read(_FINAL))

    def test_state_writing_final_config_is_always_serialized(self):
        # The final matrix writes learner history into the config's single
        # state file, so its tests must never run on concurrent workers --
        # not in CI either (no `process.env.CI ? undefined : 1`).
        text = _read(_FINAL)
        self.assertEqual(re.findall(r"^\s*workers:.*$", text, re.M), ["  workers: 1,"])
        self.assertIn("  fullyParallel: false,", text)
        self.assertNotIn("fullyParallel: true", text)
        self.assertNotRegex(text, r"\bshard\b")
        # ... and nothing that runs it overrides the worker count.
        script = json.loads(_read("package.json"))["scripts"]["test:bryggeskole-stage-final-runtime"]
        self.assertNotIn("--workers", script)
        self.assertNotIn("-j", script.split())
        workflow = _read(os.path.join(".github", "workflows", "playwright-browser-gate.yml"))
        step = re.search(r"run: npm run test:bryggeskole-stage-final-runtime(.*)", workflow)
        self.assertEqual(step.group(1).strip(), "")
        self.assertNotIn("PLAYWRIGHT_WORKERS", workflow)

    def test_same_projects_as_the_grid_config(self):
        projects = lambda text: re.findall(r"name: '([a-z-]+)'", text)
        self.assertEqual(projects(_read(_PROGRESS)), projects(_read(_GRID)))
        self.assertEqual(projects(_read(_FINAL)), projects(_read(_GRID)))


class TestScriptsAndCi(unittest.TestCase):
    def test_package_scripts(self):
        scripts = json.loads(_read("package.json"))["scripts"]
        self.assertEqual(scripts["test:bryggeskole-stage-progress-runtime"],
                         f"playwright test --config={_PROGRESS} --pass-with-no-tests")
        self.assertEqual(scripts["test:bryggeskole-stage-final-runtime"],
                         f"playwright test --config={_FINAL} --pass-with-no-tests")

    def test_ci_runs_both_isolated_gates(self):
        workflow = _read(os.path.join(".github", "workflows", "playwright-browser-gate.yml"))
        self.assertIn("run: npm run test:bryggeskole-grid-runtime", workflow)
        self.assertIn("run: npm run test:bryggeskole-stage-progress-runtime", workflow)
        self.assertIn("run: npm run test:bryggeskole-stage-final-runtime", workflow)


class TestSeedHelper(unittest.TestCase):
    def _run_main(self, env):
        sys.path.insert(0, os.path.join(_REPO_ROOT, "tests", "playwright_streamlit"))
        try:
            import seed_stage_progress_state as seed
        finally:
            sys.path.pop(0)
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env, clear=False), redirect_stdout(out), redirect_stderr(err):
            if env.get("KVERNHAUG_BRYGGESKOLE_STATE_DIR") is None:
                os.environ.pop("KVERNHAUG_BRYGGESKOLE_STATE_DIR", None)
            code = seed.main()
        return code, out.getvalue(), err.getvalue()

    def test_refuses_without_a_state_dir(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KVERNHAUG_BRYGGESKOLE_STATE_DIR", None)
            code, _, err = self._run_main({})
        self.assertEqual(code, 2)
        self.assertIn("not set", err)

    def test_refuses_the_repository_data_dir(self):
        code, _, err = self._run_main({"KVERNHAUG_BRYGGESKOLE_STATE_DIR": os.path.join(_REPO_ROOT, "data")})
        self.assertEqual(code, 2)
        self.assertIn("data/", err)

    def test_refuses_an_existing_state_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "bryggeskole_mastery_state.json"), "w", encoding="utf-8") as fh:
                fh.write("{}")
            code, _, err = self._run_main({"KVERNHAUG_BRYGGESKOLE_STATE_DIR": tmp})
            self.assertEqual(code, 2)
            self.assertIn("already exists", err)
            with open(os.path.join(tmp, "bryggeskole_mastery_state.json"), encoding="utf-8") as fh:
                self.assertEqual(fh.read(), "{}")

    def test_seeds_the_known_history_into_the_temp_dir_only(self):
        from bryggeskole import course_stage
        from bryggeskole.mastery_store import read_mastery_state

        with tempfile.TemporaryDirectory() as tmp:
            code, out, _ = self._run_main({"KVERNHAUG_BRYGGESKOLE_STATE_DIR": tmp})
            self.assertEqual(code, 0)
            path = os.path.join(tmp, "bryggeskole_mastery_state.json")
            self.assertEqual(out.strip(), path)
            self.assertEqual(os.listdir(tmp), ["bryggeskole_mastery_state.json"])
            answered = read_mastery_state(path)["answered_questions"]

        stage_map = course_stage.load_stage_map()
        status = lambda module, stage: course_stage.module_stage_status(stage_map, module, stage, answered)
        self.assertEqual(status("raavarer", "foundation"), course_stage.STATUS_WORKED_THROUGH)
        self.assertEqual(status("gjaring", "foundation"), course_stage.STATUS_IN_PROGRESS)
        for module in course_stage.MODULE_ORDER:
            for stage in course_stage.STAGES:
                if (module, stage) in (("raavarer", "foundation"), ("gjaring", "foundation")):
                    continue
                with self.subTest(module=module, stage=stage):
                    self.assertIn(status(module, stage), (None, course_stage.STATUS_NOT_STARTED))
        self.assertFalse(course_stage.stage_worked_through(stage_map, "foundation", answered))

    def test_seed_is_deterministic(self):
        documents = []
        for _ in range(2):
            with tempfile.TemporaryDirectory() as tmp:
                self.assertEqual(self._run_main({"KVERNHAUG_BRYGGESKOLE_STATE_DIR": tmp})[0], 0)
                with open(os.path.join(tmp, "bryggeskole_mastery_state.json"), encoding="utf-8") as fh:
                    documents.append(fh.read())
        self.assertEqual(documents[0], documents[1])

    def test_runs_as_a_script_from_the_repo_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {**os.environ, "KVERNHAUG_BRYGGESKOLE_STATE_DIR": tmp}
            env.pop("PYTHONPATH", None)
            result = subprocess.run([sys.executable, _SEED], cwd=_REPO_ROOT, env=env,
                                    capture_output=True, text=True, timeout=120)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(os.path.exists(os.path.join(tmp, "bryggeskole_mastery_state.json")))


if __name__ == "__main__":
    unittest.main()
