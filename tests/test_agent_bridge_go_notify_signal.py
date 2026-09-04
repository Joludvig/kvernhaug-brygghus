"""
Kvernhaug Agent Bridge -- regresjonstester for GO/NO-GO-eiervarselet
(.github/scripts/go_notify_signal.py, issue #66).

Issue #66s krav, dekket her:
  1. markøren er deterministisk og inneholder issue/head (idempotens-
     nøkkelen),
  2. samme (issue, head) gjenkjennes som duplikat -- ingen spam,
  3. varsel postes KUN når ALT av følgende bekreftes på et FERSKT
     refetch: PR åpen og uslått, eksakt live head, en formell APPROVED-
     review for NETTOPP det hodet, issuen eksklusivt status:approved,
  4. en NY head gjør et tidligere varsel foreldet -- IKKE et duplikat,
  5. feilstavede/nesten-like kommentarer telles ALDRI som markøren,
  6. ingen hemmelighet/verdi-lekkasje er mulig gjennom markør-
     konstruksjonen,
  7. CLI-kontrakten (exit-koder, GITHUB_OUTPUT-linjer, kommentarfil).

Ren stdlib-test, ingen GitHub-kall, ingen `jq`-avhengighet -- kjøres av
den vanlige suiten (`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "go_notify_signal.py")
_LIFECYCLE_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "lifecycle_labels.py")


def _last_modul(sti, navn):
    spec = importlib.util.spec_from_file_location(navn, sti)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_GNS = _last_modul(_SCRIPT, "go_notify_signal")
_LL = _last_modul(_LIFECYCLE_SCRIPT, "lifecycle_labels")

_HEAD_A = "a" * 40
_HEAD_B = "b" * 40


def _pr(number=66, state="OPEN", base="master", head_branch="agent/issue-66", head_sha=_HEAD_A):
    return {
        "number": number,
        "state": state,
        "baseRefName": base,
        "headRefName": head_branch,
        "headRefOid": head_sha,
    }


def _review(state="APPROVED", head_sha=_HEAD_A):
    return {"state": state, "commit": {"oid": head_sha}}


def _vurder(**overstyr):
    kwargs = {
        "issue_nummer": 66,
        "issue_labels": ["agent:claude", "status:approved"],
        "prs": [_pr()],
        "branch_navn": "agent/issue-66",
        "pr_reviews": [_review()],
        "eksisterende_kommentarer": [],
    }
    kwargs.update(overstyr)
    return _GNS.vurder_go_notify(**kwargs)


class TestLivssyklusEtikettSync(unittest.TestCase):
    def test_duplisert_liste_er_identisk_med_lifecycle_labels(self):
        self.assertEqual(_GNS.LIVSSYKLUS_ETIKETTER, _LL.LIVSSYKLUS_ETIKETTER)


class TestMarkorKonstruksjon(unittest.TestCase):
    # ─── 1: kanonisk markør er deterministisk og inneholder issue/head ──

    def test_1_marker_er_deterministisk_og_inneholder_issue_og_head(self):
        marker = _GNS.bygg_marker(66, _HEAD_A)
        self.assertEqual(marker, _GNS.bygg_marker(66, _HEAD_A))
        self.assertIn("issue=66", marker)
        self.assertIn(f"head={_HEAD_A}", marker)
        self.assertTrue(marker.startswith("KBH_GO_READY_V1 "))

    def test_1b_kommentar_inneholder_markor_som_egen_linje(self):
        kommentar = _GNS.bygg_kommentar(66, 45, _HEAD_A)
        self.assertIn(_GNS.bygg_marker(66, _HEAD_A), kommentar.splitlines())

    def test_1c_markorversjon_skiller_seg_fra_chief_ready_markoren(self):
        # Egen, reservert versjonsstreng -- kan aldri forveksles med
        # KBH_CHIEF_REVIEW_READY_V1 eller KBH_PR_READY_TRANSITION_DONE_V1.
        self.assertNotEqual(_GNS.MARKER_VERSJON, "KBH_CHIEF_REVIEW_READY_V1")
        self.assertNotEqual(_GNS.MARKER_VERSJON, "KBH_PR_READY_TRANSITION_DONE_V1")

    # ─── 6: ingen hemmelighet/verdi-lekkasje ─────────────────────────────

    def test_6_kommentar_inneholder_kun_issue_pr_og_head(self):
        kommentar = _GNS.bygg_kommentar(66, 45, _HEAD_A)
        for uventet in ("token", "secret", "ANTHROPIC", "OAUTH", "api_key"):
            self.assertNotIn(uventet.lower(), kommentar.lower())

    def test_6b_kommentar_nevner_go_no_go_og_ikke_auto_merge(self):
        kommentar = _GNS.bygg_kommentar(66, 45, _HEAD_A)
        self.assertIn("GO", kommentar)
        self.assertIn("NO-GO", kommentar)
        self.assertIn("manuell eier-handling", kommentar)


class TestFinnEksisterendeMarkorer(unittest.TestCase):
    def test_finner_eksakt_markor(self):
        kommentarer = ["noe tekst", _GNS.bygg_marker(66, _HEAD_A), "mer tekst"]
        self.assertIn((66, _HEAD_A), _GNS.finn_eksisterende_markorer(kommentarer))

    # ─── 5: nesten-like linjer teller aldri ──────────────────────────────

    def test_5_feilstavet_versjon_teller_ikke(self):
        kommentarer = ["KBH_GO_READY_V2 issue=66 head=" + _HEAD_A]
        self.assertEqual(_GNS.finn_eksisterende_markorer(kommentarer), set())

    def test_5b_kort_sha_teller_ikke(self):
        kommentarer = ["KBH_GO_READY_V1 issue=66 head=abc123"]
        self.assertEqual(_GNS.finn_eksisterende_markorer(kommentarer), set())

    def test_5c_ekstra_tekst_pa_samme_linje_teller_ikke(self):
        kommentarer = [f"KBH_GO_READY_V1 issue=66 head={_HEAD_A} ekstra"]
        self.assertEqual(_GNS.finn_eksisterende_markorer(kommentarer), set())

    def test_5d_feil_case_teller_ikke(self):
        kommentarer = [f"kbh_go_ready_v1 issue=66 head={_HEAD_A}"]
        self.assertEqual(_GNS.finn_eksisterende_markorer(kommentarer), set())

    def test_tom_liste_gir_tomt_sett(self):
        self.assertEqual(_GNS.finn_eksisterende_markorer([]), set())
        self.assertEqual(_GNS.finn_eksisterende_markorer(None), set())


class TestVurderGoNotify(unittest.TestCase):
    # ─── 3: den gyldige veien ─────────────────────────────────────────────

    def test_3_lykkes_naar_alt_stemmer(self):
        post, duplicate, pr_nummer, head_sha, kommentar, begrunnelse = _vurder()
        self.assertTrue(post)
        self.assertFalse(duplicate)
        self.assertEqual(pr_nummer, 66)
        self.assertEqual(head_sha, _HEAD_A)
        self.assertIsNotNone(kommentar)

    # ─── 2/4: duplikat vs. ny head ────────────────────────────────────────

    def test_2_duplikat_for_samme_issue_og_head(self):
        eksisterende = [_GNS.bygg_marker(66, _HEAD_A)]
        post, duplicate, pr_nummer, head_sha, kommentar, _ = _vurder(eksisterende_kommentarer=eksisterende)
        self.assertFalse(post)
        self.assertTrue(duplicate)
        self.assertIsNone(kommentar)
        self.assertEqual(head_sha, _HEAD_A)

    def test_4_ny_head_er_ikke_duplikat_selv_om_gammel_markor_finnes(self):
        eksisterende = [_GNS.bygg_marker(66, _HEAD_A)]
        post, duplicate, _, head_sha, _, _ = _vurder(
            prs=[_pr(head_sha=_HEAD_B)],
            pr_reviews=[_review(head_sha=_HEAD_B)],
            eksisterende_kommentarer=eksisterende,
        )
        self.assertTrue(post)
        self.assertFalse(duplicate)
        self.assertEqual(head_sha, _HEAD_B)

    # ─── fail-closed: livssyklus ────────────────────────────────────────

    def test_avviser_uten_status_approved(self):
        post, duplicate, *_ = _vurder(issue_labels=["agent:claude", "status:review"])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_flere_livssyklus_etiketter_samtidig(self):
        post, duplicate, *_ = _vurder(issue_labels=["agent:claude", "status:approved", "status:review"])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_manglende_issue_nummer(self):
        post, duplicate, *_ = _vurder(issue_nummer=None)
        self.assertFalse(post)
        self.assertFalse(duplicate)

    # ─── fail-closed: PR-tilstand ───────────────────────────────────────

    def test_avviser_merget_pr(self):
        # MERGED er ikke OPEN -- finnes ikke i kandidatlisten i det hele tatt.
        post, duplicate, *_ = _vurder(prs=[_pr(state="MERGED")])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_lukket_pr(self):
        post, duplicate, *_ = _vurder(prs=[_pr(state="CLOSED")])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_feil_branch(self):
        post, duplicate, *_ = _vurder(prs=[_pr(head_branch="agent/issue-999")])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_feil_base(self):
        post, duplicate, *_ = _vurder(prs=[_pr(base="develop")])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_null_pr_kandidater(self):
        post, duplicate, *_ = _vurder(prs=[])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_flere_pr_kandidater_ambiguost(self):
        post, duplicate, *_ = _vurder(prs=[_pr(number=1), _pr(number=2)])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_manglende_head_sha(self):
        pr = _pr()
        pr["headRefOid"] = None
        post, duplicate, *_ = _vurder(prs=[pr])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    # ─── fail-closed: review-tilstand ───────────────────────────────────

    def test_avviser_ingen_review(self):
        post, duplicate, *_ = _vurder(pr_reviews=[])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_changes_requested_review_alene(self):
        post, duplicate, *_ = _vurder(pr_reviews=[_review(state="CHANGES_REQUESTED")])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_avviser_approved_review_for_annet_hode(self):
        # Godkjenningen gjaldt et ELDRE hode -- PR-en fikk nye commits
        # etterpå uten en ny review. Skal IKKE telle for det live hodet.
        post, duplicate, *_ = _vurder(pr_reviews=[_review(state="APPROVED", head_sha=_HEAD_B)])
        self.assertFalse(post)
        self.assertFalse(duplicate)

    def test_godtar_approved_pluss_eldre_changes_requested_pa_samme_hode(self):
        # En APPROVED for det eksakte hodet er nok, selv om en tidligere
        # CHANGES_REQUESTED-review for samme hode også finnes (Chief kan
        # ha revidert sin egen dom på samme head via en formell re-review).
        post, duplicate, *_ = _vurder(pr_reviews=[
            _review(state="CHANGES_REQUESTED"),
            _review(state="APPROVED"),
        ])
        self.assertTrue(post)
        self.assertFalse(duplicate)

    def test_ukjente_input_nokler_krasjer_ikke(self):
        post, duplicate, pr_nummer, head_sha, kommentar, _ = _vurder()
        self.assertTrue(post)
        self.assertNotIn("issue_body", kommentar)
        self.assertEqual(pr_nummer, 66)
        self.assertEqual(head_sha, _HEAD_A)


class TestCli(unittest.TestCase):
    def _kjor_cli(self, payload_json, output_path):
        return subprocess.run(
            [sys.executable, _SCRIPT, output_path],
            input=payload_json, capture_output=True, text=True,
        )

    def test_cli_post_true_skriver_kommentarfil_og_exit_0(self):
        import json as _json
        payload = _json.dumps({
            "issue_number": 66,
            "issue_labels": ["agent:claude", "status:approved"],
            "prs": [_pr()],
            "reviews": [_review()],
            "branch": "agent/issue-66",
            "comments": [],
        })
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "comment.txt")
            res = self._kjor_cli(payload, out_path)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("post=true", res.stdout)
            self.assertIn("duplicate=false", res.stdout)
            self.assertIn("pr_number=66", res.stdout)
            self.assertIn(f"head_sha={_HEAD_A}", res.stdout)
            self.assertTrue(os.path.exists(out_path))
            with open(out_path, encoding="utf-8") as f:
                self.assertIn("KBH_GO_READY_V1", f.read())

    def test_cli_duplicate_exit_0_ingen_fil(self):
        import json as _json
        payload = _json.dumps({
            "issue_number": 66,
            "issue_labels": ["agent:claude", "status:approved"],
            "prs": [_pr()],
            "reviews": [_review()],
            "branch": "agent/issue-66",
            "comments": [f"KBH_GO_READY_V1 issue=66 head={_HEAD_A}"],
        })
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "comment.txt")
            res = self._kjor_cli(payload, out_path)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertIn("post=false", res.stdout)
            self.assertIn("duplicate=true", res.stdout)
            self.assertFalse(os.path.exists(out_path))

    def test_cli_fail_closed_avvisning_exit_1(self):
        import json as _json
        payload = _json.dumps({
            "issue_number": 66,
            "issue_labels": ["agent:claude", "status:review"],
            "prs": [_pr()],
            "reviews": [_review()],
            "branch": "agent/issue-66",
            "comments": [],
        })
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "comment.txt")
            res = self._kjor_cli(payload, out_path)
            self.assertEqual(res.returncode, 1)
            self.assertIn("post=false", res.stdout)
            self.assertIn("duplicate=false", res.stdout)
            self.assertFalse(os.path.exists(out_path))

    def test_cli_tomt_input_krasjer_ikke(self):
        with tempfile.TemporaryDirectory() as tmp:
            out_path = os.path.join(tmp, "comment.txt")
            res = self._kjor_cli("", out_path)
            self.assertEqual(res.returncode, 1)
            self.assertIn("post=false", res.stdout)

    def test_cli_feil_argumentantall(self):
        res = subprocess.run([sys.executable, _SCRIPT], input="", capture_output=True, text=True)
        self.assertEqual(res.returncode, 2)


if __name__ == "__main__":
    unittest.main()
