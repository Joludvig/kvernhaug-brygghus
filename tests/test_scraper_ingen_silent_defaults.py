"""
Låser kontrakten fra Supplier Data Cleanup V1: scraperen skal ALDRI produsere
en verdi som ser målt/skrapet ut når den i virkeligheten er en fallback.

Bakgrunn (Favorittbutikk-audit V1, målt på raw_data/): fire umerkede defaults
gjorde butikkdataene upålitelige, uten at noen konsument kunne se det:

  ebc = 4.0          en helt vanlig, ekte EBC for lys basemalt
  alfa = 5.0         en fullt plausibel alfasyre -- 44 av 44 Vestbrygg-humler
                     fikk denne uten at butikken oppga noe som helst
  pris = 45.0/69.0   fallback presentert som butikkpris
  attenuation = 0.75 skrevet på ALLE produkter, også malt og humle

Prinsippet som håndheves her er KBH-prinsippet «ukjent > falsk presisjon»,
samme linje som KBH_CORE_CONTRACT § 9 «No smart guessing»: manglende data skal
være eksplisitt manglende (None), aldri en oppdiktet verdi.

Alle nettverkskall er mocket -- ingen ekte HTTP-forespørsler.
"""
import inspect
import unittest
from unittest.mock import patch

from modules.product_link_scraper import parse_produktside
from modules.store_matcher import _pris_per_kg


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"


def _html(navn, breadcrumb, beskrivelse="Kvalitetsråvare.", pris_meta=None):
    """Produktside med dataLayer-brødsmule (primærsignalet hos begge butikker).

    pris_meta=None gir en side HELT uten prisinformasjon -- det er nettopp
    tilfellet der den gamle fallback-prisen slo inn.
    """
    pris_tag = (f'<meta property="product:price:amount" content="{pris_meta}">'
                if pris_meta else "")
    return f"""<html><head>
<meta property="og:title" content="{navn}">
<meta property="og:description" content="{beskrivelse}">
{pris_tag}
</head><body>
<h1>{navn}</h1>
<script>
    dataLayer.push({{
        'event': 'ProductPage',
        'BreadCrumb': '{breadcrumb}',
    }});
</script>
</body></html>"""


MALT_SMULE = "Hjem/Råvarer/Malt"
HUMLE_SMULE = "Hjem/Råvarer/Humle"
GJAER_SMULE = "Hjem/Råvarer/Gjær"

# URL uten "-<tall>-ebc"-mønster, slik at URL-fallbacken for EBC ikke slår inn.
URL_UTEN_EBC = "https://vestbrygg.no/weyermann/26110/test-produkt"


def _parse(html, kategori, url=URL_UTEN_EBC, butikk="vestbrygg"):
    with patch("modules.product_link_scraper.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(html)
        return parse_produktside(url, kategori, butikk)


class TestIngenSilentDefaults(unittest.TestCase):
    """Manglende data skal bli None -- aldri en plausibel, oppdiktet verdi."""

    def test_manglende_ebc_blir_none_ikke_4(self):
        res = _parse(_html("Pale Ale Malt", MALT_SMULE), "malt")
        self.assertIsNotNone(res)
        self.assertIsNone(res["ebc"], "manglende EBC må være None, aldri 4.0")
        self.assertNotEqual(res["ebc"], 4.0)

    def test_manglende_alfa_blir_none_ikke_5(self):
        res = _parse(_html("Tettnang Humle Pellets - 100g", HUMLE_SMULE), "humle")
        self.assertIsNotNone(res)
        self.assertIsNone(res["alfa"], "manglende alfasyre må være None, aldri 5.0")
        self.assertNotEqual(res["alfa"], 5.0)

    def test_manglende_pris_blir_none_ikke_45_eller_69(self):
        for navn, smule, kategori in [
            ("Pale Ale Malt", MALT_SMULE, "malt"),
            ("Saaz Humle Pellets - 100g", HUMLE_SMULE, "humle"),
            ("SafAle US-05", GJAER_SMULE, "gjaer"),
        ]:
            with self.subTest(kategori=kategori):
                res = _parse(_html(navn, smule), kategori)
                self.assertIsNotNone(res)
                self.assertIsNone(res["pris"], "manglende pris må være None")
                self.assertNotIn(res["pris"], (45.0, 69.0))

    def test_gjaer_far_ikke_generell_attenuation(self):
        res = _parse(_html("SafAle US-05", GJAER_SMULE), "gjaer")
        self.assertIsNotNone(res)
        self.assertIsNone(res["attenuation"],
                          "attenuation eies av masterdata, ikke av et butikkprodukt")
        self.assertNotEqual(res["attenuation"], 0.75)

    def test_malt_og_humle_far_heller_ikke_attenuation(self):
        # Den gamle defaulten ble skrevet på ALLE kategorier, ikke bare gjær.
        for navn, smule, kategori in [
            ("Pale Ale Malt", MALT_SMULE, "malt"),
            ("Saaz Humle Pellets - 100g", HUMLE_SMULE, "humle"),
        ]:
            with self.subTest(kategori=kategori):
                res = _parse(_html(navn, smule), kategori)
                self.assertIsNone(res["attenuation"])

    def test_ikke_humle_far_ikke_falsk_alfa_null(self):
        # Tidligere ble alfa initialisert til 0.0 for malt/gjær -- et tall som
        # ser ut som en måling. Feltet er ikke relevant utenfor humle.
        for navn, smule, kategori in [
            ("Pale Ale Malt", MALT_SMULE, "malt"),
            ("SafAle US-05", GJAER_SMULE, "gjaer"),
        ]:
            with self.subTest(kategori=kategori):
                res = _parse(_html(navn, smule), kategori)
                self.assertIsNone(res["alfa"])


class TestEkteVerdierBevares(unittest.TestCase):
    """Fjerningen av defaults må ikke svekke uthenting av ekte data."""

    def test_ekte_ebc_fra_navn_bevares(self):
        res = _parse(_html("Caramunich 2 Malt 120 EBC", MALT_SMULE), "malt")
        self.assertEqual(res["ebc"], 120.0)

    def test_ekte_ebc_fra_url_bevares(self):
        res = _parse(
            _html("Bohemian Pilsner Floor Malt", MALT_SMULE), "malt",
            url="https://vestbrygg.no/weyermann/20110/bohemian-pilsner-floor-malt-1-kg-hel-4-ebc--weyermann",
        )
        self.assertEqual(res["ebc"], 4.0,
                         "en EKTE 4 EBC fra URL skal fortsatt hentes ut")

    def test_ekte_alfa_fra_beskrivelse_bevares(self):
        # Ølbrygging-mønsteret: "13,9% AA, Nitrogenpakket"
        res = _parse(
            _html("Citra 2024 100 g", HUMLE_SMULE, beskrivelse="13,9% AA, Nitrogenpakket"),
            "humle",
        )
        self.assertEqual(res["alfa"], 13.9)

    def test_ekte_pris_bevares(self):
        res = _parse(_html("Pale Ale Malt", MALT_SMULE, pris_meta="49,00 kr"), "malt")
        self.assertEqual(res["pris"], 49.0)


class TestNedstromsTalerNone(unittest.TestCase):
    """store_matcher er den eneste LIVE konsumenten av rå scraperdata."""

    def test_pris_per_kg_returnerer_none_for_ukjent_pris(self):
        for kategori in ("malt", "humle", "gjaer"):
            with self.subTest(kategori=kategori):
                self.assertIsNone(_pris_per_kg(None, 1000.0, kategori))
                self.assertIsNone(_pris_per_kg(None, None, kategori))

    def test_pris_per_kg_regner_fortsatt_riktig_for_ekte_pris(self):
        self.assertEqual(_pris_per_kg(49.0, 1000.0, "malt"), 49.0)
        self.assertEqual(_pris_per_kg(24.5, 500.0, "malt"), 49.0)
        self.assertEqual(_pris_per_kg(69.0, None, "gjaer"), 69.0)


class TestEksplisittOverrideSkillesFraDefault(unittest.TestCase):
    """
    Wyeast 1318 (Litebrygg) får attenuation 0.73 satt manuelt i
    store_scraper.py. Etter at den generelle 0.75-defaulten er borte, BETYR en
    attenuation-verdi at noen har bestemt den -- ikke at systemet gjettet.
    Denne testen låser at overriden fortsatt er eksplisitt i koden, slik at
    den ikke ryddes bort som om den var enda en fallback.
    """

    def test_wyeast_1318_override_er_fortsatt_eksplisitt(self):
        import modules.store_scraper as store_scraper
        kilde = inspect.getsource(store_scraper.kjor_full_skanning)
        self.assertIn('res_1318["attenuation"] = 0.73', kilde)
        self.assertIn('res_1318["produsent"] = "Wyeast"', kilde)


if __name__ == "__main__":
    unittest.main()
