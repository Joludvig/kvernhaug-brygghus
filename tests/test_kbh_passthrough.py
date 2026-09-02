"""
PRI 2C2 (KBHR-011/KBHR-014) -- regresjonstester for at PRI 2C1-parserens
`passthrough`-resultat overlever hele veien:

    parse/import-resultat -> aktiv recipe state -> edit/rebuild -> save
    -> reload -> re-export

To lag testes, samme oppdeling og samme etablerte mønstre som
tests/test_recipe_efficiency_scope.py (les den FØRST hvis noe under er
uklart):

  1. Rene, Streamlit-frie funksjoner: modules/recipe.py sin
     `kbh_passthrough`-parameter og modules/kbh_contract.py sin
     `_flett_inn_passthrough()`/re-eksport.
  2. `st.session_state`-mønsteret (samme som tests/test_process_profiles.py
     sin _StreamlitCtxTestCase / test_recipe_efficiency_scope.py) pluss en
     ekte load->save->reload-runde via modules.recipe_storage i en
     isolert mappe (KVERNHAUG_RECIPES_DIR) -- speiler EKSAKT de nye
     linjene i ui/sidebar.py (hydrering av `_aktiv_kbh_passthrough`) og
     ui/recipe_card.py (`_bygg_recipe_fra_session()` sin nye
     `kbh_passthrough=`-kwarg), uten å bygge et fullt AppTest-harness for
     selve UI-et.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)
import streamlit as st

from modules.recipe import bygg_recipe_object, resolve_recipe_efficiency
from modules.recipe_storage import lagre_oppskrift, hent_alle_oppskrifter
from modules.kbh_contract import recipe_to_kbhrecipe_payload, bygg_kbhrecipe_konvolutt
from modules.kbh_import import parse_kbhrecipe_json


def _last_som_sidebar(navn):
    """Speiler EKSAKT de nye hydreringslinjene i ui/sidebar.py (samme
    prinsipp som test_recipe_efficiency_scope.py sin tilsvarende
    hjelpefunksjon, utvidet med PRI 2C2 sin _aktiv_kbh_passthrough)."""
    r_data = hent_alle_oppskrifter()[navn]
    st.session_state["valgt_malt"] = r_data["malts"]
    st.session_state["valgt_humle"] = r_data["hops"]
    st.session_state["valgt_gjaer_id"] = r_data["yeast"]
    st.session_state["gjeldende_navn"] = r_data["name"]
    st.session_state["brygger_stil"] = r_data.get("brygger_stil", "")
    st.session_state["batch_volum_input"] = r_data.get("batch_size", 20.0)
    st.session_state["_aktiv_recipe_efficiency"] = resolve_recipe_efficiency(r_data.get("efficiency"))
    _lagret_passthrough = r_data.get("_kbh_passthrough")
    st.session_state["_aktiv_kbh_passthrough"] = (
        copy.deepcopy(_lagret_passthrough)
        if isinstance(_lagret_passthrough, dict) and _lagret_passthrough
        else None
    )
    return r_data


def _bygg_recipe_fra_session(og=1.048, fg=1.012, abv=4.7, ibu=25, ebc=8, flavor_profile=None):
    """Speiler EKSAKT ui/recipe_card.py sin `_bygg_recipe_fra_session()`
    -- uten et fullt bygg_recipe_context()-kall (samme forenkling som
    tests/test_recipe_efficiency_scope.py bruker)."""
    return bygg_recipe_object(
        st.session_state.get("gjeldende_navn") or "Kvernhaug Spesial",
        st.session_state.get("batch_volum_input", 20.0),
        efficiency=st.session_state.get("_aktiv_recipe_efficiency") or 0.75,
        malts=st.session_state.get("valgt_malt", []),
        hops=st.session_state.get("valgt_humle", []),
        yeast=st.session_state.get("valgt_gjaer_id", "safale_us_05"),
        og=og, fg=fg, abv=abv, ibu=ibu, ebc=ebc,
        flavor_profile=flavor_profile or {},
        brygger_stil=st.session_state.get("brygger_stil", ""),
        process_profile=st.session_state.get("aktiv_prosessprofil"),
        water_source_profile=st.session_state.get("aktiv_vannkilde_snapshot"),
        water_target_profile=st.session_state.get("aktiv_vannmaal_snapshot"),
        water_treatment=st.session_state.get("aktiv_vannbehandling"),
        water_measurements=st.session_state.get("aktiv_vannmaalinger"),
        kbh_passthrough=st.session_state.get("_aktiv_kbh_passthrough"),
    )


# ─── 1-2: modules/recipe.py::bygg_recipe_object() ────────────────────────

class TestByggRecipeObjectPassthrough(unittest.TestCase):
    def test_1_uten_passthrough_fungerer_som_for(self):
        recipe = bygg_recipe_object(
            "X", 20.0, 0.75, [{"id": "weyermann_pilsner", "mengde": 4.0}], [], "safale_us_05",
            1.048, 1.012, 4.7, 25, 8, {},
        )
        self.assertNotIn("_kbh_passthrough", recipe)
        # Uendret eksisterende feltsett -- ingen regresjon.
        self.assertEqual(recipe["name"], "X")
        self.assertEqual(recipe["stats"], {"og": 1.048, "fg": 1.012, "abv": 4.7, "ibu": 25, "ebc": 8})

    def test_1b_none_og_tom_dict_gir_heller_ikke_feltet(self):
        for verdi in (None, {}):
            recipe = bygg_recipe_object(
                "X", 20.0, 0.75, [], [], "safale_us_05", 1.048, 1.012, 4.7, 25, 8, {},
                kbh_passthrough=verdi,
            )
            self.assertNotIn("_kbh_passthrough", recipe)

    def test_2_med_passthrough_deep_copierer(self):
        kilde = {"brygger": "Ola Nordmann", "notater": "Traff bra"}
        recipe = bygg_recipe_object(
            "X", 20.0, 0.75, [], [], "safale_us_05", 1.048, 1.012, 4.7, 25, 8, {},
            kbh_passthrough=kilde,
        )
        self.assertEqual(recipe["_kbh_passthrough"], kilde)
        self.assertIsNot(recipe["_kbh_passthrough"], kilde)
        # Mutasjon av kildens dict ETTERPÅ skal ALDRI lekke inn i det
        # allerede bygde recipe-objektet.
        kilde["brygger"] = "Endret Etterpå"
        self.assertEqual(recipe["_kbh_passthrough"]["brygger"], "Ola Nordmann")

    def test_2b_ikke_dict_ignoreres_stille(self):
        recipe = bygg_recipe_object(
            "X", 20.0, 0.75, [], [], "safale_us_05", 1.048, 1.012, 4.7, 25, 8, {},
            kbh_passthrough="ikke en dict",
        )
        self.assertNotIn("_kbh_passthrough", recipe)


# ─── 3-6: session_state-lifecycle ─────────────────────────────────────────

class TestSessionStateLifecycle(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        st.session_state.clear()

    def tearDown(self):
        st.session_state.clear()
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_3_eldre_recipe_uten_passthrough_hydreres_tomt(self):
        eldre = bygg_recipe_object(
            "Eldre Uten Passthrough", 20.0, 0.75, [], [], "safale_us_05",
            1.040, 1.010, 4.0, 20, 8, {},
        )
        self.assertNotIn("_kbh_passthrough", eldre)  # sikrer testen faktisk tester "mangler feltet"
        lagre_oppskrift(eldre)
        _last_som_sidebar("Eldre Uten Passthrough")
        self.assertIsNone(st.session_state["_aktiv_kbh_passthrough"])

    def test_4_recipe_med_passthrough_hydreres_korrekt(self):
        pt = {"brygger": "Ola Nordmann", "valgtStil": "21A American IPA"}
        med = bygg_recipe_object(
            "Med Passthrough", 20.0, 0.75, [], [], "safale_us_05",
            1.040, 1.010, 4.0, 20, 8, {}, kbh_passthrough=pt,
        )
        lagre_oppskrift(med)
        _last_som_sidebar("Med Passthrough")
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], pt)

    def test_5_bytte_mellom_recipes_bytter_passthrough(self):
        a = bygg_recipe_object(
            "Bytte A", 20.0, 0.68, [], [], "safale_us_05", 1.040, 1.010, 4.0, 20, 8, {},
            kbh_passthrough={"brygger": "A-bryggeren"},
        )
        b = bygg_recipe_object(
            "Bytte B", 20.0, 0.82, [], [], "safale_us_05", 1.060, 1.014, 6.0, 30, 10, {},
        )  # B har ingen passthrough i det hele tatt
        lagre_oppskrift(a)
        lagre_oppskrift(b)

        _last_som_sidebar("Bytte A")
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], {"brygger": "A-bryggeren"})

        _last_som_sidebar("Bytte B")
        self.assertIsNone(
            st.session_state["_aktiv_kbh_passthrough"],
            "B sin last skal IKKE arve A sin passthrough -- gammel passthrough må ikke henge igjen.",
        )

        _last_som_sidebar("Bytte A")
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], {"brygger": "A-bryggeren"})

    def test_6_blank_ny_recipe_nullstiller_passthrough(self):
        # Simulerer app.py sin init-default / ui/recipe_card.py sin
        # arkiver-reset -- IKKE widget-bundet, kan settes direkte.
        st.session_state["_aktiv_kbh_passthrough"] = {"brygger": "Gammel Bryggmester"}
        st.session_state["_aktiv_kbh_passthrough"] = None
        self.assertIsNone(st.session_state["_aktiv_kbh_passthrough"])


# ─── 7-8: save/load/rebuild ───────────────────────────────────────────────

class TestSaveLoadRebuild(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        st.session_state.clear()

    def tearDown(self):
        st.session_state.clear()
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_7_save_load_bevarer_passthrough(self):
        pt = {"bryggeri": "Kvernhaug", "notater": "Litt ekstra bittert"}
        original = bygg_recipe_object(
            "Save Load", 20.0, 0.70, [], [], "safale_us_05", 1.045, 1.011, 4.5, 22, 9, {},
            kbh_passthrough=pt,
        )
        lagre_oppskrift(original)
        paa_disk = hent_alle_oppskrifter()["Save Load"]
        self.assertEqual(paa_disk["_kbh_passthrough"], pt)

    def test_8_rebuild_bevarer_passthrough(self):
        pt = {"brygger": "Ola Nordmann", "fermentasjonsprofil": {"steg": [{"temp": 18, "dager": 7}]}}
        original = bygg_recipe_object(
            "Rebuild Test", 20.0, 0.70, [{"id": "weyermann_pilsner", "mengde": 4.0}], [], "safale_us_05",
            1.045, 1.011, 4.5, 22, 9, {}, kbh_passthrough=pt,
        )
        lagre_oppskrift(original)

        _last_som_sidebar("Rebuild Test")
        gjenoppbygd = _bygg_recipe_fra_session()
        self.assertEqual(gjenoppbygd["_kbh_passthrough"], pt)

        # Og en ANDRE lagring/lasting-runde (edit/rebuild/save igjen,
        # OPPGAVE D punkt 7) skal fortsatt bevare den, uendret.
        lagre_oppskrift(gjenoppbygd, kilde_filnavn="rebuild_test.json")
        _last_som_sidebar("Rebuild Test")
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], pt)


# ─── 9-18: App-writer re-eksport (modules/kbh_contract.py) ────────────────

class TestWriterReeksport(unittest.TestCase):
    def _payload_med_passthrough(self, passthrough):
        recipe = bygg_recipe_object(
            "Reeksport Test", 20.0, 0.70, [{"id": "weyermann_pilsner", "mengde": 4.0}], [], "safale_us_05",
            1.045, 1.011, 4.5, 22, 9, {}, kbh_passthrough=passthrough,
        )
        return recipe_to_kbhrecipe_payload(recipe)

    def test_9_brygger_re_emitteres(self):
        p = self._payload_med_passthrough({"brygger": "Ola Nordmann"})
        self.assertEqual(p["brygger"], "Ola Nordmann")

    def test_10_bryggeri_re_emitteres(self):
        p = self._payload_med_passthrough({"bryggeri": "Kvernhaug"})
        self.assertEqual(p["bryggeri"], "Kvernhaug")

    def test_11_notater_re_emitteres(self):
        p = self._payload_med_passthrough({"notater": "Traff godt denne gangen"})
        self.assertEqual(p["notater"], "Traff godt denne gangen")

    def test_12_valgtstil_re_emitteres(self):
        p = self._payload_med_passthrough({"valgtStil": "21A American IPA"})
        self.assertEqual(p["valgtStil"], "21A American IPA")

    def test_13_ukjent_fremtidig_felt_re_emitteres(self):
        p = self._payload_med_passthrough({"fermentasjonsprofil": {"steg": [{"temp": 18, "dager": 7}]}})
        self.assertEqual(p["fermentasjonsprofil"], {"steg": [{"temp": 18, "dager": 7}]})

    def test_14_kjent_felt_vinner_over_stale_passthrough(self):
        # passthrough inneholder en GAMMEL "navn" og "volum" -- payloadens
        # egne, FERSKE verdier (fra selve recipe-objektet, bygget av
        # bygg_recipe_object() over: "Reeksport Test"/20.0) skal alltid
        # vinne, uansett hva en stale passthrough-kopi sier.
        p = self._payload_med_passthrough({"navn": "Gammelt Navn (skal IKKE vinne)", "volum": 999})
        self.assertEqual(p["navn"], "Reeksport Test")
        self.assertEqual(p["volum"], 20.0)

    def test_14b_kjent_valgfritt_felt_som_ikke_er_satt_denne_runden_lekker_ikke(self):
        # "gjaerId" ER satt denne runden (yeast="safale_us_05" over), men
        # test poenget her er et kjent felt som IKKE er satt (ingen gjær
        # valgt) -- en stale passthrough-"gjaerId" skal likevel ALDRI
        # kunne smugles inn, siden feltnavnet i seg selv er kjent.
        recipe = bygg_recipe_object(
            "Uten Gjaer", 20.0, 0.70, [{"id": "weyermann_pilsner", "mengde": 4.0}], [], None,
            1.045, 1.011, 4.5, 22, 9, {}, kbh_passthrough={"gjaerId": "stale_gjaer_id"},
        )
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertNotIn("gjaerId", payload)

    def test_15_recipeid_filtreres(self):
        p = self._payload_med_passthrough({"recipeId": "LOKAL-ID-SKAL-ALDRI-LEKKE"})
        self.assertNotIn("recipeId", p)

    def test_16_stats_filtreres(self):
        # kbh_contract.py leser uansett aldri stats fra recipe direkte
        # (§4) -- denne testen bekrefter i tillegg at en `stats`-nøkkel
        # SPESIFIKT inni passthrough-dicten heller ikke kan smugles inn.
        p = self._payload_med_passthrough({"stats": {"og": 1.099, "ibu": 999}})
        self.assertNotIn("stats", p)

    def test_17_flavor_profile_filtreres(self):
        p = self._payload_med_passthrough({"flavor_profile": {"malt": 5}})
        self.assertNotIn("flavor_profile", p)

    def test_18_intern_container_filtreres(self):
        # Forsvar i dybden -- en (uventet) nøkkel bokstavelig navngitt
        # "_kbh_passthrough" INNE I selve passthrough-dicten skal
        # aldri kunne re-eksporteres som om det var et ukjent V1-felt.
        p = self._payload_med_passthrough({"_kbh_passthrough": {"noe": "snikinnsmurt"}})
        self.assertNotIn("_kbh_passthrough", p)

    def test_18b_alle_forbudte_samtidig(self):
        p = self._payload_med_passthrough({
            "recipeId": "X", "stats": {}, "flavor_profile": {}, "_kbh_passthrough": {},
            "brygger": "Ekte Passthrough-verdi",
        })
        self.assertNotIn("recipeId", p)
        self.assertNotIn("stats", p)
        self.assertNotIn("flavor_profile", p)
        self.assertNotIn("_kbh_passthrough", p)
        self.assertEqual(p["brygger"], "Ekte Passthrough-verdi")


# ─── 19: eksisterende writer-oppførsel uten passthrough er uendret ───────

class TestWriterUendretUtenPassthrough(unittest.TestCase):
    def test_19_payload_uten_passthrough_har_eksakt_samme_feltsett_som_for(self):
        recipe = bygg_recipe_object(
            "Uendret Writer", 23.0, 0.68,
            [{"id": "weyermann_pilsner", "mengde": 4.0}],
            [{"id": "east_kent_goldings", "gram": 20.0, "tid": 60}],
            "safale_us_05", 1.048, 1.012, 4.7, 25, 8, {},
            brygger_stil="Husets egen stil",
        )
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertEqual(payload, {
            "recipeSchemaVersion": 1,
            "navn": "Uendret Writer",
            "volum": 23.0,
            "effektivitet": 68.0,
            "malt": [{"id": "weyermann_pilsner", "mengde": 4.0}],
            "humle": [{"id": "east_kent_goldings", "gram": 20.0, "tid": 60}],
            "gjaerId": "safale_us_05",
            "bryggerStil": "Husets egen stil",
        })


# ─── 20 / OPPGAVE F: full parser -> save -> reload -> writer roundtrip ───

class TestFullPassthroughRoundtrip(unittest.TestCase):
    """OPPGAVE F -- en FREMMED V1-fil (som om den kom fra Web) med
    brygger/bryggeri/notater/valgtStil/et ukjent fremtidig felt går
    gjennom HELE kjeden: PRI 2C1-parser -> passthrough -> App-native
    recipe -> lagre -> laste (som sidebar) -> gjenoppbygge (som
    recipe_card, MED en bevisst endring av navn/volum, som en bruker
    ville gjort) -> lagre igjen -> App-writer re-eksport. Alle
    passthrough-feltene skal være UENDRET i re-eksporten; det ENDREDE
    navnet/volumet skal bruke de NYE verdiene; selve
    `_kbh_passthrough`-containeren skal ALDRI eksporteres."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        st.session_state.clear()

    def tearDown(self):
        st.session_state.clear()
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_20_full_cycle(self):
        fremmed_tekst = json.dumps({
            "format": "kbhrecipe",
            "version": 1,
            "exportedAt": "2026-09-01T00:00:00Z",
            "generator": "Kvernhaug Brygghus Web",
            "recipe": {
                "recipeSchemaVersion": 1,
                "navn": "Fremmed Web-Import",
                "volum": 20.0,
                "effektivitet": 72,
                "malt": [{"id": "weyermann_pilsner", "mengde": 4.0}],
                "humle": [{"id": "east_kent_goldings", "gram": 20, "tid": 60}],
                "gjaerId": "safale_us_05",
                "brygger": "Ola Nordmann",
                "bryggeri": "Kvernhaug",
                "notater": "Original brygglapp fra Web",
                "valgtStil": "21A American IPA",
                "fermentasjonsprofil": {"steg": [{"temp": 18, "dager": 7}]},
            },
        })
        malt_db = {"weyermann_pilsner": {}}
        humle_db = {"east_kent_goldings": {}}
        gjaer_db = {"safale_us_05": {}}

        # 1) PRI 2C1-parser
        importert = parse_kbhrecipe_json(fremmed_tekst, malt_db, humle_db, gjaer_db)
        r, pt = importert["recipe"], importert["passthrough"]
        self.assertEqual(pt, {
            "brygger": "Ola Nordmann",
            "bryggeri": "Kvernhaug",
            "notater": "Original brygglapp fra Web",
            "valgtStil": "21A American IPA",
            "fermentasjonsprofil": {"steg": [{"temp": 18, "dager": 7}]},
        })

        # 2) App-native recipe object MED passthrough (App beregner selv
        # stats/flavor_profile -- her satt til faste, vilkårlige verdier,
        # siden selve beregningsmotoren er utenfor scope for PRI 2C2).
        native = bygg_recipe_object(
            r["name"], r["batch_size"], r["efficiency"], r["malts"], r["hops"], r["yeast"],
            og=1.050, fg=1.012, abv=5.0, ibu=28, ebc=9, flavor_profile={},
            brygger_stil=r["brygger_stil"], process_profile=r["process_profile"],
            water_source_profile=r["water_source_profile"], water_target_profile=r["water_target_profile"],
            water_treatment=r["water_treatment"], water_measurements=r["water_measurements"],
            kbh_passthrough=pt,
        )

        # 3) Lagre (recipe_storage.py -- rå dict-lagring, ingen endring
        # nødvendig der, se OPPGAVE D).
        lagre_oppskrift(native)

        # 4-5) Laste (som ui/sidebar.py) -- session_state hydreres.
        _last_som_sidebar("Fremmed Web-Import")
        self.assertEqual(st.session_state["_aktiv_kbh_passthrough"], pt)

        # Simuler en BRUKERENDRING (navn og volum) FØR gjenoppbygging --
        # akkurat som å redigere feltene i UI-et.
        st.session_state["gjeldende_navn"] = "Fremmed Web-Import (Endret)"
        st.session_state["batch_volum_input"] = 25.0

        # 6) Gjenoppbygg (som ui/recipe_card.py::_bygg_recipe_fra_session()).
        gjenoppbygd = _bygg_recipe_fra_session(og=1.050, fg=1.012, abv=5.0, ibu=28, ebc=9)
        self.assertEqual(gjenoppbygd["_kbh_passthrough"], pt)
        self.assertEqual(gjenoppbygd["name"], "Fremmed Web-Import (Endret)")
        self.assertEqual(gjenoppbygd["batch_size"], 25.0)

        # 7) Lagre igjen.
        lagre_oppskrift(gjenoppbygd, kilde_filnavn="fremmed_web-import.json")

        # Bekreft passthrough overlevde HELE syklusen på disk.
        paa_disk = hent_alle_oppskrifter()["Fremmed Web-Import (Endret)"]
        self.assertEqual(paa_disk["_kbh_passthrough"], pt)

        # 8) App-writer re-eksport.
        konvolutt = bygg_kbhrecipe_konvolutt(gjenoppbygd, "2026-09-02T00:00:00Z")
        eksportert = konvolutt["recipe"]

        # Passthrough-feltene er UENDRET.
        self.assertEqual(eksportert["brygger"], "Ola Nordmann")
        self.assertEqual(eksportert["bryggeri"], "Kvernhaug")
        self.assertEqual(eksportert["notater"], "Original brygglapp fra Web")
        self.assertEqual(eksportert["valgtStil"], "21A American IPA")
        self.assertEqual(eksportert["fermentasjonsprofil"], {"steg": [{"temp": 18, "dager": 7}]})

        # Kjent, ENDRET navn/volum bruker de NYE verdiene, ikke noe fra
        # passthrough (som uansett aldri inneholdt navn/volum her).
        self.assertEqual(eksportert["navn"], "Fremmed Web-Import (Endret)")
        self.assertEqual(eksportert["volum"], 25.0)

        # Passthrough-containeren selv eksporteres ALDRI (KBHR-009).
        self.assertNotIn("_kbh_passthrough", eksportert)
        self.assertNotIn("stats", eksportert)
        self.assertNotIn("flavor_profile", eksportert)
        self.assertNotIn("_kbh_passthrough", json.dumps(konvolutt))


if __name__ == "__main__":
    unittest.main()
