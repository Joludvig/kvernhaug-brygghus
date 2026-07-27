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

    def _legg_til_egendefinert_vare(self, at, ingredient_type_visning, navn, mengde, enhet):
        at.selectbox(key="pantry_ny_type").set_value(ingredient_type_visning).run()
        at.selectbox(key="pantry_ny_ingrediens").set_value("__egendefinert__").run()
        at.text_input(key="pantry_ny_egendefinert_navn").set_value(navn).run()
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

    @staticmethod
    def _rad(at, ingredient_type, ingredient_id):
        return next(
            r for r in at.session_state["_debug_mangler_rader"]
            if r["ingredient_type"] == ingredient_type and r["ingredient_id"] == ingredient_id
        )

    def test_full_flow(self):
        at = self._kjor()

        # Wiesn-fixturen: weyermann_munich_1 (Munich I) 0.7 kg, munich_ii
        # (Munich II) 4.6 kg, vienna (Vienna) 1.8 kg, tettnang 88 g,
        # saflager_w3470 (W-34/70).
        recipe = at.session_state["_debug_ctx_recipe"]
        malt_ider = {m["id"] for m in recipe["malts"]}
        self.assertEqual(malt_ider, {"weyermann_munich_1", "munich_ii", "vienna"})
        self.assertEqual(recipe["yeast"], "saflager_w3470")
        self.assertEqual({h["id"] for h in recipe["hops"]}, {"tettnang"})

        original_recipe = copy.deepcopy(recipe)
        original_prosess = copy.deepcopy(at.session_state["aktiv_prosessprofil"])
        original_vann = copy.deepcopy(at.session_state["aktiv_vannmaal_snapshot"])

        # 1) Legg inn Munich I, Munich II, Vienna, Tettnang og W-34/70,
        # rikelig av hver -> alt skal vise "nok". Wiesn-fixturen ved 20 L og
        # denne OG-en krever 3 pakker W-34/70 (samme pitch-rate-formel som
        # bryggedagsarket, se modules/brewday_calc.beregn_pakker) -- 3
        # pakker på lager skal derfor gi "nok", ikke en gjettet mangel.
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        self._legg_til_vare(at, "Malt", "munich_ii", 5.0, "kg")
        self._legg_til_vare(at, "Malt", "vienna", 2.0, "kg")
        self._legg_til_vare(at, "Humle", "tettnang", 100.0, "g")
        self._legg_til_vare(at, "Gjær", "saflager_w3470", 3.0, "pakke")

        self.assertEqual(len(at.session_state["_debug_pantry"]["items"]), 5)

        # 2) Eksplisitt "nok" for HVER navngitte ingrediens (ikke bare
        # fravær av feil-melding samlet sett) -- inkludert gjær, som FØR
        # denne fiksen alltid ble vist som "må kontrolleres manuelt" selv
        # når bryggedagsarket allerede hadde et kjent anbefalt pakkeantall.
        for ingredient_type, ingredient_id in [
            ("malt", "weyermann_munich_1"), ("malt", "munich_ii"), ("malt", "vienna"), ("humle", "tettnang"),
        ]:
            rad = self._rad(at, ingredient_type, ingredient_id)
            self.assertEqual(rad["status"], "nok", f"{ingredient_id} skulle vist 'nok', fikk {rad}")

        gjaer_rad = self._rad(at, "gjaer", "saflager_w3470")
        self.assertEqual(gjaer_rad["required_base"], 3.0, "W-34/70-behovet skal beregnes fra samme formel som bryggedagsarket")
        self.assertEqual(gjaer_rad["available_base"], 3.0)
        self.assertEqual(gjaer_rad["status"], "nok")
        self.assertEqual(len(at.error), 0, "Malt, humle og gjær skulle dekke behovet -- ingen mangel-feil forventet")

        # 3) Reduser Tettnang under behovet (88 g) -> status blir "mangler".
        tettnang_item = next(
            i for i in at.session_state["_debug_pantry"]["items"] if i["ingredient_id"] == "tettnang"
        )
        tettnang_id = tettnang_item["pantry_item_id"]
        at.button(key=f"pantry_rediger_{tettnang_id}").click().run()
        at.number_input(key=f"pantry_rediger_mengde_{tettnang_id}").set_value(10.0).run()
        at.button(key=f"pantry_sett_{tettnang_id}").click().run()

        tettnang_rad = self._rad(at, "humle", "tettnang")
        self.assertEqual(tettnang_rad["status"], "mangler", f"Forventet 'mangler' etter reduksjon, fikk {tettnang_rad}")
        self.assertEqual(tettnang_rad["available_base"], 10.0)
        self.assertAlmostEqual(tettnang_rad["missing_base"], 78.0, places=2)
        self.assertGreater(len(at.error), 0, "Skal nå vise en mangel-feil for Tettnang")

        # 4) Skaler oppskriften til det dobbelte -- alt behov dobles,
        # inkludert det allerede manglende Tettnang-behovet.
        at.number_input(key="skaler_maal_volum").set_value(40.0).run()
        at.button(key="skaler_btn").click().run()

        skalert_recipe = at.session_state["_debug_ctx_recipe"]
        skalert_malt = {m["id"]: m["mengde"] for m in skalert_recipe["malts"]}
        self.assertAlmostEqual(skalert_malt["munich_ii"], 9.2, places=2,
                                msg="Skalering til dobbel batch skal doble malt-mengden")

        skalert_tettnang_rad = self._rad(at, "humle", "tettnang")
        self.assertEqual(skalert_tettnang_rad["required_base"], 176.0, "Tettnang-behovet skal også dobles (88 -> 176 g)")
        self.assertGreater(
            skalert_tettnang_rad["missing_base"], tettnang_rad["missing_base"],
            "Mangelen på Tettnang skal øke etter skalering, ikke bli stående på det gamle tallet",
        )
        self.assertEqual(skalert_tettnang_rad["status"], "mangler")

        # Gjærbehovet skal også oppdateres LIVE ved skalering (samme
        # pitch-rate-formel regnet på nytt med doblet batchvolum) -- 3
        # pakker på lager dekker ikke lenger det doblede behovet.
        skalert_gjaer_rad = self._rad(at, "gjaer", "saflager_w3470")
        self.assertEqual(skalert_gjaer_rad["required_base"], 6.0, "Gjærbehovet skal dobles ved dobling av batchvolum")
        self.assertEqual(skalert_gjaer_rad["available_base"], 3.0)
        self.assertEqual(skalert_gjaer_rad["status"], "mangler")

        skalert_munich_ii_rad = self._rad(at, "malt", "munich_ii")
        self.assertEqual(
            skalert_munich_ii_rad["status"], "mangler",
            "5 kg Munich II på lager dekker ikke lenger det doblede behovet på 9.2 kg",
        )
        self.assertGreater(len(at.error), 0, "Etter skalering skal minst én mangel-feil fortsatt vises")

        # 5) Prosessprofilen og vannkjemien skal være urørt av ALLE
        # Pantry-handlingene over (legg til, rediger) OG av skaleringen i
        # steg 4 (recipe_card sin egen handling, ikke Pantry sin) — kun
        # malt/humle-mengder og batchvolum skal ha endret seg, jf. steg 4
        # sin bekreftelse på at Tettnang-behovet faktisk doblet seg der.
        self.assertEqual(original_recipe["yeast"], skalert_recipe["yeast"])
        self.assertEqual(at.session_state["aktiv_prosessprofil"], original_prosess,
                          "Pantry-handlinger (og skalering) skal aldri røre prosessprofilen")
        self.assertEqual(at.session_state["aktiv_vannmaal_snapshot"], original_vann,
                          "Pantry-handlinger (og skalering) skal aldri røre vannkjemi-snapshotten")

        # 6) Ny sesjon: lageret (5 poster, med redusert Tettnang) er
        # bevart på disk. Oppskriften i DEN NYE sesjonen er den uendrede
        # fixture-oppskriften (testverten seedes på nytt fra fixturen for
        # hver økt, ikke fra noen lagret skalert tilstand) -- selve
        # skaleringen var kun en in-session brukerhandling.
        at2 = self._kjor()
        self.assertEqual(len(at2.session_state["_debug_pantry"]["items"]), 5,
                          "Lageret skal være bevart på disk mellom separate økter")
        tettnang_etter_ny_sesjon = next(
            i for i in at2.session_state["_debug_pantry"]["items"] if i["ingredient_id"] == "tettnang"
        )
        self.assertEqual(tettnang_etter_ny_sesjon["quantity"], 10.0,
                         "Den reduserte Tettnang-mengden skal også være bevart i den nye sesjonen")
        self.assertEqual(
            {m["id"] for m in at2.session_state["_debug_ctx_recipe"]["malts"]},
            {"weyermann_munich_1", "munich_ii", "vienna"},
            "Oppskriften skal fortsatt være den uendrede Wiesn-fixturen i en ny økt",
        )
        self.assertEqual(at2.session_state["_debug_ctx_recipe"], original_recipe,
                         "Oppskriften i en ny økt skal være byte-for-byte den samme fixture-oppskriften")


class TestEgendefinertIngrediensIUI(_PantryAppTestCase):
    """UI-flyt for «Egendefinert ingrediens»: valget vises i selectboxen,
    krever navn, får en custom_-ID, markeres tydelig i lagerlisten, og
    påvirker aldri oppskriftskontrollen (Krav: ingen automatisk match)."""

    def test_egendefinert_valg_finnes_i_ingrediens_selectboxen(self):
        at = self._kjor()
        at.selectbox(key="pantry_ny_type").set_value("Malt").run()
        # .options gir de FORMATTERTE visningstekstene (format_func), ikke
        # de rå master-DB-nøklene -- selve valget settes via den rå
        # sentinelverdien (se _legg_til_egendefinert_vare).
        options = at.selectbox(key="pantry_ny_ingrediens").options
        self.assertTrue(any("Egendefinert" in o for o in options), f"Fant ikke egendefinert-valget i {options}")

    def test_knapp_er_deaktivert_uten_navn(self):
        at = self._kjor()
        at.selectbox(key="pantry_ny_type").set_value("Malt").run()
        at.selectbox(key="pantry_ny_ingrediens").set_value("__egendefinert__").run()
        self.assertTrue(at.button(key="pantry_legg_til_btn").disabled)

    def test_legg_til_egendefinert_malt_far_custom_id_og_er_merket(self):
        at = self._kjor()
        self._legg_til_egendefinert_vare(at, "Malt", "Restmalt fra forrige brygg", 2.0, "kg")

        items = at.session_state["_debug_pantry"]["items"]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["is_custom"])
        self.assertTrue(items[0]["ingredient_id"].startswith("custom_"))
        self.assertEqual(items[0]["name_snapshot"], "Restmalt fra forrige brygg")

    def test_egendefinert_vises_merket_i_lagerlisten(self):
        at = self._kjor()
        self._legg_til_egendefinert_vare(at, "Malt", "Restmalt fra forrige brygg", 2.0, "kg")
        # Lagerlisten skriver navnet (med badge) via st.write() i en kolonne --
        # AppTest eksponerer disse som .markdown-noder uansett kildewidget.
        alle_tekster = " ".join(w.value for w in at.markdown)
        self.assertIn("Restmalt fra forrige brygg", alle_tekster)
        self.assertIn("Egendefinert", alle_tekster)

    def test_egendefinert_ingrediens_teller_ikke_med_i_oppskriftskontroll(self):
        at = self._kjor()
        self._legg_til_egendefinert_vare(at, "Malt", "Spesialmalt uten ID", 50.0, "kg")

        rader = at.session_state["_debug_mangler_rader"]
        # Ingen av radene i oppskriftskontrollen (som alle stammer fra
        # OPPSKRIFTENS ingredienser, ikke lagerets) skal ha en custom_-ID --
        # den egendefinerte posten skal ikke ha "smittet over" på noen måte.
        self.assertFalse(any(str(r.get("ingredient_id", "")).startswith("custom_") for r in rader))

    def test_egendefinert_navn_kan_endres_uten_at_id_endres(self):
        at = self._kjor()
        self._legg_til_egendefinert_vare(at, "Gjær", "Gjenbruksgjær", 1.0, "pakke")
        item = at.session_state["_debug_pantry"]["items"][0]
        opprinnelig_id = item["ingredient_id"]
        item_id = item["pantry_item_id"]

        at.button(key=f"pantry_rediger_{item_id}").click().run()
        at.text_input(key=f"pantry_rediger_navn_{item_id}").set_value("Gjenbruksgjær (omdøpt)").run()
        at.button(key=f"pantry_lagre_endringer_{item_id}").click().run()

        oppdatert = at.session_state["_debug_pantry"]["items"][0]
        self.assertEqual(oppdatert["name_snapshot"], "Gjenbruksgjær (omdøpt)")
        self.assertEqual(oppdatert["ingredient_id"], opprinnelig_id)


class TestLalvinEc1118IGjaerdatabasen(_PantryAppTestCase):
    """Regresjonstest for at Lalvin EC-1118 (vin-/champagnegjær, se
    data/master_gjaer_v2.json) er registrert og kan legges i lageret som en
    helt vanlig gjærpost -- IKKE som en egendefinert ingrediens, siden den nå
    finnes i masterdatabasen."""

    def test_registrer_ec1118_to_pakker(self):
        at = self._kjor()
        self._legg_til_vare(at, "Gjær", "lalvin_ec1118", 2.0, "pakke")

        items = at.session_state["_debug_pantry"]["items"]
        self.assertEqual(len(items), 1)
        item = items[0]
        self.assertEqual(item["ingredient_id"], "lalvin_ec1118")
        self.assertEqual(item["ingredient_type"], "gjaer")
        self.assertEqual(item["quantity"], 2.0)
        self.assertEqual(item["unit"], "pakke")
        self.assertEqual(item["base_quantity"], 2.0)
        self.assertFalse(item["is_custom"], "EC-1118 er en ekte masterdatabase-gjær, ikke egendefinert")
        self.assertEqual(item["name_snapshot"], "Lalvin EC-1118")


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
