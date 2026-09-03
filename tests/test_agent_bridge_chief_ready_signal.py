"""
Kvernhaug Agent Bridge V1 -- regresjonstester for Chief-ready
PR-signalet (.github/scripts/chief_ready_signal.py, issue #32).

Denne modulen er den lille, rene adapteren mellom Bridgens autoritative
issue-baserte tilstandsmaskin og den native ChatGPT Work-integrasjonen
(som kun støtter event-triggede oppgaver på PR-aktivitet, inkl.
PR-kommentarer). Se moduldocstringen i chief_ready_signal.py og
AGENT_WORKFLOW.md for hele resonnementet.

Testene dekker de ni punktene issue #32 eksplisitt krever bevist:
  1. kanonisk V1-markør er deterministisk og inneholder issue/head,
  2. samme issue/head gjenkjennes som duplikat,
  3. samme issue med NY head er IKKE et duplikat,
  4. feilstavede/nesten-like kommentarer telles ALDRI som markøren,
  5. dry-run-stien postes aldri (workflow-kildetekst-sjekk),
  6. markør-stien skjer KUN etter leveranse-PASS + status:review
     (både på funksjonsnivå her og som workflow-kildetekst-sjekk),
  7. eksisterende trigger/auth/concurrency/deliverable-tester -- dekket
     av at de fortsatt kjøres/består i den samme suiten, ikke duplisert
     her,
  8. ingen ny Claude-trigger-overflate introduseres (workflow-
     kildetekst-sjekk: ingen ny `on:`-trigger, `gh pr comment` for
     signalet kjøres UTENFOR --allowedTools/Claude-steget),
  9. ingen hemmelighet/verdi-lekkasje er mulig gjennom markør-
     konstruksjonen.

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
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "chief_ready_signal.py")
_LIFECYCLE_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "lifecycle_labels.py")
_WORKFLOW = os.path.join(_REPO_ROOT, ".github", "workflows", "claude-agent-bridge.yml")


def _last_modul(sti, navn):
    """Laster en .github/scripts-modul direkte fra sti -- samme mønster
    som de andre .github/scripts-testene i denne suiten bruker for
    workflow-hjelpere som bevisst ligger utenfor Python-
    pakkestrukturen."""
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_CRS = _last_modul(_SCRIPT, "chief_ready_signal")
_LL = _last_modul(_LIFECYCLE_SCRIPT, "lifecycle_labels")

_HEAD_A = "a" * 40
_HEAD_B = "b" * 40


def _pr(number=45, state="OPEN", base="master", head_branch="agent/issue-32", head_sha=_HEAD_A):
    return {
        "number": number,
        "state": state,
        "baseRefName": base,
        "headRefName": head_branch,
        "headRefOid": head_sha,
    }


class TestLivssyklusEtikettSync(unittest.TestCase):
    """chief_ready_signal.py dupliserer BEVISST (ikke importerer)
    lifecycle_labels.LIVSSYKLUS_ETIKETTER -- se moduldocstring for
    hvorfor. Denne testen er det som hindrer de to fra å drifte fra
    hverandre uoppdaget."""

    def test_duplisert_liste_er_identisk_med_lifecycle_labels(self):
        self.assertEqual(_CRS.LIVSSYKLUS_ETIKETTER, _LL.LIVSSYKLUS_ETIKETTER)


class TestMarkorKonstruksjon(unittest.TestCase):
    # ─── 1: kanonisk markør er deterministisk og inneholder issue/head ──

    def test_1_marker_er_deterministisk_og_inneholder_issue_og_head(self):
        marker = _CRS.bygg_marker(32, _HEAD_A)
        self.assertEqual(marker, _CRS.bygg_marker(32, _HEAD_A))
        self.assertIn("issue=32", marker)
        self.assertIn(f"head={_HEAD_A}", marker)
        self.assertTrue(marker.startswith("KBH_CHIEF_REVIEW_READY_V1 "))

    def test_1b_kommentar_inneholder_markor_som_egen_linje(self):
        kommentar = _CRS.bygg_kommentar(32, 45, _HEAD_A)
        self.assertIn(_CRS.bygg_marker(32, _HEAD_A), kommentar.splitlines())

    # ─── 9: ingen hemmelighet/verdi-lekkasje via markør-konstruksjon ────

    def test_9_kommentar_inneholder_kun_issue_pr_og_head(self):
        kommentar = _CRS.bygg_kommentar(32, 45, _HEAD_A)
        for uventet in ("token", "secret", "ANTHROPIC", "OAUTH", "api_key"):
            self.assertNotIn(uventet.lower(), kommentar.lower())

    def test_9b_vurder_signal_ignorerer_ukjente_input_nokler(self):
        # Selv om workflowen skulle sende med ekstra felt (f.eks. issue-
        # body eller Claude-output) i JSON-blobben, skal vurder_signal
        # rett og slett ikke bry seg -- funksjonssignaturen tar kun
        # navngitte, strukturerte parametre.
        post, duplicate, pr_nummer, head_sha, kommentar, _ = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["agent:claude", "status:review"],
            prs=[_pr()],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertTrue(post)
        self.assertNotIn("issue_body", kommentar)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)


class TestDuplikatDeteksjon(unittest.TestCase):
    # ─── 2: samme issue/head gjenkjennes som duplikat ────────────────────

    def test_2_samme_issue_og_head_er_duplikat(self):
        marker = _CRS.bygg_marker(32, _HEAD_A)
        funnet = _CRS.finn_eksisterende_markorer([f"Noe tekst.\n{marker}\nMer tekst."])
        self.assertIn((32, _HEAD_A), funnet)

    # ─── 3: samme issue med NY head er IKKE duplikat ─────────────────────

    def test_3_samme_issue_ny_head_er_ikke_duplikat(self):
        gammel_marker = _CRS.bygg_marker(32, _HEAD_A)
        funnet = _CRS.finn_eksisterende_markorer([gammel_marker])
        self.assertNotIn((32, _HEAD_B), funnet)

    # ─── 4: feilstavede/nesten-like linjer telles ALDRI ──────────────────

    def test_4_feil_versjon_telles_ikke(self):
        funnet = _CRS.finn_eksisterende_markorer([f"KBH_CHIEF_REVIEW_READY_V2 issue=32 head={_HEAD_A}"])
        self.assertEqual(funnet, set())

    def test_4b_feil_case_telles_ikke(self):
        funnet = _CRS.finn_eksisterende_markorer([f"kbh_chief_review_ready_v1 issue=32 head={_HEAD_A}"])
        self.assertEqual(funnet, set())

    def test_4c_manglende_mellomrom_telles_ikke(self):
        funnet = _CRS.finn_eksisterende_markorer([f"KBH_CHIEF_REVIEW_READY_V1issue=32 head={_HEAD_A}"])
        self.assertEqual(funnet, set())

    def test_4d_for_kort_sha_telles_ikke(self):
        funnet = _CRS.finn_eksisterende_markorer(["KBH_CHIEF_REVIEW_READY_V1 issue=32 head=abc123"])
        self.assertEqual(funnet, set())

    def test_4e_ekstra_tekst_pa_samme_linje_telles_ikke(self):
        funnet = _CRS.finn_eksisterende_markorer([f"se KBH_CHIEF_REVIEW_READY_V1 issue=32 head={_HEAD_A} takk"])
        self.assertEqual(funnet, set())

    def test_4f_trailing_tekst_pa_samme_linje_telles_ikke(self):
        funnet = _CRS.finn_eksisterende_markorer([f"KBH_CHIEF_REVIEW_READY_V1 issue=32 head={_HEAD_A} (ekstra)"])
        self.assertEqual(funnet, set())

    def test_4g_ekte_markor_pa_egen_linje_blant_stoy_telles(self):
        # Sanity-motstykke til 4a-4f: en EKTE markør skal fortsatt bli
        # funnet når den står alene på sin egen linje, selv omgitt av
        # annen tekst/støy før og etter.
        marker = _CRS.bygg_marker(32, _HEAD_A)
        funnet = _CRS.finn_eksisterende_markorer([f"noe støy\n{marker}\nmer støy"])
        self.assertIn((32, _HEAD_A), funnet)

    def test_4h_tom_og_none_kommentarliste_gir_tomt_sett(self):
        self.assertEqual(_CRS.finn_eksisterende_markorer([]), set())
        self.assertEqual(_CRS.finn_eksisterende_markorer(None), set())
        self.assertEqual(_CRS.finn_eksisterende_markorer([None, ""]), set())


class TestVurderSignal(unittest.TestCase):
    # ─── 6: markør-stien skjer KUN etter status:review + PASS ───────────

    def test_6_avviser_hvis_issue_ikke_er_status_review(self):
        post, duplicate, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["agent:claude", "status:working"],
            prs=[_pr()],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_6b_avviser_hvis_flere_livssyklus_etiketter_samtidig(self):
        # Race: owner har lagt på changes-requested UTEN å fjerne review
        # (brudd på den eksklusive konvensjonen) -- fail-closed uansett.
        post, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["agent:claude", "status:review", "status:changes-requested"],
            prs=[_pr()],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)

    def test_6c_avviser_hvis_ingen_apen_pr_pa_branchen(self):
        post, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)

    def test_6d_avviser_hvis_pr_er_pa_feil_branch(self):
        post, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[_pr(head_branch="some-other-branch")],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)

    def test_6e_avviser_hvis_pr_ikke_er_apen(self):
        post, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[_pr(state="MERGED")],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)

    def test_6f_avviser_hvis_pr_mot_annen_base_enn_master(self):
        post, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[_pr(base="develop")],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)

    def test_6g_avviser_ved_flere_kandidat_prer_pa_samme_branch(self):
        post, *_rest = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[_pr(number=45), _pr(number=46)],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertFalse(post)

    def test_6h_godkjenner_nar_alt_stemmer(self):
        post, duplicate, pr_nummer, head_sha, kommentar, begrunnelse = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["agent:claude", "area:infra", "status:review"],
            prs=[_pr()],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=[],
        )
        self.assertTrue(post)
        self.assertFalse(duplicate)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertIsNotNone(kommentar)
        self.assertTrue(begrunnelse)

    def test_6i_duplikat_gir_post_false_men_ikke_en_feil(self):
        eksisterende = [_CRS.bygg_marker(32, _HEAD_A)]
        post, duplicate, pr_nummer, head_sha, kommentar, _ = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[_pr()],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=eksisterende,
        )
        self.assertFalse(post)
        self.assertTrue(duplicate)
        self.assertIsNone(kommentar)
        self.assertEqual(pr_nummer, 45)
        self.assertEqual(head_sha, _HEAD_A)

    def test_6j_ny_head_etter_changes_requested_runde_er_ikke_duplikat(self):
        eksisterende = [_CRS.bygg_marker(32, _HEAD_A)]
        post, duplicate, pr_nummer, head_sha, kommentar, _ = _CRS.vurder_signal(
            issue_nummer=32,
            issue_labels=["status:review"],
            prs=[_pr(head_sha=_HEAD_B)],
            branch_navn="agent/issue-32",
            eksisterende_kommentarer=eksisterende,
        )
        self.assertTrue(post)
        self.assertFalse(duplicate)
        self.assertEqual(head_sha, _HEAD_B)
        self.assertIn(_CRS.bygg_marker(32, _HEAD_B), kommentar)


class TestCliExitKode(unittest.TestCase):
    """Chief review (PR #34): CLI-kontrakten for exit-koden -- se
    moduldocstringens 'EXIT-KODE' og main()s kommentarer. Kjører selve
    scriptet som subprocess (samme mønster som CLI-seksjonen i
    test_agent_bridge_deliverable_guard.py), slik at det er selve
    prosessens exit-status og fil-sideeffekt som testes -- ikke bare
    vurder_signal()s returverdier, som resten av denne suiten allerede
    dekker.

    Dette er den konkrete rettelsen for Chief-blokkeren på PR #34: uten
    denne, kunne 'Decide Chief-ready signal'-workflow-steget lykkes
    (exit 0) selv når live-tilstanden ikke lenger tilfredsstilte
    signal-kontrakten, slik at jobben ble grønn uten både markør og
    feilrapport."""

    def _kjor_cli(self, stdin_data, output_path):
        return subprocess.run(
            [sys.executable, _SCRIPT, output_path],
            input=json.dumps(stdin_data),
            capture_output=True, text=True,
        )

    def test_11_ugyldig_live_tilstand_gir_ikke_null_exit_og_ingen_markor(self):
        # Ambiguøs/ugyldig live-tilstand (issuen har rukket å bevege seg
        # bort fra eksklusivt status:review ved refetch) -- fail-closed
        # AVVISNING, ikke et duplikat. Skal nå feile prosessen.
        with tempfile.TemporaryDirectory() as d:
            output_path = os.path.join(d, "comment.txt")
            res = self._kjor_cli(
                {
                    "issue_number": 32,
                    "issue_labels": ["agent:claude", "status:working"],
                    "prs": [_pr()],
                    "branch": "agent/issue-32",
                    "comments": [],
                },
                output_path,
            )
            self.assertNotEqual(res.returncode, 0)
            self.assertIn("post=false", res.stdout)
            self.assertIn("duplicate=false", res.stdout)
            self.assertFalse(os.path.exists(output_path))

    def test_11b_eksakt_duplikat_gir_null_exit_og_ingen_markor(self):
        # Idempotent no-op -- fortsatt suksess (exit 0), fortsatt ingen
        # ny markør skrevet, men prosessen skal IKKE feile.
        with tempfile.TemporaryDirectory() as d:
            output_path = os.path.join(d, "comment.txt")
            res = self._kjor_cli(
                {
                    "issue_number": 32,
                    "issue_labels": ["status:review"],
                    "prs": [_pr()],
                    "branch": "agent/issue-32",
                    "comments": [_CRS.bygg_marker(32, _HEAD_A)],
                },
                output_path,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("post=false", res.stdout)
            self.assertIn("duplicate=true", res.stdout)
            self.assertFalse(os.path.exists(output_path))

    def test_11c_gyldig_fersk_tilstand_gir_null_exit_og_markor_skrevet(self):
        with tempfile.TemporaryDirectory() as d:
            output_path = os.path.join(d, "comment.txt")
            res = self._kjor_cli(
                {
                    "issue_number": 32,
                    "issue_labels": ["agent:claude", "status:review"],
                    "prs": [_pr()],
                    "branch": "agent/issue-32",
                    "comments": [],
                },
                output_path,
            )
            self.assertEqual(res.returncode, 0)
            self.assertIn("post=true", res.stdout)
            self.assertIn("duplicate=false", res.stdout)
            self.assertTrue(os.path.exists(output_path))
            with open(output_path, encoding="utf-8") as f:
                innhold = f.read()
            self.assertIn(_CRS.bygg_marker(32, _HEAD_A), innhold)


class TestWorkflowKildetekst(unittest.TestCase):
    """Inspiserer selve workflow-KILDETEKSTEN, samme stdlib-only mønster
    som test_agent_bridge_permission_config.py -- ingen PyYAML-
    avhengighet."""

    def setUp(self):
        with open(_WORKFLOW, encoding="utf-8") as f:
            self.tekst = f.read()

    # ─── 5: dry-run postes aldri ─────────────────────────────────────────

    def test_5_signal_stegene_er_gatet_pa_dry_run(self):
        for steg_navn in (
            "Refetch live state for Chief-ready signal (issue #32)",
            "Decide Chief-ready signal (issue #32)",
            "Post Chief-ready signal comment (issue #32 adapter)",
        ):
            match = re.search(
                r"^([ \t]*)- name: " + re.escape(steg_navn) + r"\n(.*?)(?=^\1- name:|\Z)",
                self.tekst, re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match, f"Fant ikke steget {steg_navn!r} i workflowen.")
            steg = match.group(0)
            self.assertIn("needs.guard.outputs.dry_run != 'true'", steg)

    # ─── 6: markør-stien skjer kun etter status:review + leveranse-PASS ─

    def test_6_signal_stegene_krever_leveranse_ok_og_kommer_etter_promote(self):
        for steg_navn in (
            "Refetch live state for Chief-ready signal (issue #32)",
            "Decide Chief-ready signal (issue #32)",
            "Post Chief-ready signal comment (issue #32 adapter)",
        ):
            match = re.search(
                r"^([ \t]*)- name: " + re.escape(steg_navn) + r"\n(.*?)(?=^\1- name:|\Z)",
                self.tekst, re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match)
            self.assertIn("steps.deliverable.outputs.ok == 'true'", match.group(0))

        pos_promote = self.tekst.index("id: promote")
        pos_refetch = self.tekst.index("Refetch live state for Chief-ready signal")
        self.assertLess(pos_promote, pos_refetch, "Signal-stegene må stå etter status:review-overgangen.")

    def test_6b_post_steget_krever_ogsa_post_true_fra_decide_steget(self):
        match = re.search(
            r"^([ \t]*)- name: Post Chief-ready signal comment \(issue #32 adapter\)\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertIn("steps.signal.outputs.post == 'true'", match.group(0))

    # ─── 8: ingen ny Claude-trigger-overflate ────────────────────────────

    def test_8_ingen_issue_comment_eller_pull_request_trigger_lagt_til(self):
        on_block_match = re.search(r'^"on":\n(.*?)(?=^permissions:)', self.tekst, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(on_block_match, "Fant ikke 'on:'-blokken.")
        on_block = on_block_match.group(1)
        self.assertNotIn("issue_comment", on_block)
        self.assertNotIn("pull_request", on_block)
        self.assertIn("issues:", on_block)
        self.assertIn("workflow_dispatch:", on_block)

    def test_8b_signal_kommentar_postes_utenfor_claude_steget_ikke_i_allowedtools(self):
        run_claude_match = re.search(
            r"^([ \t]*)- name: Run Claude Code\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(run_claude_match)
        allowed_tools_match = re.search(r'--allowedTools "([^"]*)"', run_claude_match.group(0))
        self.assertIsNotNone(allowed_tools_match)
        # chief_ready_signal.py kalles aldri av/via Claude-steget selv.
        self.assertNotIn("chief_ready_signal.py", run_claude_match.group(0))

        post_match = re.search(
            r"^([ \t]*)- name: Post Chief-ready signal comment \(issue #32 adapter\)\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(post_match)
        # Kommer et godt stykke ETTER "Run Claude Code"-steget i filen --
        # altså et helt eget, senere steg, ikke noe Claude selv gjør.
        self.assertLess(self.tekst.index("Run Claude Code"), self.tekst.index("Post Chief-ready signal comment"))

    def test_8c_ingen_gh_pr_merge_eller_git_merge_i_de_nye_signal_stegene(self):
        # test_agent_bridge_permission_config.py dekker allerede at
        # --allowedTools aldri gir Claude selv gh pr merge/git merge --
        # denne testen sjekker at de nye issue #32-stegene (som kjører
        # UTENFOR Claude, med workflowens eget token) heller ikke gjør
        # det.
        for steg_navn in (
            "Refetch live state for Chief-ready signal (issue #32)",
            "Decide Chief-ready signal (issue #32)",
            "Post Chief-ready signal comment (issue #32 adapter)",
        ):
            match = re.search(
                r"^([ \t]*)- name: " + re.escape(steg_navn) + r"\n(.*?)(?=^\1- name:|\Z)",
                self.tekst, re.MULTILINE | re.DOTALL,
            )
            self.assertIsNotNone(match)
            for forbudt in ("gh pr merge", "git merge"):
                self.assertNotIn(forbudt, match.group(0))

    # ─── Failure semantics: status:review rulles aldri tilbake ──────────

    def test_failure_step_for_signal_emisjon_ruller_ikke_issue_tilbake(self):
        match = re.search(
            r"^([ \t]*)- name: Report Chief-ready signal emission failure.*?\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        steg = match.group(0)
        self.assertIn("steps.promote.outcome == 'success'", steg)
        self.assertIn("status:review", steg)
        self.assertNotIn("lifecycle_labels.py", steg)

    def test_generisk_failure_step_er_scoped_bort_fra_promote_success(self):
        match = re.search(
            r"^([ \t]*)- name: Report failure — leave at status:working for manual follow-up\n(.*?)(?=^\1- name:|\Z)",
            self.tekst, re.MULTILINE | re.DOTALL,
        )
        self.assertIsNotNone(match)
        self.assertIn("steps.promote.outcome != 'success'", match.group(0))


if __name__ == "__main__":
    unittest.main()
