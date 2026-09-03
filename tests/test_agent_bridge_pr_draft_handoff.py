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
  5. `decide`-CLI-en skriver alltid exit 0 (aldri fail-closed) -- selve
     Draft-FORSØKET er et vekke-signal-hjelpemiddel, ikke i seg selv en
     forutsetning for at Claude skal få lov til å jobbe,
  6. workflow-kildeteksten gater de nye stegene korrekt (kun etter
     "Capture pre-run PR state", før "Run Claude Code"; den faktiske
     mutasjonen skjer kun når `set_draft == 'true'`), og introduserer
     ingen ny Claude-trigger-overflate eller merge/master-push,
  7. (Chief-review-fiks, PR #45) `verifiser_draft` -- den nye FAIL-CLOSED
     funksjonen som gjør Draft til en VERIFISERT forutsetning for
     `status:changes-requested`: status:ready og en bekreftet allerede-
     Draft PR er fortsatt ikke-alarmerende, men manglende/tvetydig PR,
     feil PR-identitet, feil/manglende hode (runde 2), eller en PR som
     IKKE er Draft ved fersk refetch gir en REELL avvisning,
  8. `verify`-CLI-modusen returnerer exit 1 på en reell avvisning og
     exit 0 ellers -- og workflowen kobler denne inn slik at "Run Claude
     Code" strukturelt ikke kan kjøre når verifiseringen feiler (fail-
     closed step-kjede, dedikert feil-rapport-steg, generisk feil-steg
     ekskluderer denne saken eksplisitt).

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import json
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


class TestVerifiserDraft(unittest.TestCase):
    """Chief-review-fiks (PR #45): FAIL-CLOSED motstykke til vurder_draft
    -- gjør Draft til en VERIFISERT forutsetning for
    status:changes-requested, på et FERSKT refetch (aldri pre-run-data)."""

    _HEAD = "a" * 40
    _ANNET_HEAD = "b" * 40
    _PR_DRAFT = {"number": 45, "state": "OPEN", "baseRefName": "master",
                 "headRefName": "agent/issue-45", "isDraft": True,
                 "headRefOid": _HEAD}
    _PR_READY = {"number": 45, "state": "OPEN", "baseRefName": "master",
                 "headRefName": "agent/issue-45", "isDraft": False,
                 "headRefOid": _HEAD}

    def test_7a_status_ready_er_alltid_verifisert_uten_pr(self):
        verified, pr_nummer, _ = _PDH.verifiser_draft(
            trigger_label="status:ready", before_pr_number=None,
            before_head_sha=None, prs=[], branch_navn="agent/issue-45",
        )
        self.assertTrue(verified)
        self.assertIsNone(pr_nummer)

    def test_7b_manglende_before_pr_number_avvises(self):
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number=None,
            before_head_sha=self._HEAD,
            prs=[self._PR_DRAFT], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)
        self.assertIsNone(pr_nummer)
        self.assertIn("Kan ikke verifisere".lower(), begrunnelse.lower())

    def test_7c_ingen_apen_pr_pa_branch_avvises(self):
        verified, *_rest = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD, prs=[], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)

    def test_7d_tvetydig_flere_apne_prer_avvises(self):
        annen_pr = dict(self._PR_DRAFT, number=99)
        verified, *_rest = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD,
            prs=[self._PR_DRAFT, annen_pr], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)

    def test_7e_pr_nummer_endret_seg_avvises(self):
        # Samme identitets-sjekk som pr_ready_handoff.py krever for AC#4:
        # et HEAD/PR-nummer som ikke lenger matcher pre-run-fangsten er
        # ikke bevist samme PR.
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="99",
            before_head_sha=self._HEAD,
            prs=[self._PR_DRAFT], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)
        self.assertEqual(pr_nummer, 45)
        self.assertIn("identitet", begrunnelse.lower())

    def test_7f_pr_er_ikke_draft_ved_refetch_avvises(self):
        # Nøyaktig blokkeren fra Chief-reviewen: en Ready (ikke-Draft) PR
        # kan aldri bestå verifiseringen for en changes-requested-runde.
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD,
            prs=[self._PR_READY], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)
        self.assertEqual(pr_nummer, 45)
        self.assertIn("IKKE Draft", begrunnelse)

    def test_7g_bekreftet_draft_godkjennes(self):
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD,
            prs=[self._PR_DRAFT], branch_navn="agent/issue-45",
        )
        self.assertTrue(verified)
        self.assertEqual(pr_nummer, 45)
        self.assertIn("Draft", begrunnelse)

    def test_7h_feil_branch_avvises(self):
        verified, *_rest = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD,
            prs=[self._PR_DRAFT], branch_navn="agent/issue-999",
        )
        self.assertFalse(verified)

    # ─── (runde 2) fersk head MÅ matche before_head_sha eksakt ────────────

    def test_7i_manglende_before_head_sha_avvises(self):
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=None,
            prs=[self._PR_DRAFT], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)
        self.assertIsNone(pr_nummer)
        self.assertIn("kan ikke verifisere", begrunnelse.lower())

    def test_7j_hode_endret_seg_avvises_selv_om_draft_og_identitet_stemmer(self):
        # Selve blokkeren fra runde-2-reviewen: en PR som fortsatt er
        # samme nummer OG Draft, men hvor headRefOid har beveget seg siden
        # pre-run-fangsten, må IKKE bestå -- det er ikke bevist at
        # forutsetningen gjelder DETTE hodet.
        pr_med_nytt_hode = dict(self._PR_DRAFT, headRefOid=self._ANNET_HEAD)
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD,
            prs=[pr_med_nytt_hode], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)
        self.assertEqual(pr_nummer, 45)
        self.assertIn("hode", begrunnelse.lower())

    def test_7k_manglende_headrefoid_i_fersk_refetch_avvises(self):
        pr_uten_head = dict(self._PR_DRAFT)
        del pr_uten_head["headRefOid"]
        verified, pr_nummer, begrunnelse = _PDH.verifiser_draft(
            trigger_label="status:changes-requested", before_pr_number="45",
            before_head_sha=self._HEAD,
            prs=[pr_uten_head], branch_navn="agent/issue-45",
        )
        self.assertFalse(verified)
        self.assertEqual(pr_nummer, 45)
        self.assertIn("hode", begrunnelse.lower())


class TestCliAlltidExitNull(unittest.TestCase):
    """`decide`-modus (default): samme filosofi som chief_retry_signal.py
    -- et avvist/skippet Draft-FORSØK skal ALDRI feile prosessen alene --
    kun exit 0. (Chief-review-fiks, PR #45: den fail-closed forutsetnings-
    HÅNDHEVINGEN skjer i `verify`-modus, se TestCliVerifyFailClosed under,
    ikke her.)"""

    def _kjor_cli(self, env_extra, argv_ekstra=()):
        env = dict(os.environ)
        env.update(env_extra)
        return subprocess.run(
            [sys.executable, _SCRIPT, *argv_ekstra], input="", capture_output=True, text=True, env=env,
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

    def test_5d_eksplisitt_decide_argument_gir_samme_resultat_som_default(self):
        uten_arg = self._kjor_cli({
            "TRIGGER_LABEL": "status:changes-requested", "BEFORE_PR_NUMBER": "45",
            "BEFORE_HEAD_SHA": "a" * 40, "BEFORE_PR_IS_DRAFT": "false",
        })
        med_arg = self._kjor_cli({
            "TRIGGER_LABEL": "status:changes-requested", "BEFORE_PR_NUMBER": "45",
            "BEFORE_HEAD_SHA": "a" * 40, "BEFORE_PR_IS_DRAFT": "false",
        }, argv_ekstra=("decide",))
        self.assertEqual(uten_arg.returncode, med_arg.returncode)
        self.assertEqual(uten_arg.stdout, med_arg.stdout)


class TestCliVerifyFailClosed(unittest.TestCase):
    """Chief-review-fiks (PR #45): `verify`-CLI-modusen -- fail-closed,
    samme exit-kode-kontrakt som chief_ready_signal.py/pr_ready_handoff.py
    (exit 1 på reell avvisning, exit 0 ellers), slik at det tilhørende
    workflow-steget selv feiler og "Run Claude Code" strukturelt aldri
    kjører (se TestWorkflowKildetekst under for kjedingen)."""

    def _kjor_verify(self, data):
        return subprocess.run(
            [sys.executable, _SCRIPT, "verify"],
            input=json.dumps(data), capture_output=True, text=True,
        )

    def test_8a_status_ready_gir_exit_0(self):
        res = self._kjor_verify({"trigger_label": "status:ready"})
        self.assertEqual(res.returncode, 0)
        self.assertIn("draft_verified=true", res.stdout)

    def test_8b_bekreftet_draft_gir_exit_0(self):
        res = self._kjor_verify({
            "trigger_label": "status:changes-requested", "before_pr_number": "45",
            "before_head_sha": "a" * 40, "branch": "agent/issue-45",
            "prs": [{"number": 45, "state": "OPEN", "baseRefName": "master",
                      "headRefName": "agent/issue-45", "isDraft": True,
                      "headRefOid": "a" * 40}],
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("draft_verified=true", res.stdout)
        self.assertIn("pr_number=45", res.stdout)

    def test_8c_ikke_draft_gir_exit_1(self):
        res = self._kjor_verify({
            "trigger_label": "status:changes-requested", "before_pr_number": "45",
            "before_head_sha": "a" * 40, "branch": "agent/issue-45",
            "prs": [{"number": 45, "state": "OPEN", "baseRefName": "master",
                      "headRefName": "agent/issue-45", "isDraft": False,
                      "headRefOid": "a" * 40}],
        })
        self.assertEqual(res.returncode, 1)
        self.assertIn("draft_verified=false", res.stdout)

    def test_8d_manglende_pr_gir_exit_1(self):
        res = self._kjor_verify({
            "trigger_label": "status:changes-requested", "before_pr_number": "45",
            "before_head_sha": "a" * 40, "branch": "agent/issue-45", "prs": [],
        })
        self.assertEqual(res.returncode, 1)
        self.assertIn("draft_verified=false", res.stdout)

    def test_8g_hode_endret_seg_gir_exit_1(self):
        # (runde 2) CLI-nivå-motstykke til test_7j: en push mellom pre-run-
        # fangst og fersk refetch må feile lukket her også.
        res = self._kjor_verify({
            "trigger_label": "status:changes-requested", "before_pr_number": "45",
            "before_head_sha": "a" * 40, "branch": "agent/issue-45",
            "prs": [{"number": 45, "state": "OPEN", "baseRefName": "master",
                      "headRefName": "agent/issue-45", "isDraft": True,
                      "headRefOid": "b" * 40}],
        })
        self.assertEqual(res.returncode, 1)
        self.assertIn("draft_verified=false", res.stdout)

    def test_8h_manglende_before_head_sha_gir_exit_1(self):
        res = self._kjor_verify({
            "trigger_label": "status:changes-requested", "before_pr_number": "45",
            "branch": "agent/issue-45",
            "prs": [{"number": 45, "state": "OPEN", "baseRefName": "master",
                      "headRefName": "agent/issue-45", "isDraft": True,
                      "headRefOid": "a" * 40}],
        })
        self.assertEqual(res.returncode, 1)
        self.assertIn("draft_verified=false", res.stdout)

    def test_8e_tom_stdin_gir_exit_0_status_ready_default(self):
        # Manglende trigger_label i tom/ugyldig JSON tolkes som "" -- ikke
        # status:changes-requested -- så ingen forutsetning gjelder.
        res = subprocess.run(
            [sys.executable, _SCRIPT, "verify"], input="", capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("draft_verified=true", res.stdout)

    def test_8f_ugyldig_json_gir_exit_0_uten_krasj(self):
        res = subprocess.run(
            [sys.executable, _SCRIPT, "verify"], input="{ikke gyldig json",
            capture_output=True, text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("draft_verified=true", res.stdout)


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
        pos_state = self.tekst.index("Refetch live state for Draft verification (issue #44)")
        pos_verify = self.tekst.index("Verify PR Draft state before Claude run (issue #44)")
        pos_claude = self.tekst.index("- name: Run Claude Code")
        self.assertLess(pos_before, pos_decide)
        self.assertLess(pos_decide, pos_convert)
        self.assertLess(pos_convert, pos_state)
        self.assertLess(pos_state, pos_verify)
        self.assertLess(pos_verify, pos_claude)

    def test_6i_decide_steget_bruker_decide_modus(self):
        steg = self._finn_steg("Decide PR Draft handoff (issue #44)")
        self.assertIn("pr_draft_handoff.py decide", steg)

    def test_6j_verify_steget_bruker_verify_modus_og_ferskt_refetch(self):
        steg = self._finn_steg("Verify PR Draft state before Claude run (issue #44)")
        self.assertIn("pr_draft_handoff.py verify", steg)

    def test_6k_refetch_steget_henter_isdraft_live_ikke_fra_capture(self):
        steg = self._finn_steg("Refetch live state for Draft verification (issue #44)")
        self.assertIn("isDraft", steg)
        self.assertIn("gh pr list", steg)

    def test_6o_refetch_steget_videresender_before_head_sha(self):
        # (Chief-review-fiks, PR #45, runde 2): verify-modus kan ikke
        # håndheve hode-matchen uten at dette steget faktisk sender
        # before_head_sha (fra "Capture pre-run PR state") inn i JSON-en
        # verify-CLI-en leser fra stdin.
        steg = self._finn_steg("Refetch live state for Draft verification (issue #44)")
        self.assertIn("before_head_sha", steg)
        self.assertIn("steps.before.outputs.before_head_sha", steg)

    def test_6l_run_claude_code_har_ingen_egen_success_override(self):
        # "Run Claude Code" sitt `if:` inneholder ingen success()/failure()/
        # always()-kall, så GitHub Actions prepender implisitt success() --
        # et feilende "Verify PR Draft state"-steg stopper jobben FØR dette
        # steget i det hele tatt evalueres. Denne testen dokumenterer/låser
        # den forutsetningen i kildeteksten.
        steg = self._finn_steg("Run Claude Code")
        if_linje = next(linje for linje in steg.splitlines() if linje.strip().startswith("if:"))
        for funksjon in ("success(", "failure(", "always(", "cancelled("):
            self.assertNotIn(funksjon, if_linje)

    def test_6m_dedikert_feilrapport_for_draft_verify(self):
        steg = self._finn_steg("Report Draft-verification failure — Claude did not run this round (issue #44)")
        self.assertIn("steps.draft_verify.outcome == 'failure'", steg)
        self.assertIn("failure()", steg)

    def test_6n_generisk_feilsteg_ekskluderer_draft_verify_avvisning(self):
        steg = self._finn_steg("Report failure — leave at status:working for manual follow-up")
        self.assertIn("steps.draft_verify.outcome != 'failure'", steg)

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
