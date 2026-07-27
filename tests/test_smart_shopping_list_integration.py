"""
Integrasjonstest for Smart Handleliste V1 — kjører den EKTE
ui/smart_shopping_list_panel.py + modules/smart_shopping_list.py +
modules/pantry.py gjennom Streamlit sitt AppTest-rammeverk, via den delte
testverten tests/_pantry_full_flow_app.py (samme vert som
tests/test_pantry_integration.py bruker — oppskriften er seedet fra den
committede Wiesn-Märzen-fixturen, ikke den private recipes/-mappen).

Isolasjon: KVERNHAUG_PANTRY_DIR settes til en tempfile.TemporaryDirectory()
i setUp() og gjenopprettes i tearDown(). Ingen test her leser eller skriver
den ekte data/pantry.json eller data/humle_lager.json.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import os
import tempfile
import unittest

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pantry_full_flow_app.py")


class _SmartShoppingListAppTestCase(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self._AppTest = AppTest
        self._gammel_env = os.environ.get("KVERNHAUG_PANTRY_DIR")
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["KVERNHAUG_PANTRY_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_PANTRY_DIR", None)
        else:
            os.environ["KVERNHAUG_PANTRY_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _kjor(self):
        at = self._AppTest.from_file(_APP)
        at.run()
        self.assertFalse(at.exception, f"_pantry_full_flow_app.py kastet exception: {at.exception}")
        return at

    def _legg_til_vare(self, at, ingredient_type_visning, ingredient_id, mengde, enhet):
        at.selectbox(key="pantry_ny_type").set_value(ingredient_type_visning).run()
        at.selectbox(key="pantry_ny_ingrediens").set_value(ingredient_id).run()
        at.selectbox(key="pantry_ny_enhet").set_value(enhet).run()
        at.number_input(key="pantry_ny_mengde").set_value(mengde).run()
        at.button(key="pantry_legg_til_btn").click().run()
        return at

    @staticmethod
    def _rad(at, ingredient_type, ingredient_id):
        return next(
            r for r in at.session_state["_debug_handleliste"]
            if r["ingredient_type"] == ingredient_type and r["ingredient_id"] == ingredient_id
        )


class TestSmartHandlelisteWiesnFullFlow(_SmartShoppingListAppTestCase):
    """Krav 15: delvis lager -> korrekt handleliste -> skaler batch ->
    mangler/kjøpsforslag oppdateres -> ny sesjon bevarer Pantry ->
    oppskrift/prosess/vannkjemi urørt."""

    def test_full_flow(self):
        at = self._kjor()

        recipe = at.session_state["_debug_ctx_recipe"]
        self.assertEqual({m["id"] for m in recipe["malts"]}, {"weyermann_munich_1", "munich_ii", "vienna"})

        original_recipe = copy.deepcopy(recipe)
        original_prosess = copy.deepcopy(at.session_state["aktiv_prosessprofil"])
        original_vann = copy.deepcopy(at.session_state["aktiv_vannmaal_snapshot"])

        # 1) Delvis lager: nok Munich I og Vienna, IKKE nok Munich II eller
        # Tettnang -- en blandet, realistisk situasjon.
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")   # trenger 0.7 kg -> nok
        self._legg_til_vare(at, "Malt", "munich_ii", 2.0, "kg")            # trenger 4.6 kg -> mangler
        self._legg_til_vare(at, "Malt", "vienna", 5.0, "kg")               # trenger 1.8 kg -> nok
        self._legg_til_vare(at, "Humle", "tettnang", 30.0, "g")            # trenger 88 g -> mangler

        # 2) Korrekt handleliste.
        munich_i = self._rad(at, "malt", "weyermann_munich_1")
        munich_ii = self._rad(at, "malt", "munich_ii")
        vienna = self._rad(at, "malt", "vienna")
        tettnang = self._rad(at, "humle", "tettnang")

        self.assertEqual(munich_i["status"], "nok")
        self.assertEqual(vienna["status"], "nok")

        self.assertEqual(munich_ii["status"], "kjop")
        self.assertEqual(munich_ii["required_base"], 4600.0)
        self.assertEqual(munich_ii["available_base"], 2000.0)
        self.assertEqual(munich_ii["missing_base"], 2600.0)
        self.assertEqual(munich_ii["suggested_purchase_quantity"], 2.6,
                          "Uten registrert malt-pakningsstørrelse skal kjøpsforslaget være eksakt")
        self.assertAlmostEqual(munich_ii["expected_remainder_base"], 0.0, places=2)

        self.assertEqual(tettnang["status"], "kjop")
        self.assertEqual(tettnang["required_base"], 88.0)
        self.assertEqual(tettnang["available_base"], 30.0)
        self.assertEqual(tettnang["missing_base"], 58.0)
        # Tettnang sin pakke_gram i master_humle_v2.json -- kjøpsforslaget
        # skal være rundet OPP til nærmeste hele pakke, ikke lik mangelen.
        self.assertGreaterEqual(tettnang["suggested_purchase_quantity"], tettnang["missing_base"])
        self.assertTrue(tettnang["package_size_known"] or tettnang["suggested_purchase_quantity"] == tettnang["missing_base"])

        # Ingen W-34/70 registrert i Pantry i det hele tatt her -- behovet
        # (3 pakker, samme pitch-rate-formel som bryggedagsarket) er derfor
        # en reell mangel, ikke en "ukjent match".
        gjaer_rad = self._rad(at, "gjaer", "saflager_w3470")
        self.assertEqual(gjaer_rad["required_base"], 3.0)
        self.assertEqual(gjaer_rad["available_base"], 0.0)
        self.assertEqual(gjaer_rad["missing_base"], 3.0)
        self.assertEqual(gjaer_rad["status"], "kjop")
        self.assertEqual(gjaer_rad["suggested_purchase_quantity"], 3.0)
        self.assertEqual(gjaer_rad["purchase_unit"], "pakke")

        sammendrag_forste = [r for r in at.session_state["_debug_handleliste"] if r["status"] == "kjop"]
        self.assertEqual(len(sammendrag_forste), 3, "Munich II, Tettnang og W-34/70 skal være de eneste 'kjop'-radene")

        # 3) Skaler batchen -- mangler og kjøpsforslag skal oppdateres live.
        at.number_input(key="skaler_maal_volum").set_value(40.0).run()
        at.button(key="skaler_btn").click().run()

        skalert_munich_ii = self._rad(at, "malt", "munich_ii")
        skalert_tettnang = self._rad(at, "humle", "tettnang")
        self.assertEqual(skalert_munich_ii["required_base"], 9200.0, "Munich II-behovet skal dobles ved skalering")
        self.assertGreater(skalert_munich_ii["missing_base"], munich_ii["missing_base"])
        self.assertGreater(
            skalert_munich_ii["suggested_purchase_quantity"], munich_ii["suggested_purchase_quantity"],
            "Kjøpsforslaget skal øke etter skalering, ikke stå på det gamle tallet",
        )
        self.assertEqual(skalert_tettnang["required_base"], 176.0)
        self.assertGreater(skalert_tettnang["missing_base"], tettnang["missing_base"])

        # Vienna hadde god margin (5 kg mot 1.8 kg) -- etter dobling
        # trenger den 3.6 kg, fortsatt dekket av 5 kg på lager.
        skalert_vienna = self._rad(at, "malt", "vienna")
        self.assertEqual(skalert_vienna["required_base"], 3600.0)
        self.assertEqual(skalert_vienna["status"], "nok")

        # 4) Oppskrift/prosessprofil/vannkjemi urørt av Pantry- og
        # Smart Handleliste-visningen (selve skaleringen i steg 3 er en
        # bevisst recipe_card-handling, ikke noe Pantry/Handleliste gjorde).
        self.assertEqual(original_recipe["yeast"], at.session_state["_debug_ctx_recipe"]["yeast"])
        self.assertEqual(at.session_state["aktiv_prosessprofil"], original_prosess)
        self.assertEqual(at.session_state["aktiv_vannmaal_snapshot"], original_vann)

        # 5) Ny sesjon: Pantry (4 poster) er bevart, oppskriften i den nye
        # sesjonen er igjen den uendrede fixture-oppskriften.
        at2 = self._kjor()
        self.assertEqual(len(at2.session_state["_debug_pantry"]["items"]), 4)
        self.assertEqual(at2.session_state["_debug_ctx_recipe"], original_recipe)
        munich_ii_ny_sesjon = self._rad(at2, "malt", "munich_ii")
        self.assertEqual(munich_ii_ny_sesjon["status"], "kjop",
                          "Handlelisten i den nye sesjonen skal fortsatt vise Munich II-mangelen (uskalert oppskrift)")


class TestSmartHandlelisteFullLagerGirIngenKjop(_SmartShoppingListAppTestCase):
    def test_full_beholdning_gir_tom_kjopsliste(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 5.0, "kg")
        self._legg_til_vare(at, "Malt", "munich_ii", 10.0, "kg")
        self._legg_til_vare(at, "Malt", "vienna", 5.0, "kg")
        self._legg_til_vare(at, "Humle", "tettnang", 200.0, "g")
        # W-34/70-behovet (3 pakker, se modules/brewday_calc.beregn_pakker)
        # må også dekkes for at "full beholdning" faktisk skal bety at
        # ingenting trengs kjøpt -- rikelig i overkant her.
        self._legg_til_vare(at, "Gjær", "saflager_w3470", 5.0, "pakke")

        antall_kjop = sum(1 for r in at.session_state["_debug_handleliste"] if r["status"] == "kjop")
        self.assertEqual(antall_kjop, 0)


class TestKnappMarginVisesIUI(_SmartShoppingListAppTestCase):
    """Krav 2 (Kvernhaug-oppryddingen 2026-07-27): Pantry sitt "knapp"-signal
    skal vises som «✅ Nok – knapp margin» i UI-et, men KUN når «Vis også
    det jeg har nok av» er aktivert — og skal aldri telle med blant «må
    kjøpes» eller påvirke estimert kostnad."""

    def test_knapp_vises_kun_med_vis_alt_aktivert(self):
        at = self._kjor()
        # Munich I trenger 0.7 kg. 0.71 kg dekker behovet (>0.7) men er
        # under 5%-sikkerhetsmarginen (0.735 kg) -> Pantry-status "knapp".
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 0.71, "kg")

        rad = self._rad(at, "malt", "weyermann_munich_1")
        self.assertEqual(rad["status"], "nok")
        self.assertEqual(rad["pantry_status"], "knapp")

        # Uten "vis alt": raden skal ikke vises i det hele tatt.
        alle_tekster_skjult = " ".join(w.value for w in at.markdown)
        self.assertNotIn("knapp margin", alle_tekster_skjult.lower())

        # Med "vis alt" aktivert: raden vises, MED den mer presise teksten.
        at.checkbox(key="smart_handleliste_vis_alt").set_value(True).run()
        alle_tekster_vist = " ".join(w.value for w in at.markdown)
        self.assertIn("knapp margin", alle_tekster_vist.lower())

    def test_knapp_teller_ikke_som_ma_kjopes_eller_kostnad(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 0.71, "kg")
        at.checkbox(key="smart_handleliste_vis_alt").set_value(True).run()

        handleliste = at.session_state["_debug_handleliste"]
        antall_kjop = sum(1 for r in handleliste if r["status"] == "kjop")
        munich_i = self._rad(at, "malt", "weyermann_munich_1")
        self.assertNotEqual(munich_i["status"], "kjop")
        self.assertEqual(munich_i["estimated_cost"], 0.0)


class TestGammeltHumlelagerPaavirkerIkkeSmartHandleliste(_SmartShoppingListAppTestCase):
    def test_humle_lager_data_endrer_ikke_resultatet(self):
        from unittest.mock import patch
        import tempfile as _tempfile

        # To HELT separate, isolerte Pantry-mapper -- én per scenario --
        # slik at lagerbeholdning fra det ene scenariet ikke ved et uhell
        # legger seg oppå det andre (begge scenariene legger inn samme
        # mengde Tettnang fra bunnen av).
        with _tempfile.TemporaryDirectory() as tmp_uten, _tempfile.TemporaryDirectory() as tmp_med:
            os.environ["KVERNHAUG_PANTRY_DIR"] = tmp_uten
            at = self._kjor()
            self._legg_til_vare(at, "Humle", "tettnang", 30.0, "g")
            uten_patch = list(at.session_state["_debug_handleliste"])

            os.environ["KVERNHAUG_PANTRY_DIR"] = tmp_med
            with patch("modules.humle_lager.les_lager", return_value={"tettnang": 100000.0}):
                at2 = self._kjor()
                self._legg_til_vare(at2, "Humle", "tettnang", 30.0, "g")
                med_patch = at2.session_state["_debug_handleliste"]

        tettnang_uten = next(r for r in uten_patch if r["ingredient_id"] == "tettnang")
        tettnang_med = next(r for r in med_patch if r["ingredient_id"] == "tettnang")
        self.assertEqual(tettnang_uten["status"], tettnang_med["status"])
        self.assertEqual(tettnang_uten["missing_base"], tettnang_med["missing_base"])
        self.assertEqual(tettnang_uten["available_base"], tettnang_med["available_base"])


if __name__ == "__main__":
    unittest.main()
