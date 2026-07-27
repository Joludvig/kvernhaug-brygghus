"""
Integrasjonstester for Supply Engine / Pantry V1 — kjører den EKTE
ui/pantry_panel.py + modules/pantry.py + modules/recipe_context.py gjennom
Streamlit sitt AppTest-rammeverk (samme mønster som tests/_full_flow_app.py
og tests/test_style_panel_ui.py), via testverten tests/_pantry_full_flow_app.py.

Isolasjon: KVERNHAUG_PANTRY_DIR settes til en tempfile.TemporaryDirectory()
i setUp() og gjenopprettes i tearDown() — ingen test her leser eller
skriver den ekte data/pantry.json. Oppskriften i testverten er seedet fra
den committede Wiesn-Märzen-fixturen (tests/fixtures/recipes/), ikke fra
brukerens private recipes/-mappe.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import copy
import os
import tempfile
import unittest

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_pantry_full_flow_app.py")


class _PantryAppTestCase(unittest.TestCase):
    def setUp(self):
        from streamlit.testing.v1 import AppTest
        self._AppTest = AppTest
        self._gammel_env = os.environ.get("KVERNHAUG_PANTRY_DIR")
        self._tmpdir = tempfile.TemporaryDirectory()
        os.environ["KVERNHAUG_PANTRY_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_PANTRY_DIR", None)
        else:
            os.environ["KVERNHAUG_PANTRY_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _kjor(self):
        at = self._AppTest.from_file(_APP)
        at.run()
        self.assertFalse(at.exception, f"_pantry_full_flow_app.py kastet exception: {at.exception}")
        return at

    def _legg_til_vare(self, at, ingredient_type_visning, ingredient_id, mengde, enhet):
        at.selectbox(key="pantry_ny_type").set_value(ingredient_type_visning).run()
        at.selectbox(key="pantry_ny_ingrediens").set_value(ingredient_id).run()
        at.selectbox(key="pantry_ny_enhet").set_value(enhet).run()
        at.number_input(key="pantry_ny_mengde").set_value(mengde).run()
        at.button(key="pantry_legg_til_btn").click().run()
        return at


class TestOppskriftOgKontekstMuteresIkke(_PantryAppTestCase):
    """Krav 15/16/17: Pantry skal aldri endre oppskriften, prosessprofilen
    eller vannkjemien den leser fra."""

    def test_oppskriften_er_uendret_etter_pantry_interaksjoner(self):
        at = self._kjor()
        original_recipe = copy.deepcopy(at.session_state["_debug_ctx_recipe"])

        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        self._legg_til_vare(at, "Humle", "tettnang", 100.0, "g")
        self._legg_til_vare(at, "Gjær", "saflager_w3470", 2.0, "pakke")

        self.assertEqual(
            at.session_state["_debug_ctx_recipe"], original_recipe,
            "Pantry-handlinger skal aldri endre oppskriften (malts/hops/yeast/stats)",
        )

    def test_prosessprofil_og_vannkjemi_er_uendret(self):
        at = self._kjor()
        original_prosess = copy.deepcopy(at.session_state["aktiv_prosessprofil"])
        original_vann = copy.deepcopy(at.session_state["aktiv_vannmaal_snapshot"])

        self._legg_til_vare(at, "Malt", "munich_ii", 5.0, "kg")
        pantry_data = at.session_state["_debug_pantry"]
        item_id = pantry_data["items"][0]["pantry_item_id"]
        at.button(key=f"pantry_slett_{item_id}").click().run()
        at.button(key="pantry_slett_bekreft").click().run()

        self.assertEqual(at.session_state["aktiv_prosessprofil"], original_prosess,
                          "Pantry skal aldri røre prosessprofilen")
        self.assertEqual(at.session_state["aktiv_vannmaal_snapshot"], original_vann,
                          "Pantry skal aldri røre vannkjemi-snapshotten")


class TestSlettingKreverBekreftelse(_PantryAppTestCase):
    """Krav 18: sletting krever eksplisitt bekreftelse i UI — ett klikk på
    søppelbøtte-knappen alene skal IKKE slette posten."""

    def test_ett_klikk_sletter_ikke_krever_bekreftelse(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        item_id = at.session_state["_debug_pantry"]["items"][0]["pantry_item_id"]

        at.button(key=f"pantry_slett_{item_id}").click().run()
        self.assertEqual(len(at.session_state["_debug_pantry"]["items"]), 1,
                          "Ett klikk på slett-knappen skal IKKE fjerne posten uten bekreftelse")
        self.assertTrue(any("Slette" in w.value for w in at.warning),
                         "Forventet en synlig bekreftelses-advarsel før sletting")

        at.button(key="pantry_slett_bekreft").click().run()
        self.assertEqual(at.session_state["_debug_pantry"]["items"], [],
                          "Etter eksplisitt bekreftelse skal posten være slettet")

    def test_avbryt_beholder_posten(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        item_id = at.session_state["_debug_pantry"]["items"][0]["pantry_item_id"]

        at.button(key=f"pantry_slett_{item_id}").click().run()
        at.button(key="pantry_slett_avbryt").click().run()
        self.assertEqual(len(at.session_state["_debug_pantry"]["items"]), 1,
                          "Avbryt skal beholde posten uendret")


class TestFullFlowLagerStatusSkaleringOgPersistens(_PantryAppTestCase):
    """Krav 25 — full AppTest: legg inn malt/humle/gjær, åpne
    Wiesn-fixturen (seedet av testverten), se korrekt nok/mangler-status,
    skaler oppskriften, se manglene oppdateres, åpne ny sesjon, bekreft at
    lageret er bevart og oppskriften urørt."""

    def test_full_flow(self):
        at = self._kjor()

        # Wiesn-fixturen: weyermann_munich_1 0.7 kg, munich_ii 4.6 kg,
        # vienna 1.8 kg, tettnang 88 g, saflager_w3470 (gjær).
        recipe = at.session_state["_debug_ctx_recipe"]
        malt_ider = {m["id"] for m in recipe["malts"]}
        self.assertEqual(malt_ider, {"weyermann_munich_1", "munich_ii", "vienna"})

        # 1) Legg inn rikelig av alt malt/humle som trengs -> "nok".
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        self._legg_til_vare(at, "Malt", "munich_ii", 5.0, "kg")
        self._legg_til_vare(at, "Malt", "vienna", 2.0, "kg")
        self._legg_til_vare(at, "Humle", "tettnang", 100.0, "g")
        self._legg_til_vare(at, "Gjær", "saflager_w3470", 2.0, "pakke")

        self.assertEqual(len(at.session_state["_debug_pantry"]["items"]), 5)

        # 2) Malt+humle skal nå vise "nok" -- ingen mangel-feil. Gjær har
        # ingen lagret anbefalt pakkeantall i dagens oppskriftsmodell og
        # skal derfor alltid vises som "må kontrolleres manuelt", ikke som
        # en falsk "nok".
        self.assertEqual(len(at.error), 0, "Malt og humle skulle dekke behovet -- ingen mangel-feil forventet")
        self.assertTrue(
            any("kontrolleres manuelt" in w.value for w in at.warning),
            "Forventet varsel om at gjær (ukjent pakkebehov) må kontrolleres manuelt",
        )

        # 3) Skaler oppskriften til det dobbelte -- malt-behovet dobles.
        at.number_input(key="skaler_maal_volum").set_value(40.0).run()
        at.button(key="skaler_btn").click().run()

        skalert_recipe = at.session_state["_debug_ctx_recipe"]
        skalert_malt = {m["id"]: m["mengde"] for m in skalert_recipe["malts"]}
        self.assertAlmostEqual(skalert_malt["munich_ii"], 9.2, places=2,
                                msg="Skalering til dobbel batch skal doble malt-mengden")

        # 4) Mangelen skal nå gjenspeile det NYE, doblede behovet: 5 kg
        # munich_ii på lager dekker ikke lenger 9.2 kg behov.
        self.assertGreater(
            len(at.error), 0,
            "Etter skalering skal munich_ii-behovet (9.2 kg) overstige lageret (5 kg) og gi en mangel-feil",
        )

        # 5) Ny sesjon: lageret er bevart, oppskriften i den NYE sesjonen
        # er den uendrede fixture-oppskriften (testverten seedes på nytt
        # fra fixturen, ikke fra noen lagret skalert tilstand).
        at2 = self._kjor()
        self.assertEqual(len(at2.session_state["_debug_pantry"]["items"]), 5,
                          "Lageret skal være bevart på disk mellom separate økter")
        self.assertEqual(
            {m["id"] for m in at2.session_state["_debug_ctx_recipe"]["malts"]},
            {"weyermann_munich_1", "munich_ii", "vienna"},
            "Oppskriften skal fortsatt være den uendrede Wiesn-fixturen i en ny økt",
        )


class TestEktAppPyRenderingSkriverIkkeTilRealPantry(unittest.TestCase):
    """
    Regresjonstest for et konkret hendelsesforløp oppdaget under utviklingen
    av dette panelet: å koble render_pantry_panel() inn i app.py betyr at
    ALLE andre, allerede eksisterende tester som rendrer den EKTE app.py via
    AppTest (f.eks. tests/test_water_target_ui_integration.py,
    tests/test_real_app_process_flow.py) nå OGSÅ render Pantry-panelet —
    uten selv å vite om eller sette KVERNHAUG_PANTRY_DIR, siden de ble
    skrevet før Pantry eksisterte.

    modules.pantry.last_pantry() opprettet tidligere filen på disk som en
    sideeffekt av bare å LESE (samme mønster som ble luket ut andre steder
    i dette repoet flere ganger før) — det gjorde at en helt vanlig
    apptest-kjøring stille skrev til den EKTE data/pantry.json. Fikset ved
    at last_pantry() nå kun returnerer en tom struktur i minnet når filen
    mangler, og aldri skriver noe selv (se modules/pantry.py sin egen
    docstring og tests/test_pantry.py sin
    test_last_pantry_skriver_ikke_til_disk_ved_en_ren_lesing).

    Denne testen kjører den VIRKELIGE, uendrede app.py — bevisst UTEN å
    sette KVERNHAUG_PANTRY_DIR — nøyaktig slik en "uvitende" eldre test
    gjør det, og bekrefter at den ekte data/pantry.json fortsatt ikke
    finnes etterpå. Er kun trygt å kjøre mot den ekte repo-stien fordi
    fiksen over garanterer at en ren rendring aldri skriver noe."""

    @staticmethod
    def _snapshot(mappe):
        # Samme mønster som tests/test_recipe_storage_isolation.py sin
        # _snapshot(): må fungere BÅDE i en fersk worktree (recipes/ finnes
        # ikke i det hele tatt ennå) OG i et vanlig utviklingsmiljø (der
        # recipes/ allerede legitimt finnes, fullt av brukerens ekte,
        # lagrede oppskrifter) — derfor sammenlignes INNHOLD før/etter,
        # ikke bare eksistens.
        if not os.path.isdir(mappe):
            return frozenset()
        return frozenset(os.listdir(mappe))

    def test_render_av_ekte_app_py_uten_pantry_dir_satt_skriver_ingenting(self):
        from streamlit.testing.v1 import AppTest

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_py = os.path.join(repo_root, "app.py")
        ekte_pantry_fil = os.path.join(repo_root, "data", "pantry.json")
        ekte_recipes_mappe = os.path.join(repo_root, "recipes")

        # KVERNHAUG_RECIPES_DIR isoleres HER (samme mønster som
        # tests/test_water_target_ui_integration.py) fordi app.py sin
        # render_sidebar() ubetinget kaller hent_alle_oppskrifter() —
        # uten isolasjon ville DENNE testen selv skrevet til/opprettet den
        # ekte recipes/-mappen som en sideeffekt, uavhengig av Pantry.
        # KVERNHAUG_PANTRY_DIR settes bevisst IKKE — det er nøyaktig
        # variabelen denne testen skal bekrefte er trygg å glemme.
        gammel_pantry_env = os.environ.pop("KVERNHAUG_PANTRY_DIR", None)
        gammel_recipes_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        tmp_recipes = tempfile.TemporaryDirectory()
        os.environ["KVERNHAUG_RECIPES_DIR"] = tmp_recipes.name
        recipes_snapshot_for = self._snapshot(ekte_recipes_mappe)
        try:
            self.assertFalse(
                os.path.exists(ekte_pantry_fil),
                "Testforutsetning: ekte data/pantry.json skal ikke finnes før denne testen kjører",
            )
            at = AppTest.from_file(app_py)
            at.run()
            self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")
            self.assertFalse(
                os.path.exists(ekte_pantry_fil),
                "En vanlig rendring av app.py (uten KVERNHAUG_PANTRY_DIR) skrev til den EKTE "
                "data/pantry.json — se modules.pantry.last_pantry()",
            )
            self.assertEqual(
                self._snapshot(ekte_recipes_mappe), recipes_snapshot_for,
                "Den ekte recipes/-mappen skal være helt uendret (isolert via KVERNHAUG_RECIPES_DIR)",
            )
        finally:
            if gammel_pantry_env is not None:
                os.environ["KVERNHAUG_PANTRY_DIR"] = gammel_pantry_env
            if gammel_recipes_env is None:
                os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
            else:
                os.environ["KVERNHAUG_RECIPES_DIR"] = gammel_recipes_env
            tmp_recipes.cleanup()
            if os.path.exists(ekte_pantry_fil):
                os.remove(ekte_pantry_fil)


if __name__ == "__main__":
    unittest.main()
