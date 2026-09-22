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
        self._gammel_aktiv_id = os.environ.pop("KVERNHAUG_TEST_KBHBREW_AKTIV_ID", None)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        if self._gammel_seed_count is None:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_SEED_COUNT", None)
        else:
            os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = self._gammel_seed_count
        if self._gammel_aktiv_id is None:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_AKTIV_ID", None)
        else:
            os.environ["KVERNHAUG_TEST_KBHBREW_AKTIV_ID"] = self._gammel_aktiv_id
        self._tmpdir.cleanup()

    def _ny_apptest(self, seed_count=1, aktiv_brew_id=None):
        os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = str(seed_count)
        if aktiv_brew_id is None:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_AKTIV_ID", None)
        else:
            os.environ["KVERNHAUG_TEST_KBHBREW_AKTIV_ID"] = aktiv_brew_id
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

    # ─── Chief review-fiks (PR #84 runde 2): strengt validerte tallfelt ─

    def test_10_ugyldig_tall_blokkerer_hele_lagringen_uten_mutasjon(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055abc").run()
        at.text_input(key="kbhbrew_hist_fg::brew-seed-0001").set_value("1.011").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew.get("actuals"), {})
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(feilmeldinger, "Forventet en synlig feilmelding")
        self.assertFalse(list(at.success), "Skal IKKE vise en lagre-bekreftelse ved ugyldig input")

    def test_11_soeppeltekst_toemmer_aldri_et_eksisterende_lagret_maal(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001")["actuals"]["og"], 1.055)

        at.text_input(key="kbhbrew_hist_fg::brew-seed-0001").set_value("abc").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew["actuals"]["og"], 1.055, "Det tidligere lagrede OG-målet må overleve uendret")
        self.assertNotIn("fg", brew["actuals"])

    def test_12_norsk_komma_desimal_lagres_som_full_korrekt_verdi(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1,055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew["actuals"]["og"], 1.055)
        self.assertTrue(list(at.success))

    def test_13_blankt_felt_toemmer_fortsatt_et_tidligere_lagret_maal(self):
        at = self._ny_apptest(seed_count=1)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001")["actuals"]["og"], 1.055)

        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertNotIn("og", brew["actuals"])

    # ─── V2-1B (issue #87): sensorikk-/lærings-skjema ──────────────────

    def test_14_redigering_av_sensing_learning_uten_lagre_klikk_skriver_ingenting(self):
        at = self._ny_apptest(seed_count=1)
        at.selectbox(key="kbhbrew_hist_sensing_judgment::brew-seed-0001").select("yes").run()
        at.text_area(key="kbhbrew_hist_sensing_notes::brew-seed-0001").set_value("Fruktig aroma").run()
        at.text_area(key="kbhbrew_hist_learning_worked::brew-seed-0001").set_value("God temperaturkontroll").run()
        at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001").set_value("Kanskje for varm mesk").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved typing: {at.exception}")
        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew.get("sensing"), {})
        self.assertEqual(brew.get("learning"), {})

    def test_15_sensing_default_er_ikke_satt_uten_autofyll(self):
        at = self._ny_apptest(seed_count=1)
        selectboks = at.selectbox(key="kbhbrew_hist_sensing_judgment::brew-seed-0001")
        self.assertEqual(selectboks.value, "")

    def test_15b_hypothesis_felt_er_tomt_uten_autofyll_naar_ingen_verdi_er_lagret(self):
        at = self._ny_apptest(seed_count=1)
        felt = at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001")
        self.assertEqual(felt.value, "")

    def test_15c_hypothesis_felt_forhaandsutfylles_med_lagret_verdi(self):
        at = self._ny_apptest(seed_count=1)
        at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001").set_value("Kanskje for varm mesk").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()

        at.run()
        felt = at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001")
        self.assertEqual(felt.value, "Kanskje for varm mesk")

    def test_16_lagre_klikk_lagrer_sensing_og_learning_og_ikke_actuals(self):
        at = self._ny_apptest(seed_count=1)
        at.selectbox(key="kbhbrew_hist_sensing_judgment::brew-seed-0001").select("yes").run()
        at.text_area(key="kbhbrew_hist_sensing_notes::brew-seed-0001").set_value("Fruktig aroma").run()
        at.text_area(key="kbhbrew_hist_learning_worked::brew-seed-0001").set_value("God temperaturkontroll").run()
        at.text_area(key="kbhbrew_hist_learning_changed::brew-seed-0001").set_value("Byttet gjærstamme").run()
        at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001").set_value("Kanskje for varm mesk").run()
        at.text_area(key="kbhbrew_hist_learning_next::brew-seed-0001").set_value("Senk mesketemperatur").run()

        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew["sensing"]["judgment"], "yes")
        self.assertEqual(brew["sensing"]["notes"], "Fruktig aroma")
        self.assertEqual(brew["learning"]["whatWorked"], "God temperaturkontroll")
        self.assertEqual(brew["learning"]["whatChanged"], "Byttet gjærstamme")
        self.assertEqual(brew["learning"]["hypothesis"], "Kanskje for varm mesk")
        self.assertEqual(brew["learning"]["nextTime"], "Senk mesketemperatur")
        # Denne lagre-knappen rører ALDRI actuals/status/brewedAt.
        self.assertEqual(brew.get("actuals"), {})
        self.assertEqual(brew.get("status"), "active")
        self.assertIsNone(brew.get("brewedAt"))

        suksessmeldinger = [e.value for e in at.success]
        self.assertTrue(suksessmeldinger, "Forventet en synlig lagre-bekreftelse")

    def test_16b_blankt_hypothesis_felt_lagrer_ingen_fabrikert_verdi(self):
        at = self._ny_apptest(seed_count=1)
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")
        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertNotIn("hypothesis", brew.get("learning", {}))

    def test_16c_blankt_hypothesis_felt_toemmer_en_tidligere_lagret_hypotese(self):
        at = self._ny_apptest(seed_count=1)
        at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001").set_value("Kanskje for varm mesk").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001")["learning"]["hypothesis"], "Kanskje for varm mesk")

        at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001").set_value("").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertNotIn("hypothesis", brew.get("learning", {}))

    def test_17_sensing_learning_lagring_bevarer_identitet_og_frosset_snapshot(self):
        at = self._ny_apptest(seed_count=1)
        brew_for = kbhbrew_storage.hent_brew("brew-seed-0001")

        at.text_area(key="kbhbrew_hist_sensing_notes::brew-seed-0001").set_value("Fruktig aroma").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()

        brew_etter = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew_etter["brewId"], brew_for["brewId"])
        self.assertEqual(brew_etter["originBrewId"], brew_for["originBrewId"])
        self.assertEqual(brew_etter["recipeId"], brew_for["recipeId"])
        self.assertEqual(brew_etter["snapshot"], brew_for["snapshot"])

    def test_18_actuals_lagring_roerer_aldri_sensing_learning_og_omvendt(self):
        at = self._ny_apptest(seed_count=1)
        at.text_area(key="kbhbrew_hist_sensing_notes::brew-seed-0001").set_value("Fruktig aroma").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001")["sensing"]["notes"], "Fruktig aroma")

        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew["actuals"]["og"], 1.055)
        # Sensing-notatet fra forrige, separate lagre-klikk må overleve
        # uendret -- actuals-lagringen skriver bare til actuals-laget.
        self.assertEqual(brew["sensing"]["notes"], "Fruktig aroma")

    def test_18b_hypothesis_lagring_roerer_aldri_actuals_snapshot_status_brewedat(self):
        at = self._ny_apptest(seed_count=1)
        brew_for = kbhbrew_storage.hent_brew("brew-seed-0001")

        at.text_area(key="kbhbrew_hist_learning_hypothesis::brew-seed-0001").set_value("Kanskje for varm mesk").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew_etter = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew_etter["learning"]["hypothesis"], "Kanskje for varm mesk")
        self.assertEqual(brew_etter.get("actuals"), brew_for.get("actuals"))
        self.assertEqual(brew_etter["snapshot"], brew_for["snapshot"])
        self.assertEqual(brew_etter["status"], brew_for["status"])
        self.assertEqual(brew_etter.get("brewedAt"), brew_for.get("brewedAt"))

    def test_19_blank_sensing_learning_er_gyldig_ingen_fabrikert_innhold(self):
        at = self._ny_apptest(seed_count=1)
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")
        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew.get("sensing"), {})
        self.assertEqual(brew.get("learning"), {})

    def test_20_blankt_sensing_notat_toemmer_et_tidligere_lagret_notat(self):
        at = self._ny_apptest(seed_count=1)
        at.text_area(key="kbhbrew_hist_sensing_notes::brew-seed-0001").set_value("Fruktig aroma").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001")["sensing"]["notes"], "Fruktig aroma")

        at.text_area(key="kbhbrew_hist_sensing_notes::brew-seed-0001").set_value("").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertNotIn("notes", brew.get("sensing", {}))

    def test_21_valg_av_ikke_satt_toemmer_en_tidligere_lagret_judgment(self):
        at = self._ny_apptest(seed_count=1)
        at.selectbox(key="kbhbrew_hist_sensing_judgment::brew-seed-0001").select("yes").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001")["sensing"]["judgment"], "yes")

        at.selectbox(key="kbhbrew_hist_sensing_judgment::brew-seed-0001").select("").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_sensing_learning_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertNotIn("judgment", brew.get("sensing", {}))

    # ─── issue #265: non-active/historisk brygg-oppførsel ──────────────
    # Fokusert regresjonsdekning for scenariet der Brygghistorikk-panelet
    # åpnes med et FORHÅNDS-SATT aktivt brygg-mål (App A1, issue #170)
    # som IKKE er det panelet initielt viser identisk med et annet
    # seedet brygg -- dvs. å åpne/redigere/lagre et historisk brygg som
    # ikke er "current active brew". Bruker KUN de allerede eksisterende,
    # støttede skriveveiene (sett_aktiv_brew_id()/oppdater_brew_lag()) --
    # ingen ny UX eller produktregel oppfinnes her.

    def _ss(self, at, key, default=None):
        try:
            return at.session_state[key]
        except KeyError:
            return default

    def test_22_current_active_brew_path_uendret_med_flere_brygg(self):
        at = self._ny_apptest(seed_count=2, aktiv_brew_id="brew-seed-0001")
        self.assertEqual(self._ss(at, "_aktiv_kbhbrew_brew_id"), "brew-seed-0001")

        selectboks = at.selectbox(key="kbhbrew_historikk_valgt_id")
        self.assertEqual(selectboks.value, "brew-seed-0001")

        metrikker = {m.label: m.value for m in at.metric}
        self.assertEqual(metrikker["Planlagt OG"], "1.052")
        self.assertEqual(metrikker["Planlagt FG"], "1.012")
        self.assertEqual(metrikker["Planlagt ABV"], "5.2%")
        self.assertEqual(metrikker["Planlagt volum"], "20 L")

    def test_23_valg_av_ikke_aktivt_brygg_muterer_ingen_av_de_to(self):
        at = self._ny_apptest(seed_count=2, aktiv_brew_id="brew-seed-0001")
        brew1_for = kbhbrew_storage.hent_brew("brew-seed-0001")
        brew2_for = kbhbrew_storage.hent_brew("brew-seed-0002")

        selectboks = at.selectbox(key="kbhbrew_historikk_valgt_id")
        self.assertEqual(selectboks.value, "brew-seed-0001")
        selectboks.select("brew-seed-0002").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved valg: {at.exception}")

        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001"), brew1_for)
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0002"), brew2_for)

    def test_24_redigering_av_ikke_aktivt_valgt_brygg_uten_lagre_skriver_ingenting(self):
        at = self._ny_apptest(seed_count=2, aktiv_brew_id="brew-seed-0001")
        brew1_for = kbhbrew_storage.hent_brew("brew-seed-0001")
        brew2_for = kbhbrew_storage.hent_brew("brew-seed-0002")

        at.selectbox(key="kbhbrew_historikk_valgt_id").select("brew-seed-0002").run()
        at.text_input(key="kbhbrew_hist_og::brew-seed-0002").set_value("1.061").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved typing: {at.exception}")

        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001"), brew1_for)
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0002"), brew2_for)

    def test_25_lagring_pa_nettopp_valgt_ikke_opprinnelig_aktivt_brygg_roerer_aldri_det_andre(self):
        at = self._ny_apptest(seed_count=2, aktiv_brew_id="brew-seed-0001")
        brew1_for = kbhbrew_storage.hent_brew("brew-seed-0001")

        at.selectbox(key="kbhbrew_historikk_valgt_id").select("brew-seed-0002").run()
        # Historikkens eksplisitte utvalg re-targetterer det delte aktive
        # målet mot det nå valgte brygget -- SAMME etablerte, allerede
        # testede kontrakt som issue #170 (test_7 i
        # tests/test_brewday_a1_measurement_apptest.py), ikke en ny regel.
        self.assertEqual(self._ss(at, "_aktiv_kbhbrew_brew_id"), "brew-seed-0002")

        at.text_input(key="kbhbrew_hist_og::brew-seed-0002").set_value("1.061").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0002"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring: {at.exception}")

        brew2 = kbhbrew_storage.hent_brew("brew-seed-0002")
        self.assertEqual(brew2["actuals"]["og"], 1.061)
        # Det opprinnelig aktive brygget (#0001) er HELT uendret --
        # verken selve dataene, identiteten, eller det frosne snapshotet.
        self.assertEqual(kbhbrew_storage.hent_brew("brew-seed-0001"), brew1_for)
        # Typing/lagre-klikket alene skriver ikke det aktive målet
        # videre utover det ene, forventede valg-drevne skiftet over.
        self.assertEqual(self._ss(at, "_aktiv_kbhbrew_brew_id"), "brew-seed-0002")


if __name__ == "__main__":
    unittest.main()
