"""
Tester for brødsmule-basert produkttype-filtrering i modules/product_link_scraper.py.

Bakgrunn: "Belgian Saison ekstraktsett" (et komplett ølsett, ikke en gjær) havnet
i raw_data/gjaer_raw.json og deretter unmatched_gjaer.json fordi produktnavnet
inneholdt "saison" — et positivt nøkkelord i gjaer_valid — mens gjaer_block ikke
kjente igjen det norske "ekstraktsett" (kun det engelske "extract"). Roten er at
nøkkelordbasert filtrering på produktnavn er inherent lekk.

parse_produktside() sjekker nå butikkens egen kategori-taksonomi (brødsmulesti)
før produktnavn-nøkkelord i det hele tatt vurderes:
1. GTM dataLayer-feltet 'BreadCrumb' (primærsignal, identisk hos begge butikker)
2. Synlig HTML-brødsmule via `.BreadCrumbLink` (fallback)
3. Eksisterende nøkkelordlogikk (siste sikkerhetsnett, kun når 1 og 2 mangler)

Alle nettverkskall er mocket — ingen ekte HTTP-forespørsler.
"""
import unittest
from unittest.mock import patch

from modules.product_link_scraper import parse_produktside


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"


def _html_med_datalayer_breadcrumb(navn, breadcrumb, beskrivelse="Kvalitetsråvare."):
    return f"""<html><head>
<meta property="og:title" content="{navn}">
<meta property="og:description" content="{beskrivelse}">
<meta property="product:price:amount" content="99.00">
</head><body>
<h1>{navn}</h1>
<script>
    dataLayer.push({{
        'Brand': 'Ukjent',
        'event': 'ProductPage',
        'BreadCrumb': '{breadcrumb}',
        'ProductID': '12345',
    }});
</script>
</body></html>"""


def _html_med_dom_breadcrumb(navn, segmenter, beskrivelse="Kvalitetsråvare."):
    lenker = "".join(f'<a class="BreadCrumbLink">{s}</a>' for s in segmenter)
    return f"""<html><head>
<meta property="og:title" content="{navn}">
<meta property="og:description" content="{beskrivelse}">
<meta property="product:price:amount" content="99.00">
</head><body>
<h1>{navn}</h1>
<div class="BreadCrumb">{lenker}</div>
</body></html>"""


def _html_uten_breadcrumb(navn, beskrivelse="Kvalitetsråvare."):
    return f"""<html><head>
<meta property="og:title" content="{navn}">
<meta property="og:description" content="{beskrivelse}">
<meta property="product:price:amount" content="99.00">
</head><body>
<h1>{navn}</h1>
</body></html>"""


class TestBrodsmuleKlassifisering(unittest.TestCase):

    def _parse(self, html, kategori, url="https://vestbrygg.no/weyermann/26110/test-produkt"):
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            return parse_produktside(url, kategori, "vestbrygg")

    def test_ekte_malt_godtas_via_datalayer(self):
        html = _html_med_datalayer_breadcrumb(
            "Bohemian Pilsner Floor Malt", "Vestbrygg/Råvarer/Malt/Basemalt"
        )
        resultat = self._parse(html, "malt")
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat["navn"], "Bohemian Pilsner Floor Malt")

    def test_ekte_humle_godtas_via_datalayer(self):
        html = _html_med_datalayer_breadcrumb(
            "Tettnang Humle Pellets 100g", "Vestbrygg/Råvarer/Humle/Pellets"
        )
        resultat = self._parse(html, "humle")
        self.assertIsNotNone(resultat)

    def test_ekte_gjaer_godtas_via_datalayer(self):
        html = _html_med_datalayer_breadcrumb(
            "WLP940 Mexican Lager Pure Pitch", "Vestbrygg/Råvarer/Gjær/Fersk Gjær"
        )
        resultat = self._parse(html, "gjaer")
        self.assertIsNotNone(resultat)

    def test_ekstraktsett_avvises_selv_med_positivt_navn_nokkelord(self):
        # "saison" er et positivt nøkkelord i gjaer_valid — brødsmulen skal
        # likevel avvise produktet før nøkkelordlogikken noensinne kjører.
        html = _html_med_datalayer_breadcrumb(
            "Belgian Saison ekstraktsett", "Ølbrygging/Øl/Ølsett/Ekstraktsett"
        )
        resultat = self._parse(html, "gjaer")
        self.assertIsNone(resultat)

    def test_deny_segment_overstyrer_allow_og_positivt_navn_nokkelord(self):
        # Kontrivert, men beviser at deny slår igjennom selv når brødsmulen
        # OGSÅ inneholder det påkrevde allow-segmentet (råvarer/gjær) og
        # navnet har et sterkt positivt nøkkelord ("yeast").
        html = _html_med_datalayer_breadcrumb(
            "Some Yeast Product", "Vestbrygg/Råvarer/Gjær/Ølsett"
        )
        resultat = self._parse(html, "gjaer")
        self.assertIsNone(resultat)

    def test_manglende_datalayer_faller_tilbake_til_dom_breadcrumb(self):
        html = _html_med_dom_breadcrumb(
            "Bohemian Pilsner Floor Malt", ["Vestbrygg", "Råvarer", "Malt", "Basemalt"]
        )
        resultat = self._parse(html, "malt")
        self.assertIsNotNone(resultat)

    def test_dom_breadcrumb_avviser_ekstraktsett(self):
        html = _html_med_dom_breadcrumb(
            "Belgian Saison ekstraktsett", ["Ølbrygging", "Øl", "Ølsett", "Ekstraktsett"]
        )
        resultat = self._parse(html, "gjaer")
        self.assertIsNone(resultat)

    def test_manglende_begge_brodsmuler_bruker_eksisterende_nokkelordlogikk_godtar(self):
        html = _html_uten_breadcrumb("Weyermann Pilsner Malt 25 kg")
        resultat = self._parse(html, "malt")
        self.assertIsNotNone(resultat)

    def test_manglende_begge_brodsmuler_bruker_eksisterende_nokkelordlogikk_avviser(self):
        html = _html_uten_breadcrumb("Tilfeldig Tilbehørsting")
        resultat = self._parse(html, "malt")
        self.assertIsNone(resultat)

    def test_datalayer_store_bokstaver_og_ekstra_mellomrom_handteres(self):
        html = _html_med_datalayer_breadcrumb(
            "Bohemian Pilsner Floor Malt", "Vestbrygg/RÅVARER/MALT/Basemalt"
        )
        resultat = self._parse(html, "malt")
        self.assertIsNotNone(resultat)

    def test_dom_breadcrumb_mellomrom_og_store_bokstaver_handteres(self):
        html = _html_med_dom_breadcrumb(
            "Bohemian Pilsner Floor Malt",
            ["  Vestbrygg  ", "\n  RÅVARER \n", "MALT", " Basemalt "],
        )
        resultat = self._parse(html, "malt")
        self.assertIsNotNone(resultat)


if __name__ == "__main__":
    unittest.main()
