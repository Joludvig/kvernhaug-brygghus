"""
Kvernhaug Agent Bridge V1.2 -- regresjonstester for leveranse-
verifisering (.github/scripts/deliverable_guard.py, issue #12).

Kjernetesten er `test_1_...`: NØYAKTIG situasjonen observert på issue
#11 -- Claude-prosessen returnerte `subtype: success`, men ingen
branch/PR/kommentar/fil ble faktisk levert. V1 flyttet issuen til
`status:review` likevel. V1.2 skal nekte, fordi det ikke finnes noen
åpen PR mot master å vise til.

Ren stdlib-test, ingen GitHub-kall, ingen bash/YAML-avhengighet --
kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests`).
"""
import importlib.util
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "deliverable_guard.py")


def _last_modul():
    """Laster .github/scripts/deliverable_guard.py direkte fra sti --
    samme mønster som tests/test_agent_bridge_trigger_guard.py og
    tests/test_agent_bridge_labels.py bruker for workflow-hjelpere som
    bevisst ligger utenfor Python-pakkestrukturen."""
    spec = importlib.util.spec_from_file_location("deliverable_guard", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_DG = _last_modul()


def _pr(number=42, state="OPEN", base="master", head="cccccc",
        additions=10, deletions=2, changed_files=3):
    return {
        "number": number,
        "state": state,
        "baseRefName": base,
        "headRefOid": head,
        "additions": additions,
        "deletions": deletions,
        "changedFiles": changed_files,
    }


class TestDeliverableGuard(unittest.TestCase):
    # ─── 1: SELVE BUGEN (issue #11 -- grønn prosess, ingen leveranse) ──

    def test_1_ready_ingen_pr_i_det_hele_tatt_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready", prs=[],
        )
        self.assertFalse(ok, f"Issue #11-situasjonen skal avvises. Begrunnelse: {begrunnelse}")
        self.assertIsNone(nummer)
        self.assertIn("Ingen åpen PR", begrunnelse)

    # ─── 2: status:ready -- diff-innhold ────────────────────────────────

    def test_2_ready_pr_finnes_men_tomt_diff_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(additions=0, deletions=0, changed_files=0)],
        )
        self.assertFalse(ok)
        self.assertEqual(nummer, 42)
        self.assertIn("tomt diff", begrunnelse)

    def test_2b_ready_pr_finnes_null_additions_men_deletions_er_fortsatt_tomt_diff_check(self):
        # changedFiles=0 alene skal også avvises selv om additions/deletions
        # av en eller annen grunn ikke er null (defensivt).
        ok, _, _ = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(additions=3, deletions=1, changed_files=0)],
        )
        self.assertFalse(ok)

    def test_3_ready_pr_med_ikke_tomt_diff_godkjennes(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(additions=50, deletions=5, changed_files=4)],
        )
        self.assertTrue(ok, begrunnelse)
        self.assertEqual(nummer, 42)

    # ─── 4: status:ready -- feil base / ikke lenger åpen ────────────────

    def test_4_ready_pr_mot_annen_base_enn_master_teller_ikke(self):
        ok, nummer, _ = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(base="develop", additions=10, deletions=0, changed_files=1)],
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)  # ingen kandidat i det hele tatt

    def test_4b_ready_allerede_merget_pr_teller_ikke_som_apen_leveranse(self):
        ok, nummer, _ = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(state="MERGED", additions=10, deletions=0, changed_files=1)],
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)

    def test_4c_ready_lukket_uten_merge_teller_ikke(self):
        ok, nummer, _ = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(state="CLOSED", additions=10, deletions=0, changed_files=1)],
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)

    # ─── 5: flere kandidater -- ikke entydig ────────────────────────────

    def test_5_flere_apne_prs_mot_master_er_ikke_entydig(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(number=1, additions=5, deletions=0, changed_files=1),
                 _pr(number=2, additions=5, deletions=0, changed_files=1)],
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)
        self.assertIn("Flere åpne PR-er", begrunnelse)

    # ─── 6: status:changes-requested -- head-endring ────────────────────

    def test_6_changes_requested_ingen_pr_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested", prs=[], forrige_head_sha="aaa",
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)
        self.assertIn("Ingen åpen PR", begrunnelse)

    def test_7_changes_requested_ingen_forrige_head_sha_fanget_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(head="bbb")],
            forrige_head_sha=None,
        )
        self.assertFalse(ok)
        self.assertEqual(nummer, 42)
        self.assertIn("ingen HEAD-SHA", begrunnelse)

    def test_8_changes_requested_uendret_head_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(head="samme-sha")],
            forrige_head_sha="samme-sha",
        )
        self.assertFalse(ok)
        self.assertEqual(nummer, 42)
        self.assertIn("uendret", begrunnelse)

    def test_9_changes_requested_endret_head_godkjennes(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(head="ny-sha-etter-push")],
            forrige_head_sha="gammel-sha-for-run",
        )
        self.assertTrue(ok, begrunnelse)
        self.assertEqual(nummer, 42)

    def test_9b_changes_requested_flere_kandidater_avvises(self):
        ok, nummer, _ = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=1, head="x"), _pr(number=2, head="y")],
            forrige_head_sha="gammel",
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)

    # ─── 10: ukjent trigger-etikett ─────────────────────────────────────

    def test_10_ukjent_trigger_label_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:approved", prs=[_pr()],
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)
        self.assertIn("Ukjent trigger-etikett", begrunnelse)

    # ─── 11: CLI-kontrakten workflowen faktisk bruker ───────────────────

    def _kjor_cli(self, env, stdin_json):
        fullt_env = dict(os.environ)
        fullt_env.update(env)
        return subprocess.run(
            [sys.executable, _SCRIPT], input=stdin_json,
            capture_output=True, text=True, env=fullt_env,
        )

    def test_11_cli_skriver_ok_true_og_pr_number_for_gyldig_leveranse(self):
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:ready"},
            '[{"number": 7, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "abc", "additions": 10, "deletions": 1, "changedFiles": 2}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=true", res.stdout)
        self.assertIn("pr_number=7", res.stdout)

    def test_11b_cli_skriver_ok_false_for_issue_11_situasjonen(self):
        res = self._kjor_cli({"TRIGGER_LABEL": "status:ready"}, "[]")
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)
        self.assertNotIn("pr_number=", res.stdout)
        self.assertIn("Ingen åpen PR", res.stderr)

    def test_11c_cli_bruker_before_head_sha_for_changes_requested(self):
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:changes-requested", "BEFORE_HEAD_SHA": "old"},
            '[{"number": 3, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "new", "additions": 1, "deletions": 0, "changedFiles": 1}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=true", res.stdout)
        self.assertIn("pr_number=3", res.stdout)

    def test_11d_cli_tolererer_tom_stdin(self):
        res = self._kjor_cli({"TRIGGER_LABEL": "status:ready"}, "")
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)


if __name__ == "__main__":
    unittest.main()
