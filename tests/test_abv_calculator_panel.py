"""
Tester for den frittstående ABV-kalkulatoren (issue #77 -- TOOLS,
Verktøy-fanen): Core-kontrakten i modules/calculations.py (validering +
begge estimater) og selve UI-panelet (ui/abv_calculator_panel.py) via
AppTest, akkurat samme mønster som tests/test_equipment_panel_terminology.py
bruker for ui/equipment_panel.py.

Kjøres med:
    py -3 -m unittest discover -s tests
    py -3 -m unittest tests.test_abv_calculator_panel
"""
import logging
import os
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from modules.calculations import (
    beregn_abv_standard,
    beregn_abv_high_gravity,
    beregn_abv_fra_og_fg,
)

_APP_PY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_abv_calculator_panel_app.py")


class TestBeregnAbvFraOgFgCoreKontrakt(unittest.TestCase):
    """Ren Core-logikk, ingen Streamlit-kontekst nødvendig."""

    def test_standard_formel_normal_ol(self):
        self.assertAlmostEqual(beregn_abv_standard(1.045, 1.010), 4.593749999999989, delta=1e-9)

    def test_high_gravity_formel_vardeldr_lignende(self):
        self.assertAlmostEqual(beregn_abv_high_gravity(1.100, 1.022), 11.31596842989086, delta=1e-9)

    def test_fra_og_fg_returnerer_begge_estimater_eksplisitt_navngitt(self):
        resultat = beregn_abv_fra_og_fg(1.100, 1.022)
        self.assertEqual(set(resultat.keys()), {"standard", "high_gravity"})
        self.assertAlmostEqual(resultat["standard"], 10.23750000000001, delta=1e-9)
        self.assertAlmostEqual(resultat["high_gravity"], 11.31596842989086, delta=1e-9)

    def test_normal_og_high_gravity_estimat_er_naer_hverandre_for_normal_ol(self):
        # Ved normalstyrke-øl skal de to formlene IKKE avvike mye -- selve
        # poenget med high-gravity-formelen er å korrigere for sterke øl.
        resultat = beregn_abv_fra_og_fg(1.045, 1.010)
        self.assertAlmostEqual(resultat["standard"], resultat["high_gravity"], delta=0.1)

    def test_og_under_eller_lik_1000_reiser_valueerror(self):
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(1.000, 0.998)
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(0.995, 0.990)

    def test_fg_under_eller_lik_null_reiser_valueerror(self):
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(1.050, 0.0)
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(1.050, -0.5)

    def test_fg_hoyere_enn_og_reiser_valueerror(self):
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(1.010, 1.045)

    def test_urealistisk_hoy_og_reiser_valueerror(self):
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(1.775, 1.020)
        with self.assertRaises(ValueError):
            beregn_abv_fra_og_fg(1.900, 1.020)

    def test_standard_og_high_gravity_reiser_samme_validering(self):
        for fn in (beregn_abv_standard, beregn_abv_high_gravity):
            with self.assertRaises(ValueError):
                fn(1.000, 0.998)


class TestAbvKalkulatorPanel(unittest.TestCase):
    """AppTest av den ekte ui/abv_calculator_panel.py, via et minimalt
    vertskap (_abv_calculator_panel_app.py) -- samme mønster som
    _equipment_panel_app.py."""

    def _kjor(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"_abv_calculator_panel_app.py kastet exception: {at.exception}")
        return at

    def test_og_og_fg_inputfelt_finnes_med_fornuftige_default(self):
        at = self._kjor()
        og_widget = at.number_input(key="abv_calc_og")
        fg_widget = at.number_input(key="abv_calc_fg")
        self.assertEqual(og_widget.value, 1.050)
        self.assertEqual(fg_widget.value, 1.010)

    def test_default_verdier_viser_standard_abv_resultat(self):
        at = self._kjor()
        metrikker = {m.label: m.value for m in at.metric}
        self.assertIn("ABV", metrikker)
        # (1.050 - 1.010) * 131.25 = 5.250000000000005 -> "5.3%" ved 1 desimal
        self.assertEqual(metrikker["ABV"], "5.3%")

    def test_ingen_oppskrift_eller_brygg_opprettes_eller_endres(self):
        # Panelet skal aldri røre valgt_malt/valgt_humle/gjeldende_navn e.l.
        # -- disse session_state-nøklene eksisterer ikke engang i dette
        # minimale vertskapet, som beviser panelet ikke initialiserer dem.
        at = self._kjor()
        for nokkel in ("valgt_malt", "valgt_humle", "gjeldende_navn", "_aktiv_recipe_efficiency"):
            self.assertNotIn(nokkel, at.session_state)

    def test_ugyldig_input_viser_feilmelding_ikke_krasj(self):
        at = self._kjor()
        # FG > OG -- ikke meningsfullt støttet.
        at.number_input(key="abv_calc_fg").set_value(1.090).run()
        self.assertFalse(at.exception, f"Kastet exception på ugyldig input: {at.exception}")
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(feilmeldinger, "Forventet en synlig feilmelding for FG > OG")

    def test_hoy_gravitet_viser_begge_estimater_pluss_forklaring(self):
        at = self._kjor()
        at.number_input(key="abv_calc_og").set_value(1.100).run()
        at.number_input(key="abv_calc_fg").set_value(1.022).run()
        self.assertFalse(at.exception, f"Kastet exception ved high-gravity input: {at.exception}")
        metrikker = {m.label: m.value for m in at.metric}
        self.assertIn("Standardestimat", metrikker)
        self.assertIn("High-gravity-estimat", metrikker)
        # (1.100 - 1.022) * 131.25 = 10.2375 -> "10.2%"
        self.assertEqual(metrikker["Standardestimat"], "10.2%")
        self.assertTrue(len(at.caption) > 0)

    def test_normalstyrke_viser_ikke_high_gravity_estimat(self):
        at = self._kjor()
        metrikker = {m.label: m.value for m in at.metric}
        self.assertNotIn("Standardestimat", metrikker)
        self.assertNotIn("High-gravity-estimat", metrikker)


if __name__ == "__main__":
    unittest.main()
