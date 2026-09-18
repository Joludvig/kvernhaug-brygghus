"""
Tester for soti.cli (issue #315, V2-5B) -- beviser samtaleløkkens
avslutningslogikk, at lokale provider-/verktøyfeil vises som lesbare
meldinger i stedet for å krasje CLI-en, og at hovedfunksjonen kobler
sammen provider/runtime/session riktig -- UTEN en ekte terminal eller en
ekte Ollama-server (input()/OllamaProvider mockes).

Kjøres med:
    py -3 -m unittest tests.test_soti_cli
"""
import unittest
from unittest import mock

from soti.cli import bygg_argument_parser, kjor_chat, main
from soti.ollama_provider import OllamaModellFeil, OllamaUtilgjengelig
from soti.providers import MockProvider, ProviderSvar
from soti.runtime import SotiRuntime
from soti.session import SotiSession


def _inn_sekvens(*svar):
    """Returnerer en injiserbar `inn`-funksjon som gir ett svar per kall,
    og kaster EOFError når sekvensen er brukt opp (simulerer at brukeren
    lukker terminalen i stedet for å henge)."""
    it = iter(svar)

    def _inn(prompt):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    return _inn


class TestKjorChatAvslutning(unittest.TestCase):
    def test_exit_kommando_avslutter_uten_a_kalle_runtime(self):
        runtime = mock.Mock()
        session = SotiSession(session_id="t")
        utskrift = []
        kjor_chat(runtime, session, inn=_inn_sekvens("exit"), ut=utskrift.append)

        runtime.handle_message.assert_not_called()
        self.assertTrue(any("avslutter" in linje.lower() for linje in utskrift))

    def test_alle_avslutningskommandoer_virker_case_insensitivt(self):
        for kommando in ["exit", "QUIT", ":q", "Avslutt"]:
            runtime = mock.Mock()
            session = SotiSession(session_id="t")
            kjor_chat(runtime, session, inn=_inn_sekvens(kommando), ut=lambda *_: None)
            runtime.handle_message.assert_not_called()

    def test_eof_avslutter_uten_krasj(self):
        runtime = mock.Mock()
        session = SotiSession(session_id="t")
        utskrift = []

        def inn_som_krasjer(prompt):
            raise EOFError

        kjor_chat(runtime, session, inn=inn_som_krasjer, ut=utskrift.append)
        runtime.handle_message.assert_not_called()

    def test_tomme_linjer_hoppes_over(self):
        runtime = mock.Mock()
        runtime.handle_message.return_value = "svar"
        session = SotiSession(session_id="t")
        utskrift = []
        kjor_chat(runtime, session, inn=_inn_sekvens("", "   ", "et ekte spørsmål", "exit"), ut=utskrift.append)

        runtime.handle_message.assert_called_once_with(session, "et ekte spørsmål")


class TestKjorChatEkteRuntime(unittest.TestCase):
    """Kjører hele løkken mot en ekte SotiRuntime + MockProvider (ingen
    Ollama nødvendig) -- beviser den faktiske multi-turn-koblingen, ikke
    bare at kjor_chat kaller en mock riktig."""

    def test_flere_turer_i_samme_sesjon_akkumuleres(self):
        provider = MockProvider(svar_regler=[
            (lambda m: True, lambda m: ProviderSvar(tekst=f"svar {len(m)}")),
        ])
        runtime = SotiRuntime(provider)
        session = SotiSession(session_id="t")
        utskrift = []

        kjor_chat(runtime, session, inn=_inn_sekvens("tur 1", "tur 2", "tur 3", "exit"), ut=utskrift.append)

        soti_svar = [linje for linje in utskrift if linje.startswith("Sóti: ")]
        self.assertEqual(len(soti_svar), 3)
        self.assertEqual(len(session.historikk), 1 + 3 * 2)  # system + (user, assistant) * 3


class TestKjorChatFeilhandtering(unittest.TestCase):
    def test_ollama_feil_vises_lesbart_og_fortsetter_lokken(self):
        runtime = mock.Mock()
        runtime.handle_message.side_effect = [
            OllamaUtilgjengelig("Fikk ikke kontakt med Ollama på http://127.0.0.1:11434."),
            "et ekte svar",
        ]
        session = SotiSession(session_id="t")
        utskrift = []
        kjor_chat(runtime, session, inn=_inn_sekvens("første", "andre", "exit"), ut=utskrift.append)

        self.assertTrue(any("lokal feil" in linje.lower() for linje in utskrift))
        self.assertTrue(any(linje.startswith("Sóti: et ekte svar") for linje in utskrift))
        self.assertEqual(runtime.handle_message.call_count, 2)

    def test_modellfeil_vises_lesbart(self):
        runtime = mock.Mock()
        runtime.handle_message.side_effect = OllamaModellFeil("Kjør 'ollama pull x' først.")
        session = SotiSession(session_id="t")
        utskrift = []
        kjor_chat(runtime, session, inn=_inn_sekvens("spørsmål", "exit"), ut=utskrift.append)

        self.assertTrue(any("lokal feil" in linje.lower() for linje in utskrift))

    def test_ukjent_verktoy_keyerror_vises_lesbart_ikke_traceback(self):
        runtime = mock.Mock()
        runtime.handle_message.side_effect = KeyError("Ukjent verktøy: 'oppdiktet_verktoy'")
        session = SotiSession(session_id="t")
        utskrift = []
        kjor_chat(runtime, session, inn=_inn_sekvens("spørsmål", "exit"), ut=utskrift.append)

        self.assertTrue(any("ukjent verktøy" in linje.lower() for linje in utskrift))


class TestArgumentParser(unittest.TestCase):
    def test_standardverdier(self):
        args = bygg_argument_parser().parse_args([])
        self.assertEqual(args.model, "llama3.1:8b-instruct-q4_K_M")
        self.assertEqual(args.base_url, "http://127.0.0.1:11434")
        self.assertEqual(args.num_ctx, 8192)
        self.assertFalse(args.skip_healthcheck)

    def test_modell_overstyrbar_for_fallback(self):
        args = bygg_argument_parser().parse_args(["--model", "ministral-3:8b"])
        self.assertEqual(args.model, "ministral-3:8b")


class TestMain(unittest.TestCase):
    def test_main_kjorer_helsesjekk_og_starter_chat_ved_suksess(self):
        with mock.patch("soti.cli.OllamaProvider") as fake_provider_cls, \
             mock.patch("builtins.input", side_effect=EOFError), \
             mock.patch("builtins.print"):
            fake_provider = fake_provider_cls.return_value
            fake_provider.sjekk_tilgjengelig.return_value = None

            resultat = main([])

        fake_provider.sjekk_tilgjengelig.assert_called_once()
        self.assertEqual(resultat, 0)

    def test_main_returnerer_1_og_starter_ikke_chat_hvis_helsesjekk_feiler(self):
        with mock.patch("soti.cli.OllamaProvider") as fake_provider_cls, \
             mock.patch("builtins.input") as fake_input, \
             mock.patch("builtins.print"):
            fake_provider = fake_provider_cls.return_value
            fake_provider.sjekk_tilgjengelig.side_effect = OllamaUtilgjengelig("Ollama nede")

            resultat = main([])

        self.assertEqual(resultat, 1)
        fake_input.assert_not_called()

    def test_skip_healthcheck_hopper_over_sjekken(self):
        with mock.patch("soti.cli.OllamaProvider") as fake_provider_cls, \
             mock.patch("builtins.input", side_effect=EOFError), \
             mock.patch("builtins.print"):
            fake_provider = fake_provider_cls.return_value

            resultat = main(["--skip-healthcheck"])

        fake_provider.sjekk_tilgjengelig.assert_not_called()
        self.assertEqual(resultat, 0)

    def test_main_sender_overstyrt_modell_til_provider(self):
        with mock.patch("soti.cli.OllamaProvider") as fake_provider_cls, \
             mock.patch("builtins.input", side_effect=EOFError), \
             mock.patch("builtins.print"):
            main(["--model", "ministral-3:8b", "--num-ctx", "16384"])

        _, kwargs = fake_provider_cls.call_args
        self.assertEqual(kwargs["model"], "ministral-3:8b")
        self.assertEqual(kwargs["num_ctx"], 16384)


if __name__ == "__main__":
    unittest.main()
