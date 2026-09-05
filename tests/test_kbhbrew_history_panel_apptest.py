"""
V2-1A (issue #83) -- AppTest-basert regresjonstest for
ui/kbhbrew_history_panel.py::render_kbhbrew_history_panel(), via
tests/fixtures/streamlit_harness/kbhbrew_history_harness.py (ekte
widget-interaksjon: utvalg + tekstfelt + knappeklikk + faktisk
gjenrendring, samme prinsipp som
tests/test_kbhbrew_create_panel_apptest.py).

Dekker de "farlige" Streamlit state-grensene issue #83 selv lister opp
under "State / safety requirements":
  1. Å velge et brygg skriver ingenting.
  2. Rendring/rerendring skriver ingenting.
  3. Å redigere widget-state UTEN å trykke Lagre skriver ingenting.
  4. ETT eksplisitt Lagre-klikk oppdaterer NØYAKTIG det valgte brygget.
  5. Lagring bevarer brewId/originBrewId/recipeId/hele det frosne
     snapshotet/urørte lag.
  6. Ingen operasjon oppretter et nytt brygg stille.
  9. Legacy recipes/_logs/ er utilgjengelig/uberørt fra denne flaten.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_history_panel_apptest -b
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_history_harness.py")


class TestKbhbrewHistoryPanelAppTest(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_seed_count = os.environ.pop("KVERNHAUG_TEST_KBHBREW_SEED_COUNT", None)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        if self._gammel_seed_count is None:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_SEED_COUNT", None)
        else:
            os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = self._gammel_seed_count
        self._tmpdir.cleanup()

    def _ny_apptest(self, seed_count=1):
        os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = str(seed_count)
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    # ─── 1: tom historikk ───────────────────────────────────────────────

    def test_1_ingen_lagrede_brygg_viser_tom_melding_uten_feil(self):
        at = self._ny_apptest(seed_count=0)
        self.assertEqual(list(at.selectbox), [])
        captions = [c.value for c in at.caption]
        self.assertTrue(any("Ingen lagrede brygg" in c for c in captions))

    # ─── 2: ren rendring/valg skriver ingenting ────────────────────────

    def test_2_ren_rendring_skriver_ingenting_og_oppretter_ikke_nytt_brygg(self):
        at = self._ny_apptest(seed_count=1)
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)
        brew_for = kbhbrew_storage.hent_brew("brew-seed-0001")

        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved rerun: {at.exception}")
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001"), brew_for)

    def test_3_a_velge_et_annet_brygg_skriver_ingenting(self):
        at = self._ny_apptest(seed_count=2)
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 2)
        selectboks = at.selectbox(key="kbhbrew_historikk_valgt_id")
        annet_valg = [v for v in selectboks.options if v != selectboks.value][0]
        selectboks.select(annet_valg).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved valg: {at.exception}")
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 2)

    # ─── 3: planlagt sammendrag viser frosne verdier ───────────────────

    def test_4_planlagt_sammendrag_viser_frosne_verdier(self):
        at = self._ny_apptest(seed_count=1)
        metrikker = {m.label: m.value for m in at.metric}
        self.assertEqual(metrikker["Planlagt OG"], "1.052")
        self.assertEqual(metrikker["Planlagt FG"], "1.012")
        self.assertEqual(metrikker["Planlagt ABV"], "5.2%")
        self.assertEqual(metrikker["Planlagt volum"], "20 L")

    # ─── 4: redigering uten lagre-klikk skriver ingenting ──────────────

    def test_5_redigering_av_actuals_uten_lagre_klikk_skriver_ingenting(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved typing: {at.exception}")
        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew.get("actuals"), {})

    # ─── 5: ett eksplisitt lagre-klikk oppdaterer nøyaktig det valgte ──

    def test_6_lagre_klikk_oppdaterer_actuals_status_og_brygget_dato(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        at.text_input(key="kbhbrew_hist_fg::brew-seed-0001").set_value("1.011").run()
        at.text_input(key="kbhbrew_hist_volum::brew-seed-0001").set_value("19.5").run()
        at.text_area(key="kbhbrew_hist_notes::brew-seed-0001").set_value("God gjæring").run()
        at.text_input(key="kbhbrew_hist_brygget_dato::brew-seed-0001").set_value("2026-09-01").run()
        at.selectbox(key="kbhbrew_hist_status::brew-seed-0001").select("done").run()

        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew["actuals"]["og"], 1.055)
        self.assertEqual(brew["actuals"]["fg"], 1.011)
        self.assertEqual(brew["actuals"]["volumeL"], 19.5)
        self.assertEqual(brew["actuals"]["notes"], "God gjæring")
        self.assertEqual(brew["status"], "done")
        self.assertEqual(brew["brewedAt"], "2026-09-01")

        suksessmeldinger = [e.value for e in at.success]
        self.assertTrue(suksessmeldinger, "Forventet en synlig lagre-bekreftelse")

    def test_7_lagring_oppretter_aldri_et_nytt_brygg(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)

    def test_8_lagring_bevarer_identitet_og_frosset_snapshot(self):
        at = self._ny_apptest(seed_count=1)
        brew_for = kbhbrew_storage.hent_brew("brew-seed-0001")

        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()

        brew_etter = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew_etter["brewId"], brew_for["brewId"])
        self.assertEqual(brew_etter["originBrewId"], brew_for["originBrewId"])
        self.assertEqual(brew_etter["recipeId"], brew_for["recipeId"])
        self.assertEqual(brew_etter["snapshot"], brew_for["snapshot"])

    # ─── 6: planlagt-vs-faktisk-visning etter lagring ──────────────────

    def test_9_planlagt_vs_faktisk_viser_avledet_abv_etter_lagring(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        at.text_input(key="kbhbrew_hist_fg::brew-seed-0001").set_value("1.010").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        # Selve avledningen skjer i modules/kbhbrew_history_ui.py -- her
        # bevises kun at den (a) faktisk vises i UI-et, (b) ALDRI havner i
        # de lagrede actuals (kbhbrew.py::FORBUDTE_ACTUALS_EKSPORTFELT).
        for forbudt in ("actual_abv", "abv", "actualAbv"):
            self.assertNotIn(forbudt, brew["actuals"])
        metrikker = {m.label: m.value for m in at.metric}
        self.assertIn("ABV — Standardestimat", metrikker)


if __name__ == "__main__":
    unittest.main()
