"""
App A1 (issue #170) -- AppTest-basert regresjonstest for App A1 sin
Steg 4/5-målingsbinding til DET AKTIVE `.kbhbrew`-brygget, via
tests/_brewday_a1_measurement_app.py (ekte widget-interaksjon:
knappeklikk + faktisk gjenrendring, samme prinsipp som
tests/test_kbhbrew_create_panel_apptest.py/
tests/test_kbhbrew_history_panel_apptest.py).

Dekker preflight-testplanen (docs/development/
app_a1_active_brew_measurement_preflight.md Section 11) og issue #170
sin egen "Tests"-liste:
  1. typing uten lagre-klikk skriver ingenting;
  2. ett eksplisitt lagre-klikk skriver OG/FG/post-boil-volum/brewedAt
     til NØYAKTIG det aktive brygget;
  3. snapshot/id/origin/recipeId er uendret etter lagring;
  4. et oppskriftsbytte ugyldiggjør en tidligere bundet aktiv-brew-
     binding (og tømmer Steg 4/5 sine ulagrede tallfelt);
  5. et nytt brygg fra SAMME oppskrift kan ikke arve utypet, ulagret
     måling fra det forrige aktive brygget;
  6. legacy recipes/_logs/ forblir utilgjengelig/uberørt.

DEMO_MODE-no-op er allerede uavhengig garantert av
modules/kbhbrew_storage.py::oppdater_brew_lag() sin egen, testede guard
(tests/test_kbhbrew_storage_identity.py) -- denne filen bekrefter i
tillegg at selve lagre-knappen ikke engang rendres i DEMO_MODE (se
test_9_lagreseksjonen_skjules_i_demo_mode), via samme
subprocess-med-env-mønster som
tests/test_equipment_panel_terminology.py.

Kjøres med:
    python3 -m unittest tests.test_brewday_a1_measurement_apptest -b
"""
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "_brewday_a1_measurement_app.py")

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


class TestBrewdayA1MeasurementBinding(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        self._equipment_file = os.path.join(self._tmpdir.name, "equipment.json")
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

    def _ny_apptest(self, recipe_id=None):
        if recipe_id:
            os.environ["KVERNHAUG_TEST_RECIPE_ID"] = recipe_id
        else:
            os.environ.pop("KVERNHAUG_TEST_RECIPE_ID", None)
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _klikk_start_nytt_brygg(self, at):
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        self.assertEqual(len(knapper), 1, "Fant ikke akkurat én 'Start nytt brygg'-knapp")
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter klikk: {at.exception}")
        return at

    def _lagre_knapp(self, at):
        knapper = [b for b in at.button if b.key == "bd_lagre_maalinger_btn"]
        self.assertEqual(len(knapper), 1, "Fant ikke akkurat én lagre-målinger-knapp")
        return knapper[0]

    # ─── 1: typing uten lagre-klikk skriver ingenting ──────────────────

    def test_1_typing_uten_lagre_klikk_skriver_ingenting(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)

        at.text_input(key="bd_og").set_value("1.055").run()
        at.text_input(key="bd_fg").set_value("1.010").run()
        at.number_input(key="bd_post_boil_vol").set_value(19.5).run()

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["actuals"], {})

    # ─── 2/3: eksplisitt lagre-klikk skriver til NØYAKTIG aktivt brygg ─

    def test_2_lagre_klikk_skriver_og_fg_volum_brewedat_til_aktivt_brygg(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        brew_foer = kbhbrew_storage.hent_brew(brew_id)

        at.text_input(key="bd_og").set_value("1.055").run()
        at.text_input(key="bd_fg").set_value("1.010").run()
        at.number_input(key="bd_post_boil_vol").set_value(19.5).run()
        forventet_dato = at.date_input(key="bd_dato").value.isoformat()

        self._lagre_knapp(at).click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring: {at.exception}")

        brew_etter = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew_etter["actuals"]["og"], 1.055)
        self.assertEqual(brew_etter["actuals"]["fg"], 1.010)
        self.assertEqual(brew_etter["actuals"]["volumeL"], 19.5)
        self.assertEqual(brew_etter["brewedAt"], forventet_dato)

        # ─── 3: snapshot/id/origin/recipeId uendret ────────────────────
        self.assertEqual(brew_etter["brewId"], brew_foer["brewId"])
        self.assertEqual(brew_etter["originBrewId"], brew_foer["originBrewId"])
        self.assertEqual(brew_etter["recipeId"], brew_foer["recipeId"])
        self.assertEqual(brew_etter["snapshot"], brew_foer["snapshot"])

        suksessmeldinger = [e.value for e in at.success]
        self.assertTrue(any(brew_id in m for m in suksessmeldinger))

    def test_ugyldig_tall_blokkerer_hele_lagringen(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")

        at.text_input(key="bd_og").set_value("søppel").run()
        at.text_input(key="bd_fg").set_value("1.010").run()
        self._lagre_knapp(at).click().run()

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["actuals"], {})
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("OG" in m for m in feilmeldinger))

    def test_ingen_aktivt_brygg_deaktiverer_lagre_knappen(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        self.assertTrue(self._lagre_knapp(at).disabled)

    # ─── 4: oppskriftsbytte ugyldiggjør aktiv-brew-binding ─────────────

    def test_4_oppskriftsbytte_ugyldiggjor_aktiv_brew_og_tommer_felt(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        forste_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(forste_brew_id)

        at.text_input(key="bd_og").set_value("1.055").run()

        os.environ["KVERNHAUG_TEST_RECIPE_ID"] = "recipeB.json"
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved oppskriftsbytte: {at.exception}")

        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        self.assertEqual(at.text_input(key="bd_og").value, "")
        self.assertTrue(self._lagre_knapp(at).disabled)

        # Det opprinnelige brygget selv er uendret (aldri rørt av bytte).
        forste_brew = kbhbrew_storage.hent_brew(forste_brew_id)
        self.assertEqual(forste_brew["actuals"], {})
        self.assertEqual(forste_brew["recipeId"], "recipeA.json")

    # ─── 5: nytt brygg fra samme oppskrift arver ALDRI ulagret tekst ───

    def test_5_nytt_brygg_samme_oppskrift_arver_ikke_ulagret_maaling(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        forste_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")

        at.text_input(key="bd_og").set_value("1.077").run()

        self._klikk_start_nytt_brygg(at)
        andre_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertNotEqual(forste_brew_id, andre_brew_id)

        self.assertEqual(at.text_input(key="bd_og").value, "")

        self.assertEqual(kbhbrew_storage.hent_brew(forste_brew_id)["actuals"], {})
        self.assertEqual(kbhbrew_storage.hent_brew(andre_brew_id)["actuals"], {})

    # ─── 6: legacy recipes/_logs/ uberørt ──────────────────────────────

    def test_6_legacy_logs_mappe_uberort(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        at.text_input(key="bd_og").set_value("1.055").run()
        at.text_input(key="bd_fg").set_value("1.010").run()
        self._lagre_knapp(at).click().run()

        self.assertFalse(os.path.exists(os.path.join(self._tmpdir.name, "_logs")))

    # ─── 7: Brygghistorikk sitt eksplisitte utvalg oppdaterer det ──────
    # delte aktive målet (issue #170 "Identity safety" #3), og Steg 4/5
    # sitt målefelt følger etter.

    def test_7_historikkens_eksplisitte_utvalg_retargetterer_steg45(self):
        at = self._ny_apptest(recipe_id="recipeA.json")
        self._klikk_start_nytt_brygg(at)
        forste_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self._klikk_start_nytt_brygg(at)
        andre_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertNotEqual(forste_brew_id, andre_brew_id)

        # Lagre en kjent OG på det FØRSTE brygget via kbhbrew_storage
        # direkte (unngår å måtte navigere UI-et tilbake dit) -- deretter
        # eksplisitt velge DET brygget i Brygghistorikk-selectboksen.
        kbhbrew_storage.oppdater_brew_lag(forste_brew_id, actuals={"og": 1.040})

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(forste_brew_id).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved historikk-valg: {at.exception}")

        self.assertEqual(_ss(at, "_aktiv_kbhbrew_brew_id"), forste_brew_id)
        self.assertEqual(at.text_input(key="bd_og").value, "1.04")

    # ─── 8: lagreseksjonen skjules helt i DEMO_MODE ────────────────────

    def test_9_lagreseksjonen_skjules_i_demo_mode(self):
        env = dict(os.environ)
        env["DEMO_MODE"] = "1"
        script = (
            "import logging; logging.getLogger('streamlit').setLevel(logging.ERROR); "
            "from streamlit.testing.v1 import AppTest; "
            f"at = AppTest.from_file(r{_HARNESS!r}); "
            "at.run(); "
            "assert not at.exception, at.exception; "
            "knapper = [b for b in at.button if b.key == 'bd_lagre_maalinger_btn']; "
            "assert knapper == [], knapper; "
            "print('OK')"
        )
        resultat = subprocess.run(
            [sys.executable, "-c", script],
            cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(resultat.returncode, 0, f"stdout={resultat.stdout}\nstderr={resultat.stderr}")
        self.assertIn("OK", resultat.stdout)


if __name__ == "__main__":
    unittest.main()
