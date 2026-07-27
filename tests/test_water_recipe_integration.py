"""
Ende-til-ende-regresjonstest for vannkjemi V1 — kjører den EKTE app.py via
streamlit.testing.v1.AppTest (samme mønster som
tests/test_real_app_process_flow.py), med isolert KVERNHAUG_RECIPES_DIR.

Dekker (fra spesifikasjonen for vannkjemi V1):
  18. Gamle oppskrifter uten vannprofil åpnes uten feil.
  19. Lagring og gjenåpning beholder vannbehandlingen.
  21. Bryggedagsarket viser riktig fordeling (via render_brewday_html).
  22. Oppskriftsingredienser (malt/humle/gjær) endres ikke.
  23. process_profile endres ikke.

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


class TestVannkjemiGjennomEktApp(unittest.TestCase):
    """Gammel oppskrift UTEN vannprofil -> åpne -> velg Jordalsvatnet 2025
    -> beregn saltforslag -> lagre -> gjenåpne i en HELT FRISK AppTest-
    sesjon -> vannbehandlingen skal være bevart, og malt/humle/gjær/
    process_profile skal være UENDRET."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        self._malt = [
            {"id": "weyermann_munich_1", "mengde": 0.65},
            {"id": "munich_ii", "mengde": 4.28},
            {"id": "vienna", "mengde": 1.60},
        ]
        self._hops = [{"id": "tettnang", "gram": 30, "tid": 60}]
        recipe = bygg_recipe_object(
            "E2E Vannkjemi Wiesn", 23.0, 0.75, self._malt, self._hops,
            "saflager_w3470", 1.064, 1.013, 6.9, 22, 20, {},
            # Ingen water_* felter — speiler en oppskrift lagret FØR
            # vannkjemi-feltene eksisterte.
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_full_flyt_last_velg_kilde_solver_lagre_gjenaapne(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Vannkjemi Wiesn").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        # Gammel oppskrift uten vannprofil skal falle tilbake til "ukjent
        # kilde" — Jordalsvatnet skal ALDRI settes automatisk.
        self.assertEqual(at.session_state["vann_kilde_valgt_id"], "__ukjent__")
        self.assertIsNone(at.session_state["aktiv_vannbehandling"]["vannkilde_id"])

        # ui/process_panel.py sin egen anbefalingsmotor kan (uavhengig av
        # vannkjemi) ha forhåndsvalgt EN standardprofil for denne malt-
        # bunnen allerede ved lasting — det er eksisterende, etablert
        # oppførsel (se modules/process_profiles.py: anbefal_prosess()).
        # Det denne testen skal bevise er at VANNBEHANDLINGEN ikke endrer
        # denne profilen videre — ikke at den nødvendigvis forblir None.
        process_profil_ved_lasting = at.session_state["aktiv_prosessprofil"]

        # Velg Jordalsvatnet 2025 eksplisitt.
        at.selectbox(key="vann_kilde_valgt_id").select("jordalsvatnet_2025").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved kildevalg: {at.exception}")
        self.assertEqual(at.session_state["vann_kilde_valgt_id"], "jordalsvatnet_2025")

        # Beregn saltforslag (den ekte «🧮 Beregn saltforslag»-knappen).
        at.button(key="vann_beregn_forslag_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved saltforslag: {at.exception}")
        forslag = at.session_state["vann_salter"]
        self.assertTrue(forslag, "Solveren foreslo ingen salter for Jordalsvatnet + standard målprofil.")

        behandling_for_lagring = at.session_state["aktiv_vannbehandling"]
        self.assertEqual(behandling_for_lagring["vannkilde_id"], "jordalsvatnet_2025")
        self.assertTrue(behandling_for_lagring["salter"])

        # Lagre (den ekte «💾 Lagre endringer»-knappen).
        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"Lagring feilet: {at.exception}")

        import modules.recipe_storage as recipe_storage
        lagret = recipe_storage.hent_alle_oppskrifter()["E2E Vannkjemi Wiesn"]
        self.assertIsNotNone(lagret["water_source_profile"])
        self.assertEqual(lagret["water_source_profile"]["water_id"], "jordalsvatnet_2025")
        self.assertIsNotNone(lagret["water_treatment"])
        self.assertEqual(lagret["water_treatment"]["vannkilde_id"], "jordalsvatnet_2025")
        self.assertTrue(lagret["water_treatment"]["salter"])
        # Ingrediensene/prosessprofilen skal IKKE ha blitt påvirket av
        # vannbehandlingen — uendret siden FØR kilde/solver ble brukt.
        self.assertEqual(lagret["malts"], self._malt)
        self.assertEqual(lagret["hops"], self._hops)
        self.assertEqual(lagret["process_profile"], process_profil_ved_lasting)

        # ── FRISK AppTest-sesjon — som å åpne appen på nytt ─────────────
        at2 = AppTest.from_file(_APP_PY)
        at2.run()
        at2.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Vannkjemi Wiesn").run()
        self.assertFalse(at2.exception, f"Gjenåpning feilet: {at2.exception}")

        self.assertEqual(at2.session_state["vann_kilde_valgt_id"], "jordalsvatnet_2025")
        behandling_etter = at2.session_state["aktiv_vannbehandling"]
        self.assertEqual(behandling_etter["vannkilde_id"], "jordalsvatnet_2025")
        self.assertTrue(behandling_etter["salter"])
        self.assertEqual(
            {s["salt_id"] for s in behandling_etter["salter"]},
            {s["salt_id"] for s in forslag},
        )

        # Ingredienser/prosessprofil fortsatt uendret etter gjenåpning.
        ctx2 = at2.session_state["_last_og"]  # tilgjengelig -> ctx ble bygget uten feil
        self.assertIsNotNone(ctx2)
        self.assertEqual(at2.session_state["valgt_malt"], self._malt)
        self.assertEqual(at2.session_state["valgt_humle"], self._hops)
        self.assertEqual(at2.session_state["aktiv_prosessprofil"], process_profil_ved_lasting)

        # Eksporten (bryggedagsarket) skal vise riktig fordeling — bruk den
        # ekte knappen, og bekreft ingen exception (samme mønster som
        # test_real_app_process_flow.py, siden AppTest ikke kan
        # introspisere download_button-innhold i denne Streamlit-versjonen).
        at2.button(key="brewday_print_btn").click().run()
        self.assertFalse(at2.exception, f"Eksport feilet: {at2.exception}")

        from modules.brewday_calc import lag_brewday_plan
        from modules.brewday_template import render_brewday_html
        plan = lag_brewday_plan(
            malt_valg=self._malt, humle_valg=self._hops, gjaer_id="saflager_w3470",
            gjaer_info={"display_name": "SafLager W-34/70", "gjaertype": "Lager", "attenuation": 0.80},
            og=1.064, batch_volum_l=23.0, humle_database={}, malt_database={},
            process_profile=process_profil_ved_lasting,
        )
        ctx_stub = {
            "name": "E2E Vannkjemi Wiesn", "volum": 23.0, "og": 1.064, "fg": 1.013, "abv": 6.9,
            "ibu": 22, "ebc": 20, "effektivitet": 0.75,
            "recipe": lagret,
        }
        water = {
            "kilde": lagret["water_source_profile"],
            "maal": lagret["water_target_profile"],
            "behandling": behandling_etter,
            "maalinger": lagret.get("water_measurements"),
        }
        html = render_brewday_html(ctx_stub, plan, {}, water=water)
        self.assertIn("Jordalsvatnet 2025", html)
        for s in behandling_etter["salter"]:
            if s["gram_mesk"] > 0.005:
                self.assertIn(f"{s['gram_mesk']:.2f} g", html)

        # Den ekte recipes/-mappen skal aldri ha blitt berørt.
        self.assertFalse(os.path.exists(os.path.join(_REPO_ROOT, "recipes", "e2e_vannkjemi_wiesn.json")))


if __name__ == "__main__":
    unittest.main()
