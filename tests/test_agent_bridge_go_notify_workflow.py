"""
Kvernhaug Agent Bridge -- workflow-kildetekst-sjekker for GO/NO-GO-
varselet (.github/workflows/claude-agent-bridge.yml, issue #66).

Dekker det som IKKE kan bevises av de rene Python-enhetstestene alene
(go_notify_signal.py / approved_notify_guard.py): at de nye jobbene
faktisk er koblet inn i workflowen på en måte som (a) aldri utvider
Claude-trigger-overflaten eller `--allowedTools`, (b) aldri introduserer
`git merge`/`gh pr merge`, og (c) er uavhengig av (ikke en endring av)
den eksisterende `guard`/`execute`-stien.

Ren tekst-/strukturtest -- ingen GitHub-kall, ingen YAML-parser-
avhengighet (samme mønster som de andre `TestWorkflowKildetekst`-
sjekkene i denne suiten, f.eks. tests/test_agent_bridge_pr_ready_handoff.py).
"""
import os
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _les_workflow():
    with open(_WORKFLOW, encoding="utf-8") as f:
        return f.read()


class TestNyeJobberFinnes(unittest.TestCase):
    def setUp(self):
        self.kilde = _les_workflow()

    def test_notify_guard_jobb_finnes(self):
        self.assertIn("notify_guard:", self.kilde)

    def test_notify_jobb_finnes_og_avhenger_av_notify_guard(self):
        self.assertIn("notify:", self.kilde)
        self.assertIn("needs: notify_guard", self.kilde)

    def test_notify_jobb_gates_pa_proceed(self):
        self.assertIn("needs.notify_guard.outputs.proceed == 'true'", self.kilde)

    def test_approved_notify_guard_script_kalles(self):
        self.assertIn(".github/scripts/approved_notify_guard.py", self.kilde)

    def test_go_notify_signal_script_kalles(self):
        self.assertIn(".github/scripts/go_notify_signal.py", self.kilde)


class TestIngenNyClaudeTriggerOverflate(unittest.TestCase):
    def setUp(self):
        self.kilde = _les_workflow()

    def test_kun_en_run_claude_code_steg(self):
        self.assertEqual(self.kilde.count("uses: anthropics/claude-code-action@v1"), 1)

    def test_allowedtools_strengen_nevner_ikke_status_approved(self):
        start = self.kilde.index("--allowedTools")
        slutt = self.kilde.index("\n", start)
        allowed_tools_linje = self.kilde[start:slutt]
        self.assertNotIn("status:approved", allowed_tools_linje)

    def test_notify_jobbene_kaller_aldri_claude_code_action(self):
        notify_guard_start = self.kilde.index("notify_guard:")
        notify_seksjon = self.kilde[notify_guard_start:]
        self.assertNotIn("anthropics/claude-code-action", notify_seksjon)

    def test_ingen_write_edit_multiedit_lagt_til_i_notify_seksjonen(self):
        notify_guard_start = self.kilde.index("notify_guard:")
        notify_seksjon = self.kilde[notify_guard_start:]
        for uventet in ("Bash(Write", "Bash(Edit", "--permission-mode"):
            self.assertNotIn(uventet, notify_seksjon)


class TestIngenMergeIntrodusert(unittest.TestCase):
    """Scoped til den NYE notify-seksjonen -- resten av filen nevner
    bevisst `git merge`/`gh pr merge` i sine egne, pre-eksisterende
    kommentarer (forklarer HVORFOR de er utelatt fra --allowedTools),
    som ikke er noe denne issuen skal røre."""

    def setUp(self):
        self.kilde = _les_workflow()
        notify_guard_start = self.kilde.index("notify_guard:")
        self.notify_seksjon = self.kilde[notify_guard_start:]

    def test_ingen_git_merge_i_notify_seksjonen(self):
        self.assertNotIn("git merge", self.notify_seksjon)

    def test_ingen_gh_pr_merge_i_notify_seksjonen(self):
        self.assertNotIn("gh pr merge", self.notify_seksjon)

    def test_notify_seksjonen_muterer_aldri_labels(self):
        self.assertNotIn("--method PUT", self.notify_seksjon)
        self.assertNotIn("issues/$ISSUE/labels", self.notify_seksjon)


class TestNotifySeksjonenErUavhengigAvGuardExecute(unittest.TestCase):
    def setUp(self):
        self.kilde = _les_workflow()

    def test_notify_guard_avhenger_ikke_av_guard_eller_execute(self):
        notify_guard_start = self.kilde.index("notify_guard:")
        notify_slutt = self.kilde.index("notify:", notify_guard_start)
        notify_guard_seksjon = self.kilde[notify_guard_start:notify_slutt]
        self.assertNotIn("needs: guard", notify_guard_seksjon)
        self.assertNotIn("needs: execute", notify_guard_seksjon)

    def test_notify_guard_reagerer_kun_pa_issues_event(self):
        notify_guard_start = self.kilde.index("notify_guard:")
        notify_slutt = self.kilde.index("notify:", notify_guard_start)
        notify_guard_seksjon = self.kilde[notify_guard_start:notify_slutt]
        self.assertIn("github.event_name == 'issues'", notify_guard_seksjon)


if __name__ == "__main__":
    unittest.main()
