"""
Kvernhaug Agent Bridge -- regresjonstester for GO/NO-GO-varselets
trigger-autorisasjon (.github/scripts/approved_notify_guard.py,
issue #66).

Speiler tests/test_agent_bridge_trigger_guard.py sitt mønster og dekker
samme klasse race/aktør-sperrer, men for det ENE `status:approved`-
eventet denne modulen portvokter (se moduldocstringen i
approved_notify_guard.py for hvorfor dette er en bevisst duplisert,
énetikett-variant av trigger_guard.py -- ikke en gjenbruk).

Ren stdlib-test, ingen GitHub-kall -- kjøres av den vanlige suiten
(`py -3 -m unittest discover -s tests -b`).
"""
import importlib.util
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "approved_notify_guard.py")


def _last_modul():
    spec = importlib.util.spec_from_file_location("approved_notify_guard", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_ANG = _last_modul()

_EIER = "Joludvig"


def _issue_event(**overstyr):
    kontekst = {
        "event_name": "issues",
        "event_action": "labeled",
        "event_label": "status:approved",
        "event_labels": ["agent:claude", "area:infra", "status:approved"],
        "live_labels": ["agent:claude", "area:infra", "status:approved"],
        "sender_login": _EIER,
        "sender_type": "User",
        "repo_owner": _EIER,
    }
    kontekst.update(overstyr)
    return kontekst


class TestApprovedNotifyGuard(unittest.TestCase):
    # ─── samme race som issue #8/#9, for status:approved ─────────────────

    def test_1_agent_lagt_til_etter_trigger_event_avvises_permanent(self):
        proceed, begrunnelse = _ANG.vurder_notify_trigger(**_issue_event(
            event_labels=["area:infra", "status:approved"],
            live_labels=["agent:claude", "area:infra", "status:approved"],
        ))
        self.assertFalse(proceed, f"Racet skal avvises. Begrunnelse: {begrunnelse}")
        self.assertIn("agent:claude", begrunnelse)

    def test_1b_tomt_event_snapshot_avvises(self):
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(event_labels=[]))
        self.assertFalse(proceed)
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(event_labels=None))
        self.assertFalse(proceed)

    # ─── den gyldige veien ─────────────────────────────────────────────

    def test_2_autorisert_naar_agent_var_med_bade_pa_event_og_live(self):
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event())
        self.assertTrue(proceed)

    # ─── live-tilstanden forsvant mellom event og guard ──────────────────

    def test_3_agent_fjernet_live_for_guard_kjorte_avvises(self):
        proceed, begrunnelse = _ANG.vurder_notify_trigger(**_issue_event(
            live_labels=["area:infra", "status:approved"],
        ))
        self.assertFalse(proceed)
        self.assertIn("live", begrunnelse.lower())

    def test_3b_status_approved_fjernet_live_avvises(self):
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(
            live_labels=["agent:claude", "area:infra", "status:review"],
        ))
        self.assertFalse(proceed)

    # ─── urelaterte etiketter / feil aktør / feil event ──────────────────

    def test_4_urelatert_etikett_trigger_aldri(self):
        for etikett in ("area:infra", "agent:claude", "status:working", "status:review",
                         "status:ready", "status:changes-requested", "enhancement"):
            proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(
                event_label=etikett,
                event_labels=["agent:claude", etikett],
                live_labels=["agent:claude", etikett, "status:approved"],
            ))
            self.assertFalse(proceed, f"{etikett} skal aldri trigge et varsel")

    def test_4b_annen_event_action_enn_labeled_avvises(self):
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(event_action="unlabeled"))
        self.assertFalse(proceed)

    def test_4c_ikke_eier_avvises(self):
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(sender_login="en-annen-bruker"))
        self.assertFalse(proceed)

    def test_4d_bot_aktor_avvises(self):
        proceed, _ = _ANG.vurder_notify_trigger(**_issue_event(sender_login=_EIER, sender_type="Bot"))
        self.assertFalse(proceed)

    def test_4e_workflow_dispatch_avvises(self):
        # I motsetning til trigger_guard.py (V1s workflow_dispatch-
        # testvei) støtter GO/NO-GO-varselet KUN issues:labeled -- se
        # claude-agent-bridge.yml, notify_guard-jobbens `if:`.
        proceed, _ = _ANG.vurder_notify_trigger(
            event_name="workflow_dispatch",
            live_labels=["agent:claude", "status:approved"],
        )
        self.assertFalse(proceed)

    # ─── CLI-kontrakten workflowen faktisk bruker ────────────────────────

    def _kjor_cli(self, env):
        fullt_env = dict(os.environ)
        fullt_env.update(env)
        return subprocess.run(
            [sys.executable, _SCRIPT], capture_output=True, text=True, env=fullt_env,
        )

    def test_5_cli_skriver_proceed_true(self):
        res = self._kjor_cli({
            "EVENT_NAME": "issues", "EVENT_ACTION": "labeled",
            "LABEL_NAME": "status:approved",
            "EVENT_LABELS": '["agent:claude","status:approved"]',
            "LIVE_LABELS": '["agent:claude","status:approved"]',
            "SENDER_LOGIN": _EIER, "SENDER_TYPE": "User", "REPO_OWNER": _EIER,
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("proceed=true", res.stdout)

    def test_5b_cli_skriver_proceed_false_for_race(self):
        res = self._kjor_cli({
            "EVENT_NAME": "issues", "EVENT_ACTION": "labeled",
            "LABEL_NAME": "status:approved",
            "EVENT_LABELS": '["status:approved"]',
            "LIVE_LABELS": '["agent:claude","status:approved"]',
            "SENDER_LOGIN": _EIER, "SENDER_TYPE": "User", "REPO_OWNER": _EIER,
        })
        self.assertEqual(res.returncode, 0)
        self.assertIn("proceed=false", res.stdout)
        self.assertIn("agent:claude", res.stderr)


if __name__ == "__main__":
    unittest.main()
