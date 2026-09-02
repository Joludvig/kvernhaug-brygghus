"""
Kvernhaug Agent Bridge V1.1 -- regresjonstester for trigger-autorisasjon
(.github/scripts/trigger_guard.py, issue #9).

Kjernetesten er `test_1_...`: NØYAKTIG racet som ble observert på issue
#8 -- `status:ready` ble lagt på FØR `agent:claude`, runneren startet
noen sekunder senere, og live-tilstanden inneholdt da begge. V1
godkjente den kjøringen. V1.1 skal avvise den permanent, fordi
`agent:claude` ikke lå i etikettene på selve EVENT-tidspunktet.

Ren stdlib-test, ingen GitHub-kall, ingen bash/YAML-avhengighet --
kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests`).
"""
import importlib.util
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "trigger_guard.py")


def _last_modul():
    """Laster .github/scripts/trigger_guard.py direkte fra sti -- den
    ligger bevisst utenfor Python-pakkestrukturen (workflow-hjelper,
    ikke app-modul), samme mønster som
    tests/test_agent_bridge_labels.py bruker."""
    spec = importlib.util.spec_from_file_location("trigger_guard", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_TG = _last_modul()

_EIER = "Joludvig"


def _issue_event(**overstyr):
    """Standard, GYLDIG issues:labeled-kontekst -- testene overstyrer
    bare det ene feltet de faktisk handler om."""
    kontekst = {
        "event_name": "issues",
        "event_action": "labeled",
        "event_label": "status:ready",
        "event_labels": ["agent:claude", "area:infra", "status:ready"],
        "live_labels": ["agent:claude", "area:infra", "status:ready"],
        "sender_login": _EIER,
        "sender_type": "User",
        "repo_owner": _EIER,
    }
    kontekst.update(overstyr)
    return kontekst


class TestTriggerGuard(unittest.TestCase):
    # ─── 1: SELVE BUGEN (issue #8-racet) ────────────────────────────────

    def test_1_agent_lagt_til_ETTER_trigger_event_avvises_permanent(self):
        # Event-tidspunkt: bare status:ready (+ area), INGEN agent:claude.
        # Live-tilstand noen sekunder senere: begge -- akkurat som #8.
        proceed, etikett, begrunnelse = _TG.vurder_trigger(**_issue_event(
            event_labels=["area:infra", "status:ready"],
            live_labels=["agent:claude", "area:infra", "status:ready"],
        ))
        self.assertFalse(proceed, f"Racet fra issue #8 skal avvises. Begrunnelse: {begrunnelse}")
        self.assertIsNone(etikett)
        self.assertIn("agent:claude", begrunnelse)

    def test_1b_samme_race_for_changes_requested(self):
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(
            event_label="status:changes-requested",
            event_labels=["area:infra", "status:changes-requested"],
            live_labels=["agent:claude", "area:infra", "status:changes-requested"],
        ))
        self.assertFalse(proceed)

    def test_1c_tomt_event_snapshot_avvises(self):
        # Defensivt: mangler event-etiketter helt (uventet payload-form)
        # -> ingen autorisasjon, aldri "anta at det var greit".
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(event_labels=[]))
        self.assertFalse(proceed)
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(event_labels=None))
        self.assertFalse(proceed)

    # ─── 2: den gyldige veien ───────────────────────────────────────────

    def test_2_autorisert_naar_agent_var_med_bade_pa_event_og_live(self):
        proceed, etikett, _ = _TG.vurder_trigger(**_issue_event())
        self.assertTrue(proceed)
        self.assertEqual(etikett, "status:ready")

    def test_2b_autorisert_for_changes_requested(self):
        proceed, etikett, _ = _TG.vurder_trigger(**_issue_event(
            event_label="status:changes-requested",
            event_labels=["agent:claude", "status:changes-requested"],
            live_labels=["agent:claude", "status:changes-requested"],
        ))
        self.assertTrue(proceed)
        self.assertEqual(etikett, "status:changes-requested")

    # ─── 3: live-tilstanden forsvant mellom event og guard ──────────────

    def test_3_agent_fjernet_live_for_guard_kjorte_avvises(self):
        proceed, _, begrunnelse = _TG.vurder_trigger(**_issue_event(
            live_labels=["area:infra", "status:ready"],  # agent:claude fjernet (disarmet)
        ))
        self.assertFalse(proceed)
        self.assertIn("live", begrunnelse.lower())

    def test_3b_trigger_status_fjernet_live_avvises(self):
        # En tidligere/samtidig kjøring har allerede flyttet tilstanden.
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(
            live_labels=["agent:claude", "area:infra", "status:working"],
        ))
        self.assertFalse(proceed)

    def test_3c_annet_trigger_event_enn_det_som_ligger_live_avvises(self):
        # Eventet gjaldt status:ready, men live har kun
        # status:changes-requested -- da er DETTE eventet ikke lenger
        # gjeldende (V1 ville feilaktig godtatt via sin "ready ellers
        # changes-requested"-utledning fra live).
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(
            event_label="status:ready",
            event_labels=["agent:claude", "status:ready"],
            live_labels=["agent:claude", "status:changes-requested"],
        ))
        self.assertFalse(proceed)

    # ─── 4: urelaterte etiketter / feil aktør ───────────────────────────

    def test_4_urelatert_etikett_trigger_aldri(self):
        for etikett in ("area:infra", "agent:claude", "status:working", "status:review",
                        "status:approved", "enhancement"):
            proceed, _, _ = _TG.vurder_trigger(**_issue_event(
                event_label=etikett,
                event_labels=["agent:claude", etikett],
                live_labels=["agent:claude", etikett, "status:ready"],
            ))
            self.assertFalse(proceed, f"{etikett} skal aldri trigge en kjøring")

    def test_4b_annen_event_action_enn_labeled_avvises(self):
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(event_action="unlabeled"))
        self.assertFalse(proceed)

    def test_4c_ikke_eier_avvises(self):
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(sender_login="en-annen-bruker"))
        self.assertFalse(proceed)

    def test_4d_bot_aktor_avvises(self):
        proceed, _, _ = _TG.vurder_trigger(**_issue_event(
            sender_login=_EIER, sender_type="Bot",
        ))
        self.assertFalse(proceed)

    # ─── 5: workflow_dispatch -- uendret V1-semantikk ───────────────────

    def test_5_dispatch_autoriseres_pa_live_tilstand_uten_event_snapshot(self):
        # Manuell kjøring er allerede portvoktet av GitHub (write-tilgang)
        # -- event-snapshot-kravet gjelder IKKE her, per issue #9.
        proceed, etikett, _ = _TG.vurder_trigger(
            event_name="workflow_dispatch",
            live_labels=["agent:claude", "area:infra", "status:ready"],
        )
        self.assertTrue(proceed)
        self.assertEqual(etikett, "status:ready")

    def test_5b_dispatch_krever_fortsatt_agent_claude_live(self):
        proceed, _, _ = _TG.vurder_trigger(
            event_name="workflow_dispatch",
            live_labels=["area:infra", "status:ready"],
        )
        self.assertFalse(proceed)

    def test_5c_dispatch_uten_trigger_status_live_avvises(self):
        proceed, _, _ = _TG.vurder_trigger(
            event_name="workflow_dispatch",
            live_labels=["agent:claude", "status:review"],
        )
        self.assertFalse(proceed)

    def test_5d_dispatch_changes_requested_live(self):
        proceed, etikett, _ = _TG.vurder_trigger(
            event_name="workflow_dispatch",
            live_labels=["agent:claude", "status:changes-requested"],
        )
        self.assertTrue(proceed)
        self.assertEqual(etikett, "status:changes-requested")

    # ─── 6: CLI-kontrakten workflowen faktisk bruker ────────────────────

    def _kjor_cli(self, env):
        fullt_env = dict(os.environ)
        fullt_env.update(env)
        return subprocess.run(
            [sys.executable, _SCRIPT], capture_output=True, text=True, env=fullt_env,
        )

    def test_6_cli_skriver_proceed_true_og_trigger_label(self):
        res = self._kjor_cli({
            "EVENT_NAME": "issues", "EVENT_ACTION": "labeled",
            "LABEL_NAME": "status:ready",
            "EVENT_LABELS": '["agent:claude","status:ready"]',
            "LIVE_LABELS": '["agent:claude","status:ready"]',
            "SENDER_LOGIN": _EIER, "SENDER_TYPE": "User", "REPO_OWNER": _EIER,
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("proceed=true", res.stdout)
        self.assertIn("trigger_label=status:ready", res.stdout)

    def test_6b_cli_skriver_proceed_false_for_race_og_ingen_trigger_label(self):
        res = self._kjor_cli({
            "EVENT_NAME": "issues", "EVENT_ACTION": "labeled",
            "LABEL_NAME": "status:ready",
            "EVENT_LABELS": '["status:ready"]',            # racet: ingen agent:claude
            "LIVE_LABELS": '["agent:claude","status:ready"]',
            "SENDER_LOGIN": _EIER, "SENDER_TYPE": "User", "REPO_OWNER": _EIER,
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("proceed=false", res.stdout)
        self.assertNotIn("trigger_label=", res.stdout)
        self.assertIn("agent:claude", res.stderr)  # begrunnelsen havner i loggen


if __name__ == "__main__":
    unittest.main()
