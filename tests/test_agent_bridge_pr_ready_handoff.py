"""
Kvernhaug Agent Bridge -- regresjonstester for PR Ready-for-review-
overgangen (.github/scripts/pr_ready_handoff.py, issue #44).

BAKGRUNN: se moduldocstringen i pr_ready_handoff.py og
AGENT_WORKFLOW.md ("PR Draft/Ready-for-review lifecycle wake mechanism")
for hele resonnementet bak hvorfor issue #44 erstatter den upålitelige
kommentar-baserte retry-vekkingen (chief_retry_signal.py, issue #40 --
fjernet av denne issuen) med en PR-tilstandsovergang.

Testene dekker akseptansekriterium 2 og 3 fra issue #44 direkte:
  1. LIVSSYKLUS_ETIKETTER/MARKER-kopiene drifter aldri fra de andre
     .github/scripts-modulenes,
  2. overgangen godkjennes når, og kun når, ALLE betingelser stemmer OG
     PR-en faktisk er Draft,
  3. runde 1-sikkerhet: en PR som allerede er Ready (ikke Draft) er et
     IKKE-alarmerende no-op (`already_ready=True`), aldri en feil,
  4. hver fail-closed avvisning fra AC#3 (stale head, feil branch/base,
     feil livssyklus-etikett, manglende markør, konflikt/duplikat-
     markør, eksisterende formell review for hoden) gir en REELL
     avvisning (`set_ready=False, already_ready=False`),
  5. CLI-ens exit-kode-kontrakt: set_ready/already_ready gir begge exit
     0, en reell avvisning gir exit 1 (samme kontrakt som
     chief_ready_signal.py),
  6. workflow-kildeteksten gater de nye stegene korrekt (etter den
     opprinnelige Chief-ready-markøren, kun ved steps.signal.outcome ==
     'success', mutasjonen skjer kun ved set_ready == 'true'), fjerner
     issue #40s retry-steg, og introduserer ingen ny Claude-trigger-
     overflate eller merge/master-push.

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "pr_ready_handoff.py")
_READY_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "chief_ready_signal.py")
_LIFECYCLE_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "lifecycle_labels.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _last_modul(sti, navn):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_PRH = _last_modul(_SCRIPT, "pr_ready_handoff")
_CREADY = _last_modul(_READY_SCRIPT, "chief_ready_signal")
_LL = _last_modul(_LIFECYCLE_SCRIPT, "lifecycle_labels")

_HEAD_A = "a" * 40
_HEAD_B = "b" * 40


def _pr(number=45, state="OPEN", base="master", head_branch="agent/issue-44", head_sha=_HEAD_A, is_draft=True):
    return {
        "number": number,
        "state": state,
        "baseRefName": base,
        "headRefName": head_branch,
        "headRefOid": head_sha,
        "isDraft": is_draft,
    }


def _review(head_sha=_HEAD_A, state="CHANGES_REQUESTED"):
    return {"commit": {"oid": head_sha}, "state": state}


class TestLivssyklusEtikettSync(unittest.TestCase):
    def test_duplisert_liste_er_identisk(self):
        self.assertEqual(_PRH.LIVSSYKLUS_ETIKETTER, _LL.LIVSSYKLUS_ETIKETTER)
        self.assertEqual(_PRH.LIVSSYKLUS_ETIKETTER, _CREADY.LIVSSYKLUS_ETIKETTER)


class TestMarkorKonstruksjonIdentiskMedOriginalen(unittest.TestCase):
    def test_marker_versjon_og_regex_matcher_originalen(self):
        self.assertEqual(_PRH.MARKER_VERSJON, _CREADY.MARKER_VERSJON)
        linje = _CREADY.bygg_marker(44, _HEAD_A)
        self.assertIsNotNone(_PRH.MARKER_LINJE_RE.match(linje))


class TestVurderReadyGodkjenner(unittest.TestCase):
    # ─── 2: godkjennes når, og kun når, ALT stemmer OG PR-en er Draft ────

    def test_godkjenner_nar_alt_stemmer(self):
        eksisterende = [_CREADY.bygg_marker(44, _HEAD_A)]
        set_ready, already_ready, pr_nummer, head_sha, begrunnelse = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["agent:claude", "area:infra", "status:review"],
            prs=[_pr(is_draft=True)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende,
            pr_reviews=[],
        )
        self.assertTrue(set_ready)
        self.assertFalse(already_ready)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertTrue(begrunnelse)


class TestRunde1Sikkerhet(unittest.TestCase):
    # ─── 3: PR allerede Ready er et IKKE-alarmerende no-op ────────────────

    def test_pr_allerede_ready_er_no_op_ikke_feil(self):
        eksisterende = [_CREADY.bygg_marker(44, _HEAD_A)]
        set_ready, already_ready, pr_nummer, head_sha, begrunnelse = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["status:review"],
            prs=[_pr(is_draft=False)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende,
            pr_reviews=[],
            trigger_label="status:ready",
        )
        self.assertFalse(set_ready)
        self.assertTrue(already_ready)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertTrue(begrunnelse)

    def test_pr_allerede_ready_uten_trigger_label_er_fortsatt_no_op(self):
        # Bakoverkompatibelt default (ingen trigger_label oppgitt) er
        # fortsatt den trygge grenen -- workflowen sender i praksis alltid
        # en av de to eksakte verdiene, men et manglende argument skal
        # ikke plutselig bli en fail-closed avvisning for eksisterende
        # kallere.
        eksisterende = [_CREADY.bygg_marker(44, _HEAD_A)]
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["status:review"],
            prs=[_pr(is_draft=False)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende,
            pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertTrue(already_ready)


class TestChangesRequestedReadyFailOpen(unittest.TestCase):
    """Chief-review-fiks (PR #45, runde 3): for status:changes-requested
    er "allerede Ready" IKKE unntaksfritt trygt -- kun bevist av en
    KBH_PR_READY_TRANSITION_DONE_V1-markør for nettopp dette hodet."""

    def test_changes_requested_allerede_ready_uten_bevis_avvises(self):
        # PR-en kan ha blitt eksternt/prematurt undraftet FØR dette
        # steget fikk kjøre -- ingen ready-transition-done-markør finnes,
        # så dette MÅ være en reell, fail-closed avvisning, ikke et
        # stille already_ready-no-op (den uteblitte re-review-vekkingen
        # issue #44 finnes for å forhindre).
        set_ready, already_ready, pr_nummer, head_sha, begrunnelse = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["status:review"],
            prs=[_pr(is_draft=False)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)],
            pr_reviews=[],
            trigger_label="status:changes-requested",
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertIn("TRANSITION_DONE", begrunnelse)

    def test_changes_requested_allerede_ready_med_bevist_markor_er_no_op(self):
        # Idempotent gjentatt kjøring: DENNE mekanismen har alt utført
        # overgangen for nettopp dette hodet tidligere (t.d. en re-kjøring
        # av "Decide PR ready-for-review transition"-steget) -- den
        # tidligere kjøringen postet KBH_PR_READY_TRANSITION_DONE_V1, så
        # dette er et bevist, trygt no-op.
        eksisterende = [
            _CREADY.bygg_marker(44, _HEAD_A),
            _PRH.bygg_ready_done_marker(44, _HEAD_A),
        ]
        set_ready, already_ready, pr_nummer, head_sha, begrunnelse = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["status:review"],
            prs=[_pr(is_draft=False)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende,
            pr_reviews=[],
            trigger_label="status:changes-requested",
        )
        self.assertFalse(set_ready)
        self.assertTrue(already_ready)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertTrue(begrunnelse)

    def test_changes_requested_ready_transition_done_markor_for_annet_hode_teller_ikke(self):
        # En ready-transition-done-markør for et ANNET (eldre) hode skal
        # ikke kunne bevise overgangen for DETTE hodet.
        eksisterende = [
            _CREADY.bygg_marker(44, _HEAD_A),
            _PRH.bygg_ready_done_marker(44, _HEAD_B),
        ]
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["status:review"],
            prs=[_pr(is_draft=False)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende,
            pr_reviews=[],
            trigger_label="status:changes-requested",
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_changes_requested_draft_pr_gar_via_vanlig_overgang_uendret(self):
        # Draft er fortsatt Draft ved dette ferske refetchet -- den
        # ordinære transition-veien er uendret av runde 3-fiksen.
        set_ready, already_ready, pr_nummer, head_sha, begrunnelse = _PRH.vurder_ready(
            issue_nummer=44,
            issue_labels=["status:review"],
            prs=[_pr(is_draft=True)],
            branch_navn="agent/issue-44",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)],
            pr_reviews=[],
            trigger_label="status:changes-requested",
        )
        self.assertTrue(set_ready)
        self.assertFalse(already_ready)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)


class TestByggReadyDoneMarker(unittest.TestCase):
    def test_marker_matcher_egen_regex(self):
        linje = _PRH.bygg_ready_done_marker(44, _HEAD_A)
        self.assertIsNotNone(_PRH.MARKER_READY_DONE_LINJE_RE.match(linje))

    def test_marker_skiller_seg_fra_chief_ready_markoren(self):
        linje = _PRH.bygg_ready_done_marker(44, _HEAD_A)
        self.assertIsNone(_PRH.MARKER_LINJE_RE.match(linje))
        chief_linje = _CREADY.bygg_marker(44, _HEAD_A)
        self.assertIsNone(_PRH.MARKER_READY_DONE_LINJE_RE.match(chief_linje))


class TestVurderReadyFailClosed(unittest.TestCase):
    # ─── 4: hver AC#3-avvisning gir en REELL avvisning ────────────────────

    def test_avviser_hvis_mangler_signalert_head(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=None,
            eksisterende_kommentarer=[], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_mangler_issue_nummer(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=None, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_feil_livssyklus_etikett(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["agent:claude", "status:changes-requested"],
            prs=[_pr()], branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_flere_livssyklus_etiketter_samtidig(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review", "status:approved"],
            prs=[_pr()], branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_ingen_apen_pr_pa_branchen(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_flere_kandidat_prer(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"],
            prs=[_pr(number=45), _pr(number=46)],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_pr_pa_feil_branch(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"],
            prs=[_pr(head_branch="some-other-branch")],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_pr_mot_annen_base_enn_master(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"],
            prs=[_pr(base="develop")],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_live_head_er_stale(self):
        # En nyere status:changes-requested-runde har allerede overtatt.
        set_ready, already_ready, pr_nummer, head_sha, _ = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"],
            prs=[_pr(head_sha=_HEAD_B)],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)
        self.assertEqual(head_sha, _HEAD_B)

    def test_avviser_hvis_null_markorer_manglende_markor(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[], pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_konflikt_duplikat_markor(self):
        eksisterende = [_CREADY.bygg_marker(44, _HEAD_A), _CREADY.bygg_marker(44, _HEAD_A)]
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende, pr_reviews=[],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_avviser_hvis_eksisterende_formell_review_for_hoden(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)],
            pr_reviews=[_review(head_sha=_HEAD_A, state="APPROVED")],
        )
        self.assertFalse(set_ready)
        self.assertFalse(already_ready)

    def test_ignorerer_review_for_annen_head(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)],
            pr_reviews=[_review(head_sha=_HEAD_B, state="CHANGES_REQUESTED")],
        )
        self.assertTrue(set_ready)

    def test_ignorerer_pending_review_uten_innsendt_tilstand(self):
        set_ready, already_ready, *_rest = _PRH.vurder_ready(
            issue_nummer=44, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-44", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CREADY.bygg_marker(44, _HEAD_A)],
            pr_reviews=[_review(head_sha=_HEAD_A, state="PENDING")],
        )
        self.assertTrue(set_ready)


class TestCliExitKode(unittest.TestCase):
    """Samme kontrakt som chief_ready_signal.py: set_ready/already_ready
    gir begge exit 0, en reell avvisning gir exit 1."""

    def _kjor_cli(self, stdin_data):
        return subprocess.run(
            [sys.executable, _SCRIPT], input=json.dumps(stdin_data), capture_output=True, text=True,
        )

    def test_reell_avvisning_gir_ikke_null_exit(self):
        res = self._kjor_cli({
            "issue_number": 44,
            "issue_labels": ["agent:claude", "status:working"],
            "prs": [_pr()],
            "branch": "agent/issue-44",
            "signaled_head_sha": _HEAD_A,
            "comments": [_CREADY.bygg_marker(44, _HEAD_A)],
            "reviews": [],
        })
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("set_ready=false", res.stdout)
        self.assertIn("already_ready=false", res.stdout)

    def test_allerede_ready_gir_null_exit(self):
        res = self._kjor_cli({
            "issue_number": 44,
            "issue_labels": ["status:review"],
            "prs": [_pr(is_draft=False)],
            "branch": "agent/issue-44",
            "signaled_head_sha": _HEAD_A,
            "comments": [_CREADY.bygg_marker(44, _HEAD_A)],
            "reviews": [],
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("set_ready=false", res.stdout)
        self.assertIn("already_ready=true", res.stdout)

    def test_gyldig_overgang_gir_null_exit_og_set_ready_true(self):
        res = self._kjor_cli({
            "issue_number": 44,
            "issue_labels": ["status:review"],
            "prs": [_pr(is_draft=True)],
            "branch": "agent/issue-44",
            "signaled_head_sha": _HEAD_A,
            "comments": [_CREADY.bygg_marker(44, _HEAD_A)],
            "reviews": [],
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("set_ready=true", res.stdout)
        self.assertIn(f"pr_number={45}", res.stdout)
        self.assertIn(f"head_sha={_HEAD_A}", res.stdout)

    def test_changes_requested_allerede_ready_uten_bevis_gir_ikke_null_exit(self):
        # CLI-nivå-motstykke til TestChangesRequestedReadyFailOpen: en
        # status:changes-requested-runde der PR-en allerede er Ready uten
        # noen ready-transition-done-markør MÅ feile lukket.
        res = self._kjor_cli({
            "issue_number": 44,
            "issue_labels": ["status:review"],
            "prs": [_pr(is_draft=False)],
            "branch": "agent/issue-44",
            "signaled_head_sha": _HEAD_A,
            "comments": [_CREADY.bygg_marker(44, _HEAD_A)],
            "reviews": [],
            "trigger_label": "status:changes-requested",
        })
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("set_ready=false", res.stdout)
        self.assertIn("already_ready=false", res.stdout)

    def test_changes_requested_allerede_ready_med_bevist_markor_gir_null_exit(self):
        res = self._kjor_cli({
            "issue_number": 44,
            "issue_labels": ["status:review"],
            "prs": [_pr(is_draft=False)],
            "branch": "agent/issue-44",
            "signaled_head_sha": _HEAD_A,
            "comments": [_CREADY.bygg_marker(44, _HEAD_A), _PRH.bygg_ready_done_marker(44, _HEAD_A)],
            "reviews": [],
            "trigger_label": "status:changes-requested",
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("set_ready=false", res.stdout)
        self.assertIn("already_ready=true", res.stdout)

    def test_gyldig_overgang_skriver_ready_done_markor_til_output_fil(self):
        # main() sitt valgfrie argv[1] -- samme mønster som
        # chief_ready_signal.py -- skal skrive den ferdige
        # ready-transition-done-markørteksten KUN når set_ready=true.
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "ready_done_marker.txt")
            res = subprocess.run(
                [sys.executable, _SCRIPT, output_path],
                input=json.dumps({
                    "issue_number": 44,
                    "issue_labels": ["status:review"],
                    "prs": [_pr(is_draft=True)],
                    "branch": "agent/issue-44",
                    "signaled_head_sha": _HEAD_A,
                    "comments": [_CREADY.bygg_marker(44, _HEAD_A)],
                    "reviews": [],
                    "trigger_label": "status:changes-requested",
                }),
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("set_ready=true", res.stdout)
            with open(output_path, encoding="utf-8") as f:
                innhold = f.read()
            self.assertEqual(innhold, _PRH.bygg_ready_done_marker(44, _HEAD_A))

    def test_already_ready_skriver_ikke_output_fil(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = os.path.join(tmp, "ready_done_marker.txt")
            res = subprocess.run(
                [sys.executable, _SCRIPT, output_path],
                input=json.dumps({
                    "issue_number": 44,
                    "issue_labels": ["status:review"],
                    "prs": [_pr(is_draft=False)],
                    "branch": "agent/issue-44",
                    "signaled_head_sha": _HEAD_A,
                    "comments": [_CREADY.bygg_marker(44, _HEAD_A)],
                    "reviews": [],
                    "trigger_label": "status:ready",
                }),
                capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("already_ready=true", res.stdout)
            self.assertFalse(os.path.exists(output_path))

    def test_manglende_stdin_data_gir_ikke_null_exit_uten_krasj(self):
        res = subprocess.run([sys.executable, _SCRIPT], input="", capture_output=True, text=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("set_ready=false", res.stdout)


class TestWorkflowKildetekst(unittest.TestCase):
    """Inspiserer selve workflow-KILDETEKSTEN, samme stdlib-only mønster
    som de andre agent-bridge-testene."""

    _NYE_STEG = (
        "Refetch live state for PR ready-for-review transition (issue #44)",
        "Decide PR ready-for-review transition (issue #44)",
        "Transition PR to Ready for review (issue #44)",
    )

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

    def test_stegene_er_gatet_pa_dry_run_og_leveranse_ok(self):
        for navn in self._NYE_STEG:
            steg = self._finn_steg(navn)
            self.assertIn("needs.guard.outputs.dry_run != 'true'", steg)
            self.assertIn("steps.deliverable.outputs.ok == 'true'", steg)

    def test_stegene_krever_signal_outcome_success(self):
        for navn in self._NYE_STEG:
            steg = self._finn_steg(navn)
            self.assertIn("steps.signal.outcome == 'success'", steg)

    def test_transition_steget_krever_set_ready_true(self):
        steg = self._finn_steg("Transition PR to Ready for review (issue #44)")
        self.assertIn("steps.ready_decide.outputs.set_ready == 'true'", steg)

    def test_stegene_kommer_etter_det_opprinnelige_signalet(self):
        pos_original_post = self.tekst.index("Post Chief-ready signal comment (issue #32 adapter)")
        for navn in self._NYE_STEG:
            self.assertLess(pos_original_post, self.tekst.index(navn))
        posisjoner = [self.tekst.index(navn) for navn in self._NYE_STEG]
        self.assertEqual(posisjoner, sorted(posisjoner))

    def test_ingen_gh_pr_merge_eller_git_merge_i_de_nye_stegene(self):
        for navn in self._NYE_STEG:
            steg = self._finn_steg(navn)
            for forbudt in ("gh pr merge", "git merge"):
                self.assertNotIn(forbudt, steg)

    def test_ingen_ny_claude_trigger_overflate(self):
        on_block_match = re.search(r'^"on":\n(.*?)(?=^permissions:)', self.tekst, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(on_block_match)
        on_block = on_block_match.group(1)
        self.assertNotIn("issue_comment", on_block)
        self.assertNotIn("pull_request", on_block)

    def test_pr_ready_handoff_kalles_aldri_av_claude_steget(self):
        run_claude_match = re.search(
            r"^([ \t]*)- name: Run Claude Code\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(run_claude_match)
        self.assertNotIn("pr_ready_handoff.py", run_claude_match.group(0))

    def test_issue_40_retry_steg_er_fjernet(self):
        for navn in (
            "Wait for Chief reaction window (issue #40 deterministic retry)",
            "Refetch live state for Chief-ready retry (issue #40)",
            "Decide Chief-ready retry signal (issue #40)",
            "Post Chief-ready retry signal comment (issue #40)",
        ):
            self.assertNotIn(navn, self.tekst)
        self.assertNotIn("sleep 900", self.tekst)

    def test_signal_emission_failure_steg_er_scoped_til_signal_outcome_failure(self):
        steg = self._finn_steg("Report Chief-ready signal emission failure — issue stays at status:review")
        self.assertIn("steps.signal.outcome == 'failure'", steg)

    def test_ready_transition_failure_steg_finnes_og_er_scoped_riktig(self):
        steg = self._finn_steg("Report PR ready-for-review transition failure — issue stays at status:review")
        self.assertIn("steps.promote.outcome == 'success'", steg)
        self.assertIn("steps.ready_decide.outcome == 'failure'", steg)
        self.assertIn("status:review", steg)

    # ─── PR #45 runde 3: trigger_label-viring + ready-transition-done- ────
    # ─── markør-postingen ──────────────────────────────────────────────────

    def test_refetch_steget_sender_trigger_label_til_scriptet(self):
        steg = self._finn_steg("Refetch live state for PR ready-for-review transition (issue #44)")
        self.assertIn('--arg trigger_label "$TRIGGER_LABEL"', steg)
        self.assertIn("trigger_label:$trigger_label", steg)

    def test_decide_steget_sender_output_fil_argument(self):
        steg = self._finn_steg("Decide PR ready-for-review transition (issue #44)")
        self.assertIn("pr_ready_handoff.py \"$RUNNER_TEMP/pr_ready_done_marker.txt\"", steg)

    def test_transition_steget_har_id(self):
        steg = self._finn_steg("Transition PR to Ready for review (issue #44)")
        self.assertIn("id: transition", steg)

    def test_ready_done_markor_postes_kun_etter_vellykket_transition(self):
        steg = self._finn_steg("Post PR ready-transition-done marker (issue #44)")
        self.assertIn("steps.ready_decide.outputs.set_ready == 'true'", steg)
        self.assertIn("steps.transition.outcome == 'success'", steg)
        self.assertIn("steps.signal.outcome == 'success'", steg)
        self.assertIn("steps.deliverable.outputs.ok == 'true'", steg)
        self.assertIn("needs.guard.outputs.dry_run != 'true'", steg)
        self.assertIn('gh pr comment "${{ steps.ready_decide.outputs.pr_number }}"', steg)
        self.assertIn("pr_ready_done_marker.txt", steg)
        for forbudt in ("gh pr merge", "git merge"):
            self.assertNotIn(forbudt, steg)

    def test_ready_done_markor_steget_kommer_etter_transition_steget(self):
        pos_transition = self.tekst.index("Transition PR to Ready for review (issue #44)")
        pos_marker_post = self.tekst.index("Post PR ready-transition-done marker (issue #44)")
        self.assertLess(pos_transition, pos_marker_post)


if __name__ == "__main__":
    unittest.main()
