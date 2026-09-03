"""
Kvernhaug Agent Bridge -- regresjonstester for den deterministiske
Chief-ready retry-signalet (.github/scripts/chief_retry_signal.py,
issue #40).

BAKGRUNN: issue #40 fant, med konkret tidsstempel-bevis fra PR #39
(issue #38s reelle re-review-runde), at en gyldig, korrekt konstruert
`KBH_CHIEF_REVIEW_READY_V1`-markor likevel ikke alltid vekker den
native ChatGPT Work event-oppgaven ved rask retry. Se moduldocstringen
i chief_retry_signal.py og AGENT_WORKFLOW.md ("Deterministic Chief-ready
retry signal") for hele resonnementet.

Testene dekker det denne modulen faktisk skal bevise:
  1. retry-markoren er byte-identisk med chief_ready_signal.py sin
     markor-konstruksjon (samme format, samme versjon),
  2. LIVSSYKLUS_ETIKETTER-kopien her drifter aldri fra
     chief_ready_signal.py sin (eller fra lifecycle_labels.py sin),
  3. retry avvises (fail-closed, IKKE en feil) hvis issuen ikke lenger
     er eksklusivt status:review, hvis PR-en ikke lenger finnes/er apen
     pa riktig branch, hvis PR-ens live head har beveget seg videre,
     hvis markor-antallet ikke er noyaktig 1, eller hvis en formell
     review for hoden allerede finnes,
  4. retry godkjennes nar, og kun nar, ALLE betingelser stemmer,
  5. CLI-en skriver alltid exit 0 (aldri fail-closed exit 1, i motsetning
     til chief_ready_signal.py -- se modulens "IKKE-ALARMERENDE VED NEI"),
  6. workflow-kildeteksten faktisk gater de fire nye stegene korrekt
     (dry-run, leveranse-PASS, kommer etter det opprinnelige signalet,
     retry-post krever ogsa retry_signal.outputs.post), og introduserer
     ingen ny Claude-trigger-overflate eller merge/master-push.

Ren stdlib-test, ingen GitHub-kall, ingen `jq`-avhengighet -- kjøres av
den vanlige suiten (`py -3 -m unittest discover -s tests -b`).
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
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "chief_retry_signal.py")
_READY_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "chief_ready_signal.py")
_LIFECYCLE_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "lifecycle_labels.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _last_modul(sti, navn):
    """Samme lastemønster som test_agent_bridge_chief_ready_signal.py
    bruker for .github/scripts-moduler utenfor Python-pakkestrukturen."""
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_CRETRY = _last_modul(_SCRIPT, "chief_retry_signal")
_CREADY = _last_modul(_READY_SCRIPT, "chief_ready_signal")
_LL = _last_modul(_LIFECYCLE_SCRIPT, "lifecycle_labels")

_HEAD_A = "a" * 40
_HEAD_B = "b" * 40


def _pr(number=45, state="OPEN", base="master", head_branch="agent/issue-40", head_sha=_HEAD_A):
    return {
        "number": number,
        "state": state,
        "baseRefName": base,
        "headRefName": head_branch,
        "headRefOid": head_sha,
    }


def _review(head_sha=_HEAD_A, state="CHANGES_REQUESTED"):
    return {"commit": {"oid": head_sha}, "state": state}


class TestLivssyklusEtikettSync(unittest.TestCase):
    def test_duplisert_liste_er_identisk_med_lifecycle_labels_og_ready_signal(self):
        self.assertEqual(_CRETRY.LIVSSYKLUS_ETIKETTER, _LL.LIVSSYKLUS_ETIKETTER)
        self.assertEqual(_CRETRY.LIVSSYKLUS_ETIKETTER, _CREADY.LIVSSYKLUS_ETIKETTER)


class TestMarkorKonstruksjonIdentiskMedOriginalen(unittest.TestCase):
    # ─── 1: retry-markoren er byte-identisk med den opprinnelige ────────

    def test_1_marker_er_identisk_med_chief_ready_signal(self):
        self.assertEqual(_CRETRY.MARKER_VERSJON, _CREADY.MARKER_VERSJON)
        self.assertEqual(_CRETRY.bygg_marker(40, _HEAD_A), _CREADY.bygg_marker(40, _HEAD_A))

    def test_1b_retry_kommentar_inneholder_markor_som_egen_linje(self):
        kommentar = _CRETRY.bygg_retry_kommentar(40, 45, _HEAD_A)
        self.assertIn(_CRETRY.bygg_marker(40, _HEAD_A), kommentar.splitlines())

    def test_1c_retry_kommentar_inneholder_ingen_hemmeligheter(self):
        kommentar = _CRETRY.bygg_retry_kommentar(40, 45, _HEAD_A)
        for uventet in ("token", "secret", "ANTHROPIC", "OAUTH", "api_key"):
            self.assertNotIn(uventet.lower(), kommentar.lower())


class TestMarkorLinjeRegexHardening(unittest.TestCase):
    """Chief review (PR #41): `MARKER_LINJE_RE` matchet tidligere ethvert
    Unicode-desimalsiffer (`\\d`) og tillot ledende nuller i issue-delen,
    sa et nesten-treff kunne normalisere til samme tall via `int(...)` i
    `_tell_markorer` og feilaktig lofte markor-antallet fra 1 til 2 --
    noe som ville avvist det eneste retry-forsoket. Disse testene
    beviser at slike nesten-treff aldri telles, verken direkte mot
    regexen eller gjennom `vurder_retry` sin ende-til-ende-beslutning."""

    def test_2a_regex_avviser_alenestaende_null(self):
        linje = f"{_CRETRY.MARKER_VERSJON} issue=0 head={_HEAD_A}"
        self.assertIsNone(_CRETRY.MARKER_LINJE_RE.match(linje))

    def test_2b_regex_avviser_ledende_null(self):
        linje = f"{_CRETRY.MARKER_VERSJON} issue=040 head={_HEAD_A}"
        self.assertIsNone(_CRETRY.MARKER_LINJE_RE.match(linje))

    def test_2c_regex_avviser_unicode_siffer(self):
        # "٤٠" er Arabic-Indic-sifre for 40 -- \d matcher disse, men
        # de er ikke gyldige ASCII-sifre i markor-grammatikken.
        linje = f"{_CRETRY.MARKER_VERSJON} issue=٤٠ head={_HEAD_A}"
        self.assertIsNone(_CRETRY.MARKER_LINJE_RE.match(linje))

    def test_2d_regex_godtar_gyldig_ascii_tall(self):
        linje = _CRETRY.bygg_marker(40, _HEAD_A)
        m = _CRETRY.MARKER_LINJE_RE.match(linje)
        self.assertIsNotNone(m)
        self.assertEqual(m.group("issue"), "40")

    def test_2e_naerttreff_teller_ikke_i_tell_markorer(self):
        naerttreff = [
            f"{_CRETRY.MARKER_VERSJON} issue=040 head={_HEAD_A}",
            f"{_CRETRY.MARKER_VERSJON} issue=٤٠ head={_HEAD_A}",
        ]
        self.assertEqual(_CRETRY._tell_markorer(naerttreff, 40, _HEAD_A), 0)

    def test_2f_naerttreff_ved_siden_av_ekte_markor_blokkerer_ikke_retry(self):
        # Et nesten-treff til stede sammen med DEN ekte markoren skal
        # fortsatt telle som noyaktig 1 -- og dermed godkjenne retryen,
        # ikke avvise den slik det opprinnelige `\d+`-hullet ville gjort.
        eksisterende = [
            _CRETRY.bygg_marker(40, _HEAD_A),
            f"{_CRETRY.MARKER_VERSJON} issue=040 head={_HEAD_A}",
        ]
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende, pr_reviews=[],
        )
        self.assertTrue(post)


class TestVurderRetry(unittest.TestCase):
    # ─── 4: godkjennes nar, og kun nar, ALT stemmer ──────────────────────

    def test_4_godkjenner_nar_alt_stemmer(self):
        eksisterende = [_CRETRY.bygg_marker(40, _HEAD_A)]
        post, pr_nummer, head_sha, kommentar, begrunnelse = _CRETRY.vurder_retry(
            issue_nummer=40,
            issue_labels=["agent:claude", "area:infra", "status:review"],
            prs=[_pr()],
            branch_navn="agent/issue-40",
            signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende,
            pr_reviews=[],
        )
        self.assertTrue(post)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertIsNotNone(kommentar)
        self.assertIn(_CRETRY.bygg_marker(40, _HEAD_A), kommentar)
        self.assertTrue(begrunnelse)

    # ─── 3: fail-closed avvisninger, ingen av dem en feil/krasj ──────────

    def test_3a_avviser_hvis_mangler_signalert_head(self):
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=None,
            eksisterende_kommentarer=[], pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3b_avviser_hvis_issue_ikke_lenger_eksklusivt_status_review(self):
        eksisterende = [_CRETRY.bygg_marker(40, _HEAD_A)]
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["agent:claude", "status:changes-requested"],
            prs=[_pr()], branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende, pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3b2_avviser_hvis_flere_livssyklus_etiketter_samtidig(self):
        eksisterende = [_CRETRY.bygg_marker(40, _HEAD_A)]
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review", "status:approved"],
            prs=[_pr()], branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende, pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3c_avviser_hvis_ingen_apen_pr_pa_branchen(self):
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CRETRY.bygg_marker(40, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3d_avviser_hvis_flere_kandidat_prer(self):
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"],
            prs=[_pr(number=45), _pr(number=46)],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CRETRY.bygg_marker(40, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3e_avviser_hvis_live_head_har_beveget_seg_videre(self):
        # En nyere status:changes-requested-runde har allerede skjedd og
        # fatt sin egen ferske markor -- retry for den GAMLE hoden er
        # meningslos.
        post, pr_nummer, head_sha, kommentar, _ = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"],
            prs=[_pr(head_sha=_HEAD_B)],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CRETRY.bygg_marker(40, _HEAD_A)], pr_reviews=[],
        )
        self.assertFalse(post)
        self.assertIsNone(kommentar)
        self.assertEqual(head_sha, _HEAD_B)

    def test_3f_avviser_hvis_null_eksisterende_markorer(self):
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[], pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3g_avviser_hvis_retry_allerede_gjort_en_gang(self):
        # To forekomster av samme markor -- et tidligere retry-forsok
        # har allerede skjedd. Maks ett retry-forsok per hode.
        eksisterende = [_CRETRY.bygg_marker(40, _HEAD_A), _CRETRY.bygg_retry_kommentar(40, 45, _HEAD_A)]
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=eksisterende, pr_reviews=[],
        )
        self.assertFalse(post)

    def test_3h_avviser_hvis_review_allerede_finnes_for_hoden(self):
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CRETRY.bygg_marker(40, _HEAD_A)],
            pr_reviews=[_review(head_sha=_HEAD_A, state="APPROVED")],
        )
        self.assertFalse(post)

    def test_3i_ignorerer_review_for_annen_head(self):
        # En review for en TIDLIGERE hode (f.eks. runde 1s
        # CHANGES_REQUESTED) skal ikke blokkere en retry for DENNE hoden.
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CRETRY.bygg_marker(40, _HEAD_A)],
            pr_reviews=[_review(head_sha=_HEAD_B, state="CHANGES_REQUESTED")],
        )
        self.assertTrue(post)

    def test_3j_ignorerer_pending_review_uten_innsendt_tilstand(self):
        # En PENDING (ikke innsendt) review skal ikke telle som "Chief
        # har reagert".
        post, *_rest = _CRETRY.vurder_retry(
            issue_nummer=40, issue_labels=["status:review"], prs=[_pr()],
            branch_navn="agent/issue-40", signalert_head_sha=_HEAD_A,
            eksisterende_kommentarer=[_CRETRY.bygg_marker(40, _HEAD_A)],
            pr_reviews=[_review(head_sha=_HEAD_A, state="PENDING")],
        )
        self.assertTrue(post)


class TestCliAlltidExitNull(unittest.TestCase):
    """Chief-retry-signalets CLI-kontrakt: I MOTSETNING TIL
    chief_ready_signal.py, skal denne ALLTID returnere exit 0 -- en
    avvist retry er i all hovedsak det sunne, forventede utfallet, ikke
    en anomali. Se moduldocstring 'IKKE-ALARMERENDE VED NEI'."""

    def _kjor_cli(self, stdin_data, output_path):
        return subprocess.run(
            [sys.executable, _SCRIPT, output_path],
            input=json.dumps(stdin_data),
            capture_output=True, text=True,
        )

    def test_5a_avvist_retry_gir_null_exit_og_ingen_fil(self):
        with tempfile.TemporaryDirectory() as d:
            output_path = os.path.join(d, "retry_comment.txt")
            res = self._kjor_cli(
                {
                    "issue_number": 40,
                    "issue_labels": ["agent:claude", "status:changes-requested"],
                    "prs": [_pr()],
                    "branch": "agent/issue-40",
                    "signaled_head_sha": _HEAD_A,
                    "comments": [_CRETRY.bygg_marker(40, _HEAD_A)],
                    "reviews": [],
                },
                output_path,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("post=false", res.stdout)
            self.assertFalse(os.path.exists(output_path))

    def test_5b_godkjent_retry_gir_null_exit_og_fil_skrevet(self):
        with tempfile.TemporaryDirectory() as d:
            output_path = os.path.join(d, "retry_comment.txt")
            res = self._kjor_cli(
                {
                    "issue_number": 40,
                    "issue_labels": ["status:review"],
                    "prs": [_pr()],
                    "branch": "agent/issue-40",
                    "signaled_head_sha": _HEAD_A,
                    "comments": [_CRETRY.bygg_marker(40, _HEAD_A)],
                    "reviews": [],
                },
                output_path,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("post=true", res.stdout)
            self.assertIn(f"pr_number={45}", res.stdout)
            self.assertIn(f"head_sha={_HEAD_A}", res.stdout)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, encoding="utf-8") as f:
                innhold = f.read()
            self.assertIn(_CRETRY.bygg_marker(40, _HEAD_A), innhold)

    def test_5c_manglende_stdin_data_gir_null_exit_uten_krasj(self):
        with tempfile.TemporaryDirectory() as d:
            output_path = os.path.join(d, "retry_comment.txt")
            res = subprocess.run(
                [sys.executable, _SCRIPT, output_path],
                input="", capture_output=True, text=True,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("post=false", res.stdout)


class TestWorkflowKildetekst(unittest.TestCase):
    """Inspiserer selve workflow-KILDETEKSTEN -- samme stdlib-only
    mønster som test_agent_bridge_chief_ready_signal.py sin
    TestWorkflowKildetekst."""

    _NYE_STEG = (
        "Wait for Chief reaction window (issue #40 deterministic retry)",
        "Refetch live state for Chief-ready retry (issue #40)",
        "Decide Chief-ready retry signal (issue #40)",
        "Post Chief-ready retry signal comment (issue #40)",
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

    def test_6a_alle_nye_steg_er_gatet_pa_dry_run_og_leveranse_ok(self):
        for navn in self._NYE_STEG:
            steg = self._finn_steg(navn)
            self.assertIn("needs.guard.outputs.dry_run != 'true'", steg)
            self.assertIn("steps.deliverable.outputs.ok == 'true'", steg)

    def test_6b_nye_steg_krever_original_signal_post_true(self):
        for navn in self._NYE_STEG:
            steg = self._finn_steg(navn)
            self.assertIn("steps.signal.outputs.post == 'true'", steg)

    def test_6c_retry_post_steget_krever_ogsa_retry_signal_post_true(self):
        steg = self._finn_steg("Post Chief-ready retry signal comment (issue #40)")
        self.assertIn("steps.retry_signal.outputs.post == 'true'", steg)

    def test_6d_stegene_kommer_etter_det_opprinnelige_signalet(self):
        pos_original_post = self.tekst.index("Post Chief-ready signal comment (issue #32 adapter)")
        for navn in self._NYE_STEG:
            self.assertLess(pos_original_post, self.tekst.index(navn))
        # Rekkefølgen internt: wait -> refetch -> decide -> post.
        posisjoner = [self.tekst.index(navn) for navn in self._NYE_STEG]
        self.assertEqual(posisjoner, sorted(posisjoner))

    def test_6e_ingen_gh_pr_merge_eller_git_merge_i_de_nye_stegene(self):
        for navn in self._NYE_STEG:
            steg = self._finn_steg(navn)
            for forbudt in ("gh pr merge", "git merge"):
                self.assertNotIn(forbudt, steg)

    def test_6f_ingen_ny_claude_trigger_overflate(self):
        on_block_match = re.search(r'^"on":\n(.*?)(?=^permissions:)', self.tekst, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(on_block_match)
        on_block = on_block_match.group(1)
        self.assertNotIn("issue_comment", on_block)
        self.assertNotIn("pull_request", on_block)

    def test_6g_chief_retry_signal_kalles_aldri_av_claude_steget(self):
        run_claude_match = re.search(
            r"^([ \t]*)- name: Run Claude Code\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(run_claude_match)
        self.assertNotIn("chief_retry_signal.py", run_claude_match.group(0))

    def test_6h_wait_steget_bruker_et_fast_dokumentert_sekundtall(self):
        steg = self._finn_steg("Wait for Chief reaction window (issue #40 deterministic retry)")
        self.assertIn("sleep 900", steg)


if __name__ == "__main__":
    unittest.main()
