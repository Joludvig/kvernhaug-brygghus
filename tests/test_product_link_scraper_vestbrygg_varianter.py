"""
Tester for Steg F1 og F2: oppdagelse og parsing av Vestbryggs faktiske
barn-/variantprodukter fra maltmor-sidene, inkludert lagerstatus
(modules/product_link_scraper.py::_variant_barnelenker_fra_html /
finn_vestbrygg_malt_med_varianter / _lagerstatus_fra_html).

Bakgrunn (se Steg E-, F1- og F2-rapportene): Vestbrygg strukturerer mange
malter som én mor-produktside pluss opptil fem faktiske barn-/
variantprodukter (1 kg hel, 1 kg knust, 100g knust, 25 kg hel, 25 kg
knust), lenket fra en "VariantVelgerVisuell"-widget i mor-sidens HTML.
Mor-sidens "Fra X,-"-pris er ALLTID kun den billigste barnets pris, aldri
en reell salgspris. Denne funksjonaliteten oppdager de faktiske
barn-lenkene fra rå-HTML — ALDRI ved å konstruere URL-er/varenummer via
det observerte ID-offset-mønsteret.

Steg F2 la i tillegg til lagerstatus-parsing: barn-siden sitt
<body class="in-stock"|"not-in-stock">-signal, verifisert identisk mot
ekte, nedlastet HTML for både Weyermann- og Thomas Fawcett-produkter.

Alle nettverkskall er mocket — ingen ekte HTTP-forespørsler, ingen ekte
raw_data/master-filer røres.
"""
import inspect
import unittest
from unittest.mock import patch

from modules.product_link_scraper import (
    _variant_barnelenker_fra_html,
    finn_vestbrygg_malt_med_varianter,
    parse_produktside,
)
import modules.store_scraper as store_scraper


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"


def _variant_blokk(href, navn, no_stock=False):
    klasse = "VariantChildVisual no-stock" if no_stock else "VariantChildVisual"
    return f"""
        <div class="{klasse}">
            <div id="ctl00_CPHCnt_test_McImg_ctl00">
                <a href="{href}"><img src="/Media/x.jpeg" alt="{navn}" title="{navn}"/></a>
            </div>
            <span class="VariantChildAttribName">{navn}</span>
        </div>"""


def _mor_side_html(varianter):
    """varianter: liste av (href, navn, no_stock)-tupler."""
    blokker = "".join(_variant_blokk(h, n, ns) for h, n, ns in varianter)
    return f"""<html><head><title>Test Mor</title></head><body>
    <div class="BreadCrumb"><a class="BreadCrumbLink">Vestbrygg</a><a class="BreadCrumbLink">Råvarer</a></div>
    <div id="ctl00_CPHCnt_ctl00_ctl00_VariantVelgerVisuell_PnlAtrOne">
        <span class="bold label-attribute1">Malt vekt</span>
        <div class="royalSlider royalSliderVariant rsDefault">
            <div class="variant-slider-row">{blokker}
            </div>
        </div>
    </div>
    <div class="RelatedProducts">
        <a href="/weyermann/99999/urelatert-malt-1-kg-hel">Urelatert malt</a>
    </div>
    <a href="/sitemap">Sitemap</a>
    <a href="#login">Logg inn</a>
    </body></html>"""


def _mor_side_uten_variantvelger():
    return """<html><body>
    <div class="BreadCrumb"><a class="BreadCrumbLink">Vestbrygg</a></div>
    <h1>Spraymalt uten variantvelger</h1>
    </body></html>"""


# Speiler den ekte Bohemian Pilsner Floor Malt-strukturen (fem varianter).
_FEM_VARIANTER = [
    ("/weyermann/20110/test-1-kg-hel", "1 kg heil malt", False),
    ("/weyermann/21110/test-1-kg-knust", "1 kg knust malt", False),
    ("/weyermann/23110/test-100g-knust", "100g knust malt", False),
    ("/weyermann/24110/test-25kg-hel", "25 kg Sekk (heil malt)", False),
    ("/weyermann/25110/test-25kg-knust", "25 kg Sekk (knust malt)", False),
]

# Speiler Carahell/Crystal-strukturen (fire varianter, ingen 25 kg knust).
_FIRE_VARIANTER = [
    ("/weyermann/20216/test-1-kg-hel", "1 kg heil malt", False),
    ("/weyermann/21216/test-1-kg-knust", "1 kg knust malt", False),
    ("/weyermann/23216/test-100g-knust", "100g knust malt", False),
    ("/weyermann/24216/test-25kg-hel", "25 kg Sekk (heil malt)", False),
]


class Test1FemVarianterFinnesAlle(unittest.TestCase):
    def test_mor_med_fem_varianter_finner_alle_fem_barn(self):
        html = _mor_side_html(_FEM_VARIANTER)
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26110/test-mor", html)
        self.assertEqual(len(barn), 5)
        self.assertEqual(barn, [
            "https://vestbrygg.no/weyermann/20110/test-1-kg-hel",
            "https://vestbrygg.no/weyermann/21110/test-1-kg-knust",
            "https://vestbrygg.no/weyermann/23110/test-100g-knust",
            "https://vestbrygg.no/weyermann/24110/test-25kg-hel",
            "https://vestbrygg.no/weyermann/25110/test-25kg-knust",
        ])


class Test2FireVarianterFinnerKunFire(unittest.TestCase):
    def test_mor_med_fire_varianter_finner_kun_fire_barn(self):
        html = _mor_side_html(_FIRE_VARIANTER)
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26216/test-mor", html)
        self.assertEqual(len(barn), 4)


class Test3Manglende25KgKnustIkkeKunstig(unittest.TestCase):
    def test_25kg_knust_opprettes_ikke_naar_den_ikke_finnes(self):
        html = _mor_side_html(_FIRE_VARIANTER)
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26216/test-mor", html)
        self.assertFalse(any("25kg-knust" in u for u in barn))


class Test4Manglende100gHelIkkeKunstig(unittest.TestCase):
    def test_100g_hel_finnes_aldri_i_noen_fixture(self):
        for varianter in (_FEM_VARIANTER, _FIRE_VARIANTER):
            html = _mor_side_html(varianter)
            barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26110/test-mor", html)
            self.assertFalse(any("100g-hel" in u for u in barn))


class Test5RelativeUrlerNormaliseres(unittest.TestCase):
    def test_relativ_href_normaliseres_til_absolutt_mot_mor_url(self):
        html = _mor_side_html([("/weyermann/20999/relativ-test", "1 kg heil malt", False)])
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26999/test-mor", html)
        self.assertEqual(barn, ["https://vestbrygg.no/weyermann/20999/relativ-test"])

    def test_allerede_absolutt_href_endres_ikke(self):
        html = _mor_side_html([
            ("https://vestbrygg.no/weyermann/20999/allerede-absolutt", "1 kg heil malt", False),
        ])
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26999/test-mor", html)
        self.assertEqual(barn, ["https://vestbrygg.no/weyermann/20999/allerede-absolutt"])


class Test6DuplikateLenkerFjernes(unittest.TestCase):
    def test_duplikat_href_i_samme_variantvelger_gir_ett_treff(self):
        html = _mor_side_html([
            ("/weyermann/20110/test-1-kg-hel", "1 kg heil malt", False),
            ("/weyermann/20110/test-1-kg-hel", "1 kg heil malt (duplikat)", False),
        ])
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26110/test-mor", html)
        self.assertEqual(barn, ["https://vestbrygg.no/weyermann/20110/test-1-kg-hel"])

    def test_duplikat_pa_tvers_av_flere_mor_sider_fjernes_i_full_utvidelse(self):
        mor_a = "https://vestbrygg.no/weyermann/26110/mor-a"
        mor_b = "https://vestbrygg.no/weyermann/26120/mor-b"
        felles_barn_html = _mor_side_html([("/weyermann/20110/felles-barn", "1 kg heil malt", False)])

        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.side_effect = lambda url, headers=None, timeout=None: _FakeResponse(felles_barn_html)
            resultat = finn_vestbrygg_malt_med_varianter([mor_a, mor_b])

        self.assertEqual(resultat, ["https://vestbrygg.no/weyermann/20110/felles-barn"])


class Test7DeterministiskUansettRekkefolge(unittest.TestCase):
    def test_barnas_rekkefolge_er_stabil_per_mor_uansett_ytre_rekkefolge(self):
        mor_a = "https://vestbrygg.no/weyermann/26110/mor-a"
        mor_b = "https://vestbrygg.no/weyermann/26216/mor-b"
        html_a = _mor_side_html(_FEM_VARIANTER)
        html_b = _mor_side_html(_FIRE_VARIANTER)

        def _get(url, headers=None, timeout=None):
            return _FakeResponse(html_a if url == mor_a else html_b)

        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.side_effect = _get
            resultat_ab = finn_vestbrygg_malt_med_varianter([mor_a, mor_b])
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.side_effect = _get
            resultat_ba = finn_vestbrygg_malt_med_varianter([mor_b, mor_a])

        barn_a = [u for u in resultat_ab if "20110" in u or "21110" in u or "23110" in u or "24110" in u or "25110" in u]
        barn_b = [u for u in resultat_ab if "20216" in u or "21216" in u or "23216" in u or "24216" in u]

        # Samme indre rekkefølge for hver mor sitt barne-sett, uansett hvor
        # i den ytre lista mor-URL-en selv befant seg:
        self.assertEqual(resultat_ab, barn_a + barn_b)
        self.assertEqual(resultat_ba, barn_b + barn_a)
        self.assertEqual(set(resultat_ab), set(resultat_ba))


class Test8RelaterteProdukterIgnoreres(unittest.TestCase):
    def test_related_products_og_navigasjonslenker_havner_aldri_i_resultatet(self):
        html = _mor_side_html(_FIRE_VARIANTER)
        barn = _variant_barnelenker_fra_html("https://vestbrygg.no/weyermann/26216/test-mor", html)
        self.assertFalse(any("99999" in u for u in barn))
        self.assertFalse(any("sitemap" in u for u in barn))
        self.assertFalse(any(u.endswith("#login") for u in barn))


class Test9BarnSiderParsesKorrekt(unittest.TestCase):
    def _barn_html(self, navn, pris_kr):
        # _extract_price() krever et ",-" eller "kr"-suffiks (samme format
        # Vestbrygg faktisk bruker i synlig tekst -- ekte barn-sider har
        # INGEN "product:price:amount"-metatag, bekreftet mot nedlastet
        # rå-HTML i Steg E/F1, så meta-taggen her er bevisst utelatt).
        return f"""<html><head>
        <meta property="og:title" content="{navn}">
        <meta property="og:description" content="Kvalitetsråvare.">
        </head><body>
        <h1>{navn}</h1>
        <span class="PriceLabel product-price-api">{pris_kr},-</span>
        <script>dataLayer.push({{'BreadCrumb': 'Vestbrygg/Råvarer/Malt/Basemalt'}});</script>
        </body></html>"""

    def test_1kg_knust_barn_gir_korrekt_pakke_gram_og_er_knust(self):
        html = self._barn_html("Test Malt - 1 kg Knust", 54)
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            resultat = parse_produktside(
                "https://vestbrygg.no/weyermann/21110/test-1-kg-knust", "malt", "vestbrygg",
            )
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat["pakke_gram"], 1000.0)
        self.assertTrue(resultat["er_knust"])
        self.assertEqual(resultat["pris"], 54.0)

    def test_100g_knust_barn_gir_korrekt_pakke_gram(self):
        html = self._barn_html("Test Malt - 100g Knust", 7)
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            resultat = parse_produktside(
                "https://vestbrygg.no/weyermann/23110/test-100g-knust", "malt", "vestbrygg",
            )
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat["pakke_gram"], 100.0)
        self.assertTrue(resultat["er_knust"])


class Test10PrisFraBarnAldriMor(unittest.TestCase):
    def test_full_pipeline_bruker_barnets_pris_ikke_mor_sidens_fra_pris(self):
        mor_url = "https://vestbrygg.no/weyermann/26110/test-mor"
        barn_url = "https://vestbrygg.no/weyermann/20110/test-1-kg-hel"

        mor_html = f"""<html><body>
        <div class="BreadCrumb"><a class="BreadCrumbLink">Vestbrygg</a></div>
        <span class="AddPriceLabel">Fra 999,-</span>
        {_variant_blokk("/weyermann/20110/test-1-kg-hel", "1 kg heil malt")}
        </body></html>"""

        barn_html = """<html><head>
        <meta property="og:title" content="Test Malt - 1 kg Hel">
        <meta property="og:description" content="Kvalitetsråvare.">
        </head><body>
        <h1>Test Malt - 1 kg Hel</h1>
        <span class="PriceLabel product-price-api">49,-</span>
        <script>dataLayer.push({'BreadCrumb': 'Vestbrygg/Råvarer/Malt/Basemalt'});</script>
        </body></html>"""

        def _get(url, headers=None, timeout=None):
            return _FakeResponse(mor_html if url == mor_url else barn_html)

        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.side_effect = _get
            urls = finn_vestbrygg_malt_med_varianter([mor_url])
            self.assertEqual(urls, [barn_url])
            rader = [parse_produktside(u, "malt", "vestbrygg") for u in urls]

        self.assertEqual(len(rader), 1)
        self.assertEqual(rader[0]["pris"], 49.0)
        self.assertNotEqual(rader[0]["pris"], 999.0)


class Test11MorUtenVariantvelgerUendret(unittest.TestCase):
    def test_mor_uten_variantvelger_beholdes_uendret(self):
        mor_url = "https://vestbrygg.no/ekstrakt-spraymalt/103793/test-spraymalt"
        html = _mor_side_uten_variantvelger()
        barn = _variant_barnelenker_fra_html(mor_url, html)
        self.assertEqual(barn, [])

        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            resultat = finn_vestbrygg_malt_med_varianter([mor_url])
        self.assertEqual(resultat, [mor_url])


class Test12OlbryggingUendret(unittest.TestCase):
    def test_olbrygging_malt_lenker_utvides_ikke_med_variantfunksjonen(self):
        # Steg F9A: selve malt-innhentingen (både Vestbrygg og Ølbrygging)
        # bor nå i den delte _skann_maltprodukter(), gjenbrukt av både
        # kjor_full_skanning() og kjor_malt_skanning() — se
        # modules/store_scraper.py sin moduldokstreng.
        kilde = inspect.getsource(store_scraper._skann_maltprodukter)
        # Ølbrygging Malt Discovery V1: Ølbrygging-lenkene bygges nå over FLERE
        # linjer (sitemap + kategoriside, forent i et set) i stedet for én
        # enkelt finn_produktsider-linje. Testens hensikt er uendret — ingen av
        # linjene som bygger Ølbrygging-lenkene skal røre Vestbryggs
        # mor-/barn-variantutvidelse — så vi ser på hele Ølbrygging-blokken.
        ol_linjer = [
            linje for linje in kilde.splitlines()
            if "malt_urls_ol" in linje or "malt_lenker_ol" in linje
        ]
        self.assertTrue(ol_linjer, "fant ingen Ølbrygging-malt-linjer i kilden")
        self.assertTrue(
            any("finn_produktsider" in linje for linje in ol_linjer),
            "kategorisiden skal fortsatt være en av Ølbrygging-kildene",
        )
        self.assertTrue(
            any("finn_malt_fra_sitemap" in linje for linje in ol_linjer),
            "sitemap skal være primærkilde for Ølbrygging-malt",
        )
        for linje in ol_linjer:
            self.assertNotIn("finn_vestbrygg_malt_med_varianter", linje)
        # Selve variant-utvidelsen skal kun stå koblet til malt_lenker_vest:
        self.assertIn("finn_vestbrygg_malt_med_varianter(malt_lenker_vest)", kilde)
        # kjor_full_skanning() skal selv ikke lenger inneholde egen
        # malt-lenkelogikk — den gjenbruker _skann_maltprodukter().
        kilde_full = inspect.getsource(store_scraper.kjor_full_skanning)
        self.assertNotIn("malt_lenker_ol", kilde_full)
        self.assertIn("_skann_maltprodukter()", kilde_full)


class Test13HumleOgGjaerUendret(unittest.TestCase):
    def test_humle_og_gjaer_flyt_refererer_ikke_variantfunksjonen(self):
        kilde = inspect.getsource(store_scraper.kjor_full_skanning)
        humle_gjaer_del = kilde[kilde.index("SKANNER HUMLE"):]
        self.assertNotIn("finn_vestbrygg_malt_med_varianter", humle_gjaer_del)


class Test14IngenRekursivLoekke(unittest.TestCase):
    def test_barn_som_peker_tilbake_til_mor_gir_ingen_ekstra_nettverkskall(self):
        mor_url = "https://vestbrygg.no/weyermann/26110/test-mor"
        # Mor-siden lenker (feilaktig/uvanlig) tilbake til seg selv som en
        # av "variantene" -- funksjonen skal likevel ALDRI hente denne på
        # nytt (ingen rekursivt kall), siden den bare behandler den
        # opprinnelige mor_urls-listen.
        html = _mor_side_html([
            ("/weyermann/26110/test-mor", "Selvreferanse", False),
            ("/weyermann/20110/test-1-kg-hel", "1 kg heil malt", False),
        ])

        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            finn_vestbrygg_malt_med_varianter([mor_url])
            # Nøyaktig ett kall -- ett per opprinnelig mor-URL, uansett hva
            # barn-lenkene i den hentede HTML-en peker til.
            self.assertEqual(mock_get.call_count, 1)


# ------------------------------------------------------------------
# Steg F2: lagerstatus-signalet parse_produktside() nå leser fra
# barn-siden sitt <body class="in-stock"|"not-in-stock">-signal.
# ------------------------------------------------------------------

def _barn_html_med_body_klasse(navn, body_klasse, pris_kr=49):
    return f"""<html><head>
    <meta property="og:title" content="{navn}">
    <meta property="og:description" content="Kvalitetsråvare.">
    </head><body class="{body_klasse}">
    <h1>{navn}</h1>
    <span class="PriceLabel product-price-api">{pris_kr},-</span>
    <script>dataLayer.push({{'BreadCrumb': 'Vestbrygg/Råvarer/Malt/Basemalt'}});</script>
    </body></html>"""


class Test5LagerstatusPaLagerParsesKorrekt(unittest.TestCase):
    def test_in_stock_body_klasse_gir_pa_lager(self):
        html = _barn_html_med_body_klasse(
            "Test Malt - 1 kg Hel",
            "body-out fav-body mode-normal in-stock body-product-info",
        )
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            resultat = parse_produktside(
                "https://vestbrygg.no/weyermann/20110/test-1-kg-hel", "malt", "vestbrygg",
            )
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat["lagerstatus"], "pa_lager")


class Test6LagerstatusUtsolgtParsesKorrekt(unittest.TestCase):
    def test_not_in_stock_body_klasse_gir_utsolgt(self):
        html = _barn_html_med_body_klasse(
            "Test Malt - 25 kg Hel",
            "body-out fav-body mode-normal not-in-stock body-product-info",
        )
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            resultat = parse_produktside(
                "https://vestbrygg.no/weyermann/24110/test-25kg-hel", "malt", "vestbrygg",
            )
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat["lagerstatus"], "utsolgt")


class Test7LagerstatusUkjentHandteresEksplisitt(unittest.TestCase):
    def test_manglende_signal_gir_eksplisitt_ukjent_ikke_utsolgt(self):
        html = _barn_html_med_body_klasse(
            "Test Malt uten kjent lagerstatus",
            "body-out fav-body mode-normal body-product-info",  # verken in-stock eller not-in-stock
        )
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse(html)
            resultat = parse_produktside(
                "https://vestbrygg.no/weyermann/29999/test-uten-signal", "malt", "vestbrygg",
            )
        self.assertIsNotNone(resultat)
        self.assertEqual(resultat["lagerstatus"], "ukjent")
        self.assertNotEqual(resultat["lagerstatus"], "utsolgt")


if __name__ == "__main__":
    unittest.main()
