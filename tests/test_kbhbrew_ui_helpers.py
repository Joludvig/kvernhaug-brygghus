"""
PRI 3B2 (issue #29) -- rene, raske enhetstester for
modules/kbhbrew_ui.py (ingen Streamlit-scriptkjøring; se
tests/test_kbhbrew_create_panel_apptest.py /
tests/test_kbhbrew_import_export_apptest.py for selve UI-flyten).

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_ui_helpers -b
"""
import unittest

from modules.kbhbrew_ui import (
    bygg_brew_eksport_filnavn,
    bygg_brew_eksport_label,
    bygg_predicted_fra_ctx,
    manglende_ingrediens_ider,
    sorter_brews_for_eksport,
)


def _ctx(**overrides):
    ctx = {
        "og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 22, "ebc": 8,
        "style_analysis": {
            "stil": "Tysk Pilsner",
            "stil_liste": [
                {"stil": "Tysk Pilsner", "score": 91},
                {"stil": "Tsjekkisk Pilsner", "score": 40},
            ],
            "bu_gu": 0.62,
        },
        "recipe": {"flavor_profile": {"Bitterhet": 4, "Brød": 3}},
    }
    ctx.update(overrides)
    return ctx


class TestByggPredictedFraCtx(unittest.TestCase):
    def test_1_henter_kjente_tallfelt_og_style_score_fra_ctx(self):
        predicted = bygg_predicted_fra_ctx(_ctx())
        self.assertEqual(predicted["og"], 1.050)
        self.assertEqual(predicted["fg"], 1.012)
        self.assertEqual(predicted["abv"], 5.0)
        self.assertEqual(predicted["ibu"], 22)
        self.assertEqual(predicted["ebc"], 8)
        self.assertAlmostEqual(predicted["buGu"], 0.62)
        self.assertEqual(predicted["flavorProfile"], {"Bitterhet": 4, "Brød": 3})
        self.assertEqual(predicted["style"], {"stil": "Tysk Pilsner", "score": 91})

    def test_2_utelater_style_helt_naar_ingen_dominant_stil(self):
        ctx = _ctx(style_analysis={"stil": None, "stil_liste": [], "bu_gu": 0.5})
        predicted = bygg_predicted_fra_ctx(ctx)
        self.assertNotIn("style", predicted)
        # bu_gu er fortsatt et reelt tall, og skal fortsatt tas med.
        self.assertAlmostEqual(predicted["buGu"], 0.5)

    def test_3_fabrikerer_aldri_manglende_tallfelt(self):
        ctx = _ctx(abv=None, ebc="ukjent")
        predicted = bygg_predicted_fra_ctx(ctx)
        self.assertNotIn("abv", predicted)
        self.assertNotIn("ebc", predicted)
        self.assertEqual(predicted["og"], 1.050)

    def test_4_bool_regnes_aldri_som_et_reelt_tall(self):
        ctx = _ctx(ibu=True)
        predicted = bygg_predicted_fra_ctx(ctx)
        self.assertNotIn("ibu", predicted)

    def test_5_tom_manglende_ctx_gir_tomt_predicted_uten_feil(self):
        self.assertEqual(bygg_predicted_fra_ctx({}), {})
        self.assertEqual(bygg_predicted_fra_ctx(None), {})

    def test_6_tom_flavor_profile_utelates(self):
        ctx = _ctx(recipe={"flavor_profile": {}})
        predicted = bygg_predicted_fra_ctx(ctx)
        self.assertNotIn("flavorProfile", predicted)


class TestEksportLabelOgFilnavn(unittest.TestCase):
    def _brew(self, **overrides):
        brew = {
            "brewId": "brew-aaaa1111-bbbb-2222-cccc-333344445555",
            "createdAt": "2026-08-01T10:00:00+00:00",
            "brewedAt": None,
            "status": "active",
            "snapshot": {"recipe": {"navn": "Kvernhaug IPA"}},
        }
        brew.update(overrides)
        return brew

    def test_1_label_bruker_brewedat_naar_satt_ellers_createdat(self):
        brew = self._brew()
        self.assertEqual(
            bygg_brew_eksport_label(brew, brew["brewId"]),
            f"Kvernhaug IPA — 2026-08-01 — active · {brew['brewId'][-8:]}",
        )
        brew2 = self._brew(brewedAt="2026-08-05T00:00:00+00:00")
        self.assertEqual(
            bygg_brew_eksport_label(brew2, brew2["brewId"]),
            f"Kvernhaug IPA — 2026-08-05 — active · {brew2['brewId'][-8:]}",
        )

    def test_2_label_uten_navn_faller_tilbake_paa_placeholder(self):
        brew = self._brew(snapshot={"recipe": {}})
        self.assertIn("(uten navn)", bygg_brew_eksport_label(brew, brew["brewId"]))

    def test_2b_to_batcher_samme_navn_dato_status_gir_ulik_label(self):
        # Chief review-fiks (PR #30 blocker 1): PRI 3B2 tillater flere
        # reelle batcher fra samme oppskrift samme dag -- etiketten må
        # fortsatt skille dem, selv når navn/dato/status er identiske.
        brew_a = self._brew(brewId="brew-aaaaaaaa-1111", createdAt="2026-08-01T09:00:00+00:00")
        brew_b = self._brew(brewId="brew-bbbbbbbb-2222", createdAt="2026-08-01T15:00:00+00:00")
        label_a = bygg_brew_eksport_label(brew_a, brew_a["brewId"])
        label_b = bygg_brew_eksport_label(brew_b, brew_b["brewId"])
        self.assertNotEqual(label_a, label_b)
        self.assertIn(brew_a["brewId"][-8:], label_a)
        self.assertIn(brew_b["brewId"][-8:], label_b)

    def test_3_filnavn_er_filsystem_trygt_og_inkluderer_kort_id(self):
        brew = self._brew(snapshot={"recipe": {"navn": "Kvernhaug/Spesial Ale"}})
        filnavn = bygg_brew_eksport_filnavn(brew, brew["brewId"])
        self.assertNotIn("/", filnavn)
        self.assertNotIn(" ", filnavn)
        self.assertTrue(filnavn.endswith(".kbhbrew"))
        self.assertIn(brew["brewId"][-8:], filnavn)

    def test_3b_filnavn_saneres_for_windows_ugyldige_tegn(self):
        # Chief review-fiks (PR #30 blocker 2): mer enn bare mellomrom/
        # skråstrek må saneres -- Windows-ugyldige tegn, kontrolltegn,
        # etterslengt punktum/mellomrom.
        brew = self._brew(snapshot={"recipe": {"navn": 'Ale: "Spesial"? <Batch>|1*2\\3..'}})
        filnavn = bygg_brew_eksport_filnavn(brew, brew["brewId"])
        for ugyldig in '\\/:*?"<>|':
            self.assertNotIn(ugyldig, filnavn)
        self.assertFalse(filnavn[:-len(".kbhbrew")].endswith((".", " ")))

    def test_3c_reservert_windows_enhetsnavn_saneres(self):
        brew = self._brew(snapshot={"recipe": {"navn": "CON"}})
        filnavn = bygg_brew_eksport_filnavn(brew, brew["brewId"])
        basenavn = filnavn.split("_")[0]
        self.assertNotEqual(basenavn.upper(), "CON")

    def test_3d_tomt_navn_etter_sanering_faller_tilbake_paa_placeholder(self):
        brew = self._brew(snapshot={"recipe": {"navn": "///???"}})
        filnavn = bygg_brew_eksport_filnavn(brew, brew["brewId"])
        self.assertTrue(filnavn.startswith("brygg_"))

    def test_4_to_batcher_samme_navn_gir_ulikt_filnavn(self):
        brew_a = self._brew(brewId="brew-aaaaaaaa-0000")
        brew_b = self._brew(brewId="brew-bbbbbbbb-1111")
        self.assertNotEqual(
            bygg_brew_eksport_filnavn(brew_a, brew_a["brewId"]),
            bygg_brew_eksport_filnavn(brew_b, brew_b["brewId"]),
        )

    def test_5_sorter_brews_for_eksport_nyeste_forst(self):
        brews = {
            "eldst": self._brew(brewId="eldst", createdAt="2026-01-01T00:00:00+00:00"),
            "nyest": self._brew(brewId="nyest", createdAt="2026-08-01T00:00:00+00:00"),
        }
        valg = sorter_brews_for_eksport(brews)
        self.assertEqual([bid for bid, _ in valg], ["nyest", "eldst"])

    def test_6_tom_brew_dict_gir_tom_liste(self):
        self.assertEqual(sorter_brews_for_eksport({}), [])
        self.assertEqual(sorter_brews_for_eksport(None), [])


class TestManglendeIngrediensIder(unittest.TestCase):
    def _recipe(self, **overrides):
        recipe = {
            "malts": [{"id": "weyermann_pilsner", "mengde": 5.0}],
            "hops": [{"id": "magnum_de", "gram": 20, "tid": 60}],
            "yeast": "safale_us_05",
        }
        recipe.update(overrides)
        return recipe

    _MALT_DB = {"weyermann_pilsner": {}}
    _HUMLE_DB = {"magnum_de": {}}
    _GJAER_DB = {"safale_us_05": {}}

    def test_1_alle_ider_finnes_gir_tom_liste(self):
        self.assertEqual(
            manglende_ingrediens_ider(self._recipe(), self._MALT_DB, self._HUMLE_DB, self._GJAER_DB),
            [],
        )

    def test_2_manglende_malt_id_rapporteres(self):
        manglende = manglende_ingrediens_ider(self._recipe(), {}, self._HUMLE_DB, self._GJAER_DB)
        self.assertIn("weyermann_pilsner", manglende)

    def test_3_manglende_humle_id_rapporteres(self):
        manglende = manglende_ingrediens_ider(self._recipe(), self._MALT_DB, {}, self._GJAER_DB)
        self.assertIn("magnum_de", manglende)

    def test_4_manglende_gjaer_id_rapporteres(self):
        manglende = manglende_ingrediens_ider(self._recipe(), self._MALT_DB, self._HUMLE_DB, {})
        self.assertIn("safale_us_05", manglende)

    def test_5_ingen_gjaer_valgt_gir_ingen_gjaer_feil(self):
        recipe = self._recipe(yeast=None)
        self.assertEqual(
            manglende_ingrediens_ider(recipe, self._MALT_DB, self._HUMLE_DB, {}),
            [],
        )

    def test_6_tom_manglende_recipe_gir_tom_liste_uten_feil(self):
        self.assertEqual(manglende_ingrediens_ider({}, {}, {}, {}), [])
        self.assertEqual(manglende_ingrediens_ider(None, None, None, None), [])


if __name__ == "__main__":
    unittest.main()
