"""
Tester for modules/export_format.py::sanitize_url() og bruken av den i
modules/shopping_template.py.

Bakgrunn: html.escape(..., quote=True) hindrer en produkt-URL fra å
bryte ut av href='...'-attributtet (anførselstegn-utbryting), men
hindrer IKKE selve URL-en fra å bruke et farlig SKJEMA --
"javascript:alert(1)" er, fullt escapet eller ikke, fortsatt en
javascript:-URL som kjører når lenken klikkes. sanitize_url() er et
EGET, tidligere steg: en allowlist (kun http/https), ikke en blokkliste.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.export_format import sanitize_url
from modules.shopping_template import render_shopping_list_html


def _ctx(navn="Test Brygg"):
    return {"name": navn, "volum": 20.0}


class TestSanitizeUrlGyldigeUrler(unittest.TestCase):
    def test_https_url_godtas(self):
        url = "https://vestbrygg.no/weyermann/26110/bohemian-pilsner-floor-malt-4-ebc--weyermann"
        self.assertEqual(sanitize_url(url), url)

    def test_http_url_godtas(self):
        url = "http://www.olbrygging.no/weyermann/101046/bohemian-pilsner-malt-4-ebc-weyermann"
        self.assertEqual(sanitize_url(url), url)

    def test_ekte_norske_butikk_urler_godtas(self):
        for url in (
            "https://vestbrygg.no/",
            "https://www.olbrygging.no/produkt/12345",
            "https://vestbrygg.no/thomas-fawcett/26302/chocolate-malt-1175-ebc--thomas-fawcett",
            "https://www.olbrygging.no/castle-malting/102973/ch%C3%A2teau-acid-malt-6-12-ebc-castle-malting",
        ):
            with self.subTest(url=url):
                self.assertEqual(sanitize_url(url), url)

    def test_https_case_insensitivt_skjema_godtas(self):
        self.assertIsNotNone(sanitize_url("HTTPS://vestbrygg.no/produkt"))
        self.assertIsNotNone(sanitize_url("HtTpS://vestbrygg.no/produkt"))

    def test_ledende_whitespace_strippes_og_godtas(self):
        self.assertEqual(sanitize_url("   https://vestbrygg.no/produkt"), "https://vestbrygg.no/produkt")
        self.assertEqual(sanitize_url("\n\thttps://vestbrygg.no/produkt  "), "https://vestbrygg.no/produkt")


class TestSanitizeUrlFarligeSkjemaAvvises(unittest.TestCase):
    def test_javascript_skjema_avvises(self):
        self.assertIsNone(sanitize_url("javascript:alert(1)"))
        self.assertIsNone(sanitize_url("JAVASCRIPT:alert(1)"))
        self.assertIsNone(sanitize_url("JavaScript:alert(document.cookie)"))

    def test_data_skjema_avvises(self):
        self.assertIsNone(sanitize_url("data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="))

    def test_file_skjema_avvises(self):
        self.assertIsNone(sanitize_url("file:///etc/passwd"))

    def test_vbscript_skjema_avvises(self):
        self.assertIsNone(sanitize_url("vbscript:msgbox(1)"))

    def test_ukjent_skjema_avvises(self):
        self.assertIsNone(sanitize_url("ftp://example.com/fil"))
        self.assertIsNone(sanitize_url("custom-scheme://noe"))
        self.assertIsNone(sanitize_url("tel:+4712345678"))

    def test_kontrolltegn_midt_i_skjema_avvises_ikke_omgaas(self):
        # Klassisk filter-omgåelse: nettlesere har historisk ignorert
        # kontrolltegn (tab/linjeskift) MIDT I et skjema, slik at
        # "java\tscript:" i praksis blir en ekte javascript:-URL selv om
        # en naiv "starter med javascript:"-sjekk ikke ville sett det.
        self.assertIsNone(sanitize_url("java\tscript:alert(1)"))
        self.assertIsNone(sanitize_url("java\nscript:alert(1)"))
        self.assertIsNone(sanitize_url("java\rscript:alert(1)"))
        self.assertIsNone(sanitize_url("\tjavascript:alert(1)"))

    def test_skjemaless_relativ_sti_avvises(self):
        # Ingen netloc -- ikke en gyldig, absolutt butikk-URL.
        self.assertIsNone(sanitize_url("/produkt/123"))
        self.assertIsNone(sanitize_url("javascript:void(0)"))


class TestSanitizeUrlUgyldigInput(unittest.TestCase):
    def test_none_gir_none(self):
        self.assertIsNone(sanitize_url(None))

    def test_tom_streng_gir_none(self):
        self.assertIsNone(sanitize_url(""))

    def test_kun_whitespace_gir_none(self):
        self.assertIsNone(sanitize_url("   \t\n  "))

    def test_ikke_streng_gir_none(self):
        self.assertIsNone(sanitize_url(12345))
        self.assertIsNone(sanitize_url(["https://vestbrygg.no"]))


class TestGenerertHandlelisteHtmlBrukerSanitizeUrl(unittest.TestCase):
    """Tester den FAKTISKE genererte HTML-en fra render_shopping_list_html(),
    ikke bare sanitize_url() isolert."""

    def _malt_item(self, url):
        return {"navn": "Test Malt", "mengde": 5.0, "total": 100.0, "er_estimat": False, "url": url}

    def test_gyldig_https_url_blir_klikkbar_lenke_i_html(self):
        html = render_shopping_list_html(
            _ctx(), [self._malt_item("https://vestbrygg.no/produkt/123")], [], None, "Vestbrygg.no",
        )
        self.assertIn("<a href='https://vestbrygg.no/produkt/123'>Test Malt</a>", html)

    def test_javascript_url_blir_ikke_klikkbar_lenke(self):
        html = render_shopping_list_html(
            _ctx(), [self._malt_item("javascript:alert(document.cookie)")], [], None, "Vestbrygg.no",
        )
        self.assertNotIn("<a href=", html)
        self.assertNotIn("javascript:", html)
        # Navnet skal likevel vises -- bare uten lenke.
        self.assertIn("Test Malt", html)

    def test_data_url_blir_ikke_klikkbar_lenke(self):
        html = render_shopping_list_html(
            _ctx(), [self._malt_item("data:text/html,<script>alert(1)</script>")], [], None, "Vestbrygg.no",
        )
        self.assertNotIn("<a href=", html)
        # NB: sjekker IKKE bare "data:" i hele dokumentet -- KBH-logoen
        # legges alltid inn som en legitim data:image/png;base64,...-URI
        # i <img src>, uavhengig av denne testen. Det som faktisk skal
        # avvises er en data:-URL i en klikkbar LENKE.
        self.assertNotIn("href='data:", html)
        self.assertIn("Test Malt", html)

    def test_manglende_url_blir_ikke_klikkbar_lenke_som_foer(self):
        html = render_shopping_list_html(_ctx(), [self._malt_item(None)], [], None, "Vestbrygg.no")
        self.assertNotIn("<a href=", html)
        self.assertIn("Test Malt", html)

    def test_gjaer_og_humle_urler_valideres_paa_samme_maate(self):
        humle_items = [{"navn": "Ond Humle", "gram": 20.0, "tid": 60, "total": 50.0,
                         "er_estimat": False, "url": "javascript:alert(1)"}]
        gjaer_item = {"navn": "Ond Gjær", "pris": 59.0, "er_estimat": False, "url": "vbscript:msgbox(1)"}
        html = render_shopping_list_html(_ctx(), [], humle_items, gjaer_item, "Vestbrygg.no")
        self.assertNotIn("<a href=", html)
        self.assertNotIn("javascript:", html)
        self.assertNotIn("vbscript:", html)
        self.assertIn("Ond Humle", html)
        self.assertIn("Ond Gjær", html)


if __name__ == "__main__":
    unittest.main()
