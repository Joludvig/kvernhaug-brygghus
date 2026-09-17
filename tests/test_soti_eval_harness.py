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


if __name__ == "__main__":
    unittest.main()
