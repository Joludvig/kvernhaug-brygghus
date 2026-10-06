"""
V2.2 G3P-7 (issue #462) -- regresjonstester for Råvarer Learn -> Plan-
broene i ui/malt_panel.py (CHUNK-RAW-A/B/C) og ui/water_panel.py
(CHUNK-RAW-J/K). Speiler tests/test_hop_panel.py sitt mønster.

Kjøres med:
    py -3 -m unittest tests.test_raavarer_learn_plan_bridges -b
"""
import logging
import os
import unittest
from unittest import mock

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from tests.apptest_session_state import apptest_session_state_keys

from bryggeskole import pilot_raw_materials as pilot
from modules.i18n import t as _t

_DIR = os.path.dirname(os.path.abspath(__file__))
_MALT_APP = os.path.join(_DIR, "_malt_panel_app.py")
_WATER_APP = os.path.join(_DIR, "_water_panel_bridge_app.py")

_MALT_IDER = ("CHUNK-RAW-A", "CHUNK-RAW-B", "CHUNK-RAW-C")
_WATER_IDER = ("CHUNK-RAW-J", "CHUNK-RAW-K")

_BRIDGES = {
    "malt": (_MALT_APP, _MALT_IDER, "raavarer.malt.laer_bro"),
    "vann": (_WATER_APP, _WATER_IDER, "raavarer.vann.laer_bro"),
}


def _kjor(app, sprak="no"):
    at = AppTest.from_file(app)
    at.session_state["sprak"] = sprak
    at.run()
    return at


def _bro(at, nokkel, sprak="no"):
    tittel = _t(nokkel + ".tittel", sprak)
    treff = [e for e in at.expander if e.label == tittel]
    assert len(treff) == 1, f"Forventet nøyaktig én bro {tittel!r}: {[e.label for e in at.expander]}"
    return treff[0]


def _markdown(bro):
    return [c.value for c in bro.children.values() if type(c).__name__ == "Markdown"]


def _forventet(ider, sprak):
    chunker = {c["id"]: c for c in pilot.read_pilot_file()["chunks"]}
    return [pilot.render_chunk(chunker[i], sprak)["text"] for i in ider]


class TestRaavarerBridges(unittest.TestCase):
    def test_kollapset_og_rendret_en_gang(self):
        for navn, (app, _ider, nokkel) in _BRIDGES.items():
            with self.subTest(navn):
                at = _kjor(app)
                self.assertFalse(at.exception)
                self.assertFalse(_bro(at, nokkel).proto.expanded)

    def test_noyaktige_chunks_i_rekkefolge_no_og_en(self):
        for navn, (app, ider, nokkel) in _BRIDGES.items():
            for sprak in ("no", "en"):
                with self.subTest(navn=navn, sprak=sprak):
                    bro = _bro(_kjor(app, sprak), nokkel, sprak)
                    self.assertEqual(_markdown(bro), _forventet(ider, sprak))

    def test_tittel_og_footer_finnes_i_begge_sprak(self):
        for _navn, (_app, _ider, nokkel) in _BRIDGES.items():
            for suffiks in (".tittel", ".footer"):
                no, en = _t(nokkel + suffiks, "no"), _t(nokkel + suffiks, "en")
                self.assertNotEqual(no, nokkel + suffiks)
                self.assertNotEqual(en, nokkel + suffiks)
                self.assertNotEqual(no, en)

    def test_footer_rendres_som_caption(self):
        for navn, (app, _ider, nokkel) in _BRIDGES.items():
            with self.subTest(navn):
                bro = _bro(_kjor(app), nokkel)
                bildetekster = [c.value for c in bro.children.values() if type(c).__name__ == "Caption"]
                self.assertEqual(bildetekster, [_t(nokkel + ".footer", "no")])

    def test_ingen_svar_eller_mastery_kall(self):
        for navn, (app, _ider, _nokkel) in _BRIDGES.items():
            with self.subTest(navn):
                with mock.patch.object(pilot, "evaluate_answer") as ev, \
                        mock.patch.object(pilot, "render_question") as rq:
                    at = _kjor(app)
                self.assertFalse(at.exception)
                ev.assert_not_called()
                rq.assert_not_called()

    def test_ingen_nye_session_state_nokler(self):
        for navn, (app, _ider, _nokkel) in _BRIDGES.items():
            with self.subTest(navn):
                at = _kjor(app)
                nye = [k for k in sorted(apptest_session_state_keys(at)) if isinstance(k, str) and ("laer_bro" in k or "raavarer" in k)]
                self.assertEqual(nye, [])

    def test_ugyldig_pilotinnhold_feiler_trygt(self):
        for navn, (app, _ider, nokkel) in _BRIDGES.items():
            with self.subTest(navn):
                with mock.patch.object(
                    pilot, "read_pilot_file", side_effect=pilot.PilotContentError(["ugyldig"])
                ):
                    at = _kjor(app)
                self.assertFalse(at.exception)
                self.assertEqual(_markdown(_bro(at, nokkel)), [])
                self.assertIn(
                    "Kunne ikke laste leksjonsinnholdet",
                    " ".join(e.value for e in at.error),
                )


class TestEksisterendePanelAtferd(unittest.TestCase):
    def test_maltbro_rendres_en_gang_med_flere_rader(self):
        at = _kjor(_MALT_APP)
        _bro(at, "raavarer.malt.laer_bro")
        self.assertEqual(len(at.session_state["valgt_malt"]), 2)

    def test_malt_rader_uendret_form(self):
        at = _kjor(_MALT_APP)
        for rad in at.session_state["valgt_malt"]:
            self.assertEqual(set(rad.keys()), {"id", "mengde"})

    def test_vannpanelet_beholder_header_og_intro(self):
        at = _kjor(_WATER_APP)
        self.assertIn("💧 Vannkjemi", [s.value for s in at.subheader])
        self.assertIn("ℹ️ Hvorfor disse tallene betyr noe (kort intro)", [e.label for e in at.expander])


if __name__ == "__main__":
    unittest.main()
