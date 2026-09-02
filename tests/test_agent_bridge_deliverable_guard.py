"""
Kvernhaug Agent Bridge V1.2 -- regresjonstester for leveranse-
verifisering (.github/scripts/deliverable_guard.py, issue #12).

Kjernetesten er `test_1_...`: NØYAKTIG situasjonen observert på issue
#11 -- Claude-prosessen returnerte `subtype: success`, men ingen
branch/PR/kommentar/fil ble faktisk levert. V1 flyttet issuen til
`status:review` likevel. V1.2 skal nekte, fordi det ikke finnes noen
åpen PR mot master å vise til.

`test_3c`/`test_3d`/`test_11e` dekker Chief-reviewets tredje runde (PR
#13): siden branch-navnet er BEVISST deterministisk og gjenbrukbart
gjennom hele issuens levetid, kan en tidligere mislykket/avbrutt/manuell
kjøring ha etterlatt en åpen PR med ikke-tomt diff på nøyaktig den
branchen. En etterfølgende status:ready-kjøring skal ALDRI kunne bli
godkjent på DEN PR-en, uansett diff-innhold eller om HEAD endret seg
underveis -- en PR som lå der FØR kjøringen startet er per definisjon
ikke bevis for hva DENNE kjøringen leverte.

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

    def test_3b_ready_ingen_preeksisterende_pr_og_ny_ikke_tom_pr_godkjennes(self):
        # Samme som test_3, men eksplisitt med forrige_head_sha="" slik
        # CLI-en faktisk mottar den fra en tom BEFORE_HEAD_SHA -- den
        # normale, tilsiktede happy-pathen etter Chief-reviewets runde 3.
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(additions=12, deletions=0, changed_files=2)],
            forrige_head_sha="",
        )
        self.assertTrue(ok, begrunnelse)
        self.assertEqual(nummer, 42)

    # ─── 3c/3d: KJERNEN I RUNDE 3-FIKSEN -- pre-eksisterende PR avvises ──
    # (Chief review, PR #13: en deterministisk, gjenbrukbar branch kan ha
    # en PR liggende igjen fra en tidligere mislykket/manuell kjøring --
    # en fersk status:ready-kjøring skal ALDRI kunne bli godkjent på den
    # gamle PR-en, uansett diff-innhold eller om HEAD endret seg.)

    def test_3c_ready_preeksisterende_pr_med_samme_head_etter_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(head="uendret-sha", additions=50, deletions=5, changed_files=4)],
            forrige_head_sha="uendret-sha",
        )
        self.assertFalse(ok, "En PR som lå der FØR kjøringen startet skal aldri godkjennes for status:ready.")
        self.assertEqual(nummer, 42)
        self.assertIn("FØR kjøringen startet", begrunnelse)

    def test_3d_ready_preeksisterende_pr_selv_med_endret_head_avvises(self):
        # Selv om HEAD FAKTISK endret seg underveis, er selve det at en
        # PR lå der FØR kjøringen startet nok til å avvise -- policyen er
        # "status:ready starter fra en ren branch", ikke "krev bevist
        # HEAD-endring" (den semantikken er reservert for
        # status:changes-requested).
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:ready",
            prs=[_pr(head="ny-sha-etter-kjoring", additions=50, deletions=5, changed_files=4)],
            forrige_head_sha="gammel-sha-for-kjoring",
        )
        self.assertFalse(ok, begrunnelse)
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
            prs=[_pr(number=42, head="samme-sha")],
            forrige_head_sha="samme-sha",
            forrige_pr_nummer=42,
        )
        self.assertFalse(ok)
        self.assertEqual(nummer, 42)
        self.assertIn("uendret", begrunnelse)

    def test_9_changes_requested_endret_head_godkjennes(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=42, head="ny-sha-etter-push")],
            forrige_head_sha="gammel-sha-for-run",
            forrige_pr_nummer=42,
        )
        self.assertTrue(ok, begrunnelse)
        self.assertEqual(nummer, 42)

    def test_9b_changes_requested_flere_kandidater_avvises(self):
        ok, nummer, _ = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=1, head="x"), _pr(number=2, head="y")],
            forrige_head_sha="gammel",
            forrige_pr_nummer=1,
        )
        self.assertFalse(ok)
        self.assertIsNone(nummer)

    # ─── 9c-9e: KJERNEN I RUNDE 4-FIKSEN -- PR-IDENTITET, ikke bare HEAD ─
    # (Chief review, PR #13: allowlisten gir fortsatt `gh pr edit`/
    # `gh pr create`, så porten må bekrefte at det faktisk er SAMME PR
    # som fikk de nye commit-ene, ikke bare at "en eller annen PR" på
    # branchen har en annen HEAD-SHA enn før.)

    def test_9c_changes_requested_samme_pr_nummer_og_endret_head_godkjennes(self):
        # Reviewets eksplisitte happy-path-krav: samme PR + endret head => pass.
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=42, head="ny-sha")],
            forrige_head_sha="gammel-sha",
            forrige_pr_nummer=42,
        )
        self.assertTrue(ok, begrunnelse)
        self.assertEqual(nummer, 42)

    def test_9d_changes_requested_annet_pr_nummer_selv_med_endret_head_avvises(self):
        # Reviewets eksplisitte kjernekrav: en ANNEN PR på samme branch,
        # selv med en HEAD-SHA som avviker fra forrige_head_sha, skal
        # ALDRI godkjennes som om det var oppfølgingen av den opprinnelige.
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=99, head="en-helt-annen-sha")],
            forrige_head_sha="gammel-sha-for-pr-42",
            forrige_pr_nummer=42,
        )
        self.assertFalse(ok, "Ulik PR-identitet skal aldri godkjennes, uansett HEAD-endring.")
        self.assertEqual(nummer, 99)
        self.assertIn("PR-identiteten endret seg", begrunnelse)

    def test_9e_changes_requested_manglende_forrige_pr_nummer_avvises(self):
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=42, head="ny-sha")],
            forrige_head_sha="gammel-sha",
            forrige_pr_nummer=None,
        )
        self.assertFalse(ok)
        self.assertEqual(nummer, 42)
        self.assertIn("ingen PR-nummer", begrunnelse)

    def test_9f_changes_requested_pr_nummer_som_streng_matcher_int(self):
        # Workflowen sender BEFORE_PR_NUMBER som en shell-streng via
        # miljøvariabler; PR-listens `number`-felt er derimot et
        # JSON-heltall. Sammenligningen må ikke feile pga. typeforskjell.
        ok, nummer, begrunnelse = _DG.vurder_leveranse(
            trigger_label="status:changes-requested",
            prs=[_pr(number=42, head="ny-sha")],
            forrige_head_sha="gammel-sha",
            forrige_pr_nummer="42",
        )
        self.assertTrue(ok, begrunnelse)
        self.assertEqual(nummer, 42)

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
        # BEFORE_HEAD_SHA eksplisitt tom -- ingen PR lå der før kjøringen
        # startet, den normale status:ready happy-pathen.
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:ready", "BEFORE_HEAD_SHA": ""},
            '[{"number": 7, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "abc", "additions": 10, "deletions": 1, "changedFiles": 2}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=true", res.stdout)
        self.assertIn("pr_number=7", res.stdout)

    def test_11b_cli_skriver_ok_false_for_issue_11_situasjonen(self):
        res = self._kjor_cli({"TRIGGER_LABEL": "status:ready", "BEFORE_HEAD_SHA": ""}, "[]")
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)
        self.assertNotIn("pr_number=", res.stdout)
        self.assertIn("Ingen åpen PR", res.stderr)

    def test_11e_cli_avviser_ready_med_preeksisterende_pr_selv_om_prosessen_lyktes(self):
        # Chief review, PR #13 runde 3: workflowen setter BEFORE_HEAD_SHA
        # fra "Capture pre-run PR state" UANSETT trigger-etikett -- denne
        # testen er den ende-til-ende CLI-kontrakten for selve
        # rettelsen (en PR som lå der FØR en status:ready-kjøring skal
        # aldri godkjennes, uansett diff).
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:ready", "BEFORE_HEAD_SHA": "sha-fra-for-kjoringen"},
            '[{"number": 9, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "sha-fra-for-kjoringen", "additions": 40, "deletions": 2, "changedFiles": 3}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)
        self.assertIn("FØR kjøringen startet", res.stderr)

    def test_11c_cli_bruker_before_head_sha_for_changes_requested(self):
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:changes-requested", "BEFORE_HEAD_SHA": "old", "BEFORE_PR_NUMBER": "3"},
            '[{"number": 3, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "new", "additions": 1, "deletions": 0, "changedFiles": 1}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=true", res.stdout)
        self.assertIn("pr_number=3", res.stdout)

    def test_11f_cli_avviser_annen_pr_selv_med_endret_head(self):
        # Chief review, PR #13 runde 4: den ende-til-ende CLI-kontrakten
        # for identitetssjekken -- BEFORE_PR_NUMBER=3, men PR-en
        # workflowen faktisk finner etterpå er #8 (f.eks. fordi den
        # opprinnelige PR-ens base ble endret og en ny PR ble opprettet
        # mot master fra samme branch) -- skal ALDRI godkjennes.
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:changes-requested", "BEFORE_HEAD_SHA": "old", "BEFORE_PR_NUMBER": "3"},
            '[{"number": 8, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "new", "additions": 1, "deletions": 0, "changedFiles": 1}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)
        self.assertIn("pr_number=8", res.stdout)
        self.assertIn("PR-identiteten endret seg", res.stderr)

    def test_11g_cli_avviser_changes_requested_uten_before_pr_number(self):
        res = self._kjor_cli(
            {"TRIGGER_LABEL": "status:changes-requested", "BEFORE_HEAD_SHA": "old", "BEFORE_PR_NUMBER": ""},
            '[{"number": 3, "state": "OPEN", "baseRefName": "master", '
            '"headRefOid": "new", "additions": 1, "deletions": 0, "changedFiles": 1}]',
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)
        self.assertIn("ingen PR-nummer", res.stderr)

    def test_11d_cli_tolererer_tom_stdin(self):
        res = self._kjor_cli({"TRIGGER_LABEL": "status:ready"}, "")
        self.assertEqual(res.returncode, 0)
        self.assertIn("ok=false", res.stdout)


if __name__ == "__main__":
    unittest.main()
