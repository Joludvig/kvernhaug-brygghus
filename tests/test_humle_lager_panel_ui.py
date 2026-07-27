"""
UI-regresjonstest for ui/humle_lager_panel.py (Kvernhaug-gjennomgang
2026-07-27, oppgave 2 — "tydeliggjør gammelt humlelager"): appen har nå
midlertidig to humlekilder — det gamle, flate humlelageret
(modules/humle_lager.py, brukt av handlelisten) og det nye Pantry-panelet
(oppskriftskontroll). Denne testen bekrefter at det gamle panelet tydelig
merker seg selv som eldre/legacy og forklarer at de to IKKE synkroniseres
automatisk, slik at en bruker ikke tror å registrere humle ett sted
automatisk oppdaterer det andre.

modules.humle_lager.les_lager() leser (read-only) fra den ekte
data/humle_lager.json — trygt her siden testverten aldri klikker noe som
trigger lagre_lager(), og fila i dag er tom ({}); ingenting skrives.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import unittest

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_humle_lager_panel_app.py")


class TestGammeltHumlelagerMerketSomEldre(unittest.TestCase):
    def _kjor(self):
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(_APP)
        at.run()
        self.assertFalse(at.exception, f"_humle_lager_panel_app.py kastet exception: {at.exception}")
        return at

    def test_panel_tittel_merker_seg_som_eldre(self):
        at = self._kjor()
        expander_titler = [e.label for e in at.expander]
        self.assertTrue(
            any("eldre" in t.lower() for t in expander_titler),
            f"Forventet 'eldre' i expander-tittelen, fant: {expander_titler}",
        )

    def test_forklarer_at_det_ikke_synkroniseres_med_pantry(self):
        at = self._kjor()
        alle_captions = " ".join(c.value for c in at.caption)
        self.assertIn("Pantry", alle_captions)
        self.assertTrue(
            "IKKE" in alle_captions or "ikke" in alle_captions.lower(),
            "Forventet en eksplisitt 'synkroniseres ikke automatisk'-forklaring",
        )

    def test_forklarer_at_det_kun_brukes_av_handlelisten(self):
        at = self._kjor()
        alle_captions = " ".join(c.value for c in at.caption)
        self.assertIn("handlelist", alle_captions.lower())


if __name__ == "__main__":
    unittest.main()
