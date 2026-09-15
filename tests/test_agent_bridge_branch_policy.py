"""
Kvernhaug Agent Bridge V1.2 -- regresjonstester for den faste
branch-navn-/push-policyen (.github/scripts/branch_policy.py), skrevet
for å lukke de to blokkerende punktene fra Chief-reviewet på PR #13:

1. `Bash(git push *)` håndhevet ikke "ingen push til master" -- enhver
   refspec/flagg-variant matchet regelen. `test_4_...` er kjernetesten:
   ingen av en rekke master-target-varianter skal noen gang være
   tekstlik identisk med en av de to eksakte push-strengene policyen
   produserer.
2. Leveranse-porten fant PR-er via issue-tidslinjens tekst-heuristikk,
   som kunne mislykkes for en helt korrekt PR. `test_6_...` verifiserer
   at `gh pr list`-kallet workflowen faktisk bruker filtrerer på
   head/base/state -- den "samme mekanismen" happy-path-et skal
   oppdages med.

Ren stdlib-test, ingen GitHub- eller Claude Code-kall, ingen
bash/YAML-avhengighet -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests`).
"""
import importlib.util
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "branch_policy.py")


def _last_modul():
    """Laster .github/scripts/branch_policy.py direkte fra sti -- samme
    mønster som de andre .github/scripts-testene i denne suiten bruker
    for workflow-hjelpere som bevisst ligger utenfor
    Python-pakkestrukturen."""
    spec = importlib.util.spec_from_file_location("branch_policy", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_BP = _last_modul()

# Adversariske push-kommandostrenger en Claude-kjøring i teorien kunne
# forsøke -- ingen av disse skal noen gang være tekstlik identisk med
# en av de to reglene tillatte_push_kommandoer() returnerer for
# "agent/issue-12".
_MASTER_TARGETING_FORSOK = (
    "git push origin master",
    "git push -u origin master",
    "git push origin HEAD:master",
    "git push origin agent/issue-12:master",
    "git push --force origin agent/issue-12:master",
    "git push -f origin agent/issue-12:master",
    "git push origin agent/issue-12 master",
    "git push origin master:agent/issue-12",
    "git push --all origin",
    "git push origin agent/issue-99",  # feil issue -- en annen branch
    "git push",
)


class TestBranchPolicy(unittest.TestCase):
    # ─── 1: branch-navnet er deterministisk og issue-spesifikt ─────────

    def test_1_navn_er_deterministisk(self):
        self.assertEqual(_BP.agent_branch_navn(12), "agent/issue-12")
        self.assertEqual(_BP.agent_branch_navn(12), _BP.agent_branch_navn(12))

    def test_1b_ulike_issuer_gir_ulike_navn(self):
        self.assertNotEqual(_BP.agent_branch_navn(12), _BP.agent_branch_navn(13))

    def test_1c_streng_issue_nummer_fungerer_som_fra_cli(self):
        # Workflowen sender issue-nummeret som en shell-streng (fra
        # $ISSUE), ikke et Python-int.
        self.assertEqual(_BP.agent_branch_navn("12"), "agent/issue-12")

    # ─── 2: tillatte_push_kommandoer -- formen ──────────────────────────

    def test_2_tillatte_push_kommandoer_har_nøyaktig_forventet_form(self):
        self.assertEqual(
            _BP.tillatte_push_kommandoer("agent/issue-12"),
            ("git push -u origin agent/issue-12", "git push origin agent/issue-12"),
        )

    def test_2b_kan_aldri_bygges_for_master_selv(self):
        with self.assertRaises(ValueError):
            _BP.tillatte_push_kommandoer("master")

    # ─── 3: happy path -- de faktiske kommandoene MÅ matche ────────────

    def test_3_de_faktiske_push_kommandoene_er_i_tillatt_settet(self):
        tillatt = _BP.tillatte_push_kommandoer("agent/issue-12")
        self.assertIn("git push -u origin agent/issue-12", tillatt)
        self.assertIn("git push origin agent/issue-12", tillatt)

    # ─── 4: KJERNEN I BLOKKER 1 -- ingen master-target matcher noensinne ─

    def test_4_ingen_master_targeting_forsok_matcher_en_tillatt_streng(self):
        tillatt = _BP.tillatte_push_kommandoer("agent/issue-12")
        for forsok in _MASTER_TARGETING_FORSOK:
            self.assertNotIn(
                forsok, tillatt,
                f"{forsok!r} skal IKKE være en tillatt push-kommando -- dette er nøyaktig "
                "hullet Chief-reviewet på PR #13 påpekte (Bash(git push *) håndhevet ikke "
                "'ingen push til master').",
            )

    def test_4b_gjelder_for_flere_ulike_issue_branches(self):
        for issue in (1, 42, 9999):
            navn = _BP.agent_branch_navn(issue)
            tillatt = _BP.tillatte_push_kommandoer(navn)
            self.assertNotIn("git push origin master", tillatt)
            self.assertNotIn("git push -u origin master", tillatt)

    # ─── 5: CLI-kontrakten workflowen faktisk bruker ────────────────────

    def _kjor_cli(self, *argv):
        return subprocess.run(
            [sys.executable, _SCRIPT, *argv], capture_output=True, text=True,
        )

    def test_5_cli_skriver_branch_navn(self):
        res = self._kjor_cli("12")
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "agent/issue-12")

    def test_5b_cli_avviser_ugyldig_issue_nummer(self):
        res = self._kjor_cli("ikke-et-tall")
        self.assertNotEqual(res.returncode, 0)

    def test_5c_cli_krever_nøyaktig_ett_argument(self):
        res = self._kjor_cli()
        self.assertNotEqual(res.returncode, 0)

    # ─── 6: KJERNEN I BLOKKER 2 -- gh pr list-kallet filtrerer riktig ───

    def test_6_gh_pr_list_args_filtrerer_pa_head_base_state(self):
        args = _BP.gh_pr_list_args("Joludvig/kvernhaug-brygghus", "agent/issue-12")
        self.assertEqual(args[0:2], ["pr", "list"])
        self.assertIn("--repo", args)
        self.assertEqual(args[args.index("--repo") + 1], "Joludvig/kvernhaug-brygghus")
        self.assertIn("--head", args)
        self.assertEqual(args[args.index("--head") + 1], "agent/issue-12")
        self.assertIn("--base", args)
        self.assertEqual(args[args.index("--base") + 1], "master")
        self.assertIn("--state", args)
        self.assertEqual(args[args.index("--state") + 1], "open")

    def test_6b_gh_pr_list_args_ber_om_feltene_deliverable_guard_trenger(self):
        args = _BP.gh_pr_list_args("owner/repo", "agent/issue-7")
        self.assertIn("--json", args)
        felter = args[args.index("--json") + 1]
        for felt in ("number", "state", "baseRefName", "headRefOid",
                     "additions", "deletions", "changedFiles"):
            self.assertIn(felt, felter)

    def test_6c_ulike_branches_gir_ulikt_head_filter(self):
        a = _BP.gh_pr_list_args("owner/repo", "agent/issue-1")
        b = _BP.gh_pr_list_args("owner/repo", "agent/issue-2")
        self.assertNotEqual(
            a[a.index("--head") + 1],
            b[b.index("--head") + 1],
        )


if __name__ == "__main__":
    unittest.main()
