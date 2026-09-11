"""
Kvernhaug CI Test Gate -- regression tests for
.github/workflows/ci-tests.yml (Chief task: "IMPLEMENT CI TEST GATE").

Plain string-/regex-based inspection of the workflow SOURCE TEXT (not
executed YAML) -- stdlib-only, no PyYAML dependency, matching the existing
convention in tests/test_agent_bridge_permission_config.py. Proves the
gate actually wires up the four required suites and does not regress to
the broken `node tests/js/*.js` glob pattern (Node does not execute every
expanded filename as a separate program). Also proves the pip cache
(issue #221) is dependency-keyed from requirements.txt, and that the
PR-scoped concurrency group cancels stale same-PR runs without
cross-cancelling unrelated master push runs.

Run by the normal suite (`python -m unittest discover -s tests`).
"""
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "ci-tests.yml")

_REQUIRED_NODE_COMMANDS = (
    "node tests/js/test_calculation_golden_vectors.js",
    "node tests/js/test_kbhrecipe_contract.js",
    "node tests/js/test_kbhbrew_contract.js",
)


def _read_workflow():
    with open(_WORKFLOW, encoding="utf-8") as f:
        return f.read()


class TestCiTestGateWorkflowExists(unittest.TestCase):
    def test_workflow_file_exists(self):
        self.assertTrue(
            os.path.isfile(_WORKFLOW),
            "Expected .github/workflows/ci-tests.yml to exist.",
        )


class TestCiTestGateTriggers(unittest.TestCase):
    def test_runs_on_pull_request(self):
        tekst = _read_workflow()
        self.assertRegex(tekst, r"pull_request\s*:")

    def test_runs_on_push_to_master(self):
        tekst = _read_workflow()
        push_block = re.search(r"push:\n(.*?)(?=\n\S|\Z)", tekst, re.DOTALL)
        self.assertIsNotNone(push_block, "Expected a `push:` trigger block.")
        self.assertIn("master", push_block.group(1))


class TestCiTestGateInvokesPythonSuite(unittest.TestCase):
    def test_full_python_suite_is_invoked(self):
        tekst = _read_workflow()
        self.assertIn("python -m unittest discover -s tests", tekst)


class TestCiTestGateInvokesAllThreeNodeSuites(unittest.TestCase):
    def test_each_required_node_contract_command_present(self):
        tekst = _read_workflow()
        for cmd in _REQUIRED_NODE_COMMANDS:
            self.assertIn(
                cmd, tekst,
                f"Expected the exact command {cmd!r} in the workflow -- "
                "each Node contract suite must be its own explicit command.",
            )

    def test_does_not_regress_to_broken_glob_pattern(self):
        # Only inspect non-comment lines: the workflow's own header comment
        # names the broken glob pattern to explain why it is avoided, which
        # must not itself trip this guard.
        run_lines = "\n".join(
            line for line in _read_workflow().splitlines()
            if not line.strip().startswith("#")
        )
        self.assertNotIn(
            "tests/js/*.js", run_lines,
            "node tests/js/*.js does not execute every expanded filename "
            "as a separate program -- each suite must be an explicit "
            "`node <file>` command instead.",
        )


class TestCiTestGatePipCache(unittest.TestCase):
    def test_setup_python_step_enables_pip_cache(self):
        tekst = _read_workflow()
        setup_python_block = re.search(
            r"uses:\s*actions/setup-python@v5\n(.*?)(?=\n\s*- name:|\Z)",
            tekst, re.DOTALL,
        )
        self.assertIsNotNone(
            setup_python_block, "Expected an actions/setup-python@v5 step.",
        )
        block = setup_python_block.group(1)
        self.assertRegex(
            block, r'cache:\s*"pip"',
            "Expected the setup-python step to enable the built-in pip cache.",
        )
        self.assertRegex(
            block, r"cache-dependency-path:\s*requirements\.txt",
            "Expected the pip cache to be keyed from requirements.txt.",
        )

    def test_no_extra_cache_action_introduced(self):
        tekst = _read_workflow()
        self.assertNotIn(
            "actions/cache@", tekst,
            "Expected the existing actions/setup-python@v5 pip cache to be "
            "used, not a separate actions/cache action/framework.",
        )


class TestCiTestGateConcurrency(unittest.TestCase):
    def test_concurrency_block_present(self):
        tekst = _read_workflow()
        self.assertIn("\nconcurrency:\n", tekst)

    def test_group_is_pr_scoped_with_push_scoped_fallback(self):
        tekst = _read_workflow()
        self.assertIn(
            "group: ci-test-gate-${{ github.event.pull_request.number "
            "|| github.sha }}",
            tekst,
        )

    def test_cancel_in_progress_enabled(self):
        tekst = _read_workflow()
        self.assertRegex(tekst, r"cancel-in-progress:\s*true")

    def test_push_fallback_key_is_sha_not_ref(self):
        # A `github.ref` fallback would be the same value (refs/heads/master)
        # for every push to master, which would cross-cancel unrelated
        # master runs -- the issue's own required invariant. `github.sha` is
        # unique per push, so the cancel-in-progress group never collides
        # across separate master pushes.
        tekst = _read_workflow()
        concurrency_block = re.search(
            r"^concurrency:\n(.*?)(?=\n\S)", tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(concurrency_block)
        self.assertNotIn("github.ref", concurrency_block.group(1))


class TestCiTestGateDoesNotTouchAgentBridge(unittest.TestCase):
    def test_agent_bridge_workflow_is_a_separate_untouched_file(self):
        agent_bridge = os.path.join(
            _REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml"
        )
        self.assertTrue(os.path.isfile(agent_bridge))
        self.assertNotEqual(os.path.abspath(agent_bridge), os.path.abspath(_WORKFLOW))


if __name__ == "__main__":
    unittest.main()
