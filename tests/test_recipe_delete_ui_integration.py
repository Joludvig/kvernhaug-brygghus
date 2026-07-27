"""
Ende-til-ende UI-regresjonstest (samme mønster som
tests/test_real_app_process_flow.py -- kjører den EKTE app.py via
streamlit.testing.v1.AppTest) for arkiverings-("slett")-flyten i
ui/recipe_card.py, etter at modules/recipe_storage.py::slett_oppskrift_fil()
ble endret til å kreve et faktisk, validert kildefilnavn i stedet for å
gjette det fra oppskriftens (redigerbare) navn.

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


class TestSlettGjeldendeIEktApp(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        recipe = bygg_recipe_object(
            "E2E Slett Test", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_slett_gjeldende_arkiverer_via_faktisk_kildefil(self):
        import modules.recipe_storage as recipe_storage

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Slett Test").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")
        self.assertEqual(at.session_state["_last_loaded_recipe_file"], "e2e_slett_test.json")

        at.button(key="slett_gjeldende_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved slett-klikk: {at.exception}")

        at.button(key="slett_bekreft_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved bekreftelse: {at.exception}")

        # Filen er faktisk arkivert -- ikke navngjettet, ikke slettet permanent.
        self.assertNotIn("E2E Slett Test", recipe_storage.hent_alle_oppskrifter())
        arkiv_mappe = os.path.join(self._tmpdir.name, "_archive")
        self.assertIn("e2e_slett_test.json", os.listdir(arkiv_mappe))

        # UI-et skal ha nullstilt seg ETTER en vellykket arkivering.
        self.assertNotIn("_last_loaded_recipe_file", at.session_state)

    def test_slett_gjeldende_er_deaktivert_for_uladet_oppskrift(self):
        # En helt fersk, aldri-lastet/-lagret oppskrift har ingen kjent
        # kildefil -- knappen skal være deaktivert i stedet for å kalle
        # slett_oppskrift_fil() med None/gjettet navn.
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception)
        knapp = at.button(key="slett_gjeldende_btn")
        self.assertTrue(knapp.disabled)


if __name__ == "__main__":
    unittest.main()
