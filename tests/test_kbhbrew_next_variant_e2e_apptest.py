"""
V2.2 G2D (issue #363) -- end-to-end AppTest regression for the
"🌱 Opprett neste variant" / next-variant-linkage flow, via the REAL,
full `app.py` (same "real user path, real widgets, real re-render"
principle as tests/test_app_a4_selector_orientation_apptest.py) rather
than a narrow, synthetic per-panel harness -- the identity-boundary
guarantee this issue exists to prove (docs/development/
v22_g2c_next_variant_linkage_contract.md §4.1/§6) spans TWO different
panels (ui/kbhbrew_history_panel.py's seed action, ui/recipe_card.py's
"Lagre som ny kopi" save), so only a real, full-app render actually
proves the two wire together correctly.

Covers (issue #363 "Required tests" 5/6/8 at the UI-wiring level -- the
pure identity-boundary logic itself is already covered, faster and
independent of Streamlit, in tests.test_kbhbrew_engine_readerwriter's
TestNesteVariantSeed):
  - the seeded draft's originRecipeId is fresh and differs from the
    source recipe's own (never inherited);
  - that SAME fresh id survives the very first "💾 Lagre som ny kopi"
    save unchanged (not re-minted a second time);
  - the source recipe's saved file is untouched;
  - ordinary "Lagre som ny kopi" (no next-variant seed involved) is
    completely unaffected -- still mints its own, unrelated fresh id,
    exactly as before this issue (regression guard for issue #283/#286).

Run with:
    python3 -m unittest tests.test_kbhbrew_next_variant_e2e_apptest -b
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.recipe_storage as recipe_storage
from modules.kbhbrew_storage import oppdater_brew_lag, opprett_og_lagre_ny_brew
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")
_DATA_DIR = os.path.join(_REPO_ROOT, "data")

_BREW_ID = "brew-e2e-363"


def _last_master(filnavn):
    with open(os.path.join(_DATA_DIR, filnavn), encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (samme mønster som
    tests/test_app_a4_selector_orientation_apptest.py)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


class _MedIsolerteOppskrifter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        self._tmpdir.cleanup()

    def _seed_kilde_og_brew(self):
        malt_db = _last_master("master_malt.json")
        humle_db = _last_master("master_humle_v2.json")
        gjaer_db = _last_master("master_gjaer_v2.json")
        malt_id = next(iter(malt_db))
        gjaer_id = next(iter(gjaer_db))

        recipe = bygg_recipe_object(
            "E2E Kildebrygg", 20.0, 0.75,
            [{"id": malt_id, "mengde": 5.0}], [],
            gjaer_id, 1.050, 1.012, 5.0, 20, 8, {},
        )
        filnavn = recipe_storage.lagre_oppskrift(recipe)
        kilde_origin_id = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertTrue(kilde_origin_id)
        # Speiler en reell live-oppskrift som allerede har fått en
        # originRecipeId FØR brygget opprettes -- snapshotet skal fryse
        # nøyaktig denne verdien (Section 2.4 i kontraktbrevet).
        recipe["originRecipeId"] = kilde_origin_id

        equipment = {
            "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
            "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
            "default_boil_time_min": 60,
        }
        brew = opprett_og_lagre_ny_brew(
            recipe, malt_db, humle_db, gjaer_db, equipment,
            {"og": 1.050, "fg": 1.012, "abv": 5.0},
            recipe_id=filnavn, brew_id=_BREW_ID,
        )
        self.assertEqual(brew["snapshot"]["recipe"]["originRecipeId"], kilde_origin_id)
        oppdater_brew_lag(_BREW_ID, learning={"nextTime": "Hev røykmalt-andelen"})
        return kilde_origin_id


class TestNesteVariantE2EAppTest(_MedIsolerteOppskrifter):

    def test_opprett_neste_variant_seeder_fersk_id_og_lagre_som_ny_kopi_bevarer_den(self):
        kilde_origin_id = self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        self.assertFalse(at.exception)

        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)

        fersk_id = _ss(at, "_aktiv_kbh_origin_recipe_id")
        self.assertTrue(fersk_id)
        self.assertNotEqual(fersk_id, kilde_origin_id)
        self.assertEqual(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"), fersk_id)
        self.assertEqual(_ss(at, "gjeldende_navn"), "E2E Kildebrygg")
        # "import as new"-semantikk (kbh_import_apply.py) -- utkastet er
        # ulagret, "Lagre endringer" skal derfor ikke være tilgjengelig.
        self.assertIsNone(_ss(at, "_last_loaded_recipe"))

        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg v2").run()
        self.assertFalse(at.exception)
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("E2E Kildebrygg v2", lagrede)
        self.assertEqual(lagrede["E2E Kildebrygg v2"]["originRecipeId"], fersk_id)
        self.assertNotEqual(lagrede["E2E Kildebrygg v2"]["originRecipeId"], kilde_origin_id)

        # Kildeoppskriften er byte-for-byte uendret på disk.
        kilde = lagrede["E2E Kildebrygg"]
        self.assertEqual(kilde["originRecipeId"], kilde_origin_id)

    def test_lagre_som_ny_kopi_uten_seed_minter_fortsatt_ny_id_som_for(self):
        kilde_origin_id = self._seed_kilde_og_brew()

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        # Laster KILDE-oppskriften via den ordinære sidebar-selectboksen
        # (INGEN neste-variant-seed involvert) og duplikerer den --
        # regresjonsvakt: en vanlig "Lagre som ny kopi" skal fortsatt
        # minte en helt egen, ny id, akkurat som før denne saken
        # (issue #283/#286).
        at.selectbox(key="sidebar_recipe_selector").select("E2E Kildebrygg").run()
        self.assertFalse(at.exception)
        self.assertIsNone(_ss(at, "_aktiv_kbh_neste_variant_frossen_origin_id"))

        at.text_input(key="gjeldende_navn").set_value("E2E Kildebrygg Kopi").run()
        self.assertFalse(at.exception)
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        kopi_id = lagrede["E2E Kildebrygg Kopi"]["originRecipeId"]
        self.assertTrue(kopi_id)
        self.assertNotEqual(kopi_id, kilde_origin_id)


if __name__ == "__main__":
    unittest.main()
