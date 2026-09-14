"""
Kvernhaug Agent Bridge -- regresjonstester for PÅ JOBB-køens
utvelgelseslogikk (.github/scripts/queue_dispatch.py, issue #260).

Dekker issue #260s ti akseptansetester direkte (se test-navnene under):
  1. tom kø -> ingen handling
  2. ett kvalifisert element -> nøyaktig én dispatch
  3. flere elementer -> kun det første starter
  4. et aktivt/working-element -> nummer to starter ikke
  5. det første når status:review -> neste kan starte
  6. failed/no-deliverable/owner-decision-tilstand -> køen pauser
  7. duplikat-event -> ingen duplikat Claude-kjøring
  8. en ikke-kø-issue ignoreres
  10. dispatch-stien bevarer live-state-kravet (status:ready teller som
      "aktiv", ikke "ikke_startet")
(9, "no merge/deploy path exists", er et fravær-av-kode-bevis --
dekket av at denne modulen aldri kaller gh/git i det hele tatt, se
tests/test_agent_bridge_permission_config.py for tilsvarende
fravær-bevis på selve broen.)

Ren stdlib-test, ingen GitHub-kall, ingen bash/YAML-avhengighet --
kjøres av den vanlige suiten (`py -3 -m unittest discover -s tests`).
"""
import importlib.util
import json
import os
import subprocess
import sys
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCRIPT = os.path.join(_REPO_ROOT, ".github", "scripts", "queue_dispatch.py")


def _last_modul():
    """Laster .github/scripts/queue_dispatch.py direkte fra sti -- samme
    mønster som tests/test_agent_bridge_trigger_guard.py og
    tests/test_agent_bridge_deliverable_guard.py bruker for
    workflow-hjelpere som bevisst ligger utenfor
    Python-pakkestrukturen."""
    spec = importlib.util.spec_from_file_location("queue_dispatch", _SCRIPT)
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


_QD = _last_modul()


def _issue(number, labels=(), state="OPEN"):
    return {"number": number, "state": state, "labels": list(labels)}


def _ko(number, status=None, priority=False, agent=True, state="OPEN"):
    labels = []
    if agent:
        labels.append("agent:claude")
    labels.append("queue:pa-jobb")
    if priority:
        labels.append("queue:priority")
    if status:
        labels.append(status)
    return _issue(number, labels=labels, state=state)


class TestElementetsTilstand(unittest.TestCase):
    def test_ingen_status_etikett_er_ikke_startet(self):
        self.assertEqual(_QD.elementets_tilstand(["agent:claude", "queue:pa-jobb"]), "ikke_startet")

    def test_ready_er_aktiv(self):
        self.assertEqual(_QD.elementets_tilstand(["status:ready"]), "aktiv")

    def test_working_er_aktiv(self):
        self.assertEqual(_QD.elementets_tilstand(["status:working"]), "aktiv")

    def test_changes_requested_er_aktiv(self):
        self.assertEqual(_QD.elementets_tilstand(["status:changes-requested"]), "aktiv")

    def test_review_er_ferdig(self):
        self.assertEqual(_QD.elementets_tilstand(["status:review"]), "ferdig")

    def test_approved_er_ferdig(self):
        self.assertEqual(_QD.elementets_tilstand(["status:approved"]), "ferdig")


class TestErKoElement(unittest.TestCase):
    def test_krever_begge_etiketter(self):
        self.assertTrue(_QD.er_ko_element(["agent:claude", "queue:pa-jobb"]))
        self.assertFalse(_QD.er_ko_element(["queue:pa-jobb"]))
        self.assertFalse(_QD.er_ko_element(["agent:claude"]))
        self.assertFalse(_QD.er_ko_element([]))


class TestVelgNeste(unittest.TestCase):
    def test_1_tom_ko_gir_ingen_dispatch(self):
        nummer, begrunnelse = _QD.velg_neste([])
        self.assertIsNone(nummer)
        self.assertIn("Tom kø", begrunnelse)

    def test_2_ett_kvalifisert_element_dispatcher_akkurat_det(self):
        nummer, _ = _QD.velg_neste([_ko(101)])
        self.assertEqual(nummer, 101)

    def test_3_flere_elementer_kun_forste_starter(self):
        nummer, _ = _QD.velg_neste([_ko(103), _ko(101), _ko(102)])
        self.assertEqual(nummer, 101)

    def test_4_aktivt_element_blokkerer_nummer_to(self):
        nummer, begrunnelse = _QD.velg_neste([_ko(101, status="status:working"), _ko(102)])
        self.assertIsNone(nummer)
        self.assertIn("#101", begrunnelse)
        self.assertIn("pause", begrunnelse)

    def test_5_forste_ferdig_lar_neste_starte(self):
        nummer, _ = _QD.velg_neste([_ko(101, status="status:review"), _ko(102)])
        self.assertEqual(nummer, 102)

    def test_5b_approved_lar_neste_starte(self):
        nummer, _ = _QD.velg_neste([_ko(101, status="status:approved"), _ko(102)])
        self.assertEqual(nummer, 102)

    def test_6_changes_requested_pauser_koen_default(self):
        # "Proposed queue model": changes-requested er en
        # owner-beslutningstilstand -- default er fail-closed, ikke
        # automatisk videre.
        nummer, begrunnelse = _QD.velg_neste([_ko(101, status="status:changes-requested"), _ko(102)])
        self.assertIsNone(nummer)
        self.assertIn("#101", begrunnelse)

    def test_6b_failed_run_som_forble_pa_status_working_pauser(self):
        # deliverable_guard.py sin fail-closed-oppførsel etterlater et
        # mislykket/leveranseløst forsøk på status:working -- akkurat
        # samme "aktiv"-tilstand som en ekte pågående kjøring, så køen
        # kan aldri automatisk hoppe forbi et stille mislykket element.
        nummer, begrunnelse = _QD.velg_neste([_ko(101, status="status:working"), _ko(102)])
        self.assertIsNone(nummer)

    def test_7_duplikat_event_gir_ingen_duplikat_dispatch(self):
        # dispatcheren har akkurat bevæpnet #101 (status:ready) idet et
        # nytt event kommer inn -- status:ready telles som "aktiv", så
        # en andre kjøring av velg_neste() med samme snapshot skal IKKE
        # velge et nytt element.
        issues = [_ko(101, status="status:ready"), _ko(102)]
        nummer1, _ = _QD.velg_neste(issues)
        nummer2, _ = _QD.velg_neste(issues)
        self.assertIsNone(nummer1)
        self.assertIsNone(nummer2)

    def test_8_ikke_ko_issue_ignoreres(self):
        # agent:claude alene (uten queue:pa-jobb) er en helt normal
        # enkelt-issue Bridge-trigger, ikke et køelement -- skal aldri
        # telle med eller blokkere køen.
        vanlig_issue = _issue(999, labels=["agent:claude", "status:working"])
        nummer, _ = _QD.velg_neste([vanlig_issue, _ko(101)])
        self.assertEqual(nummer, 101)

    def test_8b_queue_uten_agent_claude_telles_ikke(self):
        nummer, begrunnelse = _QD.velg_neste([_ko(101, agent=False)])
        self.assertIsNone(nummer)
        self.assertIn("Tom kø", begrunnelse)

    def test_9_lukket_issue_telles_ikke(self):
        nummer, _ = _QD.velg_neste([_ko(101, state="CLOSED"), _ko(102)])
        self.assertEqual(nummer, 102)

    def test_10_status_ready_teller_som_aktiv_ikke_ikke_startet(self):
        self.assertEqual(_QD.elementets_tilstand(["status:ready"]), "aktiv")
        nummer, begrunnelse = _QD.velg_neste([_ko(101, status="status:ready")])
        self.assertIsNone(nummer)
        self.assertIn("status:ready", begrunnelse)

    def test_prioritet_etikett_flytter_element_forst(self):
        nummer, _ = _QD.velg_neste([_ko(101), _ko(102, priority=True)])
        self.assertEqual(nummer, 102)

    def test_prioritet_uavgjort_faller_tilbake_pa_issue_nummer(self):
        nummer, _ = _QD.velg_neste([_ko(103, priority=True), _ko(101, priority=True)])
        self.assertEqual(nummer, 101)


class TestCliKontrakt(unittest.TestCase):
    """Selve CLI-kontrakten workflowen faktisk bruker (subprocess.run(),
    samme mønster som tests/test_agent_bridge_deliverable_guard.py sin
    'test_11_...'-serie)."""

    def _kjor(self, issues):
        return subprocess.run(
            [sys.executable, _SCRIPT],
            input=json.dumps(issues),
            capture_output=True,
            text=True,
        )

    def test_cli_dispatch_true_med_issue_number(self):
        resultat = self._kjor([_ko(101)])
        self.assertEqual(resultat.returncode, 0)
        self.assertIn("dispatch=true", resultat.stdout)
        self.assertIn("issue_number=101", resultat.stdout)

    def test_cli_dispatch_false_uten_issue_number(self):
        resultat = self._kjor([])
        self.assertEqual(resultat.returncode, 0)
        self.assertIn("dispatch=false", resultat.stdout)
        self.assertNotIn("issue_number=", resultat.stdout)

    def test_cli_tolererer_tom_stdin(self):
        resultat = subprocess.run(
            [sys.executable, _SCRIPT],
            input="",
            capture_output=True,
            text=True,
        )
        self.assertEqual(resultat.returncode, 0)
        self.assertIn("dispatch=false", resultat.stdout)

    def test_cli_avviser_ugyldig_json(self):
        resultat = subprocess.run(
            [sys.executable, _SCRIPT],
            input="{ikke gyldig json",
            capture_output=True,
            text=True,
        )
        self.assertEqual(resultat.returncode, 2)
        self.assertIn("dispatch=false", resultat.stdout)


if __name__ == "__main__":
    unittest.main()
