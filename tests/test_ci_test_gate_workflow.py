"""
Kvernhaug CI Test Gate -- regression tests for
.github/workflows/ci-tests.yml (Chief task: "IMPLEMENT CI TEST GATE").

Plain string-/regex-based inspection of the workflow SOURCE TEXT (not
executed YAML) -- stdlib-only, no PyYAML dependency, matching the existing
convention in tests/test_agent_bridge_permission_config.py. Proves the
gate actually wires up the four required suites and does not regress to
the broken `node tests/js/*.js` glob pattern (Node does not execute every
expanded filename as a separate program).

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


class TestCiTestGateDoesNotTouchAgentBridge(unittest.TestCase):
    def test_agent_bridge_workflow_is_a_separate_untouched_file(self):
        agent_bridge = os.path.join(
            _REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml"
        )
        self.assertTrue(os.path.isfile(agent_bridge))
        self.assertNotEqual(os.path.abspath(agent_bridge), os.path.abspath(_WORKFLOW))


if __name__ == "__main__":
    unittest.main()
