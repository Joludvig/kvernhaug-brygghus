"""
AppTest coverage for the Bryggeskole feedback form (issue #542):
ui/bryggeskole_feedback_panel.py wired into ui/bryggeskole_panel.py.

Covers: the voluntary entry on the overview and after a module summary; the
calm not-configured state (nothing sent); a successful send (exactly one
POST, honest confirmation, no double send); a failed send (answers kept,
retry works); an empty form is never sent; feedback never changes mastery,
progress or the open module; NO/EN parity; and DEMO_MODE writes nothing to
disk while still sending (separate process, as DEMO_MODE is read at import).

No real network: bryggeskole.feedback.send_feedback is patched, or (in the
DEMO_MODE process) its opener is replaced.

Run with:
    python3 -m unittest tests.test_ui_bryggeskole_feedback
"""
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from bryggeskole import feedback as fb
from bryggeskole.mastery_store import _STATE_DIR_ENV, read_mastery_state
from modules.i18n import TEKSTER

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "bryggeskole_harness.py")
_URL = "https://script.google.com/macros/s/EXAMPLE/exec"


def _knapp(at, key):
    knapper = [b for b in at.button if b.key == key]
    assert len(knapper) == 1, f"Fant ikke akkurat én knapp med key={key!r}: {[b.key for b in at.button]}"
    return knapper[0]


def _send_knapp(at):
    label = TEKSTER["no"]["bryggeskole.feedback.send"]
    knapper = [b for b in at.button if b.label == label]
    assert len(knapper) == 1, [b.label for b in at.button]
    return knapper[0]


def _fb_radioer(at):
    """The form's own radios (the harness also draws the language radio)."""
    return [r for r in at.radio if r.key and r.key.startswith("bs_fb_")]


def _tekster(at):
    ut = []
    for samling in (at.markdown, at.caption, at.subheader, at.info, at.success, at.error, at.warning):
        ut.extend(e.value for e in samling)
    ut.extend(b.label for b in at.button if b.label)
    return ut


class _FeedbackTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        patcher = mock.patch.dict(os.environ, {_STATE_DIR_ENV: self._tmpdir.name})
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(fb.WEBHOOK_URL_ENV, None)
        os.environ.pop(fb.TOKEN_ENV, None)
        self.addCleanup(self._tmpdir.cleanup)

    def _konfigurer(self):
        os.environ[fb.WEBHOOK_URL_ENV] = _URL

    def _oversikt(self, sprak=None):
        at = AppTest.from_file(_HARNESS)
        if sprak:
            at.session_state["sprak"] = sprak
        at.run()
        _knapp(at, "bs_velg_hjemmebrygger_btn").click().run()
        self.assertEqual(len(at.exception), 0, at.exception)
        return at

    def _apne_skjema(self, at):
        _knapp(at, "bs_feedback_apne_oversikt_btn").click().run()
        self.assertEqual(len(at.exception), 0, at.exception)
        return at


class TestInngang(_FeedbackTest):
    def test_overview_has_a_voluntary_entry_below_the_unchanged_grid(self):
        at = self._oversikt()
        self.assertEqual(_knapp(at, "bs_feedback_apne_oversikt_btn").label,
                         TEKSTER["no"]["bryggeskole.feedback.inngang"])
        self.assertIn(TEKSTER["no"]["bryggeskole.feedback.inngang_forklaring"], _tekster(at))
        kort = [b.key for b in at.button if b.key and b.key.startswith("bs_apne_modul_")]
        self.assertEqual(len(kort), 11)

    def test_english_labels(self):
        at = self._oversikt("en")
        self.assertEqual(_knapp(at, "bs_feedback_apne_oversikt_btn").label, "💬 Give feedback on the Brew School")

    def test_no_en_key_parity(self):
        no = {k for k in TEKSTER["no"] if k.startswith("bryggeskole.feedback.")}
        en = {k for k in TEKSTER["en"] if k.startswith("bryggeskole.feedback.")}
        self.assertEqual(no, en)
        for sporsmal, alternativer in fb.CLOSED_QUESTIONS.items():
            self.assertIn(f"bryggeskole.feedback.{sporsmal}.sporsmal", no)
            for alt in alternativer:
                self.assertIn(f"bryggeskole.feedback.{sporsmal}.{alt}", no)
        for felt in fb.TEXT_FIELDS:
            self.assertIn(f"bryggeskole.feedback.{felt}", no)


class TestIkkeKonfigurert(_FeedbackTest):
    def test_calm_message_no_form_nothing_sent(self):
        with mock.patch("bryggeskole.feedback.send_feedback") as send:
            at = self._apne_skjema(self._oversikt())
            self.assertIn(TEKSTER["no"]["bryggeskole.feedback.ikke_konfigurert"], [i.value for i in at.info])
            self.assertEqual(_fb_radioer(at), [])
            self.assertEqual([b for b in at.button if b.label == TEKSTER["no"]["bryggeskole.feedback.send"]], [])
            send.assert_not_called()
        _knapp(at, "bs_feedback_lukk_btn").click().run()
        _knapp(at, "bs_feedback_apne_oversikt_btn")  # back on the overview


class TestSending(_FeedbackTest):
    def _fyll_ut(self, at):
        at.radio(key="bs_fb_start_clarity").set_value("ok")
        at.radio(key="bs_fb_would_continue").set_value("maybe")
        at.text_area(key="bs_fb_unknown_terms_text").input("Hva betyr vørter?")
        return at

    def test_success_sends_once_and_says_so_honestly(self):
        self._konfigurer()
        with mock.patch("bryggeskole.feedback.send_feedback", return_value=fb.SENT) as send:
            at = self._apne_skjema(self._oversikt())
            self.assertEqual(len(_fb_radioer(at)), len(fb.CLOSED_QUESTIONS))
            self.assertTrue(all(r.value is None for r in _fb_radioer(at)), "no preselected answers")
            self._fyll_ut(at)
            _send_knapp(at).click().run()
            self.assertEqual(len(at.exception), 0, at.exception)
            self.assertEqual(send.call_count, 1)
            payload = send.call_args.args[0]
            self.assertEqual(payload["answers"], {"start_clarity": "ok", "would_continue": "maybe",
                                                  "unknown_terms_text": "Hva betyr vørter?"})
            self.assertEqual(payload["context"], {"environment": "hjemmebrygger", "stage": "foundation", "module": None})
            self.assertEqual(payload["language"], "no")
            self.assertFalse(payload["demo_mode"])
            self.assertIn(TEKSTER["no"]["bryggeskole.feedback.sendt"], [s.value for s in at.success])
            # The sent form is gone: no way to send the same submission twice.
            self.assertEqual([b for b in at.button if b.label == TEKSTER["no"]["bryggeskole.feedback.send"]], [])
            at.run()
            self.assertEqual(send.call_count, 1)
            forste_id = payload["feedback_id"]
            # A deliberate new submission gets a new random id and a clean form.
            _knapp(at, "bs_feedback_ny_btn").click().run()
            self.assertTrue(all(r.value is None for r in _fb_radioer(at)))
            at.radio(key="bs_fb_text_amount").set_value("too_much")
            _send_knapp(at).click().run()
            self.assertEqual(send.call_count, 2)
            self.assertNotEqual(send.call_args.args[0]["feedback_id"], forste_id)

    def test_failure_keeps_answers_and_retry_works(self):
        self._konfigurer()
        with mock.patch("bryggeskole.feedback.send_feedback", side_effect=[fb.FAILED, fb.SENT]) as send:
            at = self._fyll_ut(self._apne_skjema(self._oversikt()))
            _send_knapp(at).click().run()
            self.assertIn(TEKSTER["no"]["bryggeskole.feedback.feilet"], [e.value for e in at.error])
            self.assertEqual(at.radio(key="bs_fb_start_clarity").value, "ok")
            self.assertEqual(at.text_area(key="bs_fb_unknown_terms_text").value, "Hva betyr vørter?")
            # Leaving and reopening keeps the unsent draft and its id.
            forste_id = send.call_args.args[0]["feedback_id"]
            _knapp(at, "bs_feedback_lukk_btn").click().run()
            self._apne_skjema(at)
            self.assertEqual(at.radio(key="bs_fb_would_continue").value, "maybe")
            # The restored draft draws no Streamlit "default + Session State" warning.
            self.assertEqual([w.value for w in at.warning], [])
            self.assertEqual(len(at.exception), 0, at.exception)
            _send_knapp(at).click().run()
            self.assertEqual(send.call_count, 2)
            self.assertEqual(send.call_args.args[0]["feedback_id"], forste_id)
            self.assertIn(TEKSTER["no"]["bryggeskole.feedback.sendt"], [s.value for s in at.success])

    def test_empty_form_is_never_sent(self):
        self._konfigurer()
        with mock.patch("bryggeskole.feedback.send_feedback") as send:
            at = self._apne_skjema(self._oversikt())
            _send_knapp(at).click().run()
            send.assert_not_called()
            self.assertIn(TEKSTER["no"]["bryggeskole.feedback.tom"], [w.value for w in at.warning])


class TestAdskiltFraLaering(_FeedbackTest):
    def _fullfor_mesking_foundation(self, at):
        from bryggeskole import course_stage
        from bryggeskole.pilot_mashing import read_pilot_file
        pilot = read_pilot_file()
        visning = course_stage.items_for_stage(course_stage.load_stage_map(), "mesking", pilot, "foundation")
        _knapp(at, "bs_apne_modul_mesking_btn").click().run()
        while [b for b in at.button if b.key == "bs_bolk_neste_mesking_btn"]:
            _knapp(at, "bs_bolk_neste_mesking_btn").click().run()
        _knapp(at, "bs_start_sporsmal_mesking_btn").click().run()
        for i, q in enumerate(visning["questions"]):
            korrekt = next(o["id"] for o in q["options"] if o["correct"])
            at.radio(key=f"bs_valg_mesking_r1_q{i}").set_value(korrekt).run()
            _knapp(at, f"bs_svar_btn_mesking_r1_q{i}").click().run()
            _knapp(at, f"bs_fortsett_btn_mesking_r1_q{i}").click().run()
        self.assertEqual(len(at.exception), 0, at.exception)
        return at

    def test_summary_entry_and_feedback_leaves_learning_state_untouched(self):
        self._konfigurer()
        at = self._fullfor_mesking_foundation(self._oversikt())
        mastery_for = read_mastery_state()
        sesjon_for = json.dumps(at.session_state["bs_modul_sesjon"], sort_keys=True, default=str)
        with mock.patch("bryggeskole.feedback.send_feedback", return_value=fb.SENT) as send:
            _knapp(at, "bs_feedback_apne_mesking_btn").click().run()
            at.radio(key="bs_fb_learned_for_real_brew").set_value("yes")
            _send_knapp(at).click().run()
            self.assertEqual(send.call_args.args[0]["context"],
                             {"environment": "hjemmebrygger", "stage": "foundation", "module": "mesking"})
            _knapp(at, "bs_feedback_lukk_btn").click().run()
        # Back on the same summary; learning state identical.
        _knapp(at, "bs_prov_igjen_mesking_btn")
        self.assertEqual(at.session_state["bs_aktiv_modul"], "mesking")
        self.assertEqual(read_mastery_state(), mastery_for)
        self.assertEqual(json.dumps(at.session_state["bs_modul_sesjon"], sort_keys=True, default=str), sesjon_for)

    def test_opening_feedback_before_any_lesson_records_no_progress(self):
        self._konfigurer()
        with mock.patch("bryggeskole.feedback.send_feedback", return_value=fb.SENT):
            at = self._apne_skjema(self._oversikt())
            at.radio(key="bs_fb_start_clarity").set_value("easy")
            _send_knapp(at).click().run()
            _knapp(at, "bs_feedback_lukk_btn").click().run()
        self.assertEqual(os.listdir(self._tmpdir.name), [], "feedback must not create a mastery file")
        self.assertEqual(at.session_state["bs_modul_sesjon"], {})
        self.assertIn("0 av 9 moduler gjennomgått", [c.value for c in at.caption])


class TestDemoModeSenderUtenLokalSkriving(unittest.TestCase):
    """DEMO_MODE is a module-level constant (config.py) -- own process, the
    same pattern as tests/test_ui_bryggeskole_panel.py TestDemoModeIngenSkriving.
    The opener is replaced inside that process: no real network."""

    def test_demo_mode_sends_and_writes_nothing(self):
        data_dir = os.path.join(_REPO_ROOT, "data")
        data_for = sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else []
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["DEMO_MODE"] = "1"
            env[_STATE_DIR_ENV] = tmp
            env[fb.WEBHOOK_URL_ENV] = _URL
            env.pop(fb.TOKEN_ENV, None)
            script = "\n".join([
                "import json, logging",
                "logging.getLogger('streamlit').setLevel(logging.ERROR)",
                "from streamlit.testing.v1 import AppTest",
                "from bryggeskole import feedback as fb",
                "sendt = []",
                "class Svar:",
                "    status = 200",
                "    def read(self): return b'{\"ok\": true}'",
                "    def __enter__(self): return self",
                "    def __exit__(self, *a): return False",
                "def opener(req, timeout):",
                "    sendt.append(json.loads(req.data)); return Svar()",
                "fb._default_opener = opener",
                f"at = AppTest.from_file(r{_HARNESS!r}); at.run()",
                "assert not at.exception, at.exception",
                "knapp = lambda key: [b for b in at.button if b.key == key][0]",
                "knapp('bs_velg_hjemmebrygger_btn').click().run()",
                "knapp('bs_feedback_apne_oversikt_btn').click().run()",
                "at.radio(key='bs_fb_would_continue').set_value('yes')",
                "[b for b in at.button if b.label == 'Send tilbakemelding'][0].click().run()",
                "assert not at.exception, at.exception",
                "assert len(sendt) == 1, sendt",
                "assert sendt[0]['demo_mode'] is True, sendt",
                "assert sendt[0]['answers'] == {'would_continue': 'yes'}, sendt",
                "assert any('Takk' in s.value for s in at.success), [s.value for s in at.success]",
                "print('OK')",
            ])
            resultat = subprocess.run(
                [sys.executable, "-c", script],
                cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=180,
            )
            self.assertEqual(resultat.returncode, 0, f"stdout={resultat.stdout}\nstderr={resultat.stderr}")
            self.assertIn("OK", resultat.stdout)
            self.assertEqual(os.listdir(tmp), [], "DEMO_MODE must not write any learner or feedback file")
        self.assertEqual(sorted(os.listdir(data_dir)) if os.path.isdir(data_dir) else [], data_for)


if __name__ == "__main__":
    unittest.main()
