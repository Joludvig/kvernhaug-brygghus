"""
V2.2 G3K (issue #384) — ende-til-ende-regresjonstest for den planlagte
gjæringstemperaturen (`fermentation_temp_target_c` / `st.session_state
["gjaering_temp_maal_c"]`) via den EKTE app.py, samme mønster som
tests/test_water_recipe_integration.py (streamlit.testing.v1.AppTest,
isolert KVERNHAUG_RECIPES_DIR).

Dekker de påkrevde overgangene i docs/development/
v22_g3j_fermentation_learn_plan_contract.md §7/§10.3:
  (a) gammel oppskrift uten feltet åpnes tomt;
  (b) sette mål -> lagre -> gjenåpne i en HELT FRISK sesjon bevarer verdien;
  (c) oppskrift MED mål -> oppskrift UTEN feltet rydder til None;
  (d) lastet oppskrift -> sidebar-blankvalg rydder til None;
  (e) arkiver-suksess -> blank rydder via pending-før-widget-stien;
  (f) importert .kbhrecipe (feltet er ikke portabelt i denne runden)
      nullstiller til None;
  (g) malt/humle/gjær/process_profile/water_* er upåvirket.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")

_BLANKVALG = "-- Velg oppskrift --"

# Samme kjente, ekte masterdata-IDer som tests/test_kbh_import_ui_apptest.py
# bruker for .kbhrecipe-importscenarioet -- aldri antatt, alltid verifisert
# mot ekte data der en tidligere test allerede har bevist gyldigheten.
_GYLDIG_MALT_ID = "bohemian_pilsner_floor"
_GYLDIG_HUMLE_ID = "amarillo"
_GYLDIG_GJAER_ID = "lalbrew_house_ale"


def _kbhrecipe_tekst():
    payload = {
        "recipeSchemaVersion": 1,
        "navn": "GTM Importert Oppskrift",
        "volum": 20.0,
        "effektivitet": 72,
        "malt": [{"id": _GYLDIG_MALT_ID, "mengde": 4.0}],
        "humle": [{"id": _GYLDIG_HUMLE_ID, "gram": 20, "tid": 60}],
        "gjaerId": _GYLDIG_GJAER_ID,
    }
    return json.dumps({
        "format": "kbhrecipe", "version": 1, "exportedAt": "2026-09-24T00:00:00Z",
        "generator": "test", "recipe": payload,
    })


class TestGjaeringTempMaalGjennomEktApp(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        self._recipe_storage = recipe_storage

        self._malt = [
            {"id": "weyermann_munich_1", "mengde": 0.65},
            {"id": "munich_ii", "mengde": 4.28},
        ]
        self._hops = [{"id": "tettnang", "gram": 30, "tid": 60}]

        # Recipe A -- MED et planlagt gjæringsmål.
        recipe_a = bygg_recipe_object(
            "GTM Recipe A", 20.0, 0.75, self._malt, self._hops,
            "saflager_w3470", 1.050, 1.010, 5.2, 20, 10, {},
            fermentation_temp_target_c=12.5,
        )
        recipe_storage.lagre_oppskrift(recipe_a)

        # Recipe B -- speiler en oppskrift lagret FØR dette feltet
        # fantes -- ikke bare None, feltet MANGLER helt.
        recipe_b = bygg_recipe_object(
            "GTM Recipe B eldre", 20.0, 0.75, self._malt, self._hops,
            "saflager_w3470", 1.050, 1.010, 5.2, 20, 10, {},
        )
        del recipe_b["fermentation_temp_target_c"]
        recipe_storage.lagre_oppskrift(recipe_b)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _at(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")
        return at

    def test_a_gammel_oppskrift_uten_felt_apner_tomt(self):
        at = self._at()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe B eldre").run()
        self.assertFalse(at.exception)
        self.assertIsNone(at.session_state["gjaering_temp_maal_c"])
        self.assertIsNone(at.number_input(key="gjaering_temp_maal_c").value)

    def test_b_sette_lagre_gjenaapne_bevarer_eksakt_verdi_og_lar_andre_felt_uendret(self):
        at = self._at()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe B eldre").run()
        process_profil_ved_lasting = at.session_state["aktiv_prosessprofil"]

        at.number_input(key="gjaering_temp_maal_c").set_value(19.5).run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 19.5)

        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"Lagring feilet: {at.exception}")

        lagret = self._recipe_storage.hent_alle_oppskrifter()["GTM Recipe B eldre"]
        self.assertEqual(lagret["fermentation_temp_target_c"], 19.5)
        # (g) -- ingredienser/prosessprofil upåvirket av det nye feltet.
        self.assertEqual(lagret["malts"], self._malt)
        self.assertEqual(lagret["hops"], self._hops)
        self.assertEqual(lagret["yeast"], "saflager_w3470")
        self.assertEqual(lagret["process_profile"], process_profil_ved_lasting)

        # ── Helt frisk AppTest-sesjon -- som å åpne appen på nytt ──────
        at2 = AppTest.from_file(_APP_PY)
        at2.run()
        at2.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe B eldre").run()
        self.assertFalse(at2.exception, f"Gjenåpning feilet: {at2.exception}")
        self.assertEqual(at2.session_state["gjaering_temp_maal_c"], 19.5)
        self.assertEqual(at2.number_input(key="gjaering_temp_maal_c").value, 19.5)
        self.assertEqual(at2.session_state["valgt_malt"], self._malt)
        self.assertEqual(at2.session_state["valgt_humle"], self._hops)

    def test_c_bytte_fra_oppskrift_med_til_uten_felt_rydder_til_none(self):
        at = self._at()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe A").run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 12.5)

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe B eldre").run()
        self.assertFalse(at.exception)
        self.assertIsNone(at.session_state["gjaering_temp_maal_c"])
        self.assertIsNone(at.number_input(key="gjaering_temp_maal_c").value)

    def test_d_lastet_oppskrift_deretter_blankvalg_rydder_til_none(self):
        at = self._at()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe A").run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 12.5)

        at.sidebar.selectbox(key="sidebar_recipe_selector").select(_BLANKVALG).run()
        self.assertFalse(at.exception)
        self.assertIsNone(at.session_state["gjaering_temp_maal_c"])
        self.assertIsNone(at.number_input(key="gjaering_temp_maal_c").value)

    def test_e_arkiver_suksess_rydder_til_none_via_pending_for_widget(self):
        at = self._at()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe A").run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 12.5)

        at.button(key="slett_gjeldende_btn").click().run()
        self.assertFalse(at.exception)
        at.button(key="slett_bekreft_btn").click().run()
        self.assertFalse(at.exception, f"Arkivering feilet: {at.exception}")

        self.assertIsNone(at.session_state["gjaering_temp_maal_c"])
        self.assertIsNone(at.number_input(key="gjaering_temp_maal_c").value)

    def test_f_importert_kbhrecipe_nullstiller_til_none(self):
        at = self._at()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("GTM Recipe A").run()
        self.assertEqual(at.session_state["gjaering_temp_maal_c"], 12.5)

        uploader = at.sidebar.file_uploader[0]
        uploader.upload("gtm_import.kbhrecipe", _kbhrecipe_tekst().encode("utf-8"), "application/octet-stream")
        at.run()
        self.assertFalse(at.exception, f"Opplasting feilet: {at.exception}")

        analyser = [b for b in at.sidebar.button if b.key == "kbhrecipe_analyser_btn"][0]
        analyser.click().run()
        self.assertFalse(at.exception, f"Analyse feilet: {at.exception}")

        bekreft = [b for b in at.sidebar.button if b.key == "kbhrecipe_bekreft_btn"][0]
        bekreft.click().run()
        self.assertFalse(at.exception, f"Import feilet: {at.exception}")

        self.assertIsNone(at.session_state["gjaering_temp_maal_c"])
        self.assertIsNone(at.number_input(key="gjaering_temp_maal_c").value)


if __name__ == "__main__":
    unittest.main()
