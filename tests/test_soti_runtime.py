"""
Tester for SÓTI PRI 8 -- Local Runtime MVP vertical slice (issue #60).

Beviser, uten å laste ned eller kjøre noen ekte modell:
1. en lokal runtime-grensesnitt kan ta imot en brukermelding og returnere
   et svar gjennom en provider-abstraksjon,
2. Sóti sin identitet/instruksjoner er atskilt fra Core sin sannhet,
3. ett skrivebeskyttet Core-oppslag kan kalles gjennom et begrenset
   verktøygrensesnitt,
4. en bryggeskill kan pakke instruksjoner/verktøytilgang uten å duplisere
   kanonisk Core-data,
5. sesjonstilstand er lokal og testbar,
6. provider-/modellvalg er ikke hardkodet.

Kjøres med:
    py -3 -m unittest discover -s tests
    py -3 -m unittest tests.test_soti_runtime
"""
import json
import os
import unittest

from modules.master_data_io import les_master_json
from soti.identity import SOTI_IDENTITET, bygg_system_melding
from soti.providers import ModelProvider, MockProvider, ProviderSvar, ToolKall
from soti.runtime import SotiRuntime
from soti.session import SotiSession
from soti.skills import BRYGGE_OPPSLAG_SKILL, BryggeSkill, registry_for_skill
from soti.tools import ToolRegistry, bygg_standard_registry, hent_ingrediens_info

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_MALT_PATH = os.path.join(_ROOT, "data", "master_malt.json")
_KJENT_MALT_ID = "bohemian_pilsner_floor"


class TestProviderAbstraksjonIkkeHardkodet(unittest.TestCase):
    """Akseptansekriterium 1 og 6: runtime snakker gjennom en injisert
    ModelProvider, og provider-/modellvalg skjer aldri ved import-tid
    hardkoding et sted i soti-pakken."""

    def test_runtime_tar_imot_melding_og_returnerer_svar_via_provider(self):
        provider = MockProvider(fallback_tekst="Hei, jeg er Sóti (mock).")
        runtime = SotiRuntime(provider)
        session = SotiSession(session_id="s1")

        svar = runtime.handle_message(session, "Hei Sóti")

        self.assertEqual(svar, "Hei, jeg er Sóti (mock).")
        self.assertEqual(session.historikk[-1], {"role": "assistant", "content": svar})

    def test_to_ulike_providere_gir_ulikt_svar_for_samme_melding(self):
        provider_a = MockProvider(fallback_tekst="Svar A")
        provider_b = MockProvider(fallback_tekst="Svar B")

        svar_a = SotiRuntime(provider_a).handle_message(SotiSession("a"), "Hei")
        svar_b = SotiRuntime(provider_b).handle_message(SotiSession("b"), "Hei")

        self.assertNotEqual(svar_a, svar_b)

    def test_en_egendefinert_modelprovider_underklasse_kan_injiseres(self):
        class AlltidJaProvider(ModelProvider):
            def generate(self, meldinger, verktoy):
                return ProviderSvar(tekst="ja")

        svar = SotiRuntime(AlltidJaProvider()).handle_message(SotiSession("c"), "?")
        self.assertEqual(svar, "ja")


class TestIdentitetAtskiltFraCoreSannhet(unittest.TestCase):
    """Akseptansekriterium 2: identiteten/systempromptet inneholder aldri
    konkrete Core-fakta (ingrediensnavn/ID-er) -- de hentes alltid via et
    verktøykall (soti.tools), aldri hardkodet i identitetsteksten."""

    def test_identitetstekst_inneholder_ingen_ekte_maltnavn(self):
        malt_data = les_master_json(_MALT_PATH)
        identitet_lav = SOTI_IDENTITET.lower()
        for oppslag in malt_data.values():
            navn = oppslag.get("display_name")
            if navn:
                self.assertNotIn(navn.lower(), identitet_lav)

    def test_bygg_system_melding_setter_sammen_identitet_og_skill_uten_fakta(self):
        melding = bygg_system_melding(BRYGGE_OPPSLAG_SKILL.instruksjoner)
        self.assertIn(SOTI_IDENTITET, melding)
        self.assertIn("hent_ingrediens_info", melding)
        self.assertNotIn("Weyermann", melding)

    def test_identity_modulen_har_ingen_import_av_masterdata_lesing(self):
        import soti.identity as identity_modul
        kildesti = identity_modul.__file__
        with open(kildesti, "r", encoding="utf-8") as f:
            kildetekst = f.read()
        self.assertNotIn("master_data_io", kildetekst)
        self.assertNotIn("master_malt.json", kildetekst)


class TestCoreOppslagVerktoy(unittest.TestCase):
    """Akseptansekriterium 3: ett skrivebeskyttet Core-oppslag, kalt
    gjennom det begrensede verktøygrensesnittet."""

    def test_kjent_malt_id_gir_whitelistede_felt_uten_butikk_match(self):
        resultat = hent_ingrediens_info({"datasett": "malt", "sok": _KJENT_MALT_ID})
        self.assertTrue(resultat["funnet"])
        self.assertEqual(resultat["id"], _KJENT_MALT_ID)
        self.assertEqual(resultat["felt"]["display_name"], "Bohemian Pilsner Floor")
        self.assertNotIn("butikk_match", resultat["felt"])

    def test_oppslag_pa_alias_eller_navn_finner_samme_oppforing_som_id(self):
        via_id = hent_ingrediens_info({"datasett": "malt", "sok": _KJENT_MALT_ID})
        via_navn = hent_ingrediens_info({"datasett": "malt", "sok": "Bohemian Pilsner Floor"})
        self.assertEqual(via_id["id"], via_navn["id"])

    def test_ukjent_datasett_feiler_synlig_ikke_stille(self):
        resultat = hent_ingrediens_info({"datasett": "sopp", "sok": "hva som helst"})
        self.assertFalse(resultat["funnet"])
        self.assertIn("feil", resultat)

    def test_ukjent_sok_i_kjent_datasett_feiler_synlig(self):
        resultat = hent_ingrediens_info({"datasett": "malt", "sok": "finnes-ikke-xyz"})
        self.assertFalse(resultat["funnet"])

    def test_oppslag_er_skrivebeskyttet_kildefil_urort(self):
        for_innhold = None
        with open(_MALT_PATH, "rb") as f:
            for_innhold = f.read()
        hent_ingrediens_info({"datasett": "malt", "sok": _KJENT_MALT_ID})
        with open(_MALT_PATH, "rb") as f:
            etter_innhold = f.read()
        self.assertEqual(for_innhold, etter_innhold)

    def test_standard_registry_krever_registrert_verktoynavn(self):
        registry = bygg_standard_registry()
        self.assertIn("hent_ingrediens_info", registry)
        with self.assertRaises(KeyError):
            registry.utfoer("slett_alt", {})


class TestBryggeSkillOgVerktoytilgang(unittest.TestCase):
    """Akseptansekriterium 4: en skill pakker instruksjoner + verktøy-
    tilgang uten å duplisere kanonisk Core-data selv."""

    def test_skill_instruksjoner_inneholder_ingen_ingrediensfakta(self):
        malt_data = les_master_json(_MALT_PATH)
        instruksjoner_lav = BRYGGE_OPPSLAG_SKILL.instruksjoner.lower()
        for oppslag in malt_data.values():
            navn = oppslag.get("display_name")
            if navn:
                self.assertNotIn(navn.lower(), instruksjoner_lav)

    def test_registry_for_skill_begrenser_til_tillatte_verktoy(self):
        tom_skill = BryggeSkill(navn="tom", instruksjoner="", tillatte_verktoy=())
        registry = registry_for_skill(tom_skill)
        self.assertEqual(registry.alle(), [])

    def test_registry_for_bryggeoppslag_skill_har_nettopp_ett_verktoy(self):
        registry = registry_for_skill(BRYGGE_OPPSLAG_SKILL)
        navn = [verktoy.navn for verktoy in registry.alle()]
        self.assertEqual(navn, ["hent_ingrediens_info"])


class TestVerktoyRundtripGjennomRuntime(unittest.TestCase):
    """End-til-ende: en provider som ber om verktøyet, får resultatet
    tilbake, og svarer med det -- beviser at akseptansekriterium 1, 3 og 4
    faktisk fungerer sammen, ikke bare hver for seg."""

    def test_runtime_utforer_verktoykall_og_returnerer_endelig_svar(self):
        def ber_om_oppslag(meldinger):
            return not any(m["role"] == "tool" for m in meldinger)

        def be_om_verktoy(meldinger):
            return ProviderSvar(tool_kall=ToolKall(
                navn="hent_ingrediens_info",
                argumenter={"datasett": "malt", "sok": _KJENT_MALT_ID},
            ))

        def har_faatt_oppslag(meldinger):
            return any(m["role"] == "tool" for m in meldinger)

        def svar_med_resultat(meldinger):
            siste_tool = next(m["content"] for m in reversed(meldinger) if m["role"] == "tool")
            return ProviderSvar(tekst=f"Her er svaret: {siste_tool}")

        provider = MockProvider(svar_regler=[
            (ber_om_oppslag, be_om_verktoy),
            (har_faatt_oppslag, svar_med_resultat),
        ])
        runtime = SotiRuntime(provider, skill=BRYGGE_OPPSLAG_SKILL)
        session = SotiSession(session_id="rundtrip")

        svar = runtime.handle_message(session, "Hva er Bohemian Pilsner Floor?")

        self.assertIn("Bohemian Pilsner Floor", svar)
        self.assertEqual(len(provider.kall_logg), 2)
        roller = [m["role"] for m in session.historikk]
        self.assertEqual(roller, ["system", "user", "tool", "assistant"])

    def test_ukjent_verktoynavn_fra_provider_gir_synlig_feil_ikke_stille_fall(self):
        def be_om_ugyldig_verktoy(meldinger):
            return ProviderSvar(tool_kall=ToolKall(navn="finnes_ikke", argumenter={}))

        provider = MockProvider(svar_regler=[(lambda m: True, be_om_ugyldig_verktoy)])
        runtime = SotiRuntime(provider)

        with self.assertRaises(KeyError):
            runtime.handle_message(SotiSession("d"), "test")


class TestLokalSesjonstilstand(unittest.TestCase):
    """Akseptansekriterium 5: sesjonstilstand er lokal (in-memory, ingen
    global/delt state) og testbar."""

    def test_sesjonshistorikk_vokser_med_hver_tur(self):
        provider = MockProvider(fallback_tekst="ok")
        runtime = SotiRuntime(provider)
        session = SotiSession(session_id="e")

        runtime.handle_message(session, "første melding")
        self.assertEqual(len(session.historikk), 3)  # system + user + assistant

        runtime.handle_message(session, "andre melding")
        self.assertEqual(len(session.historikk), 5)  # + user + assistant, system kun én gang

    def test_to_sesjoner_deler_ikke_tilstand(self):
        provider = MockProvider(fallback_tekst="ok")
        runtime = SotiRuntime(provider)
        session_1 = SotiSession(session_id="f1")
        session_2 = SotiSession(session_id="f2")

        runtime.handle_message(session_1, "kun i sesjon 1")

        self.assertEqual(len(session_1.historikk), 3)
        self.assertEqual(len(session_2.historikk), 0)

    def test_meldinger_returnerer_en_kopi_ikke_intern_liste(self):
        session = SotiSession(session_id="g")
        session.legg_til("user", "hei")
        kopi = session.meldinger()
        kopi.append({"role": "user", "content": "skal ikke påvirke original"})
        self.assertEqual(len(session.historikk), 1)


class TestVerktoyRegistryKonstruertInnhold(unittest.TestCase):
    """Et tomt registry aksepterer ingen kall -- beviser at
    verktøygrensesnittet er konstruert-innhold (kun eksplisitt registrerte
    verktøy kan noensinne kalles), ikke en åpen dispatch."""

    def test_tomt_registry_avviser_ethvert_kall(self):
        registry = ToolRegistry()
        with self.assertRaises(KeyError):
            registry.utfoer("hent_ingrediens_info", {})


if __name__ == "__main__":
    unittest.main()
