"""
UI-tester for Steg F3: «bestill til eksakt mål»-rendring i
ui/smart_shopping_list_panel.py::_render_eksakt_mal_instruks().

Kjører den PRIVATE rendrings-hjelpefunksjonen _render_malt_pakningsforslag()
direkte via Streamlit sitt AppTest-rammeverk, mot to SEPARATE, minimale
testverter (tests/_eksakt_mal_render_app.py og
tests/_normal_pakningsforslag_render_app.py) — hver med et ferdigbygget
kjøpsresultat-objekt, helt uavhengig av Pantry, oppskrift eller ekte
masterdata, siden denne funksjonen kun formaterer et allerede beregnet
resultat. Holdt i to separate app-kjøringer (ikke én kombinert) slik at
ingen test risikerer å blande widget-tekst fra begge modiene sammen.

Se tests/test_smart_shopping_list_integration.py for den fulle,
ende-til-ende AppTest-dekningen av selve handlelisten.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import unittest

_EKSAKT_MAL_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_eksakt_mal_render_app.py")
_NORMAL_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_normal_pakningsforslag_render_app.py")
_SEKK_SPERRET_APP = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sekk_sperret_render_app.py")


def _kjor(app_path):
    from streamlit.testing.v1 import AppTest
    at = AppTest.from_file(app_path)
    at.run()
    assert not at.exception, f"{app_path} kastet exception: {at.exception}"
    return at


class Test12EksaktMalTekstErForsiktig(unittest.TestCase):
    def test_eksakt_mal_forslag_viser_instruks_med_riktig_mengde(self):
        at = _kjor(_EKSAKT_MAL_APP)
        alle_tekster = " ".join(w.value for w in at.markdown)
        self.assertIn("Eksakt mål", alle_tekster)
        self.assertIn("Vestbrygg", alle_tekster)
        self.assertIn("knust", alle_tekster.lower())
        self.assertIn("1.23 kg", alle_tekster)
        self.assertIn("1 × 1 kg", alle_tekster)
        self.assertIn("3 × 100 g", alle_tekster)

    def test_eksakt_mal_forslag_bruker_forsiktig_ikke_garantert_formulering(self):
        at = _kjor(_EKSAKT_MAL_APP)
        alle_tekster = " ".join(w.value for w in at.caption).lower()
        self.assertIn("opplyser", alle_tekster)
        self.assertIn("melding", alle_tekster)
        self.assertIn("salgsavdelingen", alle_tekster)
        self.assertIn("ikke en garantert", alle_tekster)
        self.assertNotIn("garantert leveranse", alle_tekster)


class Test13NormalFormatteringErUendret(unittest.TestCase):
    def test_normal_forslag_viser_fortsatt_anbefalt_kombinasjon_uendret(self):
        at = _kjor(_NORMAL_APP)
        alle_tekster = " ".join(w.value for w in at.markdown)
        self.assertIn("Anbefalt", alle_tekster)
        self.assertIn("1 × 1 kg", alle_tekster)
        self.assertIn("3 × 100 g", alle_tekster)
        self.assertIn("1300 g", alle_tekster)
        self.assertIn("75 kr", alle_tekster)

    def test_normal_forslag_viser_ikke_eksakt_mal_tekst(self):
        at = _kjor(_NORMAL_APP)
        alle_tekster = " ".join(w.value for w in list(at.markdown) + list(at.caption)).lower()
        self.assertNotIn("eksakt mål", alle_tekster)
        self.assertNotIn("salgsavdelingen", alle_tekster)


class Test14SekkSperrerEksaktMalIUI(unittest.TestCase):
    """Steg F5: når kjøpsresultatet kommer fra en kombinasjon som inneholder
    en hel 25 kg-sekk, skal _render_eksakt_mal_instruks() IKKE vise noen
    instruks om å oppgi en eksakt mengde i meldingsfeltet -- det ville
    antydet at Vestbrygg kan levere en delmengde av en ferdigpakket sekk,
    noe som ikke er bekreftet mulig (se modules/malt_packaging.py::
    SEKK_STORRELSE_GRAM). Testverten (_sekk_sperret_render_app.py) sender
    inn nøyaktig det kjøpsresultatet malt_packaging.py faktisk produserer i
    dette tilfellet: "bestilling" som en flat liste, uten
    "eksakt_onsket_mengde_gram"."""

    def test_ingen_eksakt_mal_instruks_vises_naar_sekk_inngar(self):
        at = _kjor(_SEKK_SPERRET_APP)
        alle_tekster = " ".join(w.value for w in list(at.markdown) + list(at.caption)).lower()
        self.assertNotIn("eksakt mål", alle_tekster)
        self.assertNotIn("salgsavdelingen", alle_tekster)
        self.assertNotIn("ønsket eksakt mengde", alle_tekster)

    def test_anbefalt_kombinasjon_med_sekk_vises_fortsatt_normalt(self):
        at = _kjor(_SEKK_SPERRET_APP)
        alle_tekster = " ".join(w.value for w in at.markdown)
        self.assertIn("Anbefalt", alle_tekster)
        self.assertIn("25 kg", alle_tekster)
        self.assertIn("700 kr", alle_tekster)


if __name__ == "__main__":
    unittest.main()
