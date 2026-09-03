"""
Kvernhaug Agent Bridge -- regresjonstester for PR Draft-handoffen
(.github/scripts/pr_draft_handoff.py, issue #44).

BAKGRUNN: issue #44 erstatter den upålitelige kommentar-baserte
retry-vekkingen (chief_retry_signal.py, issue #40 -- fjernet av denne
issuen) med en PR-tilstandsovergang (Draft -> Ready for review). Denne
modulen dekker første halvdel: konvertere PR-en til Draft idet en
status:changes-requested-runde starter. Se moduldocstringen i
pr_draft_handoff.py og AGENT_WORKFLOW.md ("PR Draft/Ready-for-review
lifecycle wake mechanism") for hele resonnementet.

Testene dekker:
  1. kun status:changes-requested konverterer til Draft -- status:ready
     (og enhver annen/tom trigger-etikett) er alltid et no-op,
  2. manglende pre-run PR-tilstand (ingen PR fantes før kjøringen) er et
     no-op, ikke en feil,
  3. en allerede-Draft PR er et idempotent no-op,
  4. en gyldig changes-requested-handoff mot en Ready (ikke-Draft) PR
     godkjennes,
  5. CLI-en skriver alltid exit 0 (aldri fail-closed) -- Draft-
     konvertering er et vekke-signal-hjelpemiddel, ikke en forutsetning
     for at Claude skal få lov til å jobbe,
  6. workflow-kildeteksten gater de nye stegene korrekt (kun etter
     "Capture pre-run PR state", før "Run Claude Code"; den faktiske
     mutasjonen skjer kun når `set_draft == 'true'`), og introduserer
     ingen ny Claude-trigger-overflate eller merge/master-push.

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import os
import re
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "pr_draft_handoff.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _last_modul(sti, navn):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_PDH = _last_modul(_SCRIPT, "pr_draft_handoff")


class TestVurderDraft(unittest.TestCase):
    # ─── 1: kun status:changes-requested konverterer ─────────────────────

    def test_1a_status_ready_er_alltid_no_op(self):
        set_draft, pr_nummer, _ = _PDH.vurder_draft(
            trigger_label="status:ready", before_pr_number="45",
            before_head_sha="a" * 40, before_pr_is_draft="false",
        )
        self.assertFalse(set_draft)
        self.assertIsNone(pr_nummer)

    def test_1b_ukjent_eller_tom_trigger_er_no_op(self):
        set_draft, *_rest = _PDH.vurder_draft(
            trigger_label="", before_pr_number="45",
            before_head_sha="a" * 40, before_pr_is_draft="false",
        )
        self.assertFalse(set_draft)

    # ─── 2: manglende pre-run PR-tilstand er no-op ────────────────────────

    def test_2a_manglende_pr_nummer_er_no_op(self):
        set_draft, pr_nummer, _ = _PDH.vurder_draft(
            trigger_label="status:changes-requested", before_pr_number=None,
            before_head_sha="a" * 40, before_pr_is_draft="false",
        )
        self.assertFalse(set_draft)
        self.assertIsNone(pr_nummer)

    def test_2b_manglende_head_sha_er_no_op(self):
        set_draft, *_rest = _PDH.vurder_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=None, before_pr_is_draft="false",
        )
        self.assertFalse(set_draft)

    # ─── 3: allerede Draft er idempotent no-op ────────────────────────────

    def test_3_allerede_draft_er_no_op_men_returnerer_pr_nummer(self):
        set_draft, pr_nummer, begrunnelse = _PDH.vurder_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha="a" * 40, before_pr_is_draft="true",
        )
        self.assertFalse(set_draft)
        self.assertEqual(pr_nummer, "45")
        self.assertIn("allerede Draft", begrunnelse)

    def test_3b_is_draft_verdi_er_case_insensitiv(self):
        set_draft, *_rest = _PDH.vurder_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha="a" * 40, before_pr_is_draft="TRUE",
        )
        self.assertFalse(set_draft)

    # ─── 4: gyldig handoff godkjennes ──────────────────────────────────────

    def test_4_gyldig_changes_requested_handoff_godkjennes(self):
        set_draft, pr_nummer, begrunnelse = _PDH.vurder_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha="a" * 40, before_pr_is_draft="false",
        )
        self.assertTrue(set_draft)
        self.assertEqual(pr_nummer, "45")
        self.assertTrue(begrunnelse)

    def test_4b_tom_is_draft_streng_behandles_som_ikke_draft(self):
        set_draft, *_rest = _PDH.vurder_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha="a" * 40, before_pr_is_draft="",
        )
        self.assertTrue(set_draft)


class TestCliAlltidExitNull(unittest.TestCase):
    """Samme filosofi som chief_retry_signal.py: et avvist/skippet
    Draft-forsøk skal ALDRI feile prosessen -- kun exit 0."""

    def _kjor_cli(self, env_extra):
        env = dict(os.environ)
        env.update(env_extra)
        return subprocess.run(
            [sys.executable, _SCRIPT], input="", capture_output=True, text=True, env=env,
        )

    def test_5a_status_ready_gir_exit_0_og_set_draft_false(self):
        res = self._kjor_cli({
            "TRIGGER_LABEL": "status:ready", "BEFORE_PR_NUMBER": "45",
            "BEFORE_HEAD_SHA": "a" * 40, "BEFORE_PR_IS_DRAFT": "false",
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("set_draft=false", res.stdout)

    def test_5b_gyldig_handoff_gir_exit_0_og_set_draft_true_med_pr_number(self):
        res = self._kjor_cli({
            "TRIGGER_LABEL": "status:changes-requested", "BEFORE_PR_NUMBER": "45",
            "BEFORE_HEAD_SHA": "a" * 40, "BEFORE_PR_IS_DRAFT": "false",
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("set_draft=true", res.stdout)
        self.assertIn("pr_number=45", res.stdout)

    def test_5c_manglende_env_gir_exit_0_uten_krasj(self):
        env = {k: v for k, v in os.environ.items() if not k.startswith("BEFORE_") and k != "TRIGGER_LABEL"}
        res = subprocess.run([sys.executable, _SCRIPT], input="", capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("set_draft=false", res.stdout)


class TestWorkflowKildetekst(unittest.TestCase):
    """Inspiserer selve workflow-KILDETEKSTEN -- samme stdlib-only
    mønster som de andre agent-bridge-testene i denne suiten."""

    def setUp(self):
        with open(_WORKFLOW, encoding="utf-8") as f:
            self.tekst = f.read()

    def _finn_steg(self, navn):
        match = re.search(
            r"^([ \t]*)- name: " + re.escape(navn) + r"\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match, f"Fant ikke steget {navn!r} i workflowen.")
        return match.group(0)

    def test_6a_decide_steg_kommer_etter_capture_pre_run_og_for_run_claude_code(self):
        pos_before = self.tekst.index("Capture pre-run PR state")
        pos_decide = self.tekst.index("Decide PR Draft handoff (issue #44)")
        pos_convert = self.tekst.index("Convert PR to Draft for changes-requested handoff (issue #44)")
        pos_claude = self.tekst.index("- name: Run Claude Code")
        self.assertLess(pos_before, pos_decide)
        self.assertLess(pos_decide, pos_convert)
        self.assertLess(pos_convert, pos_claude)

    def test_6b_convert_steget_krever_set_draft_true(self):
        steg = self._finn_steg("Convert PR to Draft for changes-requested handoff (issue #44)")
        self.assertIn("steps.draft_decide.outputs.set_draft == 'true'", steg)

    def test_6c_stegene_er_gatet_pa_dry_run_og_secret(self):
        for navn in ("Decide PR Draft handoff (issue #44)", "Convert PR to Draft for changes-requested handoff (issue #44)"):
            steg = self._finn_steg(navn)
            self.assertIn("needs.guard.outputs.dry_run != 'true'", steg)
            self.assertIn("steps.secretcheck.outputs.missing != 'true'", steg)

    def test_6d_ingen_gh_pr_merge_eller_git_merge_i_de_nye_stegene(self):
        # Sjekker kun selve `run:`-kommandoene (ikke etterfølgende
        # kommentarblokker som hører til NESTE steg, som begge disse
        # nye stegene tilfeldigvis står rett før -- de nevner "gh pr
        # merge"/"git merge" i sitat-form som en del av V1.2s historikk).
        for navn in ("Decide PR Draft handoff (issue #44)", "Convert PR to Draft for changes-requested handoff (issue #44)"):
            steg = self._finn_steg(navn)
            run_bare_linjer = "\n".join(
                linje for linje in steg.splitlines() if not linje.strip().startswith("#")
            )
            for forbudt in ("gh pr merge", "git merge"):
                self.assertNotIn(forbudt, run_bare_linjer)

    def test_6e_pr_draft_handoff_kalles_aldri_av_claude_steget(self):
        run_claude_match = re.search(
            r"^([ \t]*)- name: Run Claude Code\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(run_claude_match)
        self.assertNotIn("pr_draft_handoff.py", run_claude_match.group(0))

    def test_6f_chief_retry_signal_er_fjernet(self):
        self.assertNotIn("chief_retry_signal.py", self.tekst)
        self.assertNotIn("Wait for Chief reaction window", self.tekst)

    def test_6g_ingen_ny_claude_trigger_overflate(self):
        on_block_match = re.search(r'^"on":\n(.*?)(?=^permissions:)', self.tekst, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(on_block_match)
        on_block = on_block_match.group(1)
        self.assertNotIn("issue_comment", on_block)
        self.assertNotIn("pull_request", on_block)

    def test_6h_capture_pre_run_steget_henter_isdraft(self):
        steg = self._finn_steg("Capture pre-run PR state (used by both trigger labels — see deliverable_guard.py)")
        self.assertIn("isDraft", steg)
        self.assertIn("before_pr_is_draft", steg)


class TestChiefRetrySignalFilerFjernet(unittest.TestCase):
    def test_scriptet_finnes_ikke_lenger(self):
        self.assertFalse(
            os.path.exists(os.path.join(_REPO_ROOT, ".github", "scripts", "chief_retry_signal.py"))
        )

    def test_testfilen_finnes_ikke_lenger(self):
        self.assertFalse(
            os.path.exists(os.path.join(_REPO_ROOT, "tests", "test_agent_bridge_chief_retry_signal.py"))
        )


if __name__ == "__main__":
    unittest.main()
