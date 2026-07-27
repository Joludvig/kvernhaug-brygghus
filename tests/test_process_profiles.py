"""
Regresjonstester for prosessprofiler ("bryggemåte") — modules/process_profiles.py,
modules/brewday_calc.py sin bruk av dem, og lagring/gjenåpning via
modules/recipe.py + modules/recipe_context.py + modules/recipe_storage.py.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import json
import logging
import os
import tempfile
import unittest

import streamlit as st

# st.session_state fungerer fint utenfor en kjørende `streamlit run`-app
# (se testene under), men logger støyende "missing ScriptRunContext"-
# advarsler for hvert kall — demp dem så testutdata forblir lesbar.
logging.getLogger("streamlit").setLevel(logging.ERROR)

from modules.process_profiles import (
    tilgjengelige_profiler, hent_standardprofil, bygg_egendefinert_profil,
    anbefal_prosess, beregn_dekoksjon_uttak, beregn_reiterated_mash,
    sjekk_utstyrsbegrensninger, INFUSJON, MASHOUT, NO_SPARGE, BATCH_SPARGE,
)
from modules.brewday_calc import lag_brewday_plan, beregn_vann
from modules.brewday_template import render_brewday_html
from modules.card_template import render_a4_html
from modules.recipe import bygg_recipe_object
from modules.recipe_context import bygg_recipe_context
from modules.recipe_storage import lagre_oppskrift, hent_alle_oppskrifter
from modules.equipment import last_equipment

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _last_db(navn):
    with open(os.path.join(_REPO_ROOT, "data", navn), encoding="utf-8") as f:
        return json.load(f)


_MALT_DB  = _last_db("master_malt.json")
_HUMLE_DB = _last_db("master_humle_v2.json")
_GJAER_DB = _last_db("master_gjaer_v2.json")

_WIESN_MALT = [
    {"id": "weyermann_munich_1", "mengde": 0.65},
    {"id": "munich_ii",          "mengde": 4.28},
    {"id": "vienna",             "mengde": 1.60},
]  # summerer til 6.53 kg, jf. kontrollscenarioet


def _fake_gjaer_info(gjaertype="Lager", attenuation=0.80, navn="SafLager W-34/70"):
    return {"display_name": navn, "gjaertype": gjaertype, "attenuation": attenuation}


class TestStandardprofiler(unittest.TestCase):
    """Grunnleggende datamodell-sjekker — ikke stilspesifikke."""

    def test_alle_fem_profiltyper_finnes(self):
        ids = {p["process_id"] for p in tilgjengelige_profiler()}
        self.assertEqual(
            ids,
            {"enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash", "egendefinert"},
        )

    def test_hent_standardprofil_returnerer_uavhengig_kopi(self):
        # Muterer én hentet profil — skal ALDRI påvirke en påfølgende henting
        # av samme id (dvs. selve malen i STANDARDPROFILER er urørt).
        a = hent_standardprofil("enkel_infusjon")
        a["mash_steps"][0]["temperatur"] = 999.0
        a["mash_steps"].append({"temperatur": 1, "varighet": 1, "stegtype": INFUSJON, "kommentar": "x"})

        b = hent_standardprofil("enkel_infusjon")
        self.assertEqual(b["mash_steps"][0]["temperatur"], 66.0)
        self.assertEqual(len(b["mash_steps"]), 2)

    def test_hver_standardprofil_har_obligatoriske_felt(self):
        obligatorisk = {
            "process_id", "navn", "beskrivelse", "vanskelighetsgrad", "mash_steps",
            "sparge_method", "boil_minutes", "decoction_steps", "anbefalte_stiler",
            "utstyrsbegrensninger", "forventet_paavirkning",
        }
        for p in tilgjengelige_profiler():
            manglende = obligatorisk - set(p.keys())
            self.assertFalse(manglende, f"{p['process_id']} mangler felt: {manglende}")
            for steg in p["mash_steps"]:
                self.assertEqual(
                    {"temperatur", "varighet", "stegtype", "kommentar"}, set(steg.keys()),
                )


class TestByttMellomProfiler(unittest.TestCase):
    """Krav 1: bytte mellom enkel infusjon og Hochkurz skal gi ulik
    meskeplan og ulik total tidsbruk, uten å røre ingrediensene."""

    def _plan_for(self, process_id):
        profil = hent_standardprofil(process_id)
        plan = lag_brewday_plan(
            _WIESN_MALT, [{"id": "tettnang", "tid": 60, "gram": 30}],
            "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        return plan

    def test_infusjon_og_hochkurz_gir_ulik_maskeplan(self):
        infusjon = self._plan_for("enkel_infusjon")
        hochkurz = self._plan_for("hochkurz")

        self.assertEqual(len(infusjon["maskeplan"]), 2)
        self.assertEqual(len(hochkurz["maskeplan"]), 3)
        self.assertNotEqual(
            [s["temp_c"] for s in infusjon["maskeplan"]],
            [s["temp_c"] for s in hochkurz["maskeplan"]],
        )
        # Total mesketid (sum varighet) skal være lengre for Hochkurz.
        sum_infusjon = sum(s["varighet_min"] for s in infusjon["maskeplan"])
        sum_hochkurz = sum(s["varighet_min"] for s in hochkurz["maskeplan"])
        self.assertGreater(sum_hochkurz, sum_infusjon)

    def test_bytte_profil_endrer_ikke_maltlisten(self):
        infusjon = self._plan_for("enkel_infusjon")
        hochkurz = self._plan_for("hochkurz")
        self.assertEqual(infusjon["malt_liste"], hochkurz["malt_liste"])
        self.assertEqual(infusjon["total_korn_kg"], hochkurz["total_korn_kg"])


class TestEgendefinerteSteg(unittest.TestCase):
    """Krav 2: en helt egendefinert prosess med vilkårlige steg skal flyte
    riktig gjennom til bryggedagsplanens maskeplan."""

    def test_egendefinerte_steg_brukes_uendret(self):
        egne_steg = [
            {"temperatur": 55.0, "varighet": 15, "stegtype": INFUSJON, "kommentar": "Proteinhvile"},
            {"temperatur": 64.0, "varighet": 45, "stegtype": INFUSJON, "kommentar": "Sakkarifisering"},
            {"temperatur": 72.0, "varighet": 15, "stegtype": INFUSJON, "kommentar": "Dekstrinhvile"},
            {"temperatur": 78.0, "varighet": 5,  "stegtype": MASHOUT,  "kommentar": "Mashout"},
        ]
        profil = bygg_egendefinert_profil("Min egen prosess", egne_steg, boil_minutes=75)
        plan = lag_brewday_plan(
            _WIESN_MALT, [], "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        self.assertEqual(len(plan["maskeplan"]), 4)
        self.assertEqual([s["temp_c"] for s in plan["maskeplan"]], [55.0, 64.0, 72.0, 78.0])
        self.assertEqual(plan["maskeplan"][0]["label"], "Proteinhvile")
        self.assertEqual(plan["koketid_min"], 75)


class TestHumletid(unittest.TestCase):
    """Krav 3: korrekt skille mellom total koketid og humlens egen koketid,
    ved både 60 og 90 min total kok."""

    def _humle_tilsatt_etter(self, total_koketid, hop_tid=60):
        profil = hent_standardprofil("enkel_infusjon")
        profil["boil_minutes"] = total_koketid
        plan = lag_brewday_plan(
            _WIESN_MALT, [{"id": "tettnang", "tid": hop_tid, "gram": 30}],
            "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        return plan["humleplan"][0]

    def test_60_min_total_kok_60_min_humle_tilsettes_ved_start(self):
        h = self._humle_tilsatt_etter(60, hop_tid=60)
        self.assertEqual(h["tid"], 60)
        self.assertEqual(h["tilsatt_etter_min"], 0)

    def test_90_min_total_kok_60_min_humle_tilsettes_30_min_etter_start(self):
        h = self._humle_tilsatt_etter(90, hop_tid=60)
        self.assertEqual(h["tid"], 60)
        self.assertEqual(h["tilsatt_etter_min"], 30)

    def test_tilsatt_etter_min_er_aldri_negativ(self):
        # En humle med lengre egen koketid enn total kok er en ugyldig
        # oppskrift, men skal likevel aldri gi et negativt tidspunkt.
        h = self._humle_tilsatt_etter(60, hop_tid=90)
        self.assertGreaterEqual(h["tilsatt_etter_min"], 0)


class TestDekoksjon(unittest.TestCase):
    """Krav 4: dekoksjonsprofil skal aldri gi negative vannvolumer, uansett
    inndata, og brukeren skal kunne overstyre det foreslåtte uttaket."""

    def test_uttak_er_aldri_negativt_for_ulike_temperaturer(self):
        for mesk_l in (0.0, 5.0, 20.0, 40.0):
            for fra, til in ((63, 70), (63, 63), (70, 63), (0, 100), (99, 100)):
                uttak = beregn_dekoksjon_uttak(mesk_l, fra, til)
                self.assertGreaterEqual(uttak, 0.0, f"mesk={mesk_l} fra={fra} til={til}")
                self.assertLessEqual(uttak, mesk_l + 1e-9)

    def test_dekoksjonsplan_i_full_bryggedagsplan_gir_ingen_negative_volumer(self):
        profil = hent_standardprofil("enkel_dekoksjon")
        plan = lag_brewday_plan(
            _WIESN_MALT, [{"id": "tettnang", "tid": 60, "gram": 30}],
            "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        self.assertIsNotNone(plan["dekoksjon"])
        self.assertGreaterEqual(plan["dekoksjon"]["uttak_liter"], 0.0)
        self.assertGreaterEqual(plan["vann"]["mash_vann_l"], 0.0)
        self.assertGreaterEqual(plan["vann"]["sparge_vann_l"], 0.0)
        self.assertGreaterEqual(plan["vann"]["pre_boil_l"], 0.0)

    def test_manuelt_overstyrt_uttak_respekteres(self):
        profil = hent_standardprofil("enkel_dekoksjon")
        profil["decoction_steps"][0]["uttak_liter"] = 7.5  # brukeren har overstyrt
        plan = lag_brewday_plan(
            _WIESN_MALT, [], "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        self.assertEqual(plan["dekoksjon"]["uttak_liter"], 7.5)


class TestReiteratedMash(unittest.TestCase):
    """Krav 5: reiterated mash skal dele maltmengden riktig i to mesker og
    aldri gi negative vann-/vørtvolumer."""

    def test_malt_deles_korrekt_og_summerer_til_total(self):
        eq = last_equipment()
        r = beregn_reiterated_mash(6.53, 0.5, eq)
        self.assertAlmostEqual(r["malt_1_kg"] + r["malt_2_kg"], 6.53, places=2)
        self.assertGreater(r["malt_1_kg"], 0)
        self.assertGreater(r["malt_2_kg"], 0)

    def test_ingen_negative_volumer_over_ulike_andeler(self):
        eq = last_equipment()
        for andel in (0.1, 0.3, 0.5, 0.7, 0.9):
            r = beregn_reiterated_mash(6.53, andel, eq)
            for felt in ("vann_mesk_1_l", "vort_1_l", "vann_mesk_2_l", "vort_2_l", "sluttvolum_l"):
                self.assertGreaterEqual(r[felt], 0.0, f"{felt} negativ ved andel={andel}")

    def test_reiterated_mash_varsler_om_lang_dag_og_effektivitet(self):
        eq = last_equipment()
        r = beregn_reiterated_mash(6.53, 0.5, eq)
        samlet = " ".join(r["varsler"]).lower()
        self.assertIn("lang", samlet)
        self.assertIn("effektiv", samlet)

    def test_full_bryggedagsplan_med_reiterated_mash(self):
        profil = hent_standardprofil("reiterated_mash")
        plan = lag_brewday_plan(
            _WIESN_MALT, [], "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        self.assertIsNotNone(plan["reiterated_mash_flyt"])
        self.assertAlmostEqual(
            plan["reiterated_mash_flyt"]["malt_1_kg"] + plan["reiterated_mash_flyt"]["malt_2_kg"],
            plan["total_korn_kg"], places=1,
        )


class _StreamlitCtxTestCase(unittest.TestCase):
    """Felles oppsett for tester som går via bygg_recipe_context() og derfor
    bruker st.session_state direkte (fungerer utenfor en kjørende Streamlit-
    app, se modules/recipe_context.py — samme mønster som resten av appen)."""

    def setUp(self):
        st.session_state.clear()
        st.session_state["valgt_malt"] = [dict(m) for m in _WIESN_MALT]
        st.session_state["valgt_humle"] = [{"id": "tettnang", "tid": 60, "gram": 30}]
        st.session_state["batch_volum_input"] = 23.0
        st.session_state["brygger_stil"] = "Historisk Wiesn-Märzen"

    def tearDown(self):
        st.session_state.clear()

    def _bygg_ctx(self):
        return bygg_recipe_context(
            "Test Wiesn", st.session_state["valgt_malt"], st.session_state["valgt_humle"],
            "saflager_w3470", _MALT_DB, _HUMLE_DB, _GJAER_DB,
        )


class TestMaalvolumOgIngredienserUendret(_StreamlitCtxTestCase):
    """Krav 6 og 7: målvolum til gjæring og ingredienslisten skal være
    identiske uansett hvilken prosessprofil som er valgt."""

    def test_maalvolum_beholdes_uansett_prosessprofil(self):
        volumer = []
        for pid in ("enkel_infusjon", "hochkurz", "enkel_dekoksjon", "reiterated_mash"):
            st.session_state["aktiv_prosessprofil"] = hent_standardprofil(pid)
            ctx = self._bygg_ctx()
            volumer.append(ctx["volum"])
        self.assertEqual(len(set(volumer)), 1, f"Målvolum varierte mellom profiler: {volumer}")
        self.assertEqual(volumer[0], 23.0)

    def test_ingrediensene_endres_ikke_naar_prosessprofil_byttes(self):
        st.session_state["aktiv_prosessprofil"] = hent_standardprofil("enkel_infusjon")
        ctx_a = self._bygg_ctx()
        malts_a = copy.deepcopy(ctx_a["recipe"]["malts"])
        hops_a  = copy.deepcopy(ctx_a["recipe"]["hops"])
        yeast_a = ctx_a["recipe"]["yeast"]

        st.session_state["aktiv_prosessprofil"] = hent_standardprofil("reiterated_mash")
        ctx_b = self._bygg_ctx()

        self.assertEqual(malts_a, ctx_b["recipe"]["malts"])
        self.assertEqual(hops_a, ctx_b["recipe"]["hops"])
        self.assertEqual(yeast_a, ctx_b["recipe"]["yeast"])
        # OG/FG/ABV/IBU/EBC er også rent ingrediensutledet — uendret av bryggemåte.
        self.assertEqual(ctx_a["og"], ctx_b["og"])
        self.assertEqual(ctx_a["ibu"], ctx_b["ibu"])

    def test_recipe_object_har_uavhengig_process_profile_felt(self):
        st.session_state["aktiv_prosessprofil"] = hent_standardprofil("hochkurz")
        ctx = self._bygg_ctx()
        self.assertEqual(ctx["recipe"]["process_profile"]["process_id"], "hochkurz")
        # Selve nøkkelsettet i recipe-objektet skal ikke ha vokst inn i
        # ingrediensfeltene.
        self.assertIn("process_profile", ctx["recipe"])
        self.assertIn("malts", ctx["recipe"])
        self.assertNotIn("process_profile", ctx["recipe"]["malts"])


class TestLagringOgGjenaapning(_StreamlitCtxTestCase):
    """Krav 8: lagring og gjenåpning av en oppskrift skal beholde valgt
    prosessprofil."""

    def test_lagre_og_les_tilbake_beholder_prosessprofil(self):
        st.session_state["aktiv_prosessprofil"] = hent_standardprofil("hochkurz")
        ctx = self._bygg_ctx()
        recipe_obj = ctx["recipe"]

        opprinnelig_cwd = os.getcwd()
        tmpdir = tempfile.TemporaryDirectory()
        try:
            os.chdir(tmpdir.name)
            lagre_oppskrift(recipe_obj)
            alle = hent_alle_oppskrifter()
            self.assertIn(recipe_obj["name"], alle)
            lest = alle[recipe_obj["name"]]
            self.assertIsNotNone(lest.get("process_profile"))
            self.assertEqual(lest["process_profile"]["process_id"], "hochkurz")
            self.assertEqual(lest["process_profile"]["mash_steps"], hent_standardprofil("hochkurz")["mash_steps"])
            # Ingrediensene skal naturligvis også overleve rundturen uendret.
            self.assertEqual(lest["malts"], recipe_obj["malts"])
        finally:
            os.chdir(opprinnelig_cwd)
            tmpdir.cleanup()

    def test_oppskrift_uten_prosessprofil_lagres_og_leses_greit(self):
        recipe_obj = bygg_recipe_object(
            "Uten prosess", 20.0, 0.75, [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 25, 8, {},
        )
        opprinnelig_cwd = os.getcwd()
        tmpdir = tempfile.TemporaryDirectory()
        try:
            os.chdir(tmpdir.name)
            lagre_oppskrift(recipe_obj)
            lest = hent_alle_oppskrifter()["Uten prosess"]
            self.assertIsNone(lest.get("process_profile"))
        finally:
            os.chdir(opprinnelig_cwd)
            tmpdir.cleanup()


class TestBryggedagsarkViserProfil(unittest.TestCase):
    """Krav 9: bryggedagsarket (og A4-eksporten) skal vise riktig
    prosessprofil når en er valgt."""

    def _ctx_stub(self, process_profile):
        return {
            "name": "Test Wiesn", "volum": 23.0, "brygger_stil": "Historisk Wiesn-Märzen",
            "og": 1.064, "fg": 1.013, "abv": 6.9, "ibu": 22, "ebc": 20, "total_pris": 400,
            "effektivitet": 0.75,
            "summary": "Rik, maltrik smaksprofil.",
            "style_analysis": {"stil": "Historisk Wiesn-Märzen", "stil_liste": []},
            "recipe": bygg_recipe_object(
                "Test Wiesn", 23.0, 0.75, _WIESN_MALT, [{"id": "tettnang", "gram": 30, "tid": 60}],
                "saflager_w3470", 1.064, 1.013, 6.9, 22, 20, {},
                brygger_stil="Historisk Wiesn-Märzen", process_profile=process_profile,
            ),
        }

    def test_bryggedagsark_viser_valgt_profilnavn(self):
        profil = hent_standardprofil("hochkurz")
        ctx = self._ctx_stub(profil)
        plan = lag_brewday_plan(
            _WIESN_MALT, [{"id": "tettnang", "tid": 60, "gram": 30}],
            "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        html = render_brewday_html(ctx, plan, {})
        self.assertIn("Hochkurz", html)
        self.assertIn("63.0°C", html)  # første Hochkurz-steg

    def test_bryggedagsark_uten_profil_krasjer_ikke(self):
        ctx = self._ctx_stub(None)
        plan = lag_brewday_plan(
            _WIESN_MALT, [], "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=None,
        )
        html = render_brewday_html(ctx, plan, {})
        self.assertIn("Test Wiesn", html)

    def test_a4_eksport_viser_valgt_profilnavn(self):
        profil = hent_standardprofil("enkel_dekoksjon")
        ctx = self._ctx_stub(profil)
        html = render_a4_html(ctx, _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Enkel dekoksjon", html)


class TestKontrollscenarioHistoriskWiesnMarzen(unittest.TestCase):
    """
    Kontrollscenario (IKKE hardkodet inn i selve motoren — kun brukt som
    input her, akkurat som en hvilken som helst annen oppskrift ville blitt
    behandlet): Historisk Wiesn-Märzen, 23 L til gjæring, 6.53 kg malt
    (Munich I / Munich II / Vienna), OG 1.064, ABV 6.9 %, IBU 22.

    Appen skal anbefale Hochkurz (63/40, 70/30, 77/10, 60 min kok) — samme
    generelle regel («Märzen/Historisk Wiesn-Märzen -> Hochkurz») som
    gjelder for enhver annen oppskrift av denne stilen.
    """

    def test_anbefaler_hochkurz(self):
        eq = last_equipment()
        stats = {"og": 1.064, "fg": 1.013, "abv": 6.9, "ibu": 22, "ebc": 20}
        pid, begrunnelse = anbefal_prosess("Historisk Wiesn-Märzen", stats, 6.53, eq, historisk_autentisitet=False)
        self.assertEqual(pid, "hochkurz")
        self.assertTrue(begrunnelse)

    def test_hochkurz_standardsteg_matcher_spesifikasjonen(self):
        profil = hent_standardprofil("hochkurz")
        steg = [(s["temperatur"], s["varighet"]) for s in profil["mash_steps"]]
        self.assertEqual(steg, [(63.0, 40), (70.0, 30), (77.0, 10)])
        self.assertEqual(profil["boil_minutes"], 60)

    def test_med_historisk_autentisitet_tilbys_dekoksjon(self):
        eq = last_equipment()
        stats = {"og": 1.064, "fg": 1.013, "abv": 6.9, "ibu": 22, "ebc": 20}
        pid, _ = anbefal_prosess("Historisk Wiesn-Märzen", stats, 6.53, eq, historisk_autentisitet=True)
        self.assertEqual(pid, "enkel_dekoksjon")

    def test_full_bryggedagsplan_for_kontrolloppskriften(self):
        profil = hent_standardprofil("hochkurz")
        plan = lag_brewday_plan(
            _WIESN_MALT, [{"id": "tettnang", "tid": 60, "gram": 22}],
            "saflager_w3470", _fake_gjaer_info(), 1.064, 23.0,
            _HUMLE_DB, malt_database=_MALT_DB, process_profile=profil,
        )
        self.assertAlmostEqual(plan["total_korn_kg"], 6.53, places=2)
        self.assertEqual(plan["koketid_min"], 60)
        self.assertEqual(
            [(s["temp_c"], s["varighet_min"]) for s in plan["maskeplan"]],
            [(63.0, 40), (70.0, 30), (77.0, 10)],
        )


if __name__ == "__main__":
    unittest.main()
