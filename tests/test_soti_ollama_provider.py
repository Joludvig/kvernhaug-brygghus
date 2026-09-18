"""
Tester for soti.ollama_provider (issue #315, V2-5B) -- beviser at
OllamaProvider oversetter meldinger/verktøy til Ollamas API-format riktig,
sender et eksplisitt num_ctx, og oversetter nettverks-/HTTP-/JSON-feil til
de synlige, spesifikke unntakstypene issue #315 §4 krever -- UTEN å kreve
en ekte Ollama-server, GPU eller modellnedlasting: HTTP-laget mockes.

Kjøres med:
    py -3 -m unittest tests.test_soti_ollama_provider
"""
import io
import json
import unittest
import urllib.error
from unittest import mock

from soti.ollama_provider import (
    STANDARD_NUM_CTX,
    OllamaModellFeil,
    OllamaProvider,
    OllamaProviderFeil,
    OllamaSvarFeil,
    OllamaTidsavbrudd,
    OllamaUtilgjengelig,
)
from soti.providers import ModelProvider
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


def _fake_http_error(code, error_body=None, url="http://127.0.0.1:11434/api/chat"):
    body = json.dumps(error_body).encode("utf-8") if error_body is not None else b""
    return urllib.error.HTTPError(url, code, "feil", {}, io.BytesIO(body))


class TestOllamaProviderErModelProvider(unittest.TestCase):
    def test_er_en_modelprovider_underklasse(self):
        self.assertTrue(issubclass(OllamaProvider, ModelProvider))


class TestMeldingsOgVerktoyOversettelse(unittest.TestCase):
    def test_ren_tekst_svar_gir_providersvar_uten_tool_kall(self):
        raw = {"message": {"role": "assistant", "content": "Hei fra Sóti"}}
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            svar = provider.generate([{"role": "user", "content": "Hei"}], [])

        self.assertEqual(svar.tekst, "Hei fra Sóti")
        self.assertIsNone(svar.tool_kall)

    def test_tool_calls_med_dict_argumenter_parses(self):
        raw = {
            "message": {
                "role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": {"datasett": "malt", "sok": "pilsner"}}}],
            }
        }
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            svar = provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(svar.tool_kall.navn, "hent_ingrediens_info")
        self.assertEqual(svar.tool_kall.argumenter, {"datasett": "malt", "sok": "pilsner"})

    def test_tool_calls_med_json_streng_argumenter_parses(self):
        raw = {
            "message": {
                "role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": '{"datasett": "humle", "sok": "cascade"}'}}],
            }
        }
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            svar = provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(svar.tool_kall.argumenter, {"datasett": "humle", "sok": "cascade"})

    def test_ukjent_tool_arguments_json_gir_tomt_dict_ikke_krasj(self):
        raw = {
            "message": {
                "role": "assistant", "content": "",
                "tool_calls": [{"function": {"name": "hent_ingrediens_info", "arguments": "ikke gyldig json"}}],
            }
        }
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            svar = provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(svar.tool_kall.argumenter, {})

    def test_meldingsroller_og_innhold_videreformidles_uendret(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        meldinger = [
            {"role": "system", "content": "system-tekst"},
            {"role": "user", "content": "bruker-tekst"},
            {"role": "tool", "content": "[verktoy] resultat"},
        ]
        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.generate(meldinger, [])

        self.assertEqual(captured["body"]["messages"], meldinger)

    def test_kjent_verktoy_far_eksplisitt_skjema(self):
        kjent_tool = Tool(navn="hent_ingrediens_info", beskrivelse="test", handler=lambda a: {})
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.generate([{"role": "user", "content": "..."}], [kjent_tool])

        sendt_skjema = captured["body"]["tools"][0]["function"]["parameters"]
        self.assertIn("datasett", sendt_skjema["properties"])
        self.assertIn("sok", sendt_skjema["properties"])

    def test_ukjent_verktoynavn_far_apent_skjema_ikke_krasj(self):
        ukjent_tool = Tool(navn="fremtidig_verktoy", beskrivelse="test", handler=lambda a: {})
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.generate([{"role": "user", "content": "..."}], [ukjent_tool])

        sendt_skjema = captured["body"]["tools"][0]["function"]["parameters"]
        self.assertEqual(sendt_skjema, {"type": "object"})

    def test_ingen_verktoy_gir_intet_tools_felt(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertNotIn("tools", captured["body"])


class TestEksplisittKontekstvindu(unittest.TestCase):
    def test_standard_num_ctx_er_8192(self):
        self.assertEqual(STANDARD_NUM_CTX, 8192)

    def test_default_konstruktor_sender_num_ctx_8192(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(captured["body"]["options"]["num_ctx"], 8192)

    def test_num_ctx_overstyrbar(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("ministral-3:8b", num_ctx=16384)
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertEqual(captured["body"]["options"]["num_ctx"], 16384)


class TestLoopbackOgIngenSkyfallback(unittest.TestCase):
    def test_standard_base_url_er_loopback(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.generate([{"role": "user", "content": "..."}], [])

        self.assertTrue(captured["url"].startswith("http://127.0.0.1:11434"))

    def test_kaller_aldri_noe_annet_endepunkt_enn_konfigurert_base_url(self):
        raw = {"message": {"role": "assistant", "content": "ok"}}
        kalte_urler = []

        def fake_urlopen(req, timeout=None):
            kalte_urler.append(req.full_url)
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M", base_url="http://127.0.0.1:11434")
            provider.generate([{"role": "user", "content": "..."}], [])
            provider.sjekk_tilgjengelig()

        for url in kalte_urler:
            self.assertTrue(url.startswith("http://127.0.0.1:11434/"))


class TestFeilkartlegging(unittest.TestCase):
    def test_url_error_gir_ollama_utilgjengelig(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            with self.assertRaises(OllamaUtilgjengelig):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_timeout_gir_ollama_tidsavbrudd(self):
        with mock.patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M", timeout_s=5.0)
            with self.assertRaises(OllamaTidsavbrudd):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_http_404_gir_ollama_modellfeil(self):
        feil = _fake_http_error(404, {"error": "model 'ukjent-modell' not found, try pulling it first"})
        with mock.patch("urllib.request.urlopen", side_effect=feil):
            provider = OllamaProvider("ukjent-modell")
            with self.assertRaises(OllamaModellFeil):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_http_500_gir_ollama_svarfeil(self):
        feil = _fake_http_error(500, {"error": "internal server error"})
        with mock.patch("urllib.request.urlopen", side_effect=feil):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            with self.assertRaises(OllamaSvarFeil):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_ugyldig_json_i_svaret_gir_ollama_svarfeil(self):
        class _FakeRespUgyldigJson:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return b"dette er ikke json"

        with mock.patch("urllib.request.urlopen", return_value=_FakeRespUgyldigJson()):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            with self.assertRaises(OllamaSvarFeil):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_error_felt_i_200_svar_gir_ollama_modellfeil(self):
        raw = {"error": "model 'x' not found"}
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("x")
            with self.assertRaises(OllamaModellFeil):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_manglende_message_felt_gir_ollama_svarfeil(self):
        raw = {"noe_annet": True}
        with mock.patch("urllib.request.urlopen", return_value=_fake_urlopen_response(raw)):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            with self.assertRaises(OllamaSvarFeil):
                provider.generate([{"role": "user", "content": "..."}], [])

    def test_alle_feiltyper_er_ollamaproviderfeil(self):
        self.assertTrue(issubclass(OllamaUtilgjengelig, OllamaProviderFeil))
        self.assertTrue(issubclass(OllamaTidsavbrudd, OllamaProviderFeil))
        self.assertTrue(issubclass(OllamaModellFeil, OllamaProviderFeil))
        self.assertTrue(issubclass(OllamaSvarFeil, OllamaProviderFeil))


class TestSjekkTilgjengelig(unittest.TestCase):
    def test_sjekk_tilgjengelig_poster_til_api_show_med_modellnavn(self):
        raw = {"name": "llama3.1:8b-instruct-q4_K_M", "details": {}}
        captured = {}

        def fake_urlopen(req, timeout=None):
            captured["url"] = req.full_url
            captured["body"] = json.loads(req.data.decode("utf-8"))
            return _fake_urlopen_response(raw)

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            provider.sjekk_tilgjengelig()

        self.assertTrue(captured["url"].endswith("/api/show"))
        self.assertEqual(captured["body"]["name"], "llama3.1:8b-instruct-q4_K_M")

    def test_sjekk_tilgjengelig_kaster_ollama_utilgjengelig_hvis_server_nede(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("Connection refused")):
            provider = OllamaProvider("llama3.1:8b-instruct-q4_K_M")
            with self.assertRaises(OllamaUtilgjengelig):
                provider.sjekk_tilgjengelig()

    def test_sjekk_tilgjengelig_kaster_ollama_modellfeil_hvis_modell_mangler(self):
        feil = _fake_http_error(404, {"error": "model 'x' not found"})
        with mock.patch("urllib.request.urlopen", side_effect=feil):
            provider = OllamaProvider("x")
            with self.assertRaises(OllamaModellFeil):
                provider.sjekk_tilgjengelig()


if __name__ == "__main__":
    unittest.main()
