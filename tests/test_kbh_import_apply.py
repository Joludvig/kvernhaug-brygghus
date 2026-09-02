"""
PRI 2C3 -- regresjonstester for modules/kbh_import_apply.py sin
`apply_kbhrecipe_import_to_session_state()`, den ENE, delte
hjelpefunksjonen som hydrerer session_state fra et PRI 2C1-parser-
resultat (modules/kbh_import.py::parse_kbhrecipe_json()) inn i den
aktive App-oppskriften.

Samme st.session_state-mønster som tests/test_kbh_passthrough.py (les
den FØRST hvis noe under er uklart) -- ingen Streamlit-sideharness,
kun `st.session_state` i "bare mode" (samme som resten av denne
kodebasens tester).

To lag testes:
  1. `apply_kbhrecipe_import_to_session_state()` isolert, med
     håndbygde `import_resultat`-dicts som følger EKSAKT den formen
     parse_kbhrecipe_json() faktisk returnerer.
  2. Én full integrasjonstest: en fremmed .kbhrecipe V1-tekst ->
     parse_kbhrecipe_json() -> apply_kbhrecipe_import_to_session_state()
     -- beviser hele kjeden, ikke bare hjelpefunksjonen i isolasjon.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import logging
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)
import streamlit as st

from modules.kbh_import import parse_kbhrecipe_json
from modules.kbh_import_apply import apply_kbhrecipe_import_to_session_state
from modules.process_profiles import hent_standardprofil, bygg_egendefinert_profil


def _native_recipe(**overrides):
    """Et App-native recipe-dict i EKSAKT den formen
    parse_kbhrecipe_json() sitt `["recipe"]`-felt har (se
    modules/kbh_import.py sin egen docstring for feltlisten)."""
    base = {
        "name": "Importert Test-Ale",
        "batch_size": 22.0,
        "efficiency": 0.70,
        "brygger_stil": "Testbryggerens egen stil",
        "malts": [{"id": "weyermann_pilsner", "mengde": 4.5}],
        "hops": [{"id": "east_kent_goldings", "gram": 25.0, "tid": 60}],
        "yeast": "safale_us_05",
        "process_profile": None,
        "water_source_profile": None,
        "water_target_profile": None,
        "water_treatment": None,
        "water_measurements": None,
    }
    base.update(overrides)
    return base


def _import_resultat(passthrough=None, **recipe_overrides):
    return {"recipe": _native_recipe(**recipe_overrides), "passthrough": passthrough or {}}


class TestApplyKbhrecipeImportTilSessionState(unittest.TestCase):
    def setUp(self):
        st.session_state.clear()

    def tearDown(self):
        st.session_state.clear()

    # ─── 1-2: grunnleggende feltmapping ────────────────────────────────

    def test_1_ingrediens_og_grunnfelt_settes_korrekt(self):
        resultat = _import_resultat()
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertEqual(st.session_state["valgt_malt"], [{"id": "weyermann_pilsner", "mengde": 4.5}])
        self.assertEqual(st.session_state["valgt_humle"], [{"id": "east_kent_goldings", "gram": 25.0, "tid": 60}])
        self.assertEqual(st.session_state["valgt_gjaer_id"], "safale_us_05")
        self.assertEqual(st.session_state["gjeldende_navn"], "Importert Test-Ale")
        self.assertEqual(st.session_state["_gjeldende_navn_preserved"], "Importert Test-Ale")
        self.assertEqual(st.session_state["brygger_stil"], "Testbryggerens egen stil")
        self.assertEqual(st.session_state["batch_volum_input"], 22.0)
        self.assertEqual(st.session_state["_original_batch_size"], 22.0)

    def test_2_recipe_scoped_efficiency_settes(self):
        resultat = _import_resultat(efficiency=0.68)
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertEqual(st.session_state["_aktiv_recipe_efficiency"], 0.68)

    # ─── 3-4: passthrough ───────────────────────────────────────────────

    def test_3_passthrough_settes_deep_copiert(self):
        pt = {"brygger": "Ola Nordmann", "notater": "Traff bra"}
        resultat = _import_resultat(passthrough=pt)
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], pt)
        self.assertIsNot(st.session_state["_aktiv_kbh_passthrough"], pt)
        pt["brygger"] = "Endret Etterpå"
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"]["brygger"], "Ola Nordmann")

    def test_3b_tom_passthrough_gir_none(self):
        resultat = _import_resultat(passthrough={})
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertIsNone(st.session_state["_aktiv_kbh_passthrough"])

    def test_4_manglende_passthrough_nokkel_gir_none(self):
        resultat = {"recipe": _native_recipe()}  # ingen "passthrough"-nøkkel i det hele tatt
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertIsNone(st.session_state["_aktiv_kbh_passthrough"])

    # ─── 5-6: prosess ───────────────────────────────────────────────────

    def test_5_kjent_prosess_settes(self):
        kanonisk = hent_standardprofil("hochkurz")
        resultat = _import_resultat(process_profile=kanonisk)
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertEqual(st.session_state["aktiv_prosessprofil"]["process_id"], "hochkurz")
        self.assertEqual(st.session_state["aktiv_prosessprofil"]["mash_steps"], kanonisk["mash_steps"])

    def test_5b_egendefinert_prosess_bevares_uendret(self):
        egen = bygg_egendefinert_profil("Min egen", [
            {"temperatur": 64.0, "varighet": 45, "stegtype": "infusjon", "kommentar": ""},
        ])
        resultat = _import_resultat(process_profile=egen)
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertEqual(st.session_state["aktiv_prosessprofil"]["mash_steps"], egen["mash_steps"])

    def test_6_manglende_prosess_gir_none(self):
        resultat = _import_resultat(process_profile=None)
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertIsNone(st.session_state["aktiv_prosessprofil"])

    # ─── 7: vann ────────────────────────────────────────────────────────

    def test_7_vann_felter_settes(self):
        resultat = _import_resultat(
            water_source_profile={"water_id": "x", "ca": 20.0},
            water_target_profile={"target_id": "y"},
            water_treatment={"salter": [{"id": "gips", "gram": 4.0}]},
            water_measurements={"maalt_mash_ph": 5.3},
        )
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertEqual(st.session_state["_lastet_water_source_profile"], {"water_id": "x", "ca": 20.0})
        self.assertEqual(st.session_state["_lastet_water_target_profile"], {"target_id": "y"})
        self.assertEqual(st.session_state["_lastet_water_treatment"], {"salter": [{"id": "gips", "gram": 4.0}]})
        self.assertEqual(st.session_state["_lastet_water_measurements"], {"maalt_mash_ph": 5.3})

    def test_7b_manglende_vann_gir_alle_none(self):
        resultat = _import_resultat()
        apply_kbhrecipe_import_to_session_state(resultat)
        self.assertIsNone(st.session_state["_lastet_water_source_profile"])
        self.assertIsNone(st.session_state["_lastet_water_target_profile"])
        self.assertIsNone(st.session_state["_lastet_water_treatment"])
        self.assertIsNone(st.session_state["_lastet_water_measurements"])

    # ─── 8-9: panel-/widget-oppfriskingsstate ───────────────────────────

    def test_8_import_versjon_bumpes(self):
        st.session_state["import_versjon"] = 3
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertEqual(st.session_state["import_versjon"], 4)

    def test_8b_import_versjon_mangler_starter_paa_1(self):
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertEqual(st.session_state["import_versjon"], 1)

    def test_9_malt_pct_pending_sync_nullstilles(self):
        st.session_state["_malt_pct_pending_sync"] = True
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertFalse(st.session_state["_malt_pct_pending_sync"])

    def test_9b_skaler_maal_volum_fjernes(self):
        st.session_state["skaler_maal_volum"] = 25.0
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("skaler_maal_volum", st.session_state)

    # ─── 10-12: "import as new" -- identitet TØMMES, aldri arvet ───────

    def test_10_last_loaded_recipe_fjernes(self):
        st.session_state["_last_loaded_recipe"] = "En Annen, Lagret Oppskrift"
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("_last_loaded_recipe", st.session_state)

    def test_11_last_loaded_recipe_file_fjernes(self):
        st.session_state["_last_loaded_recipe_file"] = "en_annen_lagret_oppskrift.json"
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("_last_loaded_recipe_file", st.session_state)

    def test_12_ingen_identitet_i_det_hele_tatt_krasjer_ikke(self):
        # Helt fersk økt -- nøklene finnes ikke fra før i det hele tatt.
        self.assertNotIn("_last_loaded_recipe", st.session_state)
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("_last_loaded_recipe", st.session_state)
        self.assertNotIn("_last_loaded_recipe_file", st.session_state)

    # ─── 12b-12d: Chief review-fiks (PR #5) -- prosess-/vann-panelenes
    # egne "synced_for"-markører må fjernes, ikke bare stå igjen som None,
    # slik at ui/process_panel.py/ui/water_panel.py tvinges til å resynke
    # fra den importerte prosessen/vannet selv når forrige aktive
    # oppskrift OGSÅ allerede var ny/ulagret (_last_loaded_recipe var
    # None BÅDE før og etter -- se
    # tests/test_kbh_import_process_water_resync_apptest.py for det fulle,
    # ekte UI-nivå-beviset via AppTest; dette er kun den raske,
    # isolerte bekreftelsen på selve markør-fjerningen).

    def test_12b_prosess_synced_for_fjernes(self):
        st.session_state["_prosess_synced_for"] = None  # simulerer "allerede synket mot en ulagret oppskrift"
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("_prosess_synced_for", st.session_state)

    def test_12c_vann_synced_for_fjernes(self):
        st.session_state["_vann_synced_for"] = None
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("_vann_synced_for", st.session_state)

    def test_12d_markorer_fjernes_ogsaa_naar_de_pekte_paa_en_navngitt_lagret_oppskrift(self):
        # Samme fjerning uansett hvilken verdi markørene hadde FØR importen
        # -- ikke bare relevant for None -> None-tilfellet.
        st.session_state["_prosess_synced_for"] = "En Tidligere Lagret Oppskrift"
        st.session_state["_vann_synced_for"] = "En Tidligere Lagret Oppskrift"
        apply_kbhrecipe_import_to_session_state(_import_resultat())
        self.assertNotIn("_prosess_synced_for", st.session_state)
        self.assertNotIn("_vann_synced_for", st.session_state)

    # ─── 13: gammel state kan ikke lekke inn i den importerte oppskriften ─

    def test_13_stale_state_fra_forrige_aktiv_oppskrift_lekker_ikke(self):
        # Simuler en FULLT etablert, aktiv økt (en tidligere lastet
        # LAGRET oppskrift, med sin egen identitet, prosess, vann,
        # passthrough, efficiency osv.) FØR importen skjer.
        st.session_state["valgt_malt"] = [{"id": "vienna", "mengde": 9.9}]
        st.session_state["valgt_humle"] = [{"id": "amarillo", "gram": 99, "tid": 5}]
        st.session_state["valgt_gjaer_id"] = "lalbrew_diamond_lager"
        st.session_state["gjeldende_navn"] = "Gammel Aktiv Oppskrift"
        st.session_state["brygger_stil"] = "Gammel Stil"
        st.session_state["batch_volum_input"] = 99.0
        st.session_state["_aktiv_recipe_efficiency"] = 0.99
        st.session_state["_aktiv_kbh_passthrough"] = {"notater": "Gammel notat"}
        st.session_state["aktiv_prosessprofil"] = hent_standardprofil("hochkurz")
        st.session_state["_lastet_water_source_profile"] = {"water_id": "gammel"}
        st.session_state["_last_loaded_recipe"] = "Gammel Aktiv Oppskrift"
        st.session_state["_last_loaded_recipe_file"] = "gammel_aktiv_oppskrift.json"

        # Den importerte filen har BEVISST ANNERLEDES/manglende verdier
        # for alle disse feltene.
        resultat = _import_resultat(
            passthrough={},  # ingen passthrough i det hele tatt denne gangen
            process_profile=None,
            water_source_profile=None,
        )
        apply_kbhrecipe_import_to_session_state(resultat)

        self.assertEqual(st.session_state["valgt_malt"], [{"id": "weyermann_pilsner", "mengde": 4.5}])
        self.assertEqual(st.session_state["valgt_humle"], [{"id": "east_kent_goldings", "gram": 25.0, "tid": 60}])
        self.assertEqual(st.session_state["valgt_gjaer_id"], "safale_us_05")
        self.assertEqual(st.session_state["gjeldende_navn"], "Importert Test-Ale")
        self.assertEqual(st.session_state["brygger_stil"], "Testbryggerens egen stil")
        self.assertEqual(st.session_state["batch_volum_input"], 22.0)
        self.assertEqual(st.session_state["_aktiv_recipe_efficiency"], 0.70)
        self.assertIsNone(st.session_state["_aktiv_kbh_passthrough"])
        self.assertIsNone(st.session_state["aktiv_prosessprofil"])
        self.assertIsNone(st.session_state["_lastet_water_source_profile"])
        self.assertNotIn("_last_loaded_recipe", st.session_state)
        self.assertNotIn("_last_loaded_recipe_file", st.session_state)

    # ─── 14: full integrasjon -- parser -> apply ───────────────────────

    def test_14_full_integrasjon_parser_til_session_state(self):
        fremmed_tekst = json.dumps({
            "format": "kbhrecipe",
            "version": 1,
            "exportedAt": "2026-09-02T00:00:00Z",
            "generator": "Kvernhaug Brygghus Web",
            "recipe": {
                "recipeSchemaVersion": 1,
                "navn": "Ekte Import Fra Fil",
                "volum": 25.0,
                "effektivitet": 72,
                "malt": [{"id": "weyermann_pilsner", "mengde": 5.0}],
                "humle": [{"id": "east_kent_goldings", "gram": 30, "tid": 60}],
                "gjaerId": "safale_us_05",
                "bryggerStil": "Ekte Test-stil",
                "brygger": "Ola Nordmann",
                "notater": "Fra en ekte .kbhrecipe-fil",
            },
        })
        malt_db = {"weyermann_pilsner": {}}
        humle_db = {"east_kent_goldings": {}}
        gjaer_db = {"safale_us_05": {}}

        # Simuler at BRUKEREN nettopp hadde en ANNEN, lagret oppskrift
        # aktiv (samme "stale state kan ikke lekke"-poeng som over, men
        # nå via den EKTE parseren).
        st.session_state["_last_loaded_recipe"] = "En Annen Oppskrift"
        st.session_state["_last_loaded_recipe_file"] = "en_annen_oppskrift.json"

        resultat = parse_kbhrecipe_json(fremmed_tekst, malt_db, humle_db, gjaer_db)
        apply_kbhrecipe_import_to_session_state(resultat)

        self.assertEqual(st.session_state["gjeldende_navn"], "Ekte Import Fra Fil")
        self.assertEqual(st.session_state["batch_volum_input"], 25.0)
        self.assertAlmostEqual(st.session_state["_aktiv_recipe_efficiency"], 0.72)
        self.assertEqual(st.session_state["brygger_stil"], "Ekte Test-stil")
        self.assertEqual(st.session_state["valgt_gjaer_id"], "safale_us_05")
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], {
            "brygger": "Ola Nordmann", "notater": "Fra en ekte .kbhrecipe-fil",
        })
        self.assertNotIn("_last_loaded_recipe", st.session_state)
        self.assertNotIn("_last_loaded_recipe_file", st.session_state)


if __name__ == "__main__":
    unittest.main()
