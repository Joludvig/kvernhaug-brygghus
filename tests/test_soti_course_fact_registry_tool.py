"""
Tester for Sóti sitt verifiserte Course Fact Registry-verktøy (V2-5C1,
issue #317) -- beviser:

1. verktøyet bruker utelukkende den betrodde verifiserte-only API-en
   (bryggeskole.course_fact_registry.get_verified_record/
   find_verified_records), aldri rå registerlesing;
2. kun de tre produksjonsverifiserte fagfaktaene er nåbare gjennom det;
3. draft/reviewed/deprecated syntetiske poster lekker aldri gjennom det
   betrodde verktøyet;
4. eksakt ID-oppslag er deterministisk;
5. konsept- og modulfiltrering er deterministisk;
6. kilder/proveniens overlever Sóti-verktøysvaret;
7. et ugyldig register feiler synlig (fail-closed);
8. den kombinerte skillen eksponerer nøyaktig de to tiltenkte verktøyene;
9. det eksisterende Core-ingrediensverktøyet er uendret;
10. CLI-/runtime-koblingen kan bruke den kombinerte skillen via mocks,
    uten en ekte Ollama-server.

Ingen ekte modell/Ollama-server kreves -- alt kjøres mot ekte
`bryggeskole.course_fact_registry`-kode og syntetiske fixtures under
tests/fixtures/course_fact_registry/ (samme fixtures som
tests/test_course_fact_registry.py selv bruker), pluss den ekte
produksjonsregisterfilen for punkt 2/4.

Kjøres med:
    py -3 -m unittest tests.test_soti_course_fact_registry_tool
"""
import os
import unittest
from unittest import mock

from bryggeskole.course_fact_registry import CourseFactRegistryError
from soti.cli import kjor_chat
from soti.providers import MockProvider, ProviderSvar, ToolKall
from soti.runtime import SotiRuntime
from soti.session import SotiSession
from soti.skills import (
    BRYGGE_OPPSLAG_SKILL,
    SOTI_KOMBINERT_SKILL,
    registry_for_skill,
)
from soti.tools import bygg_standard_registry, hent_ingrediens_info, hent_verifisert_fagfakta

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURES = os.path.join(_ROOT, "tests", "fixtures", "course_fact_registry")
_PRODUCTION_REGISTRY = os.path.join(_ROOT, "bryggeskole", "data", "course_fact_registry.json")
_MIXED_FIXTURE = os.path.join(_FIXTURES, "verified_consumer_mixed.json")
_MALFORMED_FIXTURE = os.path.join(_FIXTURES, "invalid_document_shape.json")
_KJENT_MALT_ID = "bohemian_pilsner_floor"


def _patch_registry_path(path):
    return mock.patch("soti.tools._COURSE_FACT_REGISTRY_PATH", path)


class TestVerktoyetBrukerKunBetroddAPI(unittest.TestCase):
    """Akseptansekriterium 1: verktøyet leser aldri den rå registerfilen
    direkte og kaller aldri read_registry_file()/validate_registry() fra
    den betrodde stien."""

    def test_tools_modulen_importerer_kun_verifisert_only_funksjoner(self):
        import ast

        import soti.tools as tools_modul
        with open(tools_modul.__file__, "r", encoding="utf-8") as f:
            kildetekst = f.read()
        self.assertIn(
            "from bryggeskole.course_fact_registry import find_verified_records, get_verified_record",
            kildetekst,
        )
        # Dokumentasjonstekst nevner de forbudte funksjonsnavnene i prosa
        # (for å forklare hva verktøyet ALDRI skal gjøre) -- se på selve
        # AST-en i stedet for rå tekst, slik at det er selve KODEN
        # (import-navn, faktiske identifikatorbruk), ikke docstringen, som
        # bevises fri for dem.
        tre = ast.parse(kildetekst)
        navn_i_bruk = {
            node.id for node in ast.walk(tre) if isinstance(node, ast.Name)
        }
        importerte_navn = {
            alias.asname or alias.name
            for node in ast.walk(tre)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        self.assertNotIn("read_registry_file", navn_i_bruk | importerte_navn)
        self.assertNotIn("validate_registry", navn_i_bruk | importerte_navn)

    def test_verktoyfunksjonen_kaller_den_betrodde_apien_ikke_rafiler(self):
        with mock.patch("soti.tools.get_verified_record") as fake_get, \
             mock.patch("soti.tools.find_verified_records") as fake_find:
            fake_find.return_value = []
            hent_verifisert_fagfakta({"concept": "fermentation.temperature"})
            fake_find.assert_called_once()
            fake_get.assert_not_called()

            fake_get.return_value = None
            hent_verifisert_fagfakta({"id": "FACT-BREW-0001"})
            fake_get.assert_called_once()


class TestKunProduksjonsverifiserteFaktaErNaabare(unittest.TestCase):
    """Akseptansekriterium 2: nøyaktig de tre produksjonsverifiserte
    fagfaktaene er nåbare gjennom verktøyet mot den ekte registerfilen.

    Bruker et modulfilter som dekker alle tre, ikke et tomt argument-
    objekt -- siden Chief-korreksjonen (PR #320) gir et tomt/uten-
    selector-kall et bundet ikke-funnet-svar i stedet for "list alt",
    se TestIngenAnerkjentSelectorGirBundetIkkeFunnet under."""

    def test_modulfilter_som_dekker_alle_gir_nettopp_de_tre_verifiserte_faktaene(self):
        resultat = hent_verifisert_fagfakta({"module": "fermentation.fundamentals"})
        self.assertTrue(resultat["funnet"])
        ider = sorted(post["id"] for post in resultat["fakta"])
        self.assertEqual(ider, ["FACT-BREW-0001", "FACT-BREW-0002", "FACT-BREW-0003"])


class TestIngenAnerkjentSelectorGirBundetIkkeFunnet(unittest.TestCase):
    """Chief-korreksjon (PR #320, issue #317): et argumentobjekt uten
    minst én anerkjent selector (id/concept/module) -- tomt, `None`,
    eller kun ukjente nøkler -- skal aldri stille tolkes som "list alle
    verifiserte fakta". Det skal gi et bundet ikke-funnet-svar direkte,
    uten i det hele tatt å slå opp i registeret (så et gjettet/feil-
    formet verktøykall for et spørsmål utenfor registeret aldri kan
    returnere urelaterte verifiserte fakta i stedet for den påkrevde
    kunnskapshull-stien)."""

    def test_tomt_argumentobjekt_gir_ikke_funnet(self):
        resultat = hent_verifisert_fagfakta({})
        self.assertFalse(resultat["funnet"])
        self.assertIn("feil", resultat)

    def test_ingen_argumenter_i_det_hele_tatt_gir_ikke_funnet(self):
        resultat = hent_verifisert_fagfakta(None)
        self.assertFalse(resultat["funnet"])

    def test_kun_ukjente_nokler_gir_ikke_funnet(self):
        resultat = hent_verifisert_fagfakta({"sok": "gjæringstemperatur", "fritekst": "ja"})
        self.assertFalse(resultat["funnet"])

    def test_tomt_argumentobjekt_slar_aldri_opp_i_registeret(self):
        with mock.patch("soti.tools.get_verified_record") as fake_get, \
             mock.patch("soti.tools.find_verified_records") as fake_find:
            hent_verifisert_fagfakta({})
        fake_get.assert_not_called()
        fake_find.assert_not_called()

    def test_tomt_argumentobjekt_er_bundet_selv_med_ugyldig_register(self):
        # Fail-closed gjelder når et faktisk oppslag forsøkes (se
        # TestUgyldigRegisterFeilerSynlig) -- et argumentobjekt uten
        # anerkjent selector gjør ikke noe oppslag i det hele tatt, så et
        # korrupt register skal ikke kunne krasje denne bundne stien.
        with _patch_registry_path(_MALFORMED_FIXTURE):
            resultat = hent_verifisert_fagfakta({})
        self.assertFalse(resultat["funnet"])

    def test_concept_alene_er_fortsatt_en_gyldig_selector(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"concept": "c.a"})
        self.assertTrue(resultat["funnet"])

    def test_module_alene_er_fortsatt_en_gyldig_selector(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"module": "m.a"})
        self.assertTrue(resultat["funnet"])


class TestDraftReviewedDeprecatedLekkerAldri(unittest.TestCase):
    """Akseptansekriterium 3: syntetiske draft/reviewed/deprecated poster
    som deler konsept/modul med en verifisert post, lekker aldri gjennom
    det betrodde verktøyet -- selv når de ellers ville matchet filteret."""

    def test_draft_med_samme_konsept_og_modul_lekker_ikke(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"concept": "c.a", "module": "m.a"})
        ider = [post["id"] for post in resultat["fakta"]]
        self.assertNotIn("FACT-TEST-0023", ider)  # draft
        self.assertEqual(ider, ["FACT-TEST-0020"])

    def test_deprecated_og_reviewed_ider_gir_ikke_funnet_via_eksakt_oppslag(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            deprecated = hent_verifisert_fagfakta({"id": "FACT-TEST-0025"})
            reviewed = hent_verifisert_fagfakta({"id": "FACT-TEST-0026"})
        self.assertFalse(deprecated["funnet"])
        self.assertFalse(reviewed["funnet"])

    def test_eksakt_id_oppslag_pa_en_ikke_verifisert_id_gir_ikke_funnet(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"id": "FACT-TEST-0023"})
        self.assertFalse(resultat["funnet"])
        self.assertIn("feil", resultat)


class TestEksaktIdOppslagErDeterministisk(unittest.TestCase):
    """Akseptansekriterium 4."""

    def test_samme_id_gir_samme_ene_post_ved_gjentatt_kall(self):
        forste = hent_verifisert_fagfakta({"id": "FACT-BREW-0001"})
        andre = hent_verifisert_fagfakta({"id": "FACT-BREW-0001"})
        self.assertEqual(forste, andre)
        self.assertEqual(len(forste["fakta"]), 1)
        self.assertEqual(forste["fakta"][0]["id"], "FACT-BREW-0001")

    def test_ukjent_id_gir_ikke_funnet_ikke_unntak(self):
        resultat = hent_verifisert_fagfakta({"id": "FACT-BREW-9999"})
        self.assertFalse(resultat["funnet"])


class TestKonseptOgModulFiltreringErDeterministisk(unittest.TestCase):
    """Akseptansekriterium 5 -- reproduserer nøyaktig scenariet
    verified_consumer_mixed.json ble bygget for å bevise."""

    def test_konsept_alene_filtrerer(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"concept": "c.a"})
        ider = sorted(post["id"] for post in resultat["fakta"])
        self.assertEqual(ider, ["FACT-TEST-0020", "FACT-TEST-0021"])

    def test_modul_alene_filtrerer(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"module": "m.a"})
        ider = sorted(post["id"] for post in resultat["fakta"])
        self.assertEqual(ider, ["FACT-TEST-0020", "FACT-TEST-0022"])

    def test_konsept_og_modul_kombinert_er_and_semantikk(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            resultat = hent_verifisert_fagfakta({"concept": "c.a", "module": "m.a"})
        ider = [post["id"] for post in resultat["fakta"]]
        self.assertEqual(ider, ["FACT-TEST-0020"])

    def test_gjentatt_kall_med_samme_filter_gir_samme_resultat(self):
        with _patch_registry_path(_MIXED_FIXTURE):
            forste = hent_verifisert_fagfakta({"concept": "c.a"})
            andre = hent_verifisert_fagfakta({"concept": "c.a"})
        self.assertEqual(forste, andre)


class TestKilderOgProveniensOverlever(unittest.TestCase):
    """Akseptansekriterium 6: sources/proveniens strippes aldri."""

    def test_kilder_med_ref_er_intakt_i_verktoysvaret(self):
        resultat = hent_verifisert_fagfakta({"id": "FACT-BREW-0001"})
        post = resultat["fakta"][0]
        self.assertIn("sources", post)
        self.assertTrue(post["sources"])
        for kilde in post["sources"]:
            self.assertIn("ref", kilde)
            self.assertIn("tier", kilde)
            self.assertTrue(kilde["ref"].startswith("http"))
        self.assertIn("verified_at", post)
        self.assertIn("classification", post)


class TestUgyldigRegisterFeilerSynlig(unittest.TestCase):
    """Akseptansekriterium 7: fail-closed -- aldri et stille fall tilbake
    til rådata eller et oppdiktet svar."""

    def test_malformet_register_kaster_course_fact_registry_error(self):
        with _patch_registry_path(_MALFORMED_FIXTURE):
            with self.assertRaises(CourseFactRegistryError):
                hent_verifisert_fagfakta({"concept": "fermentation.temperature"})

    def test_malformet_register_kaster_ogsaa_for_id_oppslag(self):
        with _patch_registry_path(_MALFORMED_FIXTURE):
            with self.assertRaises(CourseFactRegistryError):
                hent_verifisert_fagfakta({"id": "FACT-BREW-0001"})

    def test_cli_lokken_viser_registerfeil_lesbart_og_fortsetter(self):
        runtime = mock.Mock()
        runtime.handle_message.side_effect = [
            CourseFactRegistryError(["ugyldig register"]),
            "et ekte svar",
        ]
        session = SotiSession(session_id="t")
        utskrift = []

        def inn_sekvens(sekvens):
            it = iter(sekvens)

            def _inn(prompt):
                try:
                    return next(it)
                except StopIteration:
                    raise EOFError
            return _inn

        kjor_chat(runtime, session, inn=inn_sekvens(["forste", "andre", "exit"]), ut=utskrift.append)

        self.assertTrue(any("fagfakta-registeret er ugyldig" in linje.lower() for linje in utskrift))
        self.assertTrue(any(linje.startswith("Sóti: et ekte svar") for linje in utskrift))
        self.assertEqual(runtime.handle_message.call_count, 2)


class TestKombinertSkillEksponererKunDeToTiltenkteVerktoyene(unittest.TestCase):
    """Akseptansekriterium 8."""

    def test_kombinert_skill_har_nettopp_de_to_verktoyene(self):
        registry = registry_for_skill(SOTI_KOMBINERT_SKILL)
        navn = sorted(verktoy.navn for verktoy in registry.alle())
        self.assertEqual(navn, ["hent_ingrediens_info", "hent_verifisert_fagfakta"])

    def test_legacy_bryggeoppslag_skill_er_uendret(self):
        registry = registry_for_skill(BRYGGE_OPPSLAG_SKILL)
        navn = [verktoy.navn for verktoy in registry.alle()]
        self.assertEqual(navn, ["hent_ingrediens_info"])

    def test_standardregistryet_inneholder_begge_verktoyene(self):
        registry = bygg_standard_registry()
        self.assertIn("hent_ingrediens_info", registry)
        self.assertIn("hent_verifisert_fagfakta", registry)


class TestCoreIngrediensverktoyUendret(unittest.TestCase):
    """Akseptansekriterium 9: det eksisterende Core-oppslaget fungerer
    fortsatt nøyaktig som før denne utvidelsen."""

    def test_kjent_malt_id_gir_fortsatt_whitelistede_felt(self):
        resultat = hent_ingrediens_info({"datasett": "malt", "sok": _KJENT_MALT_ID})
        self.assertTrue(resultat["funnet"])
        self.assertEqual(resultat["felt"]["display_name"], "Bohemian Pilsner Floor")
        self.assertNotIn("butikk_match", resultat["felt"])


class TestCliRuntimeMedKombinertSkillUtenOllama(unittest.TestCase):
    """Akseptansekriterium 10: CLI-/runtime-koblingen kan bruke den
    kombinerte skillen gjennom mocks, uten en ekte Ollama-server."""

    def test_runtime_med_kombinert_skill_utforer_fagfakta_verktoykall(self):
        def ber_om_oppslag(meldinger):
            return not any(m["role"] == "tool" for m in meldinger)

        def be_om_fagfakta(meldinger):
            return ProviderSvar(tool_kall=ToolKall(
                navn="hent_verifisert_fagfakta",
                argumenter={"id": "FACT-BREW-0001"},
            ))

        def svar_med_resultat(meldinger):
            siste_tool = next(m["content"] for m in reversed(meldinger) if m["role"] == "tool")
            return ProviderSvar(tekst=f"Her er svaret: {siste_tool}")

        provider = MockProvider(svar_regler=[
            (ber_om_oppslag, be_om_fagfakta),
            (lambda m: True, svar_med_resultat),
        ])
        runtime = SotiRuntime(provider, skill=SOTI_KOMBINERT_SKILL)
        session = SotiSession(session_id="kombinert")

        svar = runtime.handle_message(session, "Hvordan påvirker gjæringstemperatur gjæraktivitet?")

        self.assertIn("FACT-BREW-0001", svar)
        roller = [m["role"] for m in session.historikk]
        self.assertEqual(roller, ["system", "user", "tool", "assistant"])

    def test_kombinert_skill_registry_avviser_hent_ingrediens_info_naar_skillen_ikke_tillater_det(self):
        tom_skill_registry = registry_for_skill(BRYGGE_OPPSLAG_SKILL)
        with self.assertRaises(KeyError):
            tom_skill_registry.utfoer("hent_verifisert_fagfakta", {})

    def test_main_kobler_sotiruntime_til_kombinert_skill(self):
        with mock.patch("soti.cli.OllamaProvider") as fake_provider_cls, \
             mock.patch("soti.cli.SotiRuntime") as fake_runtime_cls, \
             mock.patch("builtins.input", side_effect=EOFError), \
             mock.patch("builtins.print"):
            fake_provider = fake_provider_cls.return_value
            fake_provider.sjekk_tilgjengelig.return_value = None

            from soti.cli import main
            main([])

        _, kwargs = fake_runtime_cls.call_args
        self.assertEqual(kwargs["skill"], SOTI_KOMBINERT_SKILL)


if __name__ == "__main__":
    unittest.main()
