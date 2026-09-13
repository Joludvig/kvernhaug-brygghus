"""
App-regresjon (issue #242) -- den bekreftede A3-1-interaksjonsregresjonen
der en vellykket import kan stille reversere seg selv tilbake til den
FORRIGE lagrede oppskriften, rett etter importens egen rerun.

Root cause (se docs/development/app_a4_workflow_polish_preflight.md
Section 5, korrigert): FØR PR #238/A3-1 ryddet IKKE
apply_import_to_session_state() _last_loaded_recipe/_last_loaded_recipe_file.
A3-1 la til denne ryddingen (speilet fra modules/kbh_import_apply.py),
men rørte ALDRI selve `sidebar_recipe_selector`-widgetens EGEN, bundne
verdi. Import-handlerens `st.rerun()` fantes fra FØR (harmløs alene).
Etter A3-1: en import rydder identiteten -> reruner -> selectboksen
sin widget-state har FORTSATT den gamle, lagrede oppskriftens navn ->
ui/sidebar.py sin reload-ved-mismatch-sjekk (linje ~68-69) tolker den
gamle widget-verdien som et bevisst nytt valg -> laster den gamle
oppskriften -> det nyimporterte innholdet overskrives stille.

Denne testen kjører den EKTE brukerstien via full `app.py`-AppTest --
IKKE en syntetisk harness som setter `_last_loaded_recipe` direkte
(det ville hoppet forbi akkurat den widget-state-mismatchen denne
regresjonen består av, se test_1 i
tests/test_app_a3_state_orientation_apptest.py sin egen advarsel om
nøyaktig denne fallgruven i preflightens Section 14, punkt 1):

  1. lagre en ekte oppskrift på disk;
  2. velg den via den EKTE `sidebar_recipe_selector`-widgeten;
  3. bekreft at den faktisk ble lastet;
  4. lim inn en ANNEN oppskrift via den ekte tekstimport-UI-en;
  5. bekreft importen (samme knappeklikk som en ekte bruker ville gjort);
  6. la handlerens EGNE st.rerun() kjøre (AppTest følger dette
     automatisk innenfor samme .run()-kall, se eksisterende
     test_1_tekstimport_rydder_gammel_lastet_identitet);
  7. verifiser at det importerte innholdet fortsatt er aktivt -- IKKE
     den gamle, lagrede oppskriften.

Denne testen MÅ feile på uendret master (før #242-fiksen) og bestå
etter fiksen.

Kjøres med:
    py -3 -m unittest tests.test_app_a3_import_revert_regression_apptest -v
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.recipe_storage as recipe_storage
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")

_GYLDIG_EQUIPMENT = {
    "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}

# Ekte, eksisterende kanoniske ID-er (data/master_*.json) -- samme
# disiplin som resten av testsuiten (se f.eks. tests/test_kbh_import_ui_apptest.py).
_GYLDIG_MALT_ID = "bohemian_pilsner_floor"
_GYLDIG_HUMLE_ID = "amarillo"
_GYLDIG_GJAER_ID = "lalbrew_house_ale"


def _kbhrecipe_tekst(**overrides):
    payload = {
        "recipeSchemaVersion": 1,
        "navn": "Ny Importert Kbhrecipe Ale",
        "volum": 22.0,
        "effektivitet": 72,
        "malt": [{"id": _GYLDIG_MALT_ID, "mengde": 4.5}],
        "humle": [{"id": _GYLDIG_HUMLE_ID, "gram": 20, "tid": 60}],
        "gjaerId": _GYLDIG_GJAER_ID,
        "brygger": "Regresjonstester",
        "notater": "Fra #242-regresjonstest",
    }
    payload.update(overrides)
    return json.dumps({
        "format": "kbhrecipe", "version": 1, "exportedAt": "2026-09-13T00:00:00Z",
        "generator": "test", "recipe": payload,
    })


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


class _MedIsolertEquipmentOgRecipes(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        _equip_dir = os.path.join(self._tmpdir.name, "_equip")
        os.makedirs(_equip_dir, exist_ok=True)
        self._equipment_file = os.path.join(_equip_dir, "equipment.json")
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            json.dump(_GYLDIG_EQUIPMENT, f)
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._equipment_file

        recipe = bygg_recipe_object(
            "Gammel Lagret Oppskrift", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        if self._gammel_equipment_file is None:
            os.environ.pop("KVERNHAUG_EQUIPMENT_FILE", None)
        else:
            os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._gammel_equipment_file
        self._tmpdir.cleanup()

    def _ny_apptest_med_lastet_gammel_oppskrift(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("Gammel Lagret Oppskrift").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "Gammel Lagret Oppskrift")
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), "gammel_lagret_oppskrift.json")
        self.assertEqual(_ss(at, "gjeldende_navn"), "Gammel Lagret Oppskrift")
        return at


# ═══════════════════════════════════════════════════════════════════
# Tekstimport-stien -- den BEKREFTEDE F0-regresjonen.
# ═══════════════════════════════════════════════════════════════════

class TestTekstimportOverleverIkkeGammelOppskrift(_MedIsolertEquipmentOgRecipes):
    def test_1_tekstimport_av_ny_oppskrift_overlever_egen_rerun(self):
        at = self._ny_apptest_med_lastet_gammel_oppskrift()

        at.sidebar.text_area(key="import_tekst_input").set_value(
            "Navn: Ny Importert Tekst Ale\n5 kg Bohemian Pilsner Floor"
        ).run()
        self.assertFalse(at.exception)
        at.sidebar.button(key="import_analyser_btn").click().run()
        self.assertFalse(at.exception)
        at.sidebar.button(key="import_bekreft_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved import-bekreft: {at.exception}")

        # Identiteten SKAL forbli ryddet (A3-1, uendret oppførsel) ...
        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))
        # ... OG det nyimporterte innholdet skal faktisk fortsatt være
        # aktivt -- IKKE stille reversert til "Gammel Lagret Oppskrift"
        # (den bekreftede #242-regresjonen).
        self.assertEqual(_ss(at, "gjeldende_navn"), "Ny Importert Tekst Ale")
        self.assertEqual(_ss(at, "valgt_malt"), [{"id": _GYLDIG_MALT_ID, "mengde": 5.0}])

    def test_2_tekstimport_uten_tidligere_valgt_lagret_oppskrift_fungerer_uendret(self):
        # Regresjonsvakt: uten en forutgående lagret-oppskrift-seleksjon
        # (den vanligste tekstimport-brukssituasjonen) skal importen
        # fortsatt fungere helt uendret -- fiksen skal ALDRI kunne
        # forstyrre denne, langt vanligere stien.
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception)

        at.sidebar.text_area(key="import_tekst_input").set_value(
            "Navn: Ny Importert Tekst Ale\n5 kg Bohemian Pilsner Floor"
        ).run()
        at.sidebar.button(key="import_analyser_btn").click().run()
        at.sidebar.button(key="import_bekreft_btn").click().run()
        self.assertFalse(at.exception)

        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))
        self.assertEqual(_ss(at, "gjeldende_navn"), "Ny Importert Tekst Ale")


# ═══════════════════════════════════════════════════════════════════
# .kbhrecipe-stien -- verifiseres UAVHENGIG, IKKE antatt (#242 Step 3).
# ═══════════════════════════════════════════════════════════════════

class TestKbhrecipeImportOverleverIkkeGammelOppskrift(_MedIsolertEquipmentOgRecipes):
    def test_3_kbhrecipe_import_av_ny_oppskrift_overlever_egen_rerun(self):
        at = self._ny_apptest_med_lastet_gammel_oppskrift()

        uploader = at.sidebar.file_uploader[0]
        uploader.upload("regresjon.kbhrecipe", _kbhrecipe_tekst().encode("utf-8"), "application/octet-stream")
        at.run()
        self.assertFalse(at.exception)
        at.sidebar.button(key="kbhrecipe_analyser_btn").click().run()
        self.assertFalse(at.exception)
        at.sidebar.button(key="kbhrecipe_bekreft_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved kbhrecipe-import-bekreft: {at.exception}")

        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))
        self.assertEqual(_ss(at, "gjeldende_navn"), "Ny Importert Kbhrecipe Ale")
        self.assertEqual(_ss(at, "valgt_malt"), [{"id": _GYLDIG_MALT_ID, "mengde": 4.5}])


# ═══════════════════════════════════════════════════════════════════
# Regresjonsvakter -- eksplisitt lagret-oppskrift-valg og A3-4 må
# fortsatt fungere UENDRET etter #242-fiksen.
# ═══════════════════════════════════════════════════════════════════

class TestEksplisittValgOgLagringUendret(_MedIsolertEquipmentOgRecipes):
    def setUp(self):
        super().setUp()
        recipe2 = bygg_recipe_object(
            "Annen Lagret Oppskrift", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 3.0}], [],
            "safale_us_05", 1.045, 1.010, 4.5, 15, 6, {},
        )
        recipe_storage.lagre_oppskrift(recipe2)

    def test_4_eksplisitt_bytte_til_annen_lagret_oppskrift_fungerer_uendret(self):
        at = self._ny_apptest_med_lastet_gammel_oppskrift()

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("Annen Lagret Oppskrift").run()
        self.assertFalse(at.exception)

        self.assertEqual(_ss(at, "_last_loaded_recipe"), "Annen Lagret Oppskrift")
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), "annen_lagret_oppskrift.json")
        self.assertEqual(_ss(at, "gjeldende_navn"), "Annen Lagret Oppskrift")

    def test_5_velg_ingen_oppskrift_placeholder_rydder_identitet_uendret(self):
        at = self._ny_apptest_med_lastet_gammel_oppskrift()

        at.sidebar.selectbox(key="sidebar_recipe_selector").select_index(0).run()
        self.assertFalse(at.exception)

        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))


if __name__ == "__main__":
    unittest.main()
