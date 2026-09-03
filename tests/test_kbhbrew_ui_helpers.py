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
        self.assertEqual(
            bygg_brew_eksport_label(self._brew()),
            "Kvernhaug IPA — 2026-08-01 — active",
        )
        self.assertEqual(
            bygg_brew_eksport_label(self._brew(brewedAt="2026-08-05T00:00:00+00:00")),
            "Kvernhaug IPA — 2026-08-05 — active",
        )

    def test_2_label_uten_navn_faller_tilbake_paa_placeholder(self):
        brew = self._brew(snapshot={"recipe": {}})
        self.assertIn("(uten navn)", bygg_brew_eksport_label(brew))

    def test_3_filnavn_er_filsystem_trygt_og_inkluderer_kort_id(self):
        brew = self._brew(snapshot={"recipe": {"navn": "Kvernhaug/Spesial Ale"}})
        filnavn = bygg_brew_eksport_filnavn(brew, brew["brewId"])
        self.assertNotIn("/", filnavn)
        self.assertNotIn(" ", filnavn)
        self.assertTrue(filnavn.endswith(".kbhbrew"))
        self.assertIn(brew["brewId"][-8:], filnavn)

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


if __name__ == "__main__":
    unittest.main()
