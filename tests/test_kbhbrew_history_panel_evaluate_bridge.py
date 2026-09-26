"""
V2.2 G3O (issue #395) -- AppTest-basert regresjonstest for den nye
Learn -> Reflect-broen i ui/kbhbrew_history_panel.py, per
docs/development/v22_g3n_evaluate_inspect_closure_contract.md §10.

Bruker samme tests/fixtures/streamlit_harness/kbhbrew_history_harness.py
som tests/test_kbhbrew_history_panel_apptest.py -- ekte widget-
interaksjon/gjenrendring, ikke ren st.session_state-manipulering.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_history_panel_evaluate_bridge -b
"""
import logging
import os
import tempfile
import unittest
from unittest import mock

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage
from modules.i18n import t as _t

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_history_harness.py")


def _finn_laer_bro(at, sprak="no"):
    tittel = _t("brew_history.laer_bro.tittel", sprak)
    treff = [e for e in at.expander if e.label == tittel]
    assert len(treff) == 1, f"Fant ikke akkurat én Learn->Reflect-bro med label={tittel!r}: {[e.label for e in at.expander]}"
    return treff[0]


class TestKbhbrewHistoryEvaluateBridge(unittest.TestCase):
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

    def _ny_apptest(self, seed_count=1, sprak=None):
        os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = str(seed_count)
        at = AppTest.from_file(_HARNESS)
        if sprak is not None:
            at.session_state["sprak"] = sprak
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    # ─── plassering/kollapset-som-standard/nøyaktig én forekomst ───────

    def test_1_broen_finnes_er_kollapset_og_rendres_nøyaktig_én_gang(self):
        at = self._ny_apptest(seed_count=1)
        broer = [e for e in at.expander if e.label == _t("brew_history.laer_bro.tittel")]
        self.assertEqual(len(broer), 1)
        self.assertFalse(broer[0].proto.expanded)

    def test_2_broen_ligger_etter_planlagt_sammendrag_og_foer_actuals_skjemaet(self):
        at = self._ny_apptest(seed_count=1)
        bro = _finn_laer_bro(at)
        actuals_tittel = f"**{_t('brew_history.actuals_tittel')}**"
        actuals_overskrift = [m for m in at.markdown if m.value == actuals_tittel]
        self.assertEqual(len(actuals_overskrift), 1)
        hoved = at.main
        bro_indeks = [i for i, node in hoved.children.items() if node is bro]
        actuals_indeks = [i for i, node in hoved.children.items() if node is actuals_overskrift[0]]
        self.assertEqual(len(bro_indeks), 1)
        self.assertEqual(len(actuals_indeks), 1)
        self.assertLess(bro_indeks[0], actuals_indeks[0])

    # ─── NO/EN-tekst rendres uendret ────────────────────────────────────

    def test_3_broen_viser_de_tre_no_tekstene_uendret(self):
        at = self._ny_apptest(seed_count=1)
        bro = _finn_laer_bro(at)
        markdown_barn = [c.value for c in bro.children.values() if type(c).__name__ == "Markdown"]
        caption_barn = [c.value for c in bro.children.values() if type(c).__name__ == "Caption"]
        self.assertEqual(markdown_barn, [_t("brew_history.laer_bro.forklaring", "no")])
        self.assertEqual(
            caption_barn,
            [
                _t("brew_history.laer_bro.usikkerhet_hint", "no"),
                _t("brew_history.laer_bro.neste_tid_hint", "no"),
            ],
        )

    def test_4_broen_viser_de_tre_en_tekstene_uendret(self):
        at = self._ny_apptest(seed_count=1, sprak="en")
        bro = _finn_laer_bro(at, sprak="en")
        markdown_barn = [c.value for c in bro.children.values() if type(c).__name__ == "Markdown"]
        caption_barn = [c.value for c in bro.children.values() if type(c).__name__ == "Caption"]
        self.assertEqual(markdown_barn, [_t("brew_history.laer_bro.forklaring", "en")])
        self.assertEqual(
            caption_barn,
            [
                _t("brew_history.laer_bro.usikkerhet_hint", "en"),
                _t("brew_history.laer_bro.neste_tid_hint", "en"),
            ],
        )

    # ─── ingen pilot-lesing / ingen ny skrivevei ────────────────────────

    def test_5_broen_kaller_aldri_bryggeskole_pilot_lesing(self):
        with mock.patch("bryggeskole.pilot_mashing.read_pilot_file") as pilot_mock:
            at = self._ny_apptest(seed_count=1)
            _finn_laer_bro(at)
            pilot_mock.assert_not_called()

    def test_6_broen_introduserer_ingen_nytt_session_state_utover_expander_flagget(self):
        at = self._ny_apptest(seed_count=1)
        nokler_for = set(at.session_state)
        _finn_laer_bro(at)
        at.run()
        nokler_etter = set(at.session_state)
        nye = nokler_etter - nokler_for
        self.assertEqual(nye, set(), f"Broen skal ikke legge til nye session_state-nøkler ved rerendring: {nye}")

    def test_7_valg_av_annet_brygg_paavirker_ikke_broens_tekst(self):
        at = self._ny_apptest(seed_count=2)
        bro_for = _finn_laer_bro(at)
        tekst_for = [c.value for c in bro_for.children.values() if type(c).__name__ == "Markdown"]

        selectboks = at.selectbox(key="kbhbrew_historikk_valgt_id")
        annet_valg = [v for v in selectboks.options if v != selectboks.value][0]
        selectboks.select(annet_valg).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved brygg-bytte: {at.exception}")

        bro_etter = _finn_laer_bro(at)
        tekst_etter = [c.value for c in bro_etter.children.values() if type(c).__name__ == "Markdown"]
        self.assertEqual(tekst_for, tekst_etter)

    def test_8_eksisterende_lagreveier_er_uendret_med_broen_til_stede(self):
        at = self._ny_apptest(seed_count=1)
        _finn_laer_bro(at)
        at.text_input(key="kbhbrew_hist_og::brew-seed-0001").set_value("1.055").run()
        knapper = [b for b in at.button if b.key == "kbhbrew_hist_lagre_btn::brew-seed-0001"]
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")
        brew = kbhbrew_storage.hent_brew("brew-seed-0001")
        self.assertEqual(brew["actuals"]["og"], 1.055)
        # Broen er fortsatt til stede og uendret etter en ekte lagring.
        _finn_laer_bro(at)


if __name__ == "__main__":
    unittest.main()
