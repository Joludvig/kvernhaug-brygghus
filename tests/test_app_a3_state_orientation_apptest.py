"""
App A3 (issue #237) -- AppTest-basert regresjonstest for de fire
orienteringsfiksene fra docs/development/app_a3_state_orientation_
preflight.md Section 11/12, alle bygget på TOPPEN av det allerede
etablerte, uendrede App A1-mønsteret (issue #170 "Identity safety",
tests/test_brewday_a1_measurement_apptest.py) -- ingen nytt state-
maskineri, ingen ny identitetspeker.

Dekker:
  A3-1: modules/recipe_importer.py::apply_import_to_session_state()
        rydder nå _last_loaded_recipe/_last_loaded_recipe_file, akkurat
        som modules/kbh_import_apply.py allerede gjør for
        .kbhrecipe-import -- via den EKTE "Importer oppskrift fra
        tekst"-UI-en i ui/sidebar.py (tests/fixtures/streamlit_harness/
        brewday_a3_import_harness.py), IKKE den syntetiske
        KVERNHAUG_TEST_RECIPE_ID-harnessen A1-suiten bruker for sin
        egen test_4 (se preflightens Section 14, punkt 1).
  A3-2: den tidligere "✅ Aktivt brygg denne økten"-teksten (ui/
        kbhbrew_panel.py) skiller nå eksplisitt mellom denne øktens
        Bryggdag-skrivemål og brygget sin egen lagrede status.
  A3-3: "💾 Lagre målinger"-seksjonen (ui/brewday_panel.py) viser en
        synlig advarsel FØR lagre-klikket når målbrygget ikke lenger
        har lagret status "active" -- for BÅDE done og discarded, men
        ALDRI for active, og knappen forblir aktivert (ingen autosave,
        eksplisitt klikk kreves fortsatt).
  A3-4: en navneendrende "💾 Lagre endringer" (ui/recipe_card.py)
        trigger nå en umiddelbar st.rerun(), slik at et evt. aktivt
        brygg sin ugyldiggjøring blir synlig i SAMME interaksjon --
        mens en navneUENDRET lagring fortsatt IKKE trigger noen ekstra
        rerun-oppførsel.

Kjøres med:
    py -3 -m unittest tests.test_app_a3_state_orientation_apptest -v
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")
_IMPORT_HARNESS = os.path.join(
    _REPO_ROOT, "tests", "fixtures", "streamlit_harness", "brewday_a3_import_harness.py",
)
_A1_HARNESS = os.path.join(_REPO_ROOT, "tests", "_brewday_a1_measurement_app.py")

_GYLDIG_EQUIPMENT = {
    "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (se tests/test_kbh_import_ui_apptest.py)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


class _MedIsolertEquipmentOgRecipes(unittest.TestCase):
    """Felles isolasjon (aldri ekte data/equipment.json eller recipes/) --
    speiler tests/test_brewday_a1_measurement_apptest.py/
    tests/test_kbhbrew_create_panel_apptest.py sitt eget setUp-mønster."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        # Egen undermappe, ALDRI KVERNHAUG_RECIPES_DIR sin rot -- render_sidebar()
        # (kjørt av noen av testene i denne filen, i motsetning til A1-suiten sin
        # egen minimale harness) lister hele oppskrift-mapperoten, og
        # equipment.json ville ellers blitt logget som en ugyldig/hoppet-over
        # "oppskriftsfil" (harmløst, men unødvendig støy -- se
        # modules/recipe_storage.py::hent_alle_oppskrifter()).
        _equip_dir = os.path.join(self._tmpdir.name, "_equip")
        os.makedirs(_equip_dir, exist_ok=True)
        self._equipment_file = os.path.join(_equip_dir, "equipment.json")
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            json.dump(_GYLDIG_EQUIPMENT, f)
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._equipment_file

        self._gammel_recipe_id = os.environ.pop("KVERNHAUG_TEST_RECIPE_ID", None)

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        if self._gammel_equipment_file is None:
            os.environ.pop("KVERNHAUG_EQUIPMENT_FILE", None)
        else:
            os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._gammel_equipment_file
        if self._gammel_recipe_id is None:
            os.environ.pop("KVERNHAUG_TEST_RECIPE_ID", None)
        else:
            os.environ["KVERNHAUG_TEST_RECIPE_ID"] = self._gammel_recipe_id
        self._tmpdir.cleanup()


# ═══════════════════════════════════════════════════════════════════
# A3-1/A3-3-del1: EKTE tekstimport rydder identitet og ugyldiggjør det
# gamle aktive brygget -- via den kombinerte sidebar+brewday-harnessen.
# ═══════════════════════════════════════════════════════════════════

class TestA31TekstimportRydderIdentitet(_MedIsolertEquipmentOgRecipes):
    def _ny_apptest(self):
        at = AppTest.from_file(_IMPORT_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _klikk_start_nytt_brygg(self, at):
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        self.assertEqual(len(knapper), 1, "Fant ikke akkurat én 'Start nytt brygg'-knapp")
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter klikk: {at.exception}")

    def _importer_tekst(self, at, tekst):
        at.sidebar.text_area(key="import_tekst_input").set_value(tekst).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved tekstinnliming: {at.exception}")
        analyser = [b for b in at.sidebar.button if b.key == "import_analyser_btn"]
        self.assertEqual(len(analyser), 1)
        analyser[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved analyse: {at.exception}")
        bekreft = [b for b in at.sidebar.button if b.key == "import_bekreft_btn"]
        self.assertEqual(len(bekreft), 1, "Fant ikke 'Importer oppskrift'-knappen -- ingen treff i analysen?")
        bekreft[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved import-bekreft: {at.exception}")

    # ─── 1: tekstimport rydder gammel oppskriftsidentitet ──────────────

    def test_1_tekstimport_rydder_gammel_lastet_identitet(self):
        at = self._ny_apptest()
        at.session_state["_last_loaded_recipe"] = "En Gammel Lagret Oppskrift"
        at.session_state["_last_loaded_recipe_file"] = "en_gammel_lagret_oppskrift.json"
        at.run()

        self._importer_tekst(at, "5 kg Bohemian Pilsner Floor")

        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))

    # ─── 2/3: gammelt aktivt brygg ugyldiggjøres, Steg 4/5 tømmes ──────

    def test_2_gammelt_aktivt_brygg_ugyldiggjores_etter_tekstimport(self):
        at = self._ny_apptest()
        at.session_state["_last_loaded_recipe_file"] = "recipe_a.json"
        at.run()

        self._klikk_start_nytt_brygg(at)
        gammel_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(gammel_brew_id)
        gammelt_brew = kbhbrew_storage.hent_brew(gammel_brew_id)
        self.assertEqual(gammelt_brew["recipeId"], "recipe_a.json")

        at.text_input(key="bd_og").set_value("1.055").run()

        self._importer_tekst(at, "5 kg Bohemian Pilsner Floor")

        # ─── 3: det ugyldiggjorte aktive målet tar Steg 4/5 sine
        # ulagrede tallfelt med seg -- ALDRI stille bundet videre til det
        # gamle brygget.
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        self.assertEqual(at.text_input(key="bd_og").value, "")
        lagre_knapp = [b for b in at.button if b.key == "bd_lagre_maalinger_btn"][0]
        self.assertTrue(lagre_knapp.disabled)

        # Det opprinnelige brygget selv er uendret -- aldri rørt av importen.
        gammelt_brew_etter = kbhbrew_storage.hent_brew(gammel_brew_id)
        self.assertEqual(gammelt_brew_etter["actuals"], {})
        self.assertEqual(gammelt_brew_etter["recipeId"], "recipe_a.json")


# ═══════════════════════════════════════════════════════════════════
# A3-2: skrivemål-tekst skiller "denne øktens mål" fra lagret status.
# ═══════════════════════════════════════════════════════════════════

class TestA32SkrivemaalTekstSkillerFraStatus(_MedIsolertEquipmentOgRecipes):
    def test_4_skrivemaal_teksten_pastar_ikke_lagret_status_aktiv(self):
        os.environ["KVERNHAUG_TEST_RECIPE_ID"] = "recipeA.json"
        at = AppTest.from_file(_A1_HARNESS)
        at.run()
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        knapper[0].click().run()
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)

        kbhbrew_storage.oppdater_brew_lag(brew_id, status="done")
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        suksessmeldinger = [e.value for e in at.success]
        treff = [m for m in suksessmeldinger if brew_id in m]
        self.assertEqual(len(treff), 1, f"Fant ikke skrivemål-meldingen: {suksessmeldinger}")
        melding = treff[0]

        # Den nye teksten skal fortelle at DETTE er skrivemålet, og vise
        # den lagrede statusen (Ferdig) SEPARAT -- aldri fremstille et
        # Ferdig-brygg som om det har lagret status "Aktiv".
        self.assertIn("skriver til", melding)
        self.assertIn("Ferdig", melding)
        self.assertNotIn("Aktivt brygg denne økten", melding)


# ═══════════════════════════════════════════════════════════════════
# A3-3: advarsel før lagring til et ikke-aktivt historisk mål.
# ═══════════════════════════════════════════════════════════════════

class TestA33AdvarselFoerLagringTilHistoriskMaal(_MedIsolertEquipmentOgRecipes):
    def _apptest_med_brew(self, status=None):
        os.environ["KVERNHAUG_TEST_RECIPE_ID"] = "recipeA.json"
        at = AppTest.from_file(_A1_HARNESS)
        at.run()
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        knapper[0].click().run()
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)
        if status is not None:
            kbhbrew_storage.oppdater_brew_lag(brew_id, status=status)
            at.run()
            self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")
        return at, brew_id

    def _lagre_knapp(self, at):
        return [b for b in at.button if b.key == "bd_lagre_maalinger_btn"][0]

    # ─── 5: done-status viser advarsel ──────────────────────────────────

    def test_5_done_status_viser_advarsel(self):
        at, brew_id = self._apptest_med_brew(status="done")
        advarsler = [w.value for w in at.warning]
        self.assertTrue(any("Ferdig" in w for w in advarsler), f"Ingen advarsel funnet: {advarsler}")
        # Eksplisitt klikk kreves fortsatt -- knappen skal IKKE deaktiveres.
        self.assertFalse(self._lagre_knapp(at).disabled)

    # ─── 6: discarded-status viser advarsel ─────────────────────────────

    def test_6_discarded_status_viser_advarsel(self):
        at, brew_id = self._apptest_med_brew(status="discarded")
        advarsler = [w.value for w in at.warning]
        self.assertTrue(any("Forkastet" in w for w in advarsler), f"Ingen advarsel funnet: {advarsler}")
        self.assertFalse(self._lagre_knapp(at).disabled)

    # ─── 7: active-status viser IKKE den historiske advarselen ──────────

    def test_7_active_status_viser_ikke_advarsel(self):
        at, brew_id = self._apptest_med_brew(status=None)
        self.assertEqual(_ss(at, "_aktiv_kbhbrew_brew_id"), brew_id)
        advarsler = [w.value for w in at.warning]
        self.assertEqual(advarsler, [], f"Uventet advarsel for et aktivt brygg: {advarsler}")

    # ─── 8: Brygghistorikkens eksplisitte utvalg retargetterer fortsatt
    # Bryggdag (App A1 -- uendret), OG advarselen følger med målet ──────

    def test_8_historikkvalg_retargetterer_og_advarsel_folger_med(self):
        os.environ["KVERNHAUG_TEST_RECIPE_ID"] = "recipeA.json"
        at = AppTest.from_file(_A1_HARNESS)
        at.run()
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        knapper[0].click().run()
        ferdig_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        kbhbrew_storage.oppdater_brew_lag(ferdig_brew_id, status="done")

        knapper[0].click().run()
        aktivt_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertNotEqual(ferdig_brew_id, aktivt_brew_id)
        # Nyopprettet brygg er aktivt -- ingen advarsel ennå.
        self.assertEqual([w.value for w in at.warning], [])

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(ferdig_brew_id).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved historikk-valg: {at.exception}")

        # A1 (uendret): Brygghistorikkens eksplisitte valg retargetterer
        # fortsatt Bryggdag sitt skrivemål.
        self.assertEqual(_ss(at, "_aktiv_kbhbrew_brew_id"), ferdig_brew_id)
        # A3-3 (nytt): og målet er nå Ferdig, så advarselen vises.
        advarsler = [w.value for w in at.warning]
        self.assertTrue(any("Ferdig" in w for w in advarsler), f"Ingen advarsel funnet: {advarsler}")


# ═══════════════════════════════════════════════════════════════════
# A3-4: umiddelbar rerun/orientering etter navneendrende "Lagre
# endringer" -- via den EKTE app.py (recipe_card.py + brewday_panel.py
# sammen), speiler tests/test_recipe_delete_ui_integration.py sitt
# "ekte app.py, isolert recipes-mappe"-mønster.
# ═══════════════════════════════════════════════════════════════════

class TestA34UmiddelbarOrienteringEtterNavneendring(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        _equip_dir = os.path.join(self._tmpdir.name, "_equip")
        os.makedirs(_equip_dir, exist_ok=True)
        self._equipment_file = os.path.join(_equip_dir, "equipment.json")
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            json.dump(_GYLDIG_EQUIPMENT, f)
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._equipment_file

        import modules.recipe_storage as recipe_storage
        recipe = bygg_recipe_object(
            "E2E A3 Rename", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        if self._gammel_equipment_file is None:
            os.environ.pop("KVERNHAUG_EQUIPMENT_FILE", None)
        else:
            os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._gammel_equipment_file
        self._tmpdir.cleanup()

    # ─── 9: navneendring + lagring -> umiddelbar ugyldiggjøring ────────

    def test_9_navneendring_og_lagring_ugyldiggjor_aktivt_brygg_umiddelbart(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E A3 Rename").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), "e2e_a3_rename.json")

        at.button(key="kbhbrew_start_ny_brew_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved brygg-opprettelse: {at.exception}")
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)
        self.assertEqual(kbhbrew_storage.hent_brew(brew_id)["recipeId"], "e2e_a3_rename.json")

        at.text_input(key="gjeldende_navn").set_value("E2E A3 Rename Omdopt").run()
        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lagring: {at.exception}")

        # Identiteten er byttet ...
        nytt_filnavn = _ss(at, "_last_loaded_recipe_file")
        self.assertNotEqual(nytt_filnavn, "e2e_a3_rename.json")
        # ... og det gamle aktive brygget er ALLEREDE ugyldiggjort i SAMME
        # interaksjon -- ikke først synlig etter en senere, urelatert rerun.
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))

        # Selve brygget (frosset snapshot/recipeId) er uendret.
        uendret_brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(uendret_brew["recipeId"], "e2e_a3_rename.json")

    # ─── 10: uendret navn -> ingen unødvendig ekstra rerun-oppførsel ───

    def test_10_uendret_navn_lagring_beholder_forventet_oppforsel(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E A3 Rename").run()
        self.assertFalse(at.exception)

        at.button(key="kbhbrew_start_ny_brew_btn").click().run()
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)

        # Ingen navneendring -- kun et vanlig "Lagre endringer"-klikk.
        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lagring: {at.exception}")

        # Identiteten (filnavn) er UENDRET, og det aktive brygget forblir
        # gyldig -- samme oppførsel som FØR A3-4-fiksen.
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), "e2e_a3_rename.json")
        self.assertEqual(_ss(at, "_aktiv_kbhbrew_brew_id"), brew_id)


if __name__ == "__main__":
    unittest.main()
