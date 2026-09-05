"""
V2-1A (issue #83) -- rene, raske enhetstester for
modules/kbhbrew_history_ui.py (ingen Streamlit-scriptkjøring; se
tests/test_kbhbrew_history_panel_apptest.py for selve UI-flyten).

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_history_ui_helpers -b
"""
import unittest

from modules.kbhbrew_history_ui import (
    bygg_planlagt_sammendrag,
    bygg_planlagt_vs_faktisk,
    parse_actual_tallfelt,
)


def _brew(**overrides):
    brew = {
        "brewId": "brew-aaaa1111",
        "originBrewId": "brew-aaaa1111",
        "status": "active",
        "createdAt": "2026-08-01T10:00:00+00:00",
        "brewedAt": None,
        "snapshot": {
            "recipe": {"navn": "Kvernhaug IPA", "volum": 20.0},
            "predicted": {"og": 1.052, "fg": 1.012, "abv": 5.2},
        },
        "actuals": {},
    }
    brew.update(overrides)
    return brew


class TestByggPlanlagtSammendrag(unittest.TestCase):
    def test_1_leser_alle_kjente_felt_fra_snapshot_og_brew(self):
        sammendrag = bygg_planlagt_sammendrag(_brew(brewedAt="2026-08-10T00:00:00+00:00"))
        self.assertEqual(sammendrag["navn"], "Kvernhaug IPA")
        self.assertEqual(sammendrag["planlagt_og"], 1.052)
        self.assertEqual(sammendrag["planlagt_fg"], 1.012)
        self.assertEqual(sammendrag["planlagt_abv"], 5.2)
        self.assertEqual(sammendrag["planlagt_volum"], 20.0)
        self.assertEqual(sammendrag["opprettet_dato"], "2026-08-01T10:00:00+00:00")
        self.assertEqual(sammendrag["brygget_dato"], "2026-08-10T00:00:00+00:00")
        self.assertEqual(sammendrag["status"], "active")

    def test_2_manglende_navn_faller_tilbake_paa_placeholder(self):
        brew = _brew(snapshot={"recipe": {}, "predicted": {}})
        self.assertEqual(bygg_planlagt_sammendrag(brew)["navn"], "(uten navn)")

    def test_3_manglende_predicted_felt_gir_none_aldri_fabrikert_tall(self):
        brew = _brew(snapshot={"recipe": {"navn": "X", "volum": 20.0}, "predicted": {}})
        sammendrag = bygg_planlagt_sammendrag(brew)
        self.assertIsNone(sammendrag["planlagt_og"])
        self.assertIsNone(sammendrag["planlagt_fg"])
        self.assertIsNone(sammendrag["planlagt_abv"])

    def test_4_tom_manglende_brew_gir_ingen_feil(self):
        sammendrag = bygg_planlagt_sammendrag({})
        self.assertEqual(sammendrag["navn"], "(uten navn)")
        self.assertIsNone(sammendrag["planlagt_og"])
        sammendrag_none = bygg_planlagt_sammendrag(None)
        self.assertEqual(sammendrag_none["navn"], "(uten navn)")

    def test_5_bool_regnes_aldri_som_et_reelt_tall(self):
        brew = _brew(snapshot={"recipe": {"navn": "X", "volum": True}, "predicted": {"og": True}})
        sammendrag = bygg_planlagt_sammendrag(brew)
        self.assertIsNone(sammendrag["planlagt_volum"])
        self.assertIsNone(sammendrag["planlagt_og"])


class TestByggPlanlagtVsFaktisk(unittest.TestCase):
    def test_1_ingen_actuals_viser_kun_planlagt_ingen_faktisk(self):
        sammenligning = bygg_planlagt_vs_faktisk(_brew())
        self.assertEqual(sammenligning["og"], {"planlagt": 1.052, "faktisk": None})
        self.assertEqual(sammenligning["fg"], {"planlagt": 1.012, "faktisk": None})
        self.assertEqual(sammenligning["volum"], {"planlagt": 20.0, "faktisk": None})
        self.assertEqual(sammenligning["abv"]["planlagt"], 5.2)
        self.assertIsNone(sammenligning["abv"]["faktisk"])

    def test_2_volum_utelates_helt_naar_ingen_planlagt_volum_finnes(self):
        brew = _brew(snapshot={"recipe": {"navn": "X"}, "predicted": {"og": 1.05, "fg": 1.01, "abv": 5.0}})
        sammenligning = bygg_planlagt_vs_faktisk(brew)
        self.assertNotIn("volum", sammenligning)

    def test_3_faktisk_abv_avledes_kun_naar_baade_og_og_fg_actuals_finnes(self):
        brew = _brew(actuals={"og": 1.055})
        sammenligning = bygg_planlagt_vs_faktisk(brew)
        self.assertIsNone(sammenligning["abv"]["faktisk"])

        brew2 = _brew(actuals={"og": 1.055, "fg": 1.010})
        sammenligning2 = bygg_planlagt_vs_faktisk(brew2)
        faktisk = sammenligning2["abv"]["faktisk"]
        self.assertIsNotNone(faktisk)
        self.assertIn("standard", faktisk)
        self.assertIn("high_gravity", faktisk)
        self.assertAlmostEqual(faktisk["standard"], (1.055 - 1.010) * 131.25)
        self.assertEqual(sammenligning2["abv"]["faktisk_og"], 1.055)

    def test_4_faktisk_abv_aldri_lagret_kun_avledet_for_visning(self):
        # Selve funksjonen skriver ingenting -- ren lesefunksjon. Beviser
        # også at brew-input-dicten aldri muteres av kallet.
        brew = _brew(actuals={"og": 1.055, "fg": 1.010})
        brew_kopi_for = dict(brew)
        bygg_planlagt_vs_faktisk(brew)
        self.assertEqual(brew, brew_kopi_for)

    def test_5_og_og_fg_utelates_helt_naar_verken_planlagt_eller_faktisk_finnes(self):
        brew = _brew(snapshot={"recipe": {"navn": "X", "volum": 20.0}, "predicted": {}}, actuals={})
        sammenligning = bygg_planlagt_vs_faktisk(brew)
        self.assertNotIn("og", sammenligning)
        self.assertNotIn("fg", sammenligning)
        self.assertNotIn("abv", sammenligning)

    def test_6_ugyldig_faktisk_og_fg_kombinasjon_gir_ingen_krasj(self):
        # fg > og er ugyldig for beregn_abv_fra_og_fg() (ValueError) --
        # skal fanges stille og gi faktisk=None, ikke en unntaks-krasj.
        brew = _brew(actuals={"og": 1.010, "fg": 1.055})
        sammenligning = bygg_planlagt_vs_faktisk(brew)
        self.assertIsNone(sammenligning["abv"]["faktisk"])

    def test_7_tom_manglende_brew_gir_tomt_resultat_uten_feil(self):
        self.assertEqual(bygg_planlagt_vs_faktisk({}), {})
        self.assertEqual(bygg_planlagt_vs_faktisk(None), {})


class TestParseActualTallfelt(unittest.TestCase):
    """Chief review-fiks (PR #84 runde 2, issue #83) -- se
    modules/kbhbrew_history_ui.py::parse_actual_tallfelt() sin egen
    docstring for hvorfor denne strenge forhåndsvalideringen finnes."""

    def test_1_blankt_felt_er_gyldig_og_betyr_toem(self):
        self.assertEqual(parse_actual_tallfelt(""), (True, None))
        self.assertEqual(parse_actual_tallfelt("   "), (True, None))
        self.assertEqual(parse_actual_tallfelt(None), (True, None))

    def test_2_eksakt_punktum_desimal_er_gyldig(self):
        self.assertEqual(parse_actual_tallfelt("1.055"), (True, 1.055))
        self.assertEqual(parse_actual_tallfelt(" 1.055 "), (True, 1.055))
        self.assertEqual(parse_actual_tallfelt("-2.5"), (True, -2.5))
        self.assertEqual(parse_actual_tallfelt("20"), (True, 20.0))

    def test_3_norsk_komma_desimal_normaliseres_trygt(self):
        self.assertEqual(parse_actual_tallfelt("1,055"), (True, 1.055))
        self.assertEqual(parse_actual_tallfelt("19,5"), (True, 19.5))

    def test_4_komma_prefiks_ble_tidligere_stille_kuttet_til_1_0_naa_avvist_med_full_verdi(self):
        # Regresjon for selve Chief-blockeren: "1,055" skal aldri bli
        # tolket som det trunkerte tallet "1" -- se test 3 for at det nå
        # normaliseres til den FULLE, korrekte verdien 1.055 i stedet.
        ok, verdi = parse_actual_tallfelt("1,055")
        self.assertTrue(ok)
        self.assertNotEqual(verdi, 1.0)
        self.assertEqual(verdi, 1.055)

    def test_5_etterslep_avvises_helt_ikke_stille_kuttet(self):
        ok, verdi = parse_actual_tallfelt("1.055abc")
        self.assertFalse(ok)
        self.assertIsNone(verdi)

    def test_6_soeppeltekst_avvises_ikke_tolket_som_toem(self):
        ok, verdi = parse_actual_tallfelt("abc")
        self.assertFalse(ok)
        self.assertIsNone(verdi)

    def test_7_flere_komma_eller_komma_og_punktum_avvises(self):
        self.assertEqual(parse_actual_tallfelt("1,05,5")[0], False)
        self.assertEqual(parse_actual_tallfelt("1,055.2")[0], False)

    def test_8_uendelig_og_nan_avvises(self):
        self.assertEqual(parse_actual_tallfelt("Infinity")[0], False)
        self.assertEqual(parse_actual_tallfelt("-Infinity")[0], False)
        self.assertEqual(parse_actual_tallfelt("nan")[0], False)


if __name__ == "__main__":
    unittest.main()
