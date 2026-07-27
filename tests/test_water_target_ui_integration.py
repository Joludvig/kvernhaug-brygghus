"""
Ende-til-ende-regresjonstest (via streamlit.testing.v1.AppTest, samme
mønster som tests/test_water_recipe_integration.py) for målprofil-
biblioteket i ui/water_panel.py:

  - Anbefalingen for en humlepreget stil (IPA) skal ALDRI velge
    «Humledrevet øl» automatisk — kun vises som forslag.
  - Velger brukeren «Egendefinert» og redigerer sine egne grenser, skal
    disse bevares gjennom lagring OG en helt fersk gjenåpning, selv om
    oppskriftens stil ville anbefalt en annen profil.

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


class TestMaalprofilAnbefalingOgEgendefinert(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        self._tmpdir_maal = tempfile.TemporaryDirectory()
        self._gammel_maal_env = os.environ.get("KVERNHAUG_WATER_TARGETS_FILE")
        os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = os.path.join(self._tmpdir_maal.name, "water_targets.json")

        # Kopier den ekte målprofil-biblioteket inn i den isolerte filen,
        # slik at UI-et har noe å velge mellom UTEN å røre den ekte filen.
        import json
        with open(os.path.join(_REPO_ROOT, "data", "water_targets.json"), encoding="utf-8") as f:
            ekte_maal = json.load(f)
        os.makedirs(self._tmpdir_maal.name, exist_ok=True)
        with open(os.environ["KVERNHAUG_WATER_TARGETS_FILE"], "w", encoding="utf-8") as f:
            json.dump(ekte_maal, f, ensure_ascii=False, indent=2)

        import modules.recipe_storage as recipe_storage
        self._malt = [{"id": "weyermann_pilsner", "mengde": 5.0}]
        self._hops = [{"id": "magnum_de", "gram": 40, "tid": 60}]
        recipe = bygg_recipe_object(
            "E2E Maalprofil IPA", 20.0, 0.75, self._malt, self._hops,
            "safale_us_05", 1.060, 1.010, 6.5, 55, 8, {},
            brygger_stil="IPA",
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_recipes_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_env
        self._tmpdir.cleanup()

        if self._gammel_maal_env is None:
            os.environ.pop("KVERNHAUG_WATER_TARGETS_FILE", None)
        else:
            os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = self._gammel_maal_env
        self._tmpdir_maal.cleanup()

    def test_anbefaling_velger_aldri_automatisk_og_egendefinert_bevares(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Maalprofil IPA").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        # Ingen lagret vannprofil -> panelet faller tilbake til FØRSTE
        # profil i biblioteket, ALDRI den anbefalte, med mindre den
        # tilfeldigvis er først. «Humledrevet øl» (den reelle anbefalingen
        # for IPA) er IKKE plukket automatisk.
        valgt_ved_lasting = at.session_state["vann_maal_valgt_id"]
        self.assertNotEqual(
            valgt_ved_lasting, "humledrevet_ol",
            "Anbefalingsmotoren valgte målprofil automatisk — den skal KUN foreslå.",
        )

        # Velg «Egendefinert» eksplisitt og rediger noen grenser.
        at.selectbox(key="vann_maal_valgt_id").select("egendefinert").run()
        self.assertFalse(at.exception)
        self.assertEqual(at.session_state["vann_maal_valgt_id"], "egendefinert")

        at.number_input(key="vann_maal_ca_min").set_value(11.0).run()
        at.number_input(key="vann_maal_ca_max").set_value(19.0).run()
        at.number_input(key="vann_maal_so4_min").set_value(6.0).run()
        at.number_input(key="vann_maal_so4_max").set_value(14.0).run()
        self.assertFalse(at.exception)

        at.button(key="vann_lagre_maal_btn").click().run()
        self.assertFalse(at.exception, f"Lagring av målprofil feilet: {at.exception}")

        # Lagre selve oppskriften, slik at snapshotet av «Egendefinert»
        # (med brukerens grenser) fryses fast i oppskriftsfilen.
        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"Lagring av oppskrift feilet: {at.exception}")

        import modules.recipe_storage as recipe_storage
        lagret = recipe_storage.hent_alle_oppskrifter()["E2E Maalprofil IPA"]
        self.assertEqual(lagret["water_target_profile"]["target_id"], "egendefinert")
        self.assertEqual(lagret["water_target_profile"]["ca_min"], 11.0)
        self.assertEqual(lagret["water_target_profile"]["ca_max"], 19.0)
        self.assertEqual(lagret["water_target_profile"]["so4_min"], 6.0)
        self.assertEqual(lagret["water_target_profile"]["so4_max"], 14.0)

        # ── FRISK AppTest-sesjon — som å åpne appen på nytt ─────────────
        at2 = AppTest.from_file(_APP_PY)
        at2.run()
        at2.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Maalprofil IPA").run()
        self.assertFalse(at2.exception, f"Gjenåpning feilet: {at2.exception}")

        # Egendefinert-valget og brukerens egne grenser er BEVART — til
        # tross for at oppskriftens stil (IPA) ville anbefalt "Humledrevet
        # øl". Anbefalingen vises fortsatt (se aktiv_vannmaal_snapshot),
        # men har IKKE overstyrt det lagrede valget.
        self.assertEqual(at2.session_state["vann_maal_valgt_id"], "egendefinert")
        aktiv_maal = at2.session_state["aktiv_vannmaal_snapshot"]
        self.assertEqual(aktiv_maal["target_id"], "egendefinert")
        self.assertEqual(aktiv_maal["ca_min"], 11.0)
        self.assertEqual(aktiv_maal["ca_max"], 19.0)
        self.assertEqual(aktiv_maal["so4_min"], 6.0)
        self.assertEqual(aktiv_maal["so4_max"], 14.0)

        # Biblioteket sin "humledrevet_ol"-mal er fortsatt urørt av dette.
        from modules.water_chemistry import last_vannmaal
        self.assertEqual(last_vannmaal()["humledrevet_ol"]["ca_min"], 75)
        self.assertEqual(last_vannmaal()["humledrevet_ol"]["so4_min"], 100)

        # Den ekte recipes/-mappen og det ekte målprofil-biblioteket skal
        # aldri ha blitt berørt av noe av dette.
        self.assertFalse(os.path.exists(os.path.join(_REPO_ROOT, "recipes", "e2e_maalprofil_ipa.json")))


if __name__ == "__main__":
    unittest.main()
