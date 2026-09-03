"""
PRI 3B2 (issue #29) -- AppTest-basert regresjonstest for
ui/kbhbrew_panel.py::render_kbhbrew_create_panel(), via
tests/fixtures/streamlit_harness/kbhbrew_create_harness.py (ekte
widget-interaksjon: knappeklikk + faktisk gjenrendring, samme prinsipp
som tests/test_kbh_import_ui_apptest.py).

Dekker Streamlit rerun-/idempotens-garantiene fra issue #29:
  - rendring/rerendring oppretter ALDRI et brygg alene;
  - ETT eksplisitt knappeklikk oppretter NØYAKTIG ett nytt lokalt brygg,
    med korrekt oppskrift/kontekst fanget i snapshotet;
  - en etterfølgende rerun (uten nytt klikk) viser/beholder DET brygget
    i stedet for å stille opprette et nytt;
  - et NYTT eksplisitt klikk oppretter et NYTT batch (flere reelle
    brygg fra samme oppskrift er gyldig historikk, IKKE en duplikat-
    feil -- se issue #29 "do not deduplicate by recipe name");
  - en oppskrift som ikke er gyldig for eksport viser en tydelig,
    handlingsrettet feil og skriver INGENTING;
  - opprettelses-preflighten (Chief review, PR #30 blocker 3) nekter og
    skriver INGENTING når utstyrsprofilen ikke er bekreftet lagret
    (mangler/korrupt fil), eller når oppskriften refererer en malt-ID
    som ikke finnes i gjeldende masterdata.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_create_panel_apptest -b
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_create_harness.py")


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (se tests/test_kbh_import_ui_apptest.py)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


_GYLDIG_EQUIPMENT = {
    "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}


class TestKbhbrewCreatePanelAppTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_invalid = os.environ.pop("KVERNHAUG_TEST_KBHBREW_INVALID", None)
        self._gammel_missing_malt = os.environ.pop("KVERNHAUG_TEST_KBHBREW_MISSING_MALT", None)

        # Isolert, GYLDIG utstyrsprofil som default (happy path) -- ALDRI
        # den ekte data/equipment.json (se modules/equipment.py::
        # _equipment_file()). Enkelttester som trenger en manglende/
        # korrupt profil overstyrer denne selv.
        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        self._equipment_file = os.path.join(self._tmpdir.name, "equipment.json")
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            json.dump(_GYLDIG_EQUIPMENT, f)
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._equipment_file

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        if self._gammel_invalid is not None:
            os.environ["KVERNHAUG_TEST_KBHBREW_INVALID"] = self._gammel_invalid
        else:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_INVALID", None)
        if self._gammel_missing_malt is not None:
            os.environ["KVERNHAUG_TEST_KBHBREW_MISSING_MALT"] = self._gammel_missing_malt
        else:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_MISSING_MALT", None)
        if self._gammel_equipment_file is None:
            os.environ.pop("KVERNHAUG_EQUIPMENT_FILE", None)
        else:
            os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._gammel_equipment_file
        self._tmpdir.cleanup()

    def _ny_apptest(self):
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _klikk_start(self, at):
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        self.assertEqual(len(knapper), 1, "Fant ikke akkurat én 'Start nytt brygg'-knapp")
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter klikk: {at.exception}")
        return at

    # ─── 1: ren rendring skriver ingenting ──────────────────────────────

    def test_1_ren_rendring_oppretter_ingen_brew(self):
        at = self._ny_apptest()
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))

    # ─── 2: ett klikk = ett brygg, med korrekt snapshot-innhold ────────

    def test_2_ett_klikk_oppretter_noyaktig_ett_brygg_med_riktig_snapshot(self):
        at = self._ny_apptest()
        self._klikk_start(at)

        brews = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(len(brews), 1)
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)
        brew = brews[brew_id]
        self.assertEqual(brew["originBrewId"], brew_id)
        self.assertEqual(brew["status"], "active")
        self.assertEqual(brew["snapshot"]["recipe"]["navn"], "Harness Pilsner")
        self.assertEqual(brew["snapshot"]["predicted"]["og"], 1.050)
        self.assertEqual(brew["snapshot"]["predicted"]["style"], {"stil": "Tysk Pilsner", "score": 80})
        self.assertIn("weyermann_pilsner", brew["snapshot"]["ingredients"]["malt"])

    # ─── 3: rerun viser/beholder samme brygg, oppretter aldri på nytt ──

    def test_3_etterfolgende_rerun_oppretter_ikke_nytt_brygg(self):
        at = self._ny_apptest()
        self._klikk_start(at)
        brew_id_etter_klikk = _ss(at, "_aktiv_kbhbrew_brew_id")

        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved rerun: {at.exception}")
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)
        self.assertEqual(_ss(at, "_aktiv_kbhbrew_brew_id"), brew_id_etter_klikk)

        suksessmeldinger = [e.value for e in at.success]
        self.assertTrue(any(brew_id_etter_klikk in m for m in suksessmeldinger))

    # ─── 4: et nytt eksplisitt klikk = et nytt, uavhengig batch ────────

    def test_4_nytt_eksplisitt_klikk_oppretter_et_nytt_batch(self):
        at = self._ny_apptest()
        self._klikk_start(at)
        forste_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")

        self._klikk_start(at)
        andre_brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")

        self.assertNotEqual(forste_brew_id, andre_brew_id)
        brews = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(len(brews), 2)
        self.assertIn(forste_brew_id, brews)
        self.assertIn(andre_brew_id, brews)

    # ─── 5: ugyldig oppskrift -- tydelig feil, ingenting skrevet ───────

    def test_5_ugyldig_oppskrift_viser_feil_og_skriver_ingenting(self):
        os.environ["KVERNHAUG_TEST_KBHBREW_INVALID"] = "1"
        at = self._ny_apptest()
        self._klikk_start(at)

        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("ikke gyldig for eksport" in m for m in feilmeldinger))

    # ─── 6/7/8: opprettelses-preflight (Chief review, PR #30 blocker 3) ─

    def test_6_manglende_utstyrsprofil_viser_feil_og_skriver_ingenting(self):
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = os.path.join(self._tmpdir.name, "finnes-ikke.json")
        at = self._ny_apptest()
        self._klikk_start(at)

        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("bekreftet utstyrsprofil" in m for m in feilmeldinger))

    def test_7_korrupt_utstyrsprofil_viser_feil_og_skriver_ingenting(self):
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            f.write("{ikke gyldig json")
        at = self._ny_apptest()
        self._klikk_start(at)

        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("bekreftet utstyrsprofil" in m for m in feilmeldinger))

    def test_8_manglende_malt_id_i_masterdata_viser_feil_og_skriver_ingenting(self):
        os.environ["KVERNHAUG_TEST_KBHBREW_MISSING_MALT"] = "1"
        at = self._ny_apptest()
        self._klikk_start(at)

        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("weyermann_pilsner" in m for m in feilmeldinger))


if __name__ == "__main__":
    unittest.main()
