"""
Kvernhaug Agent Bridge -- regresjonstester for PÅ JOBB-køens
utvelgelseslogikk (.github/scripts/queue_dispatch.py, issue #260, issue
#405).

Dekker issue #260s ti akseptansetester direkte (se test-navnene under):
  1. tom kø -> ingen handling
  2. ett kvalifisert element -> nøyaktig én dispatch
  3. flere elementer -> kun det første starter
  4. et aktivt/working-element -> nummer to starter ikke
  5. SUPERSEDERT av issue #405, se under -- opprinnelig "det første når
     status:review -> neste kan starte", nå det motsatte.
  6. failed/no-deliverable/owner-decision-tilstand -> køen pauser
  7. duplikat-event -> ingen duplikat Claude-kjøring
  8. en ikke-kø-issue ignoreres
  10. dispatch-stien bevarer live-state-kravet (status:ready teller som
      "aktiv", ikke "ikke_startet")
(9, "no merge/deploy path exists", er et fravær-av-kode-bevis --
dekket av at denne modulen aldri kaller gh/git i det hele tatt, se
tests/test_agent_bridge_permission_config.py for tilsvarende
fravær-bevis på selve broen.)

Issue #405 ("full conveyor: automatic Chief review + auto-resume next
queued lane") retter et bug i #260s opprinnelige modell: status:review
og status:approved talte som "ferdig" og blokkerte ALDRI neste
køelement, selv om PR-en enda ikke var owner-GO'et eller merget -- det
brøt den nye "main WIP = 1 gjennom review/approved/merge"-modellen.
`TestElementetsTilstand.test_review_er_aktiv`/`test_approved_er_aktiv`
og `TestVelgNeste.test_5_review_blokkerer_neste_issue_405`/
`test_5b_approved_blokkerer_neste_issue_405` dekker selve fiksen direkte
(issue #405s minstekrav 1-5, sammen med de allerede eksisterende
test_4/test_6/test_10 for working/changes-requested/ready).
`test_9b_review_blokkerer_helt_til_faktisk_lukket_issue_405` dekker
minstekrav 6 ("lukket/completed forrige item gjør neste eligible") --
det finnes ikke lenger noen status:*-etikett som alene frigjør køen; kun
at issuen faktisk lukkes (forsvinner fra `state=OPEN`-snapshotten) gjør
det. `test_9c_merge_close_wake_gir_nokyaktig_en_dispatch_issue_405`
dekker minstekrav 7/8 (nøyaktig én dispatch per faktisk tilgjengelig
element, selv ved et duplikat merge/close-wake-event) på den rene
funksjonens nivå -- selve wake-mekanismen (nye `issues: closed`/
`pull_request: closed`-triggere) legges til i pa-jobb-queue.yml, som
allerede deler denne modulens fail-closed/idempotente egenskaper via sin
eksisterende `concurrency: group: pa-jobb-queue`
(cancel-in-progress: false) -- se docs/development/AGENT_WORKFLOW.md.

`TestHarAktivBroKjoring`/`TestVelgNeste`s `test_11_*`/`test_12_*` og
`TestCliKontrakt`s `test_cli_aktiv_bro_kjoring_*` dekker Chief-reviewens
runde 1-BLOCKER på PR #263: en repo-vid, IKKE-kølagt Claude Agent
Bridge-kjøring (claude-agent-bridge.yml bruker per-issue `concurrency`,
ikke ett globalt lag) må også pause køen, og køen må fortsette igjen
når den aktiviteten er borte.

`TestHarAktivBroKjoring.test_ukjent_status_telles_som_aktiv_fail_closed`/
`test_manglende_status_felt_telles_som_aktiv_fail_closed` og
`TestVelgNeste.test_13_*` dekker Chief-reviewens runde 2-BLOCKER: ukjent
eller manglende `status`-evidens skal BLOKKERE dispatch (fail-closed),
ikke tillate den.

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

    def test_review_er_aktiv(self):
        # Issue #405: status:review blokkerer nå køen (var "ferdig" under
        # issue #260 -- se queue_dispatch.py moduldoc "ENDRING (issue #405, ...)").
        self.assertEqual(_QD.elementets_tilstand(["status:review"]), "aktiv")

    def test_approved_er_aktiv(self):
        # Issue #405: samme endring for status:approved -- venter fortsatt
        # på owner GO + faktisk merge, ikke ferdig før issuen er lukket.
        self.assertEqual(_QD.elementets_tilstand(["status:approved"]), "aktiv")


class TestErKoElement(unittest.TestCase):
    def test_krever_begge_etiketter(self):
        self.assertTrue(_QD.er_ko_element(["agent:claude", "queue:pa-jobb"]))
        self.assertFalse(_QD.er_ko_element(["queue:pa-jobb"]))
        self.assertFalse(_QD.er_ko_element(["agent:claude"]))
        self.assertFalse(_QD.er_ko_element([]))


class TestHarAktivBroKjoring(unittest.TestCase):
    def test_tomt_gir_false(self):
        self.assertFalse(_QD.har_aktiv_bro_kjoring([]))
        self.assertFalse(_QD.har_aktiv_bro_kjoring(None))

    def test_kun_completed_gir_false(self):
        self.assertFalse(_QD.har_aktiv_bro_kjoring([{"status": "completed"}, {"status": "completed"}]))

    def test_in_progress_gir_true(self):
        self.assertTrue(_QD.har_aktiv_bro_kjoring([{"status": "in_progress"}]))

    def test_hver_aktiv_status_gjenkjennes(self):
        for status in _QD.AKTIVE_KJORINGSSTATUSER:
            self.assertTrue(_QD.har_aktiv_bro_kjoring([{"status": status}]), status)

    def test_blanding_av_completed_og_aktiv_gir_true(self):
        self.assertTrue(_QD.har_aktiv_bro_kjoring([{"status": "completed"}, {"status": "queued"}]))

    def test_ukjent_status_telles_som_aktiv_fail_closed(self):
        # Chief review runde 2 (PR #263): workflowen forhåndsfiltrerer
        # allerede til status != "completed", så ETHVERT element som
        # kommer inn her ER bevis på en ikke-fullført kjøring -- også en
        # fremtidig/ukjent statusstreng GitHub Actions ennå ikke bruker.
        self.assertTrue(_QD.har_aktiv_bro_kjoring([{"status": "some_future_status"}]))

    def test_manglende_status_felt_telles_som_aktiv_fail_closed(self):
        # Malformert/ufullstendig evidens skal aldri tolkes som "trygt
        # å dispatche" -- en falsk pause er reverserbar, en falsk
        # fravær-av-aktivitet er nettopp scope-kollisjonen issue #260
        # skal forhindre.
        self.assertTrue(_QD.har_aktiv_bro_kjoring([{}]))
        self.assertTrue(_QD.har_aktiv_bro_kjoring([{"status": None}]))
        self.assertTrue(_QD.har_aktiv_bro_kjoring([{"status": ""}]))


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

    def test_5_review_blokkerer_neste_issue_405(self):
        # SUPERSEDER issue #260s opprinnelige akseptansetest 5
        # ("first item reaching status:review -> next may start"): issue
        # #405 retter nettopp denne oppførselen, fordi den lot en ny
        # implementasjonsjobb starte FØR forrige PR var owner-GO'et og
        # merget -- to samtidige "main write lane"-forsøk. status:review
        # blokkerer nå køen helt til issuen faktisk er lukket (se
        # test_9_lukket_issue_telles_ikke, som dekker den *faktiske*
        # "forrige ferdig"-veien: issuen forsvinner fra state=OPEN-
        # snapshotten, ikke at den bærer en spesifikk status:*-etikett).
        nummer, begrunnelse = _QD.velg_neste([_ko(101, status="status:review"), _ko(102)])
        self.assertIsNone(nummer)
        self.assertIn("#101", begrunnelse)

    def test_5b_approved_blokkerer_neste_issue_405(self):
        # Samme fiks (issue #405) for status:approved: venter fortsatt på
        # owner GO + faktisk merge, blokkerer nettopp DERFOR fortsatt.
        nummer, begrunnelse = _QD.velg_neste([_ko(101, status="status:approved"), _ko(102)])
        self.assertIsNone(nummer)
        self.assertIn("#101", begrunnelse)

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

    def test_9b_review_blokkerer_helt_til_faktisk_lukket_issue_405(self):
        # Issue #405, minstekrav 6: "lukket/completed forrige item gjør
        # neste eligible" -- ikke at det bare NÅR en bestemt status:*-
        # etikett. Samme issue #101, tre snapshotter av samme livssyklus:
        # fortsatt review (blokkerer), fortsatt approved (blokkerer),
        # faktisk lukket (etter owner GO + merge -- fri).
        nummer_review, _ = _QD.velg_neste([_ko(101, status="status:review"), _ko(102)])
        self.assertIsNone(nummer_review)
        nummer_approved, _ = _QD.velg_neste([_ko(101, status="status:approved"), _ko(102)])
        self.assertIsNone(nummer_approved)
        nummer_lukket, _ = _QD.velg_neste([_ko(101, status="status:approved", state="CLOSED"), _ko(102)])
        self.assertEqual(nummer_lukket, 102)

    def test_9c_merge_close_wake_gir_nokyaktig_en_dispatch_issue_405(self):
        # Issue #405, minstekrav 7/8: et merge/close-event (og et evt.
        # duplikat derav -- issue auto-close OG PR closed kan begge fyre)
        # skal gi NØYAKTIG ÉN dispatch av det nye eligible elementet, ikke
        # flere. pa-jobb-queue.yml sin delte `concurrency: group:
        # pa-jobb-queue` (cancel-in-progress: false) serialiserer to slike
        # nesten-samtidige workflow-kjøringer, så den andre kjøringens
        # egen ferske gh-issue-list-spørring vil alltid se den FØRSTE
        # kjøringens bevæpning (status:ready) -- simulert her ved å kalle
        # velg_neste() to ganger på snapshotter som viser akkurat det
        # forløpet, uten noen mellomliggende tilstand denne rene
        # funksjonen ikke allerede får se.
        forste_snapshot = [_ko(101, status="status:approved", state="CLOSED"), _ko(102)]
        nummer1, _ = _QD.velg_neste(forste_snapshot)
        self.assertEqual(nummer1, 102)
        andre_snapshot = [_ko(101, status="status:approved", state="CLOSED"), _ko(102, status="status:ready")]
        nummer2, begrunnelse2 = _QD.velg_neste(andre_snapshot)
        self.assertIsNone(nummer2)
        self.assertIn("#102", begrunnelse2)

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

    def test_11_repo_vid_ikke_ko_bro_kjoring_pauser_koen(self):
        # Chief-reviewens BLOCKER (PR #263): et rent "ikke_startet"
        # køelement, uten at NOEN queue:pa-jobb-issue selv er "aktiv" --
        # men en helt vanlig, ikke-kølagt Bridge-kjøring (issue #999, som
        # aldri vises i queue:pa-jobb-snapshotten i det hele tatt) kjører
        # akkurat nå repo-vidt. Køen må likevel pause.
        nummer, begrunnelse = _QD.velg_neste(
            [_ko(101)],
            aktive_bro_kjoringer=[{"status": "in_progress", "head_branch": "agent/issue-999"}],
        )
        self.assertIsNone(nummer)
        self.assertIn("pause", begrunnelse)

    def test_12_repo_vid_aktivitet_borte_lar_koen_fortsette(self):
        # Samme kø som over, men den repo-vide kjøringen er nå completed
        # (eller helt fraværende) -- køen skal velge neste kandidat igjen.
        nummer, _ = _QD.velg_neste(
            [_ko(101)],
            aktive_bro_kjoringer=[{"status": "completed", "head_branch": "agent/issue-999"}],
        )
        self.assertEqual(nummer, 101)
        nummer2, _ = _QD.velg_neste([_ko(101)], aktive_bro_kjoringer=[])
        self.assertEqual(nummer2, 101)

    def test_12b_ingen_aktive_bro_kjoringer_arg_er_bakoverkompatibel(self):
        nummer, _ = _QD.velg_neste([_ko(101)])
        self.assertEqual(nummer, 101)

    def test_12c_tom_ko_gir_tom_ko_begrunnelse_selv_med_aktiv_bro_kjoring(self):
        # Ingen vits i å pause noe som ikke finnes -- tom kø rapporteres
        # som tom kø, ikke som "pauset av repo-vid aktivitet".
        nummer, begrunnelse = _QD.velg_neste([], aktive_bro_kjoringer=[{"status": "in_progress"}])
        self.assertIsNone(nummer)
        self.assertIn("Tom kø", begrunnelse)

    def test_13_ukjent_eller_manglende_status_pauser_koen_fail_closed(self):
        # Chief review runde 2 (PR #263): malformert/ukjent evidens skal
        # BLOKKERE dispatch, ikke tillate den -- samme scenario som
        # test_11, men med statusverdier har_aktiv_bro_kjoring() ikke
        # gjenkjenner fra AKTIVE_KJORINGSSTATUSER-listen.
        for kjoring in ({"status": "some_future_status"}, {}, {"status": None}):
            with self.subTest(kjoring=kjoring):
                nummer, begrunnelse = _QD.velg_neste([_ko(101)], aktive_bro_kjoringer=[kjoring])
                self.assertIsNone(nummer)
                self.assertIn("pause", begrunnelse)


class TestCliKontrakt(unittest.TestCase):
    """Selve CLI-kontrakten workflowen faktisk bruker (subprocess.run(),
    samme mønster som tests/test_agent_bridge_deliverable_guard.py sin
    'test_11_...'-serie)."""

    def _kjor(self, issues, aktive_bro_kjoringer=None):
        env = dict(os.environ)
        if aktive_bro_kjoringer is not None:
            env["AKTIVE_BRO_KJORINGER"] = json.dumps(aktive_bro_kjoringer)
        else:
            env.pop("AKTIVE_BRO_KJORINGER", None)
        return subprocess.run(
            [sys.executable, _SCRIPT],
            input=json.dumps(issues),
            capture_output=True,
            text=True,
            env=env,
        )

    def test_cli_aktiv_bro_kjoring_pauser_dispatch(self):
        resultat = self._kjor([_ko(101)], aktive_bro_kjoringer=[{"status": "queued"}])
        self.assertEqual(resultat.returncode, 0)
        self.assertIn("dispatch=false", resultat.stdout)
        self.assertNotIn("issue_number=", resultat.stdout)
        self.assertIn("pause", resultat.stderr)

    def test_cli_uten_aktiv_bro_kjoring_env_dispatcher_som_for(self):
        resultat = self._kjor([_ko(101)], aktive_bro_kjoringer=None)
        self.assertEqual(resultat.returncode, 0)
        self.assertIn("dispatch=true", resultat.stdout)
        self.assertIn("issue_number=101", resultat.stdout)

    def test_cli_avviser_ugyldig_aktive_bro_kjoringer_json(self):
        env = dict(os.environ)
        env["AKTIVE_BRO_KJORINGER"] = "{ikke gyldig json"
        resultat = subprocess.run(
            [sys.executable, _SCRIPT],
            input=json.dumps([_ko(101)]),
            capture_output=True,
            text=True,
            env=env,
        )
        self.assertEqual(resultat.returncode, 2)
        self.assertIn("dispatch=false", resultat.stdout)

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
