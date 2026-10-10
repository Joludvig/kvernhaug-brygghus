"""
Tests for scripts/ci/classify_pr_changes.py -- the CI fast-path classifier.

The fast path may only be chosen when every changed file is an active
Bryggeskole pilot quiz JSON. Everything else, and every doubtful case, must
choose FULL CI.

Run with:
    python3 -m unittest tests.test_ci_quiz_fast_path
"""
import importlib.util
import os
import tempfile
import unittest
from unittest import mock

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPEC = importlib.util.spec_from_file_location(
    "classify_pr_changes", os.path.join(_ROOT, "scripts", "ci", "classify_pr_changes.py")
)
cls = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(cls)

_FERM = "bryggeskole/data/pilot_fermentation_temperature.json"
_MASH = "bryggeskole/data/pilot_mashing_fundamentals.json"


def _mode(files, event="pull_request"):
    return cls.classify(event, files)[0]


class TestFastPathCases(unittest.TestCase):
    def test_a_single_pilot_json_is_quiz_content_only(self):
        self.assertEqual(_mode([_FERM]), cls.QUIZ_CONTENT_ONLY)

    def test_b_two_pilot_jsons_are_quiz_content_only(self):
        self.assertEqual(_mode([_FERM, _MASH]), cls.QUIZ_CONTENT_ONLY)

    def test_c_pilot_json_plus_python_is_full(self):
        self.assertEqual(_mode([_FERM, "bryggeskole/pilot_mashing.py"]), cls.FULL)

    def test_d_pilot_json_plus_test_is_full(self):
        self.assertEqual(_mode([_FERM, "tests/test_pilot_fermentation.py"]), cls.FULL)

    def test_e_fact_registry_is_full(self):
        self.assertEqual(_mode(["bryggeskole/data/course_fact_registry.json"]), cls.FULL)
        self.assertEqual(_mode([_FERM, "bryggeskole/data/course_fact_registry.json"]), cls.FULL)

    def test_stage_map_is_full(self):
        self.assertEqual(_mode(["bryggeskole/data/course_stage_map.json"]), cls.FULL)

    def test_f_workflow_file_is_full(self):
        self.assertEqual(_mode([".github/workflows/ci-tests.yml"]), cls.FULL)
        self.assertEqual(_mode([_FERM, ".github/workflows/playwright-browser-gate.yml"]), cls.FULL)

    def test_g_web_file_is_full(self):
        self.assertEqual(_mode(["web/index.html"]), cls.FULL)
        self.assertEqual(_mode([_FERM, "web/app.js"]), cls.FULL)

    def test_h_non_pull_request_events_are_full(self):
        self.assertEqual(_mode([_FERM], event="push"), cls.FULL)
        self.assertEqual(_mode([_FERM], event="workflow_dispatch"), cls.FULL)
        self.assertEqual(_mode([_FERM], event=""), cls.FULL)

    def test_i_empty_or_ambiguous_is_full(self):
        self.assertEqual(_mode([]), cls.FULL)
        self.assertEqual(_mode(["", "  "]), cls.FULL)
        self.assertEqual(_mode(["bryggeskole/data/unknown.json"]), cls.FULL)


class TestPathStrictness(unittest.TestCase):
    def test_near_misses_are_full(self):
        for path in (
            "bryggeskole/data/sub/pilot_x.json",
            "bryggeskole/data/pilot_x.json.bak",
            "bryggeskole/data/pilot_x.JSON",
            "bryggeskole/data/pilot_.json",
            "bryggeskole/data/xpilot_x.json",
            "bryggeskole/pilot_x.json",
            "other/bryggeskole/data/pilot_x.json",
            "bryggeskole/data/pilot_x.json/../course_fact_registry.json",
            "docs/development/BRYGGESKOLE_QUIZ_DESIGN_STANDARD_V1_1.md",
            "CLAUDE.md",
            "package.json",
            "requirements.txt",
        ):
            with self.subTest(path=path):
                self.assertEqual(_mode([path]), cls.FULL)

    def test_one_outside_file_among_many_pilot_files_is_full(self):
        self.assertEqual(_mode([_FERM, _MASH, "tests/js/test_kbhbrew_contract.js"]), cls.FULL)


class TestCliFailsClosed(unittest.TestCase):
    def _run(self, argv):
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_OUTPUT"}
        out = []
        with mock.patch.dict(os.environ, env, clear=True):
            with mock.patch("builtins.print", side_effect=lambda *a, **k: out.append(" ".join(map(str, a)))):
                cls.main(argv)
        return "\n".join(out)

    def test_push_event_chooses_full(self):
        self.assertIn("FULL CI", self._run(["--event", "push", "--base", "a", "--head", "b"]))

    def test_missing_shas_choose_full(self):
        self.assertIn("FULL CI", self._run(["--event", "pull_request"]))

    def test_git_failure_chooses_full(self):
        with mock.patch.object(cls, "changed_files", side_effect=RuntimeError("boom")):
            out = self._run(["--event", "pull_request", "--base", "a", "--head", "b"])
        self.assertIn("FULL CI", out)
        self.assertIn("boom", out)

    def test_quiz_only_diff_chooses_fast_path(self):
        with mock.patch.object(cls, "changed_files", return_value=[_FERM]):
            out = self._run(["--event", "pull_request", "--base", "a", "--head", "b"])
        self.assertIn("QUIZ_CONTENT_ONLY FAST PATH", out)

    def test_writes_mode_to_github_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "out.txt")
            with mock.patch.dict(os.environ, {"GITHUB_OUTPUT": path}):
                with mock.patch.object(cls, "changed_files", return_value=[_FERM, _MASH]):
                    with mock.patch("builtins.print"):
                        cls.main(["--event", "pull_request", "--base", "a", "--head", "b"])
            with open(path, encoding="utf-8") as fh:
                self.assertEqual(fh.read().strip(), "mode=QUIZ_CONTENT_ONLY")


if __name__ == "__main__":
    unittest.main()
