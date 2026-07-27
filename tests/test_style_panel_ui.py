"""
UI-regresjonstest for ui/style_panel.py (Kvernhaug-gjennomgang 2026-07-27,
krav 3): headline («Numerisk nærmeste stil», basert på raw_score) og
prosentlisten under («Samlet stiltreff», basert på den signaturjusterte
`score`) kan peke på to ulike stiler for samme oppskrift — se
tests/test_style_engine.py::TestNumeriskNaermesteVsSamletTopp for selve
mekanismen og et konkret, reproduserbart tallscenario.

Denne testen kjører den EKTE ui/style_panel.py (via tests/_style_panel_app.py)
mot akkurat det scenariet og bekrefter at siden faktisk forklarer forskjellen
i tekst, i stedet for å vise to rangeringer uten noen forklaring — det ville
lest ut som et motstridende resultat.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import unittest

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)


class TestUiTeksterForklarerNumeriskVsSamlet(unittest.TestCase):

    def _kjor(self):
        from streamlit.testing.v1 import AppTest
        app_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_style_panel_app.py")
        at = AppTest.from_file(app_py)
        at.run()
        self.assertFalse(at.exception, f"_style_panel_app.py kastet exception: {at.exception}")
        return at

    def test_headline_er_eksplisitt_merket_numerisk(self):
        at = self._kjor()
        overskrifter = [s.value for s in at.subheader]
        self.assertTrue(
            any(o.startswith("Numerisk nærmeste stil") for o in overskrifter),
            f"Fant ingen 'Numerisk nærmeste stil'-headline blant: {overskrifter}",
        )
        self.assertFalse(
            any(o.startswith("Nærmeste stil:") for o in overskrifter),
            "Den gamle, uspesifiserte 'Nærmeste stil'-teksten er tilbake — "
            "den skjulte at headline og listen under kan være uenige",
        )

    def test_forklarende_bildetekst_finnes_under_headline(self):
        at = self._kjor()
        alle_captions = " ".join(c.value for c in at.caption)
        self.assertIn("signaturbonus", alle_captions.lower())

    def test_prosentlisten_er_merket_som_samlet_ikke_numerisk(self):
        at = self._kjor()
        overskrifter = [s.value for s in at.subheader]
        self.assertTrue(
            any("Samlet stiltreff" in o for o in overskrifter),
            f"Fant ingen 'Samlet stiltreff'-headline blant: {overskrifter}",
        )

    def test_scenariet_faktisk_viser_ulik_rangering_i_denne_kjoringen(self):
        # Sikrer at testen fortsatt tester noe reelt: hvis noen i fremtiden
        # endrer scoringsmodellen slik at scenariet i _style_panel_app.py
        # ikke lenger divergerer, skal DENNE testen feile synlig i stedet for
        # at UI-forklarings-testene over stille slutter å teste noe.
        from modules.style_engine import analyser_stil_og_balanse
        recipe = {
            "stats": {"og": 1.031, "fg": 1.0082, "ibu": 32.2, "ebc": 17.7, "abv": 2.99},
            "flavor_profile": {
                "Brød": 6.0, "Sitrus": 1.3, "Bitterhet": 2.0, "Fruktighet": 3.6,
                "Krydder": 6.4, "Maltfylde": 3.4, "Toast": 6.3, "Karamell": 0.4,
                "Nøtter": 1.7, "Sjokolade": 2.1, "Kaffe": 3.1, "Røyk": 3.0,
                "Honning": 0.3, "Jordlig": 5.2, "Tropisk": 5.3, "Steinfrukt": 3.2,
            },
            "malts": [], "hops": [], "yeast": "wlp500",
        }
        resultat = analyser_stil_og_balanse(recipe)
        listetopp = sorted(resultat["stil_liste"], key=lambda s: (-s["score"], s["prio"]))[0]
        self.assertNotEqual(resultat["stil"], listetopp["stil"])


class TestUiMerkerIkkeOffisielleStiler(unittest.TestCase):
    """Krav 2: Historisk Wiesn-Märzen skal vises tydelig merket som en
    Kvernhaug/historisk kategori — ikke som en ordinær BJCP-stil — både når
    den er headline («Numerisk nærmeste stil») og i prosentlisten under."""

    def _kjor(self):
        from streamlit.testing.v1 import AppTest
        app_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_style_panel_wiesn_app.py")
        at = AppTest.from_file(app_py)
        at.run()
        self.assertFalse(at.exception, f"_style_panel_wiesn_app.py kastet exception: {at.exception}")
        return at

    def test_headline_lander_pa_historisk_wiesn_marzen(self):
        at = self._kjor()
        overskrifter = [s.value for s in at.subheader]
        self.assertTrue(
            any("Historisk Wiesn-Märzen" in o for o in overskrifter),
            f"Testforutsetningen (headline = Historisk Wiesn-Märzen) holder ikke: {overskrifter}",
        )

    def test_headline_har_ikke_offisiell_bjcp_merke(self):
        at = self._kjor()
        alle_captions = " ".join(c.value for c in at.caption)
        self.assertIn("ikke en offisiell BJCP-stil", alle_captions)

    def test_listeoppforingen_har_ogsaa_merket(self):
        at = self._kjor()
        alle_tekster = " ".join(w.value for w in at.markdown)
        self.assertIn("Historisk Wiesn-Märzen", alle_tekster)
        self.assertIn("ikke offisiell BJCP-stil", alle_tekster)

    def test_ordinaere_bjcp_stiler_far_ikke_merket(self):
        # Negativ kontroll: en ekte BJCP-stil i samme liste (Heller Bock,
        # som også scorer høyt for denne oppskriften) skal IKKE ha merket.
        at = self._kjor()
        alle_tekster = [w.value for w in at.markdown]
        bock_linjer = [t for t in alle_tekster if "Heller Bock" in t]
        self.assertTrue(bock_linjer, "Fant ingen Heller Bock-linje å sjekke")
        for linje in bock_linjer:
            self.assertNotIn("Kvernhaug/historisk", linje)


if __name__ == "__main__":
    unittest.main()
