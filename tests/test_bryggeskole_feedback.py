"""
Tests for bryggeskole/feedback.py -- the anonymous representative-user
feedback payload and its webhook transport (issue #542).

No real network: every send goes through an injected fake opener.

Run with:
    python3 -m unittest tests.test_bryggeskole_feedback
"""
import io
import json
import os
import re
import tempfile
import unittest
import urllib.error

from bryggeskole import feedback as fb

_URL = "https://script.google.com/macros/s/EXAMPLE/exec"
_MODULER = ("raavarer", "mesking", "pakking")


def _payload(answers=None, context=None, **extra):
    kwargs = dict(
        answers=answers if answers is not None else {"start_clarity": "easy"},
        language="no",
        context=context if context is not None else {"environment": "hjemmebrygger", "stage": "foundation", "module": "mesking"},
        feedback_id="0" * 32,
        submitted_at="2026-10-16T12:00:00+00:00",
        demo_mode=True,
        module_ids=_MODULER,
    )
    kwargs.update(extra)
    return fb.build_payload(**kwargs)


class _Svar:
    def __init__(self, status=200, body=b'{"ok": true}'):
        self.status = status
        self._body = body

    def read(self):
        return self._body

    def getcode(self):
        return self.status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Opener:
    """Records every request; returns a fixed reply or raises."""

    def __init__(self, svar=None, feil=None):
        self.svar = svar or _Svar()
        self.feil = feil
        self.kall = []

    def __call__(self, request, timeout):
        self.kall.append((request, timeout))
        if self.feil is not None:
            raise self.feil
        return self.svar


class TestPayloadSchema(unittest.TestCase):
    def test_exact_top_level_fields(self):
        p = _payload()
        self.assertEqual(set(p), {"schema", "schema_version", "feedback_id", "submitted_at", "language",
                                  "demo_mode", "context", "answers"})
        self.assertEqual(p["schema"], "kbh.bryggeskole.feedback")
        self.assertEqual(p["schema_version"], 1)
        self.assertEqual(set(p["context"]), {"environment", "stage", "module"})
        json.dumps(p)  # serialisable as-is

    def test_closed_answers_only_accept_their_option_ids(self):
        p = _payload({"start_clarity": "easy", "text_amount": "ten out of ten", "would_continue": "maybe",
                      "stage_difference": 7})
        self.assertEqual(p["answers"], {"start_clarity": "easy", "would_continue": "maybe"})

    def test_every_closed_question_and_text_field_round_trips(self):
        svar = {k: v[0] for k, v in fb.CLOSED_QUESTIONS.items()}
        svar.update({k: f"  tekst {k}  " for k in fb.TEXT_FIELDS})
        p = _payload(svar)
        self.assertEqual(set(p["answers"]), set(fb.CLOSED_QUESTIONS) | set(fb.TEXT_FIELDS))
        self.assertEqual(p["answers"]["other_comments"], "tekst other_comments")

    def test_free_text_is_capped_and_empty_text_left_out(self):
        p = _payload({"other_comments": "x" * 5000, "unknown_terms_text": "   "})
        self.assertEqual(len(p["answers"]["other_comments"]), fb.TEXT_MAX_CHARS)
        self.assertNotIn("unknown_terms_text", p["answers"])

    def test_no_single_overall_score_question(self):
        for options in fb.CLOSED_QUESTIONS.values():
            self.assertFalse(any(re.fullmatch(r"\d+", o) for o in options), options)

    def test_context_unknown_values_are_dropped(self):
        p = _payload(context={"environment": "kjeller", "stage": "bryggemester", "module": "ukjent"})
        self.assertEqual(p["context"], {"environment": None, "stage": None, "module": None})
        p = _payload(context=None)
        self.assertEqual(p["context"]["module"], "mesking")
        p = fb.build_payload({"start_clarity": "ok"}, "en", None, "id", "ts", False)
        self.assertEqual(p["context"], {"environment": None, "stage": None, "module": None})

    def test_unknown_language_falls_back_to_no(self):
        self.assertEqual(_payload(language="de")["language"], "no")
        self.assertEqual(_payload(language="en")["language"], "en")

    def test_has_content(self):
        self.assertFalse(fb.has_content({}))
        self.assertFalse(fb.has_content({"other_comments": "  ", "start_clarity": "bogus"}))
        self.assertTrue(fb.has_content({"other_comments": "Fint kurs"}))

    def test_feedback_id_is_random_hex_not_derived(self):
        a, b = fb.new_feedback_id(), fb.new_feedback_id()
        self.assertRegex(a, r"^[0-9a-f]{32}$")
        self.assertNotEqual(a, b)


class TestNoPersonalDataOrLearnerState(unittest.TestCase):
    _FORBUDT = ("name", "navn", "email", "e-post", "epost", "ip", "user_agent", "user_id", "learner",
                "mastery", "concepts", "attempts", "progress", "completion", "session", "bs_")

    def test_injected_identifying_or_learner_keys_never_pass(self):
        svar = {"start_clarity": "easy", "name": "Ola", "email": "ola@example.com", "ip": "10.0.0.1",
                "mastery": {"mashing.temperature": 1}, "concepts": {}, "bs_modul_sesjon": {}}
        p = _payload(svar, context={"environment": "hjemmebrygger", "stage": "foundation", "module": "mesking",
                                    "user_id": "abc", "ip": "10.0.0.1"})
        self.assertEqual(p["answers"], {"start_clarity": "easy"})
        self.assertEqual(set(p["context"]), {"environment", "stage", "module"})
        nokler = json.dumps(sorted(_alle_nokler(p)))
        for ord_ in self._FORBUDT:
            self.assertNotIn(f'"{ord_}', nokler.lower(), ord_)

    def test_module_source_has_no_disk_io(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bryggeskole", "feedback.py")
        with io.open(path, encoding="utf-8") as fh:
            kode = fh.read()
        for forbudt in ("open(", "write(", "pathlib", "shutil", "mastery", "streamlit"):
            self.assertNotIn(forbudt, kode.replace("urlopen(", "").split('"""', 2)[2], forbudt)


def _alle_nokler(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from _alle_nokler(v)


class TestEndpointConfig(unittest.TestCase):
    def test_missing_blank_or_non_https_is_not_configured(self):
        for verdi in (None, "", "   ", "http://example.com/hook", "ftp://x/y", "https://", "script.google.com/x"):
            env = {} if verdi is None else {fb.WEBHOOK_URL_ENV: verdi}
            with self.subTest(verdi=verdi):
                self.assertIsNone(fb.webhook_url(env))
                self.assertFalse(fb.is_configured(env))

    def test_https_url_is_configured(self):
        self.assertEqual(fb.webhook_url({fb.WEBHOOK_URL_ENV: f"  {_URL} "}), _URL)


class TestSend(unittest.TestCase):
    def test_missing_endpoint_sends_nothing(self):
        opener = _Opener()
        self.assertEqual(fb.send_feedback(_payload(), environ={}, opener=opener), fb.NOT_CONFIGURED)
        self.assertEqual(opener.kall, [])

    def test_success_posts_json_once(self):
        opener = _Opener()
        p = _payload()
        self.assertEqual(fb.send_feedback(p, environ={fb.WEBHOOK_URL_ENV: _URL}, opener=opener), fb.SENT)
        self.assertEqual(len(opener.kall), 1)
        request, timeout = opener.kall[0]
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.full_url, _URL)
        self.assertEqual(request.get_header("Content-type"), "application/json; charset=utf-8")
        self.assertEqual(json.loads(request.data.decode("utf-8")), p)
        self.assertEqual(timeout, fb.TIMEOUT_SECONDS)

    def test_token_only_in_body_and_only_when_configured(self):
        opener = _Opener()
        fb.send_feedback(_payload(), environ={fb.WEBHOOK_URL_ENV: _URL, fb.TOKEN_ENV: "hemmelig"}, opener=opener)
        self.assertEqual(json.loads(opener.kall[0][0].data)["token"], "hemmelig")
        opener = _Opener()
        fb.send_feedback(_payload(), environ={fb.WEBHOOK_URL_ENV: _URL, fb.TOKEN_ENV: "  "}, opener=opener)
        self.assertNotIn("token", json.loads(opener.kall[0][0].data))

    def test_payload_dict_is_not_mutated_by_token(self):
        p = _payload()
        fb.send_feedback(p, environ={fb.WEBHOOK_URL_ENV: _URL, fb.TOKEN_ENV: "t"}, opener=_Opener())
        self.assertNotIn("token", p)

    def test_failures_are_reported_never_raised(self):
        http_feil = urllib.error.HTTPError(_URL, 500, "Server Error", {}, io.BytesIO(b""))
        tilfeller = {
            "http 500": _Opener(feil=http_feil),
            "network": _Opener(feil=urllib.error.URLError("no route")),
            "timeout": _Opener(feil=TimeoutError("timed out")),
            "status 302 body": _Opener(svar=_Svar(status=302)),
            "html instead of json": _Opener(svar=_Svar(body=b"<html>Sign in</html>")),
            "ok false": _Opener(svar=_Svar(body=b'{"ok": false, "error": "bad schema"}')),
            "ok missing": _Opener(svar=_Svar(body=b'{"status": "done"}')),
            "ok truthy string": _Opener(svar=_Svar(body=b'{"ok": "yes"}')),
        }
        for navn, opener in tilfeller.items():
            with self.subTest(navn):
                self.assertEqual(fb.send_feedback(_payload(), environ={fb.WEBHOOK_URL_ENV: _URL}, opener=opener),
                                 fb.FAILED)

    def test_send_writes_nothing_to_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            gammel = os.getcwd()
            os.chdir(tmp)
            try:
                fb.send_feedback(_payload(), environ={fb.WEBHOOK_URL_ENV: _URL}, opener=_Opener())
                fb.send_feedback(_payload(), environ={}, opener=_Opener())
            finally:
                os.chdir(gammel)
            self.assertEqual(os.listdir(tmp), [])


class TestReceiverContract(unittest.TestCase):
    """The sample Apps Script receiver must accept exactly the keys and
    option ids this module sends, in the documented column order."""

    def setUp(self):
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "docs", "development", "bryggeskole_feedback_receiver.gs")
        with io.open(path, encoding="utf-8") as fh:
            self.gs = fh.read()

    def test_closed_questions_and_options_match(self):
        blokk = re.search(r"var CLOSED = \{(.*?)\};", self.gs, re.S).group(1)
        gs = {k: tuple(re.findall(r"'([a-z_]+)'", v)) for k, v in re.findall(r"(\w+): \[([^\]]*)\]", blokk)}
        self.assertEqual(list(gs), list(fb.CLOSED_QUESTIONS))
        self.assertEqual(gs, fb.CLOSED_QUESTIONS)

    def test_text_fields_and_schema_match(self):
        blokk = re.search(r"var TEXT = \[(.*?)\];", self.gs, re.S).group(1)
        self.assertEqual(tuple(re.findall(r"'([a-z_]+)'", blokk)), fb.TEXT_FIELDS)
        self.assertIn(f"var SCHEMA = '{fb.SCHEMA}';", self.gs)
        self.assertIn(f"var SCHEMA_VERSION = {fb.SCHEMA_VERSION};", self.gs)
        self.assertIn(f"var TEXT_MAX = {fb.TEXT_MAX_CHARS};", self.gs)

    def test_receiver_holds_no_real_endpoint_or_secret(self):
        self.assertNotRegex(self.gs, r"script\.google\.com/macros/s/[A-Za-z0-9_-]{20,}")
        self.assertIn("getProperty('FEEDBACK_TOKEN')", self.gs)


if __name__ == "__main__":
    unittest.main()
