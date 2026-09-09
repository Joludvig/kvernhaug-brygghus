"""
Regresjonstester for A2.1 (issue #160): brew-log `actual_abv`
(ui/recipe_card.py) og live Brewday `Beregnet ABV` (ui/brewday_panel.py)
skal begge delegere til Core sin autoritative
modules/calculations.py::beregn_abv_standard() i stedet for å inline den
samme `(OG - FG) * 131.25`-formelen selv -- og dermed også arve Core sin
validering (særlig: FG > OG skal ALDRI gi en stille lagret/vist negativ
ABV).

Gyldig OG/FG skal fortsatt gi eksakt samme tallverdi som før (formelen
er UENDRET -- kun eierskapet flyttet til Core), så disse testene låser
BÅDE "uendret for gyldig input" og "trygg no-value for FG > OG" i én og
samme runde, med samme AppTest-mønster som
tests/test_brewday_tab_ux_cleanup.py (lagret oppskrift i en tempdir,
lastet via sidebar_recipe_selector).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.calculations import beregn_abv_standard
from modules.recipe import bygg_recipe_object
from modules.recipe_storage import hent_logg

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")

_OPPSKRIFT_NAVN = "A2.1 Målt ABV E2E"


def _finn_number_input(at, label):
    for widget in at.number_input:
        if widget.label == label:
            return widget
    raise AssertionError(f"Fant ikke number_input med label {label!r}")


def _finn_button(at, label):
    for widget in at.button:
        if widget.label == label:
            return widget
    raise AssertionError(f"Fant ikke button med label {label!r}")


class _MedLastetOppskrift(unittest.TestCase):
    """Felles oppsett: en lagret oppskrift, lastet inn i en fullstendig
    app.py-kjøring via AppTest, akkurat som
    tests/test_brewday_tab_ux_cleanup.py sitt etablerte mønster."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        malt = [{"id": "weyermann_pilsner", "mengde": 5.0}]
        hops = [{"id": "magnum_de", "gram": 20, "tid": 60}]
        recipe = bygg_recipe_object(
            _OPPSKRIFT_NAVN, 20.0, 0.75, malt, hops,
            "safale_us_05", 1.050, 1.010, 5.0, 20, 6, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _last_app_med_oppskrift(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")
        at.sidebar.selectbox(key="sidebar_recipe_selector").select(_OPPSKRIFT_NAVN).run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")
        return at


class TestBrewLogActualAbvDelegererTilCore(_MedLastetOppskrift):
    """ui/recipe_card.py sin bryggelogg-skjema-innsending
    ("actual_abv")."""

    def test_gyldig_og_fg_gir_uendret_standard_abv(self):
        at = self._last_app_med_oppskrift()
        _finn_number_input(at, "Faktisk OG").set_value(1.055).run()
        _finn_number_input(at, "Faktisk FG (valgfritt)").set_value(1.012).run()
        _finn_button(at, "Legg til loggoppføring").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved innsending: {at.exception}")

        logg = hent_logg(_OPPSKRIFT_NAVN)
        self.assertEqual(len(logg), 1)
        forventet = round(beregn_abv_standard(1.055, 1.012), 1)
        self.assertEqual(logg[0]["actual_abv"], forventet)
        # Selve formelen er UENDRET -- kun flyttet til Core.
        self.assertEqual(forventet, round((1.055 - 1.012) * 131.25, 1))

    def test_fg_storre_enn_og_lagrer_ingen_negativ_abv(self):
        at = self._last_app_med_oppskrift()
        _finn_number_input(at, "Faktisk OG").set_value(1.010).run()
        _finn_number_input(at, "Faktisk FG (valgfritt)").set_value(1.055).run()
        _finn_button(at, "Legg til loggoppføring").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved innsending: {at.exception}")

        logg = hent_logg(_OPPSKRIFT_NAVN)
        self.assertEqual(len(logg), 1)
        self.assertIsNone(logg[0]["actual_abv"])


class TestBrewdayBeregnetAbvDelegererTilCore(_MedLastetOppskrift):
    """ui/brewday_panel.py sin live "Beregnet ABV"-metric (Steg 5:
    Gjæring)."""

    def test_gyldig_og_fg_gir_uendret_standard_abv(self):
        at = self._last_app_med_oppskrift()
        at.tabs[2].text_input(key="bd_og").set_value("1.055").run()
        at.tabs[2].text_input(key="bd_fg").set_value("1.012").run()
        self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

        metrikker = [m for m in at.metric if m.label == "Beregnet ABV"]
        self.assertEqual(len(metrikker), 1)
        forventet = beregn_abv_standard(1.055, 1.012)
        self.assertEqual(metrikker[0].value, f"{forventet:.1f}%")

    def test_fg_storre_enn_og_viser_ingen_negativ_abv_metric(self):
        at = self._last_app_med_oppskrift()
        at.tabs[2].text_input(key="bd_og").set_value("1.010").run()
        at.tabs[2].text_input(key="bd_fg").set_value("1.055").run()
        self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

        metrikker = [m for m in at.metric if m.label == "Beregnet ABV"]
        self.assertEqual(metrikker, [], "Ingen 'Beregnet ABV'-metric skal vises for FG > OG")


if __name__ == "__main__":
    unittest.main()
