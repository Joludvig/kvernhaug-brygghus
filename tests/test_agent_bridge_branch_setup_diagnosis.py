"""
Kvernhaug Agent Bridge V1.7 -- regresjonstester for
.github/scripts/branch_setup_diagnosis.py (issue #259).

Kjernetesten er `test_1_...`: gjenskaper nøyaktig #257s fingeravtrykk
(status:ready, INGEN remote branch etter en "success"-kjøring) og
forventer diagnosen `branch_never_pushed` -- den skal ALDRI kunne
forveksles med et bevisst Claude-valg om å ikke gjøre endringer.

Ren stdlib-test, ingen GitHub-kall, ingen bash/YAML-avhengighet --
kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests`).
"""
import importlib.util
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "branch_setup_diagnosis.py")


def _last_modul():
    spec = importlib.util.spec_from_file_location("branch_setup_diagnosis", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_BSD = _last_modul()


class TestBranchSetupDiagnosis(unittest.TestCase):
    # ─── 1: KJERNEN -- #257s eksakte fingeravtrykk ───────────────────────

    def test_1_status_ready_ingen_remote_branch_gir_branch_never_pushed(self):
        diagnosis, reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:ready",
            remote_branch_finnes=False,
        )
        self.assertEqual(diagnosis, "branch_never_pushed")
        self.assertIn("257", reason)

    def test_1b_branch_never_pushed_nevner_ikke_bevisst_valg_som_arsak(self):
        _diagnosis, reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:ready",
            remote_branch_finnes=False,
        )
        self.assertIn("IKKE et bevisst valg", reason)

    # ─── 2: status:ready, branch finnes -- IKKE et tillatelsesproblem ────

    def test_2_status_ready_remote_branch_finnes_gir_branch_pushed_no_pr(self):
        diagnosis, reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:ready",
            remote_branch_finnes=True,
        )
        self.assertEqual(diagnosis, "branch_pushed_no_pr")
        self.assertNotIn("avvist av tillatelsesmodellen", reason)

    # ─── 3: status:changes-requested -- branch-eksistens beviser ingenting ──

    def test_3_changes_requested_med_forrige_tilstand_gir_no_new_commits(self):
        diagnosis, _reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:changes-requested",
            remote_branch_finnes=True,
            forrige_pr_nummer="42",
            forrige_head_sha="abc123",
        )
        self.assertEqual(diagnosis, "no_new_commits")

    def test_3b_changes_requested_uten_forrige_tilstand_gir_missing_prior_state(self):
        diagnosis, _reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:changes-requested",
            remote_branch_finnes=True,
        )
        self.assertEqual(diagnosis, "missing_prior_state")

    def test_3c_changes_requested_bruker_ikke_remote_branch_finnes_alene(self):
        # Selv om remote_branch_finnes=False, skal changes-requested ALDRI
        # returnere branch_never_pushed -- den diagnosen er kun gyldig for
        # status:ready, siden en changes-requested-branch alltid forventes
        # å eksistere fra en TIDLIGERE runde.
        diagnosis, _reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:changes-requested",
            remote_branch_finnes=False,
            forrige_pr_nummer="42",
            forrige_head_sha="abc123",
        )
        self.assertNotEqual(diagnosis, "branch_never_pushed")

    # ─── 4: ukjent trigger-etikett ────────────────────────────────────────

    def test_4_ukjent_trigger_etikett_gir_unknown_trigger(self):
        diagnosis, _reason = _BSD.diagnoser_manglende_leveranse(
            trigger_label="status:approved",
            remote_branch_finnes=False,
        )
        self.assertEqual(diagnosis, "unknown_trigger")

    # ─── 5: CLI-kontrakten workflowen faktisk bruker ────────────────────

    def _kjor_cli(self, env_overrides):
        env = dict(os.environ)
        env.update(env_overrides)
        return subprocess.run(
            [sys.executable, _SCRIPT], capture_output=True, text=True, env=env,
        )

    def test_5_cli_skriver_github_output_linjer(self):
        res = self._kjor_cli({"TRIGGER_LABEL": "status:ready", "REMOTE_BRANCH_EXISTS": "false"})
        self.assertEqual(res.returncode, 0)
        self.assertIn("diagnosis=branch_never_pushed", res.stdout)
        self.assertIn("reason=", res.stdout)

    def test_5b_cli_tolker_remote_branch_exists_case_insensitivt(self):
        res = self._kjor_cli({"TRIGGER_LABEL": "status:ready", "REMOTE_BRANCH_EXISTS": "True"})
        self.assertEqual(res.returncode, 0)
        self.assertIn("diagnosis=branch_pushed_no_pr", res.stdout)

    def test_5c_cli_manglende_env_er_trygt_default(self):
        env = dict(os.environ)
        env.pop("TRIGGER_LABEL", None)
        env.pop("REMOTE_BRANCH_EXISTS", None)
        env.pop("BEFORE_PR_NUMBER", None)
        env.pop("BEFORE_HEAD_SHA", None)
        res = subprocess.run([sys.executable, _SCRIPT], capture_output=True, text=True, env=env)
        self.assertEqual(res.returncode, 0)
        self.assertIn("diagnosis=unknown_trigger", res.stdout)


if __name__ == "__main__":
    unittest.main()
