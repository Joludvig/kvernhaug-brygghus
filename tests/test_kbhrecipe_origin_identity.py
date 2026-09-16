"""
Issue #283 -- persistens-/identitetstester for
modules/recipe_storage.py sine `.kbhrecipe originRecipeId`-funksjoner
(docs/development/CORE_KBHRECIPE_ORIGIN_IDENTITY_V1.md), mirroring
tests/test_kbhbrew_storage_identity.py sitt etablerte mønster for
`.kbhbrew` sin `originBrewId`.

Dekker:
  - App sin ENESTE mint-mekanisme (sikre_origin_recipe_id()): mint +
    atomisk enkelt-felt-skriving KUN til den ene kildefilen, KUN når
    feltet mangler/er ugyldig;
  - andre kall (uendret fil) returnerer samme, eksisterende verdi --
    ALDRI re-mintet;
  - DEMO_MODE og "ingen kjent kildefil" er begge no-op, ingen skriving;
  - duplikat-deteksjon (finnes_oppskrift_med_origin()) -- eksakt
    strenglikhet, ingen falske positiver/negativer;
  - hele ui/recipe_card.py sin knapp-livssyklus (Lagre endringer/Lagre
    som ny kopi/Eksporter), speilet via en lokal `_bygg_recipe_fra_session()`-
    hjelpefunksjon -- samme forenkling som
    tests/test_kbh_passthrough.py bruker for _kbh_passthrough, uten å
    bygge et fullt AppTest-harness for selve UI-et.

Bruker UTELUKKENDE tempfile.TemporaryDirectory() via
KVERNHAUG_RECIPES_DIR -- aldri den ekte recipes/-mappen.

Kjøres med:
    python3 -m unittest tests.test_kbhrecipe_origin_identity -b
"""
import json
import logging
import os
import tempfile
import unittest
from unittest import mock

logging.getLogger("streamlit").setLevel(logging.ERROR)
import streamlit as st

from modules.recipe import bygg_recipe_object
import modules.recipe_storage as recipe_storage


def _recipe(navn="Identitetstest"):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
    )


class _IsolertRecipeMappeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _les_fil(self, filnavn):
        with open(os.path.join(self._tmpdir.name, filnavn), encoding="utf-8") as f:
            return json.load(f)


class TestSikreOriginRecipeIdMinter(_IsolertRecipeMappeTestCase):
    def test_forste_kall_minter_og_skriver_atomisk_tilbake(self):
        filnavn = recipe_storage.lagre_oppskrift(_recipe())
        self.assertNotIn("originRecipeId", self._les_fil(filnavn))

        origin = recipe_storage.sikre_origin_recipe_id(filnavn)

        self.assertIsInstance(origin, str)
        self.assertTrue(origin.strip())
        self.assertEqual(self._les_fil(filnavn)["originRecipeId"], origin)

    def test_andre_kall_returnerer_samme_verdi_ikke_re_mintet(self):
        filnavn = recipe_storage.lagre_oppskrift(_recipe())
        forste = recipe_storage.sikre_origin_recipe_id(filnavn)
        andre = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertEqual(forste, andre)

    def test_kun_originrecipeid_feltet_endres_paa_disk(self):
        # "atomisk tilbake til AKKURAT den ene filen" -- ingen andre felt
        # i den lagrede filen skal røres av selve mint-operasjonen.
        recipe = _recipe()
        recipe["brygger_stil"] = "Skal overleve uendret"
        filnavn = recipe_storage.lagre_oppskrift(recipe)
        for_data = self._les_fil(filnavn)

        recipe_storage.sikre_origin_recipe_id(filnavn)

        etter_data = self._les_fil(filnavn)
        for nokkel, verdi in for_data.items():
            self.assertEqual(etter_data[nokkel], verdi)

    def test_eksisterende_gyldig_origin_bevares_uendret(self):
        recipe = _recipe()
        filnavn = recipe_storage.lagre_oppskrift(recipe)
        data = self._les_fil(filnavn)
        data["originRecipeId"] = "allerede-satt-fra-tidligere-import"
        with open(os.path.join(self._tmpdir.name, filnavn), "w", encoding="utf-8") as f:
            json.dump(data, f)

        origin = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertEqual(origin, "allerede-satt-fra-tidligere-import")

    def test_tom_streng_origin_regnes_som_mangler_og_mintes(self):
        recipe = _recipe()
        filnavn = recipe_storage.lagre_oppskrift(recipe)
        data = self._les_fil(filnavn)
        data["originRecipeId"] = "   "
        with open(os.path.join(self._tmpdir.name, filnavn), "w", encoding="utf-8") as f:
            json.dump(data, f)

        origin = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertTrue(origin.strip())
        self.assertNotEqual(origin, "   ")

    def test_ingen_kjent_kildefil_er_en_noop(self):
        self.assertIsNone(recipe_storage.sikre_origin_recipe_id(None))
        self.assertIsNone(recipe_storage.sikre_origin_recipe_id(""))

    def test_ikke_eksisterende_fil_er_en_noop(self):
        self.assertIsNone(recipe_storage.sikre_origin_recipe_id("finnes_ikke.json"))

    def test_demo_mode_er_en_noop(self):
        filnavn_kandidat = "en_oppskrift.json"
        with mock.patch.object(recipe_storage, "DEMO_MODE", True):
            self.assertIsNone(recipe_storage.sikre_origin_recipe_id(filnavn_kandidat))


class TestFinnesOppskriftMedOrigin(_IsolertRecipeMappeTestCase):
    def test_ingen_lagrede_oppskrifter_gir_false(self):
        self.assertFalse(recipe_storage.finnes_oppskrift_med_origin("noe-id"))

    def test_eksakt_match_gir_true(self):
        filnavn = recipe_storage.lagre_oppskrift(_recipe())
        origin = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertTrue(recipe_storage.finnes_oppskrift_med_origin(origin))

    def test_ingen_match_gir_false(self):
        filnavn = recipe_storage.lagre_oppskrift(_recipe())
        recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertFalse(recipe_storage.finnes_oppskrift_med_origin("en-helt-annen-id"))

    def test_manglende_tom_eller_ikke_streng_gir_alltid_false(self):
        filnavn = recipe_storage.lagre_oppskrift(_recipe())
        recipe_storage.sikre_origin_recipe_id(filnavn)
        for kandidat in (None, "", "   ", 12345, [], {}):
            self.assertFalse(recipe_storage.finnes_oppskrift_med_origin(kandidat))

    def test_mappe_som_ikke_finnes_gir_false(self):
        self.assertFalse(
            recipe_storage.finnes_oppskrift_med_origin("noe-id", mappe=os.path.join(self._tmpdir.name, "finnes_ikke"))
        )


def _bygg_recipe_fra_session(origin_recipe_id=None):
    """Speiler EKSAKT ui/recipe_card.py sin `_bygg_recipe_fra_session()`,
    begrenset til feltene som er relevante for originRecipeId -- samme
    forenkling som tests/test_kbh_passthrough.py sin tilsvarende
    hjelpefunksjon."""
    return bygg_recipe_object(
        st.session_state.get("gjeldende_navn") or "Kvernhaug Spesial",
        st.session_state.get("batch_volum_input", 20.0),
        efficiency=0.75,
        malts=st.session_state.get("valgt_malt", []),
        hops=st.session_state.get("valgt_humle", []),
        yeast=st.session_state.get("valgt_gjaer_id", "safale_us_05"),
        og=1.048, fg=1.012, abv=4.7, ibu=25, ebc=8, flavor_profile={},
        origin_recipe_id=origin_recipe_id,
    )


class TestRecipeCardKnappLivssyklus(_IsolertRecipeMappeTestCase):
    """Speiler ui/recipe_card.py sine tre knapper (Lagre endringer/Lagre
    som ny kopi/Eksporter) sin faktiske originRecipeId-håndtering, uten
    et fullt AppTest-Streamlit-oppsett -- dekker issue #283 sin
    "Verification"-liste direkte."""

    def setUp(self):
        super().setUp()
        st.session_state.clear()
        st.session_state["gjeldende_navn"] = "Livssyklustest"
        st.session_state["batch_volum_input"] = 20.0
        st.session_state["valgt_malt"] = [{"id": "weyermann_pilsner", "mengde": 5.0}]
        st.session_state["valgt_humle"] = []
        st.session_state["valgt_gjaer_id"] = "safale_us_05"

    def tearDown(self):
        st.session_state.clear()
        super().tearDown()

    def _eksporter(self, kilde_filnavn):
        """Speiler EKSAKT "📦 Eksporter"-knappens origin-logikk i
        ui/recipe_card.py."""
        if kilde_filnavn:
            origin = recipe_storage.sikre_origin_recipe_id(kilde_filnavn)
            if origin:
                st.session_state["_aktiv_kbh_origin_recipe_id"] = origin
        else:
            origin = st.session_state.get("_aktiv_kbh_origin_recipe_id")
        return _bygg_recipe_fra_session(origin_recipe_id=origin)

    def test_1_forste_eksplisitte_eksport_minter_og_skriver_atomisk(self):
        filnavn = recipe_storage.lagre_oppskrift(_bygg_recipe_fra_session())
        self.assertNotIn("originRecipeId", self._les_fil(filnavn))

        eksportert = self._eksporter(filnavn)

        self.assertIn("originRecipeId", eksportert)
        self.assertEqual(self._les_fil(filnavn)["originRecipeId"], eksportert["originRecipeId"])

    def test_2_andre_eksport_bevarer_samme_origin(self):
        filnavn = recipe_storage.lagre_oppskrift(_bygg_recipe_fra_session())
        forste = self._eksporter(filnavn)
        andre = self._eksporter(filnavn)
        self.assertEqual(forste["originRecipeId"], andre["originRecipeId"])

    def test_3_ingen_skriving_ved_ren_lasting(self):
        filnavn = recipe_storage.lagre_oppskrift(_bygg_recipe_fra_session())
        self._eksporter(filnavn)  # mint origin først, som en tidligere økt ville gjort
        for_mtime = os.path.getmtime(os.path.join(self._tmpdir.name, filnavn))
        for_data = self._les_fil(filnavn)

        # "Last inn" -- ren lesing, akkurat som ui/sidebar.py sin
        # load-gren (hent_alle_oppskrifter() + tildeling til
        # session_state) -- ALDRI et skrivekall.
        lastet = recipe_storage.hent_alle_oppskrifter()[st.session_state["gjeldende_navn"]]
        st.session_state["_aktiv_kbh_origin_recipe_id"] = lastet.get("originRecipeId")

        self.assertEqual(os.path.getmtime(os.path.join(self._tmpdir.name, filnavn)), for_mtime)
        self.assertEqual(self._les_fil(filnavn), for_data)

    def test_4_lagre_endringer_bevarer_eksisterende_origin(self):
        filnavn = recipe_storage.lagre_oppskrift(_bygg_recipe_fra_session())
        self._eksporter(filnavn)  # minter og aktiverer origin i session_state
        origin_foer = st.session_state["_aktiv_kbh_origin_recipe_id"]

        # "💾 Lagre endringer" -- preserverer AKTIV origin uendret.
        st.session_state["gjeldende_navn"] = "Livssyklustest (redigert)"
        redigert = _bygg_recipe_fra_session(origin_recipe_id=origin_foer)
        nytt_filnavn = recipe_storage.lagre_oppskrift(redigert, kilde_filnavn=filnavn)

        self.assertEqual(self._les_fil(nytt_filnavn)["originRecipeId"], origin_foer)

    def test_5_lagre_som_ny_kopi_far_ingen_origin_foer_egen_eksport(self):
        filnavn = recipe_storage.lagre_oppskrift(_bygg_recipe_fra_session())
        self._eksporter(filnavn)  # kilden har nå en origin

        # "💾 Lagre som ny kopi" -- ALDRI arv kildens origin (§3.5).
        st.session_state["gjeldende_navn"] = "Livssyklustest Kopi"
        kopi = _bygg_recipe_fra_session(origin_recipe_id=None)
        kopi_filnavn = recipe_storage.lagre_oppskrift(kopi, kilde_filnavn=None, bloker_ved_navnekollisjon=True)

        self.assertNotIn("originRecipeId", self._les_fil(kopi_filnavn))

        # Kopiens EGEN, senere eksport minter en FRESH origin, forskjellig
        # fra kildens.
        kopi_eksportert = self._eksporter(kopi_filnavn)
        kilde_data = self._les_fil(filnavn)
        self.assertNotEqual(kopi_eksportert["originRecipeId"], kilde_data["originRecipeId"])


if __name__ == "__main__":
    unittest.main()
