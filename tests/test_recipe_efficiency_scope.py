"""
PRI 2C0 (KBHR-019) -- regresjonstester for at en lagret/importert
oppskrifts `efficiency` er RECIPE-SCOPED når den finnes, i stedet for å
bli stille overskrevet av gjeldende utstyrsprofil ved neste
last/beregn/lagre-runde.

Bakgrunn (bevist FØR denne rettelsen, se PRI 2C0-rapporten):
modules/recipe_context.py::bygg_recipe_context() leste tidligere
UBETINGET last_equipment().get("efficiency") -- en lagret oppskrifts
egen efficiency-verdi ble aldri lest tilbake noe sted, og forsvant
derfor stille (ble erstattet av utstyrsprofilens verdi) ved første
load->rebygg->lagre-runde.

To lag testes:
  1. Den rene, Streamlit-frie policy-funksjonen
     modules.recipe.resolve_recipe_efficiency() -- fullt unit-testbar.
  2. bygg_recipe_context() sin faktiske bruk av
     st.session_state["_aktiv_recipe_efficiency"] (samme
     st.session_state-mønster som tests/test_process_profiles.py sin
     _StreamlitCtxTestCase), pluss en ekte load->save-runde via
     modules.recipe_storage i en isolert mappe (KVERNHAUG_RECIPES_DIR)
     -- speiler EKSAKT den nye linjen i ui/sidebar.py
     (resolve_recipe_efficiency(r_data.get("efficiency"))) uten å bygge
     et fullt AppTest-harness for selve sidebaren (se OPPGAVE F).

Utstyrsprofilens verdi er alltid mocket eksplisitt (aldri antatt lik
den ekte data/equipment.json sitt faktiske innhold, og aldri skrevet
til).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import tempfile
import unittest
from unittest import mock

import streamlit as st

logging.getLogger("streamlit").setLevel(logging.ERROR)

from modules.recipe import bygg_recipe_object, resolve_recipe_efficiency
from modules.recipe_context import bygg_recipe_context
from modules.recipe_storage import lagre_oppskrift, hent_alle_oppskrifter
from modules.kbh_contract import recipe_to_kbhrecipe_payload


# ─── 1: resolve_recipe_efficiency() -- ren policy-funksjon ────────────────

class TestResolveRecipeEfficiency(unittest.TestCase):
    def test_gyldig_float_beholdes(self):
        self.assertEqual(resolve_recipe_efficiency(0.68), 0.68)

    def test_gyldig_int_beholdes(self):
        self.assertEqual(resolve_recipe_efficiency(1), 1)

    def test_manglende_felt_gir_none(self):
        self.assertIsNone(resolve_recipe_efficiency(None))

    def test_streng_gir_none(self):
        self.assertIsNone(resolve_recipe_efficiency("0.68"))

    def test_bool_gir_none(self):
        # bool er en int-subklasse i Python -- må avvises eksplisitt,
        # ellers ville True blitt tolket som 1 (100% effektivitet).
        self.assertIsNone(resolve_recipe_efficiency(True))
        self.assertIsNone(resolve_recipe_efficiency(False))

    def test_null_gir_none(self):
        self.assertIsNone(resolve_recipe_efficiency(0.0))

    def test_negativ_gir_none(self):
        self.assertIsNone(resolve_recipe_efficiency(-0.5))

    def test_nan_gir_none(self):
        self.assertIsNone(resolve_recipe_efficiency(float("nan")))

    def test_liste_gir_none(self):
        self.assertIsNone(resolve_recipe_efficiency([0.68]))


# ─── 2: bygg_recipe_context() sin bruk av aktiv override ──────────────────

class _EffScopeTestCase(unittest.TestCase):
    """Samme st.session_state-mønster som tests/test_process_profiles.py
    sin _StreamlitCtxTestCase. Utstyrsprofilen mockes eksplisitt til
    0.75 -- aldri lest fra eller skrevet til den ekte data/equipment.json."""

    def setUp(self):
        st.session_state.clear()
        st.session_state["valgt_malt"] = [{"id": "weyermann_pilsner", "mengde": 4.0}]
        st.session_state["valgt_humle"] = [{"id": "magnum_de", "gram": 20, "tid": 60}]
        st.session_state["batch_volum_input"] = 20.0
        st.session_state["brygger_stil"] = ""
        self._eq_patch = mock.patch(
            "modules.recipe_context.last_equipment",
            return_value={"efficiency": 0.75},
        )
        self._eq_mock = self._eq_patch.start()

    def tearDown(self):
        self._eq_patch.stop()
        st.session_state.clear()

    def _ctx(self):
        return bygg_recipe_context(
            "Test", st.session_state["valgt_malt"], st.session_state["valgt_humle"],
            "safale_us_05", {}, {}, {},
        )


class TestAktivRecipeEfficiencyOverride(_EffScopeTestCase):
    def test_1_recipe_override_vinner_over_equipment(self):
        st.session_state["_aktiv_recipe_efficiency"] = 0.68
        ctx = self._ctx()
        self.assertEqual(ctx["effektivitet"], 0.68)

    def test_4_ingen_override_bruker_equipment_default(self):
        st.session_state["_aktiv_recipe_efficiency"] = None
        ctx = self._ctx()
        self.assertEqual(ctx["effektivitet"], 0.75)

    def test_4b_manglende_nokkel_i_det_hele_tatt_bruker_ogsaa_equipment(self):
        # Simulerer f.eks. en test/kontekst som aldri satte nøkkelen --
        # samme fallback som "ingen override".
        self.assertNotIn("_aktiv_recipe_efficiency", st.session_state)
        ctx = self._ctx()
        self.assertEqual(ctx["effektivitet"], 0.75)

    def test_6_bytte_mellom_to_recipes_bytter_riktig_verdi(self):
        st.session_state["_aktiv_recipe_efficiency"] = 0.68
        eff_a = self._ctx()["effektivitet"]
        st.session_state["_aktiv_recipe_efficiency"] = 0.82
        eff_b = self._ctx()["effektivitet"]
        self.assertEqual(eff_a, 0.68)
        self.assertEqual(eff_b, 0.82)

    def test_5_ny_blank_recipe_etter_override_bruker_equipment_igjen(self):
        st.session_state["_aktiv_recipe_efficiency"] = 0.68
        self.assertEqual(self._ctx()["effektivitet"], 0.68)
        # "Ny blank oppskrift" (app.py sin init-default / recipe_card.py
        # sin arkiver-reset) setter overriden tilbake til None.
        st.session_state["_aktiv_recipe_efficiency"] = None
        self.assertEqual(self._ctx()["effektivitet"], 0.75)

    def test_equipment_endres_aldri_som_sideeffekt(self):
        st.session_state["_aktiv_recipe_efficiency"] = 0.68
        self._ctx()
        # Selve poenget: når en recipe-override finnes, kalles
        # last_equipment() (nødvendigvis read-only, se mocken over) ALDRI
        # i det hele tatt -- verifiser at mocken IKKE ble kalt, i stedet
        # for bare å anta det.
        self._eq_mock.assert_not_called()


# ─── 3: ekte load -> save-runde via recipe_storage (isolert mappe) ────────

class TestEfficiencyLoadSaveRoundtrip(unittest.TestCase):
    """Speiler EKSAKT den nye linjen i ui/sidebar.py
    (`resolve_recipe_efficiency(r_data.get("efficiency"))`), uten å bygge
    et AppTest-harness for hele sidebaren (se OPPGAVE F)."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        st.session_state.clear()
        self._eq_patch = mock.patch(
            "modules.recipe_context.last_equipment",
            return_value={"efficiency": 0.75},
        )
        self._eq_mock = self._eq_patch.start()

    def tearDown(self):
        self._eq_patch.stop()
        st.session_state.clear()
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _last_som_sidebar(self, navn):
        """Speiler nøyaktig hydreringslinjene ui/sidebar.py bruker."""
        r_data = hent_alle_oppskrifter()[navn]
        st.session_state["valgt_malt"] = r_data["malts"]
        st.session_state["valgt_humle"] = r_data["hops"]
        st.session_state["gjeldende_navn"] = r_data["name"]
        st.session_state["batch_volum_input"] = r_data.get("batch_size", 20.0)
        st.session_state["_aktiv_recipe_efficiency"] = resolve_recipe_efficiency(r_data.get("efficiency"))
        return r_data

    def _ctx(self):
        return bygg_recipe_context(
            st.session_state["gjeldende_navn"], st.session_state["valgt_malt"],
            st.session_state["valgt_humle"], "safale_us_05", {}, {}, {},
        )

    def test_1_og_2_load_deretter_save_beholder_068(self):
        original = bygg_recipe_object(
            "Roundtrip 068", 20.0, 0.68,
            [{"id": "weyermann_pilsner", "mengde": 4.0}], [], "safale_us_05",
            1.048, 1.012, 4.7, 25, 8, {},
        )
        lagre_oppskrift(original)

        self._last_som_sidebar("Roundtrip 068")
        ctx = self._ctx()
        self.assertEqual(ctx["effektivitet"], 0.68, "Punkt 1: aktiv effektivitet etter load skal være 0.68")

        lagret_paa_nytt = bygg_recipe_object(
            ctx["name"], st.session_state["batch_volum_input"], ctx["effektivitet"],
            malts=st.session_state["valgt_malt"], hops=st.session_state["valgt_humle"],
            yeast="safale_us_05",
            og=ctx["og"], fg=ctx["fg"], abv=ctx["abv"], ibu=ctx["ibu"], ebc=ctx["ebc"],
            flavor_profile=ctx["recipe"].get("flavor_profile", {}),
        )
        lagre_oppskrift(lagret_paa_nytt, kilde_filnavn="roundtrip_068.json")
        paa_disk = hent_alle_oppskrifter()["Roundtrip 068"]["efficiency"]
        self.assertEqual(paa_disk, 0.68, "Punkt 2: save etter load skal beholde 0.68, ikke bli 0.75")

    def test_3_global_equipment_uendret_av_load(self):
        original = bygg_recipe_object(
            "Roundtrip Eq", 20.0, 0.68,
            [{"id": "weyermann_pilsner", "mengde": 4.0}], [], "safale_us_05",
            1.048, 1.012, 4.7, 25, 8, {},
        )
        lagre_oppskrift(original)
        self._last_som_sidebar("Roundtrip Eq")
        self._ctx()
        # Mock er read-only -- se test_equipment_endres_aldri_som_sideeffekt
        # over for samme resonnement. Her: verifiser i tillegg at ingen
        # kode noensinne importerte/kalte lagre_equipment under load+ctx.
        with mock.patch("modules.equipment.lagre_equipment") as lagre_mock:
            self._last_som_sidebar("Roundtrip Eq")
            self._ctx()
            lagre_mock.assert_not_called()

    def test_4_recipe_uten_efficiency_felt_bruker_equipment_075(self):
        original = bygg_recipe_object(
            "Roundtrip Uten Eff", 20.0, 0.68,
            [], [], "safale_us_05", 1.040, 1.010, 4.0, 20, 8, {},
        )
        del original["efficiency"]  # simulerer en eldre native fil
        lagre_oppskrift(original, kilde_filnavn=None)

        self._last_som_sidebar("Roundtrip Uten Eff")
        ctx = self._ctx()
        self.assertEqual(ctx["effektivitet"], 0.75)

    def test_6_bytte_a_068_til_b_082_via_faktisk_lagrede_filer(self):
        a = bygg_recipe_object("Roundtrip A", 20.0, 0.68, [], [], "safale_us_05",
                                1.040, 1.010, 4.0, 20, 8, {})
        b = bygg_recipe_object("Roundtrip B", 20.0, 0.82, [], [], "safale_us_05",
                                1.060, 1.014, 6.0, 30, 10, {})
        lagre_oppskrift(a)
        lagre_oppskrift(b)

        self._last_som_sidebar("Roundtrip A")
        eff_a = self._ctx()["effektivitet"]
        self._last_som_sidebar("Roundtrip B")
        eff_b = self._ctx()["effektivitet"]
        self.assertEqual(eff_a, 0.68)
        self.assertEqual(eff_b, 0.82)


# ─── 7: .kbhrecipe-writer konverterer fortsatt 0.68 -> 68 uendret ─────────

class TestKbhrecipeEffektivitetKonverteringUendret(unittest.TestCase):
    """PRI 2C0 endrer IKKE modules/kbh_contract.py -- kun HVA som sendes
    inn som `efficiency` (recipe-scoped i stedet for alltid equipment).
    Selve ×100-konverteringen skal derfor være fullstendig uendret."""

    def test_068_konverteres_til_68(self):
        recipe = bygg_recipe_object(
            "X", 20.0, 0.68, [{"id": "weyermann_pilsner", "mengde": 4.0}],
            [], "safale_us_05", 1.048, 1.012, 4.7, 25, 8, {},
        )
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertEqual(payload["effektivitet"], 68)


if __name__ == "__main__":
    unittest.main()
