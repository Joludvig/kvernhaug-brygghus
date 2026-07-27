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
import json
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


def _antall_backupfiler(mappe):
    return len([f for f in os.listdir(mappe) if ".backup_" in f])


class TestPantryBackupOgGjenopprettingIUI(_PantryAppTestCase):
    """UI-flyt for automatisk backup + «Gjenopprett fra backup»: hurtig-
    justering (+/-/sett i rediger-panelet) skal utløse en automatisk
    backup akkurat som oppdatering/sletting/import gjør det på
    motornivå (se tests/test_pantry.py::Test28PantryBackupOgGjenoppretting),
    og gjenoppretting skal ALDRI skje uten eksplisitt bekreftelse+klikk."""

    def test_hurtigjustering_lager_automatisk_backup(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        item_id = at.session_state["_debug_pantry"]["items"][0]["pantry_item_id"]
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 0, "Første lagring skal ikke ha laget noen backup ennå")

        at.button(key=f"pantry_rediger_{item_id}").click().run()
        at.number_input(key=f"pantry_juster_delta_{item_id}").set_value(0.5).run()
        at.button(key=f"pantry_pluss_{item_id}").click().run()

        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 1,
                          "Hurtigjustering (+/-/sett) skal utløse en automatisk backup av forrige tilstand")

    def test_gjenopprett_knapp_er_deaktivert_uten_bekreftelse(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        item_id = at.session_state["_debug_pantry"]["items"][0]["pantry_item_id"]
        at.button(key=f"pantry_rediger_{item_id}").click().run()
        at.number_input(key=f"pantry_rediger_mengde_{item_id}").set_value(9.0).run()
        at.button(key=f"pantry_sett_{item_id}").click().run()
        # Én backup finnes nå (tilstanden med 1.0 kg, fra FØR denne endringen).

        knapp = at.button(key="pantry_backup_gjenopprett_btn")
        self.assertTrue(knapp.disabled, "Gjenopprett-knappen skal være deaktivert før eksplisitt bekreftelse")
        self.assertEqual(at.session_state["_debug_pantry"]["items"][0]["quantity"], 9.0,
                          "Lageret skal fortsatt vise den nye mengden -- ingenting gjenopprettet uten klikk")

    def test_gjenopprett_med_bekreftelse_gjenoppretter_faktisk(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        item_id = at.session_state["_debug_pantry"]["items"][0]["pantry_item_id"]
        at.button(key=f"pantry_rediger_{item_id}").click().run()
        at.number_input(key=f"pantry_rediger_mengde_{item_id}").set_value(9.0).run()
        at.button(key=f"pantry_sett_{item_id}").click().run()
        # Backup-innholdet er tilstanden med 1.0 kg (FØR denne endringen).

        at.checkbox(key="pantry_backup_bekreft").set_value(True).run()
        at.button(key="pantry_backup_gjenopprett_btn").click().run()

        gjenopprettet_items = at.session_state["_debug_pantry"]["items"]
        self.assertEqual(len(gjenopprettet_items), 1)
        self.assertEqual(gjenopprettet_items[0]["quantity"], 1.0,
                          "Lageret skal nå vise den gjenopprettede (tidligere) mengden, ikke 9.0")

    def test_gjenoppretting_tar_selv_en_ny_backup(self):
        at = self._kjor()
        self._legg_til_vare(at, "Malt", "weyermann_munich_1", 1.0, "kg")
        item_id = at.session_state["_debug_pantry"]["items"][0]["pantry_item_id"]
        at.button(key=f"pantry_rediger_{item_id}").click().run()
        at.number_input(key=f"pantry_rediger_mengde_{item_id}").set_value(9.0).run()
        at.button(key=f"pantry_sett_{item_id}").click().run()
        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 1)

        at.checkbox(key="pantry_backup_bekreft").set_value(True).run()
        at.button(key="pantry_backup_gjenopprett_btn").click().run()

        self.assertEqual(_antall_backupfiler(self._tmpdir.name), 2,
                          "Selve gjenopprettingen er en lagring og skal derfor selv utløse en ny backup")


_SENTINEL_PANTRY = {
    "schema_version": 1,
    "updated_at": "2026-01-01T00:00:00",
    "items": [
        {
            "pantry_item_id": "11111111-1111-1111-1111-111111111111",
            "ingredient_type": "malt",
            "ingredient_id": "sentinel_malt_ikke_rediger",
            "name_snapshot": "SENTINEL -- skal IKKE endres av denne testen",
            "quantity": 42.0,
            "unit": "kg",
            "base_quantity": 42000.0,
            "base_unit": "g",
            "opened": False,
            "best_before": None,
            "lot_number": "",
            "storage_location": "",
            "notes": "",
            "is_custom": False,
        }
    ],
}
_SENTINEL_JSON = json.dumps(_SENTINEL_PANTRY, ensure_ascii=False, indent=2)


class TestEktAppPyRenderingPaavirkerIkkeEksisterendePantry(unittest.TestCase):
    """
    Regresjonstest for at en vanlig rendring av den EKTE, uendrede app.py
    (samme fil som start_app.bat starter) aldri endrer en allerede
    eksisterende pantry.json.

    SIKKERHETSHISTORIKK (2026-07-27): en tidligere versjon av denne testen
    pekte direkte på REPOETS EKTE data/pantry.json (bevisst uten å sette
    KVERNHAUG_PANTRY_DIR, for å teste at det er trygt å glemme den) og
    slettet den ubetinget i en finally-blokk uansett utfall. Det viste seg
    IKKE trygt nok i praksis — se commit 72e6b77. Denne testen rører ALDRI
    lenger noen beregnet produksjonssti i det hele tatt:

      1. KVERNHAUG_PANTRY_DIR settes ALLTID til en fersk
         tempfile.TemporaryDirectory() (aldri utelatt).
      2. En kjent SENTINEL-pantry.json skrives inn i den midlertidige
         mappen FØR app.py kjøres.
      3. Den ekte, uendrede app.py kjøres via AppTest.
      4. Testen bekrefter at sentinel-filen er BYTE-FOR-BYTE identisk
         etterpå.
      5. Cleanup består UTELUKKENDE av at TemporaryDirectory() avsluttes
         (via `with`) — ingen os.remove() mot noen sti i det hele tatt,
         beregnet eller ikke.

    Denne testen leser, tester eksistensen av, oppretter og sletter ALDRI
    prosjektets virkelige data/pantry.json."""

    def test_render_av_ekte_app_py_endrer_ikke_sentinel_pantry(self):
        from streamlit.testing.v1 import AppTest

        with tempfile.TemporaryDirectory() as pantry_tmp, tempfile.TemporaryDirectory() as recipes_tmp:
            sentinel_fil = os.path.join(pantry_tmp, "pantry.json")
            with open(sentinel_fil, "w", encoding="utf-8") as f:
                f.write(_SENTINEL_JSON)

            gammel_pantry_env = os.environ.get("KVERNHAUG_PANTRY_DIR")
            gammel_recipes_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
            os.environ["KVERNHAUG_PANTRY_DIR"] = pantry_tmp
            os.environ["KVERNHAUG_RECIPES_DIR"] = recipes_tmp
            try:
                repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                app_py = os.path.join(repo_root, "app.py")

                at = AppTest.from_file(app_py)
                at.run()
                self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

                with open(sentinel_fil, encoding="utf-8") as f:
                    innhold_etter = f.read()
                self.assertEqual(
                    innhold_etter, _SENTINEL_JSON,
                    "En vanlig rendring av app.py skal la en eksisterende pantry.json stå "
                    "byte-for-byte uendret",
                )
            finally:
                if gammel_pantry_env is None:
                    os.environ.pop("KVERNHAUG_PANTRY_DIR", None)
                else:
                    os.environ["KVERNHAUG_PANTRY_DIR"] = gammel_pantry_env
                if gammel_recipes_env is None:
                    os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
                else:
                    os.environ["KVERNHAUG_RECIPES_DIR"] = gammel_recipes_env
        # `with`-blokken over har allerede ryddet opp begge midlertidige
        # mapper (TemporaryDirectory.__exit__) -- ingen manuell filsletting.


if __name__ == "__main__":
    unittest.main()
