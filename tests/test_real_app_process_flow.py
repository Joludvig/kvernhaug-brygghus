"""
Ende-til-ende-regresjonstest som kjører den EKTE app.py direkte (ikke en
proxy/testvert) via streamlit.testing.v1.AppTest — samme funksjonsrekke-
følge og samme feltnavn som den virkelige appflyten:

    sidebar (last lagret oppskrift) -> bygg_recipe_context() ->
    render_process_panel() -> lag_brewday_plan() -> render_brewday_html()

Bakgrunn: en tidligere runde bygget en "realistisk testvert"
(tests/_full_flow_app.py) som beviste at kjeden var korrekt, men
brukeren rapporterte at feilen fortsatt viste seg i den FAKTISKE,
kjørende appen etter full omstart av Streamlit. En grundig instrumentert
diagnose — kjørt direkte mot app.py (samme fil som `start_app.bat`
starter) via AppTest, med den EKTE lagrede "Kvernhaug Wiesn-Märzen
1872"-oppskriften fra recipes/-mappen — viste at ALLE fem leddene
(aktiv_prosessprofil, ctx["recipe"]["process_profile"],
process_profile-argumentet til lag_brewday_plan(), ferdig
brewday_plan["maskeplan"], og dataene faktisk sendt til
render_brewday_html()) allerede var konsistent 63/40, 70/30, 77/10 — for
både den auto-anbefalte banen og et eksplisitt bytte
Enkel infusjon -> Hochkurz. Denne testen låser nettopp dette fast som en
permanent regresjon mot app.py selv (ikke en proxy), slik at en
fremtidig regresjon i selve app.py sin rekkefølge (f.eks. om noen bytter
rekkefølgen på fane-rendring) fanges opp.

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


class TestRealAppPyHochkurzEksport(unittest.TestCase):
    """Kjører den EKTE app.py (samme fil som start_app.bat starter) —
    ikke en isolert testvert — gjennom nøyaktig den rapporterte
    sekvensen: last en lagret oppskrift UTEN process_profile (som
    speiler de virkelige, allerede lagrede Wiesn-Märzen-filene i
    recipes/), velg eksplisitt Enkel infusjon og deretter Hochkurz, og
    trykk den ekte eksportknappen."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        # Ingen process_profile satt i det hele tatt — speiler EKSAKT
        # skjemaet til de virkelige, allerede lagrede Wiesn-Märzen-
        # oppskriftene i recipes/ (lagret før process_profile-feltet
        # eksisterte).
        recipe = bygg_recipe_object(
            "E2E Real App Wiesn", 23.0, 0.75,
            [
                {"id": "weyermann_munich_1", "mengde": 0.65},
                {"id": "munich_ii",          "mengde": 4.28},
                {"id": "vienna",             "mengde": 1.60},
            ],
            [{"id": "tettnang", "gram": 30, "tid": 60}],
            "saflager_w3470", 1.064, 1.013, 6.9, 22, 20, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_last_oppskrift_bytt_til_hochkurz_og_eksporter(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Real App Wiesn").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        # Eksplisitt via Enkel infusjon FØRST (samme rekkefølge som i den
        # rapporterte bug'en: "bytte fra Enkel infusjon til Hochkurz").
        at.selectbox(key="valgt_prosess_id").select("enkel_infusjon").run()
        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved profilbytte: {at.exception}")

        forventet = [(63.0, 40), (70.0, 30), (77.0, 10)]

        aktiv = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(aktiv["navn"], "Hochkurz (stegmesk)")
        self.assertEqual([(s["temperatur"], s["varighet"]) for s in aktiv["mash_steps"]], forventet)

        # Trykk den EKTE "Generer Bryggedagsark"-knappen i ui/brewday_panel.py
        # — ingen midlertidige debug-nøkler igjen; bekreft i stedet direkte
        # via den ekte produksjonsfunksjonen at planen/eksporten som
        # FAKTISK ble beregnet med denne (bekreftet kanoniske)
        # aktiv_prosessprofil er korrekt.
        at.button(key="brewday_print_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved eksport: {at.exception}")

        aktiv_etter_eksport = at.session_state["aktiv_prosessprofil"]
        self.assertEqual(
            [(s["temperatur"], s["varighet"]) for s in aktiv_etter_eksport["mash_steps"]], forventet,
        )

        from modules.brewday_calc import lag_brewday_plan
        from modules.brewday_template import render_brewday_html

        plan = lag_brewday_plan(
            malt_valg=[
                {"id": "weyermann_munich_1", "mengde": 0.65},
                {"id": "munich_ii",          "mengde": 4.28},
                {"id": "vienna",             "mengde": 1.60},
            ],
            humle_valg=[{"id": "tettnang", "gram": 30, "tid": 60}],
            gjaer_id="saflager_w3470",
            gjaer_info={"display_name": "SafLager W-34/70", "gjaertype": "Lager", "attenuation": 0.80},
            og=1.064, batch_volum_l=23.0, humle_database={}, malt_database={},
            process_profile=aktiv_etter_eksport,
        )
        maskeplan = [(s["temp_c"], s["varighet_min"]) for s in plan["maskeplan"]]
        self.assertEqual(maskeplan, forventet)
        self.assertNotIn((66.0, 60), maskeplan)
        self.assertNotIn((78.0, 5), maskeplan)

        ctx_stub = {
            "name": "E2E Real App Wiesn", "volum": 23.0, "og": 1.064, "fg": 1.013, "abv": 6.9,
            "ibu": 22, "ebc": 20, "effektivitet": 0.75,
            "recipe": bygg_recipe_object(
                "E2E Real App Wiesn", 23.0, 0.75, [], [], "saflager_w3470",
                1.064, 1.013, 6.9, 22, 20, {}, process_profile=aktiv_etter_eksport,
            ),
        }
        html = render_brewday_html(ctx_stub, plan, {})
        self.assertIn("63.0°C", html)
        self.assertIn("70.0°C", html)
        self.assertIn("77.0°C", html)
        self.assertNotIn("66.0°C", html)
        self.assertNotIn("78.0°C", html)


class TestLagreOgGjenaapneGjennomEktApp(unittest.TestCase):
    """Krav: gammel oppskrift uten process_profile -> velg Hochkurz ->
    LAGRE oppskriften -> ÅPNE DEN PÅ NYTT (frisk AppTest-sesjon, som en
    ekte nettleser-omstart) -> widgetene, aktiv profil, det lagrede
    oppskriftsobjektet OG eksporten skal alle vise nøyaktig kanonisk
    Hochkurz: 63/40, 70/30, 77/10.

    Kjøres mot den EKTE app.py, med en isolert KVERNHAUG_RECIPES_DIR
    (aldri den virkelige recipes/-mappen) — se tests/test_recipe_storage_isolation.py."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        recipe = bygg_recipe_object(
            "E2E Lagre Og Gjenaapne", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )  # ingen process_profile — som en gammel, ekte lagret oppskrift
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_last_velg_hochkurz_lagre_gjenaapne_gir_kanonisk_overalt(self):
        forventet = [(63.0, 40), (70.0, 30), (77.0, 10)]

        # ── ØKT 1: last, velg Hochkurz, lagre ────────────────────────────
        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Lagre Og Gjenaapne").run()
        self.assertFalse(at.exception)

        at.selectbox(key="valgt_prosess_id").select("hochkurz").run()
        self.assertFalse(at.exception)
        self.assertEqual(
            [(s["temperatur"], s["varighet"]) for s in at.session_state["aktiv_prosessprofil"]["mash_steps"]],
            forventet,
        )

        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"Lagring feilet: {at.exception}")

        # Bekreft at oppskriftsobjektet FAKTISK lagret på disk (i den
        # isolerte mappen) har kanonisk Hochkurz.
        import modules.recipe_storage as recipe_storage
        lagret = recipe_storage.hent_alle_oppskrifter()["E2E Lagre Og Gjenaapne"]
        self.assertEqual(lagret["process_profile"]["navn"], "Hochkurz (stegmesk)")
        self.assertEqual(
            [(s["temperatur"], s["varighet"]) for s in lagret["process_profile"]["mash_steps"]],
            forventet,
        )

        # ── ØKT 2: helt FRISK AppTest-sesjon — som å åpne appen på nytt ──
        at2 = AppTest.from_file(_APP_PY)
        at2.run()
        at2.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Lagre Og Gjenaapne").run()
        self.assertFalse(at2.exception, f"Gjenåpning feilet: {at2.exception}")

        # 1) aktiv_prosessprofil
        aktiv = at2.session_state["aktiv_prosessprofil"]
        self.assertEqual(aktiv["navn"], "Hochkurz (stegmesk)")
        self.assertEqual([(s["temperatur"], s["varighet"]) for s in aktiv["mash_steps"]], forventet)

        # 2) Widgetene (samme teknikk som tests/test_process_panel.py sin
        #    _widget_steg() — leser number_input-verdiene DIREKTE).
        revisjon = at2.session_state["_process_widget_revision"]
        widget_steg = []
        i = 0
        while True:
            try:
                temp = at2.number_input(key=f"mash_temp_{revisjon}_{i}").value
                tid = at2.number_input(key=f"mash_time_{revisjon}_{i}").value
            except KeyError:
                break
            widget_steg.append((temp, tid))
            i += 1
        self.assertEqual(widget_steg, forventet)

        # 3) Eksport — den ekte knappen, ekte produksjonsfunksjon.
        at2.button(key="brewday_print_btn").click().run()
        self.assertFalse(at2.exception)

        from modules.brewday_calc import lag_brewday_plan
        plan = lag_brewday_plan(
            malt_valg=[{"id": "weyermann_pilsner", "mengde": 5.0}],
            humle_valg=[], gjaer_id="safale_us_05",
            gjaer_info={"display_name": "US-05", "gjaertype": "Ale", "attenuation": 0.75},
            og=1.050, batch_volum_l=20.0, humle_database={}, malt_database={},
            process_profile=at2.session_state["aktiv_prosessprofil"],
        )
        maskeplan = [(s["temp_c"], s["varighet_min"]) for s in plan["maskeplan"]]
        self.assertEqual(maskeplan, forventet)
        self.assertNotIn((66.0, 60), maskeplan)
        self.assertNotIn((78.0, 5), maskeplan)

        # Bekreft at den ekte recipes/-mappen aldri ble berørt av noe av dette.
        self.assertFalse(os.path.exists(os.path.join(_REPO_ROOT, "recipes", "e2e_lagre_og_gjenaapne.json")))


if __name__ == "__main__":
    unittest.main()
