"""
Tester for issue #311 sin evalueringsharness (scripts/soti_eval/) --
beviser at OllamaProvider oversetter meldinger/verktøy til Ollamas
API-format og tolker svaret tilbake til et ProviderSvar/ToolKall riktig,
UTEN å kreve en ekte Ollama-server, GPU eller modellnedlasting: HTTP-laget
mockes. Disse testene dekker kun evalueringsverktøyet selv -- de sier
ingenting om noen konkret modells kvalitet (det står i
docs/development/SOTI_MODEL_RUNTIME_EVAL_V1.md).

Kjøres med:
    py -3 -m unittest tests.test_soti_eval_harness
"""
import json
import unittest
from unittest import mock

from scripts.soti_eval.ollama_provider import OllamaProvider, OllamaMaalinger, raw_generate
from scripts.soti_eval.run_eval import _tolk_verktoy_suksess, _uttrekk_ny_verktoy_telemetri
from soti.session import SotiSession
from soti.tools import Tool


def _fake_urlopen_response(payload_dict):
    body = json.dumps(payload_dict).encode("utf-8")

    class _FakeResp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return body

    return _FakeResp()


class TestOllamaProviderMeldingsoversettelse(unittest.TestCase):
    def test_ren_tekst_svar_gir_providersvar_uten_tool_kall(self):
        raw = {"message": {"role": "assistant", "content": "Hei fra modellen"}, "eval_count": 5, "eval_duration": 1_000_000_000}
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("dummy-model")
            svar = provider.generate([{"role": "user", "content": "Hei"}], [])

        self.assertEqual(svar.tekst, "Hei fra modellen")
        self.assertIsNone(svar.tool_kall)
        self.assertEqual(provider.siste_maalinger.tokens_per_sekund(), 5.0)

    def test_tool_calls_i_svaret_gir_toolkall_med_parsede_argumenter(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": {"datasett": "humle", "sok": "cascade_us"}}}],
            }
        }
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("dummy-model")
            svar = provider.generate([{"role": "user", "content": "Slå opp cascade"}], [])

        self.assertEqual(svar.tool_kall.navn, "hent_ingrediens_info")
        self.assertEqual(svar.tool_kall.argumenter, {"datasett": "humle", "sok": "cascade_us"})

    def test_tool_calls_med_argumenter_som_json_streng_parses(self):
        raw = {
            "message": {
                "role": "assistant",
                "content": "",
                "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": '{"datasett": "malt", "sok": "x"}'}}],
            }
        }
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("dummy-model")
            svar = provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(svar.tool_kall.argumenter, {"datasett": "malt", "sok": "x"})

    def test_ukjent_verktoynavn_far_apent_skjema_ikke_krasj(self):
        ukjent_tool = Tool(navn="et_helt_nytt_verktoy", beskrivelse="test", handler=lambda a: {})
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("dummy-model")
            provider.generate([{"role": "user", "content": "..."}], [ukjent_tool])

        sendt_skjema = captured["body"]["tools"][0]["function"]["parameters"]
        self.assertEqual(sendt_skjema, {"type": "object"})

    def test_kjent_verktoy_far_eksplisitt_skjema(self):
        kjent_tool = Tool(navn="hent_ingrediens_info", beskrivelse="test", handler=lambda a: {})
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("dummy-model")
            provider.generate([{"role": "user", "content": "..."}], [kjent_tool])

        sendt_skjema = captured["body"]["tools"][0]["function"]["parameters"]
        self.assertIn("datasett", sendt_skjema["properties"])
        self.assertIn("sok", sendt_skjema["properties"])


class TestOllamaMaalinger(unittest.TestCase):
    def test_tokens_per_sekund_none_uten_data(self):
        m = OllamaMaalinger({})
        self.assertIsNone(m.tokens_per_sekund())

    def test_tokens_per_sekund_beregnes_riktig(self):
        m = OllamaMaalinger({"eval_count": 20, "eval_duration": 2_000_000_000})
        self.assertEqual(m.tokens_per_sekund(), 10.0)


class TestRawGenerate(unittest.TestCase):
    def test_raw_generate_returnerer_svartekst_og_maalinger(self):
        raw = {"response": "Svaret her", "eval_count": 3, "eval_duration": 300_000_000}
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            svar, maalinger = raw_generate("dummy-model", "en prompt")

        self.assertEqual(svar, "Svaret her")
        self.assertEqual(maalinger.eval_count, 3)

    def test_num_ctx_og_think_sendes_naar_satt(self):
        raw = {"response": "svar"}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            raw_generate("dummy-model", "prompt", num_ctx=8192, think=False)

        self.assertEqual(captured["body"]["options"]["num_ctx"], 8192)
        self.assertEqual(captured["body"]["think"], False)

    def test_num_ctx_og_think_utelates_naar_ikke_satt(self):
        raw = {"response": "svar"}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            raw_generate("dummy-model", "prompt")

        self.assertNotIn("num_ctx", captured["body"]["options"])
        self.assertNotIn("think", captured["body"])


class TestOllamaMaalingerThinking(unittest.TestCase):
    def test_thinking_hentes_fra_chat_melding(self):
        m = OllamaMaalinger({"message": {"content": "x", "thinking": "tanke..."}})
        self.assertEqual(m.thinking, "tanke...")

    def test_thinking_hentes_fra_generate_toppniva(self):
        m = OllamaMaalinger({"response": "x", "thinking": "tanke..."})
        self.assertEqual(m.thinking, "tanke...")

    def test_thinking_none_naar_fravaerende(self):
        m = OllamaMaalinger({"message": {"content": "x"}})
        self.assertIsNone(m.thinking)


class TestOllamaProviderTelemetriOgOpsjoner(unittest.TestCase):
    """Selektiv-kritisk telemetri (Chief-gjennomgang av PR #312): beviser at
    tool_kall_logg fanger navn+argumenter for HVERT generate()-kall, ikke
    bare det siste -- uten dette ville et verktøykall fra runde 1 av 2 vært
    tapt før evalueringsscriptet fikk lest det (siste_raw_response
    overskrives av runde 2)."""

    def test_tool_kall_logg_registrerer_kall_uten_verktoy(self):
        raw = {"message": {"role": "assistant", "content": "Hei"}}
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("dummy-model")
            provider.generate([{"role": "user", "content": "Hei"}], [])

        self.assertEqual(provider.tool_kall_logg, [{"navn": None, "argumenter": None}])

    def test_tool_kall_logg_registrerer_verktoykall_med_argumenter(self):
        raw = {
            "message": {
                "role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": {"datasett": "malt", "sok": "x"}}}],
            }
        }
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("dummy-model")
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(provider.tool_kall_logg, [{"navn": "hent_ingrediens_info", "argumenter": {"datasett": "malt", "sok": "x"}}])

    def test_tool_kall_logg_akkumulerer_over_flere_kall(self):
        raw1 = {"message": {"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": {"datasett": "malt", "sok": "a"}}}]}}
        raw2 = {"message": {"role": "assistant", "content": "ferdig"}}
        responses = [_fake_urlopen_response(raw1), _fake_urlopen_response(raw2)]

        with mock.patch("urllib.request.urlopen", side_effect=responses):
            provider = OllamaProvider("dummy-model")
            provider.generate([{"role": "user", "content": "..."}], [])
            provider.generate([{"role": "user", "content": "..."}, {"role": "tool", "content": "..."}], [])

        self.assertEqual(len(provider.tool_kall_logg), 2)
        self.assertEqual(provider.tool_kall_logg[0]["navn"], "hent_ingrediens_info")
        self.assertIsNone(provider.tool_kall_logg[1]["navn"])

    def test_num_ctx_og_think_sendes_i_payload_naar_satt(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("dummy-model", num_ctx=16384, think=True)
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(captured["body"]["options"]["num_ctx"], 16384)
        self.assertEqual(captured["body"]["think"], True)

    def test_num_ctx_og_think_utelates_naar_ikke_satt(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("dummy-model")
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertNotIn("num_ctx", captured["body"]["options"])
        self.assertNotIn("think", captured["body"])


class TestVerktoySuksessTolkning(unittest.TestCase):
    def test_funnet_true_gir_suksess(self):
        self.assertTrue(_tolk_verktoy_suksess("{'funnet': True, 'id': 'x'}"))

    def test_funnet_false_gir_ikke_suksess(self):
        self.assertFalse(_tolk_verktoy_suksess("{'funnet': False, 'feil': 'ukjent'}"))

    def test_ukjent_format_gir_none(self):
        self.assertIsNone(_tolk_verktoy_suksess("noe helt annet"))


class TestUttrekkVerktoyTelemetri(unittest.TestCase):
    """_uttrekk_ny_verktoy_telemetri parer provider.tool_kall_logg (navn +
    faktiske argumenter modellen sendte) med de tilhørende "tool"-
    meldingene SotiRuntime la i sesjonshistorikken -- dette er den
    reproduserbarhetsforbedringen Chief-gjennomgangen av PR #312 krevde."""

    class _FakeProvider:
        def __init__(self, tool_kall_logg):
            self.tool_kall_logg = tool_kall_logg

    def test_parer_tool_kall_logg_med_tool_meldinger_i_rekkefolge(self):
        provider = self._FakeProvider([
            {"navn": "hent_ingrediens_info", "argumenter": {"datasett": "malt", "sok": "x"}},
            {"navn": None, "argumenter": None},
        ])
        session = SotiSession(session_id="t")
        session.legg_til("tool", "[hent_ingrediens_info] {'funnet': True, 'id': 'x'}")

        telemetri = _uttrekk_ny_verktoy_telemetri(provider, session, tur=1, kall_idx_start=0, tool_msg_idx_start=0)

        self.assertEqual(len(telemetri), 1)
        self.assertEqual(telemetri[0]["navn"], "hent_ingrediens_info")
        self.assertEqual(telemetri[0]["argumenter"], {"datasett": "malt", "sok": "x"})
        self.assertTrue(telemetri[0]["suksess"])
        self.assertEqual(telemetri[0]["tur"], 1)

    def test_kun_nye_oppforinger_siden_startindeks_tas_med(self):
        provider = self._FakeProvider([
            {"navn": "hent_ingrediens_info", "argumenter": {"datasett": "malt", "sok": "a"}},
            {"navn": None, "argumenter": None},
            {"navn": "hent_ingrediens_info", "argumenter": {"datasett": "humle", "sok": "b"}},
            {"navn": None, "argumenter": None},
        ])
        session = SotiSession(session_id="t")
        session.legg_til("tool", "[hent_ingrediens_info] {'funnet': True, 'id': 'a'}")
        session.legg_til("tool", "[hent_ingrediens_info] {'funnet': False, 'feil': 'x'}")

        telemetri = _uttrekk_ny_verktoy_telemetri(provider, session, tur=2, kall_idx_start=2, tool_msg_idx_start=1)

        self.assertEqual(len(telemetri), 1)
        self.assertEqual(telemetri[0]["argumenter"], {"datasett": "humle", "sok": "b"})
        self.assertFalse(telemetri[0]["suksess"])
        self.assertEqual(telemetri[0]["tur"], 2)


if __name__ == "__main__":
    unittest.main()
