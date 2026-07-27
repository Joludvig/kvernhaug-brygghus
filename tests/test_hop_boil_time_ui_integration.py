"""
Ende-til-ende UI-regresjonstest (samme mønster som
tests/test_real_app_process_flow.py -- kjører den EKTE app.py via
streamlit.testing.v1.AppTest, ikke en proxy/testvert): bekrefter at en
oppskrift med en humle hvis egen koketid overstiger total koketid faktisk
vises som et varsel i BÅDE Bryggemåte-panelet og Bryggedag-panelet, og at
"🖨️ Generer Bryggedagsark"-knappen er låst til brukeren har bekreftet
avviket eksplisitt.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")


class TestHumletidOverKoketidIEktApp(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        # 90 min humle, ingen prosessprofil valgt ennå (=> standard 60 min
        # koketid siden ingen pilsnermalt er brukt) -- akkurat scenarioet
        # fra feilrapporten: UI viste tilsetning ved kokestart samtidig
        # som en umulig 90-minutters IBU ble beregnet.
        recipe = bygg_recipe_object(
            "E2E Humletid Over Koketid", 20.0, 0.75,
            [{"id": "vienna", "mengde": 5.0}],
            [{"id": "magnum", "gram": 20, "tid": 90}],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_varsel_vises_og_eksport_er_last_til_bekreftet(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Humletid Over Koketid").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        # Bekreft utgangstilstanden: 90 min humle, standard 60 min koketid.
        self.assertEqual(st_boil := at.session_state["prosess_boil_minutes"], 60)
        self.assertEqual(at.session_state["valgt_humle"][0]["tid"], 90)

        # === Bryggemåte-panelet: varsel om umulig humletid ===
        varsel_tekster = " ".join(w.value for w in at.warning)
        self.assertIn("koketid", varsel_tekster.lower())
        self.assertIn("Magnum", varsel_tekster)

        # === Bryggedag-panelet: eksportknappen er låst ===
        eksport_knapp = at.button(key="brewday_print_btn")
        self.assertTrue(eksport_knapp.disabled, "Eksportknappen skal være låst før avviket er bekreftet")

        bekreft_checkbox = at.checkbox(key="bd_bekreft_humletid_avvik")
        self.assertFalse(bekreft_checkbox.value)

        bekreft_checkbox.check().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved bekreftelse: {at.exception}")

        eksport_knapp = at.button(key="brewday_print_btn")
        self.assertFalse(eksport_knapp.disabled, "Eksportknappen skal låses opp etter eksplisitt bekreftelse")

    def test_ingen_varsel_eller_lasing_naar_humletid_er_innenfor_koketiden(self):
        import modules.recipe_storage as recipe_storage
        ok_recipe = bygg_recipe_object(
            "E2E Humletid OK", 20.0, 0.75,
            [{"id": "vienna", "mengde": 5.0}],
            [{"id": "magnum", "gram": 20, "tid": 60}],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(ok_recipe)

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Humletid OK").run()
        self.assertFalse(at.exception)

        varsel_tekster = " ".join(w.value for w in at.warning)
        self.assertNotIn("koketid", varsel_tekster.lower())

        eksport_knapp = at.button(key="brewday_print_btn")
        self.assertFalse(eksport_knapp.disabled)
        # Bekreftelses-checkboxen skal ikke engang rendres når det ikke
        # finnes noe avvik å bekrefte.
        with self.assertRaises(KeyError):
            at.checkbox(key="bd_bekreft_humletid_avvik")


if __name__ == "__main__":
    unittest.main()
