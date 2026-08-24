"""
Tester for sitemap-basert malt-discovery (Ølbrygging Malt Discovery V1).

ROTÅRSAK som låses her: Ølbrygging-malt ble tidligere KUN oppdaget via
kategorisiden /ol/ingredienser/malt?page=N. Den siden ignorerer ?page-
parameteren -- side 1, 2 og 3 returnerer byte-identisk innhold med de samme
28 produktlenkene -- så finn_produktsider() stoppet på 28 malter uansett hvor
stort sortimentet faktisk er. Sitemapet inneholder vesentlig flere.

Begge butikkene kjører McWeb 3.15.2 og deler URL-grammatikk
(/<merke-eller-kategori>/<varenummer>/<slug>), så den samme sitemap-logikken
som humle og gjær allerede brukte, gjelder også for malt. Derfor er de tre
funksjonene nå ett felles oppslag med hver sin sti-liste som data.

Kategorisiden er beholdt som SUPPLEMENT, ikke erstattet: den inneholder
produkter som mangler i sitemapet (verifisert mot ekte data: fire CaraRed-
varianter). Kalleren tar unionen.

Alle nettverkskall er mocket -- ingen test her gjør ekte HTTP.
"""
import re
import unittest
from unittest.mock import patch

from modules.product_link_scraper import (
    GJAER_SITEMAP_PATHS,
    HUMLE_SITEMAP_PATHS,
    MALT_SITEMAP_PATHS,
    finn_malt_fra_sitemap,
    finn_humle_fra_sitemap,
    finn_gjær_fra_sitemap,
)


class _FakeResponse:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code
        self.apparent_encoding = "utf-8"
        self.encoding = "utf-8"


def _sitemap(urls):
    inner = "".join(f"<url><loc>{u}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?><urlset>{inner}</urlset>'


OL = "https://www.olbrygging.no"
VB = "https://vestbrygg.no"

# Ekte URL-former, hentet fra butikkenes sitemap / raw_data.
MALT_OL = [
    f"{OL}/weyermann/101046/bohemian-pilsner-malt-4-ebc-weyermann",
    f"{OL}/weyermann/102275/carafa-special-ii-malt-1100-ebc-weyermann",
    f"{OL}/viking-malt/106260/carabody-max-8-ebc-viking-malt",
    f"{OL}/castle-malting/104001/chateau-pilsen-3-5-ebc",
    f"{OL}/simpsons-malt/105001/golden-promise-6-ebc",
    f"{OL}/bonsak-g%c3%a5rdsmalteri/105500/bonsak-rugmalt-hel",
    f"{OL}/j%c3%a6rmalt/105600/jaermalt-pilsner-hel",
]
IKKE_MALT_OL = [
    f"{OL}/kegland/108001/malt-muncher-med-3-valser-maltm%c3%b8lle",
    f"{OL}/brewtools/108002/brewtools-b40pro-9kg-malt-dot--no-eu",
    f"{OL}/caputo/108003/caputo-nuvola-tipo-0-finmalt-italiensk-mel",
    f"{OL}/humle/110600/citra-2024-100g-13-9pcnt-aa-nitrogenpakket",
    f"{OL}/fermentis/109001/safale-us-05",
    f"{OL}/ol/ingredienser/malt",          # kategoriside, ikke produkt
    f"{OL}/weyermann/abc/uten-varenummer",  # mangler McWeb-varenummer
]


def _hent(funksjon, base_url, urls):
    with patch("modules.product_link_scraper.requests.get") as mock_get:
        mock_get.return_value = _FakeResponse(_sitemap(urls))
        return funksjon(base_url)


class TestMaltDiscoveryFraSitemap(unittest.TestCase):

    def test_finner_maltprodukter_fra_sitemap(self):
        funnet = _hent(finn_malt_fra_sitemap, OL, MALT_OL + IKKE_MALT_OL)
        for u in MALT_OL:
            self.assertIn(u, funnet, f"skulle funnet {u}")

    def test_filtrerer_bort_ikke_malt(self):
        funnet = set(_hent(finn_malt_fra_sitemap, OL, MALT_OL + IKKE_MALT_OL))
        for u in IKKE_MALT_OL:
            self.assertNotIn(u, funnet, f"skulle IKKE funnet {u}")

    def test_krever_mcweb_varenummer_i_url(self):
        # Et merkesegment alene er ikke nok -- URL-en må ha /<4+ siffer>/.
        uten = f"{OL}/weyermann/12/for-kort-varenummer"
        med = f"{OL}/weyermann/1234/gyldig-varenummer"
        funnet = set(_hent(finn_malt_fra_sitemap, OL, [uten, med]))
        self.assertIn(med, funnet)
        self.assertNotIn(uten, funnet)

    def test_tomt_sitemap_gir_tom_liste_ikke_krasj(self):
        self.assertEqual(_hent(finn_malt_fra_sitemap, OL, []), [])

    def test_http_feil_gir_tom_liste_ikke_krasj(self):
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.return_value = _FakeResponse("", status_code=500)
            self.assertEqual(finn_malt_fra_sitemap(OL), [])

    def test_nettverksfeil_gir_tom_liste_ikke_krasj(self):
        with patch("modules.product_link_scraper.requests.get") as mock_get:
            mock_get.side_effect = OSError("nettverk nede")
            self.assertEqual(finn_malt_fra_sitemap(OL), [])


class TestEksisterendeDiscoveryUendret(unittest.TestCase):
    """Humle- og gjær-discovery skal fungere nøyaktig som før refaktoreringen."""

    def test_humle_discovery_fortsatt_intakt(self):
        humle = [
            f"{VB}/pellets/30648/tettnang-humle-pellets-100g-tyskland",
            f"{OL}/humle/110600/citra-2024-100g-13-9pcnt-aa",
        ]
        annet = [f"{OL}/weyermann/101046/bohemian-pilsner-malt-4-ebc"]
        funnet = set(_hent(finn_humle_fra_sitemap, OL, humle + annet))
        self.assertIn(humle[1], funnet)
        self.assertNotIn(annet[0], funnet)

    def test_gjaer_discovery_fortsatt_intakt(self):
        gjaer = [
            f"{OL}/whitelabs/107077/wlp810-san-francisco-lager-70ml",
            f"{OL}/fermentis/109001/safale-us-05-11-5g",
        ]
        annet = [f"{OL}/weyermann/101046/bohemian-pilsner-malt-4-ebc"]
        funnet = set(_hent(finn_gjær_fra_sitemap, OL, gjaer + annet))
        for u in gjaer:
            self.assertIn(u, funnet)
        self.assertNotIn(annet[0], funnet)

    def test_vestbrygg_www_normaliseres_til_apex(self):
        # Vestbrygg publiserer sitemap-URL-er med www, mens resten av kodebasen
        # bruker apex-domenet. Uten normalisering ville samme produkt kunne
        # skrapes to ganger.
        funnet = _hent(finn_humle_fra_sitemap, VB,
                       ["https://www.vestbrygg.no/pellets/30648/tettnang-humle-pellets"])
        self.assertEqual(funnet, ["https://vestbrygg.no/pellets/30648/tettnang-humle-pellets"])

    def test_olbrygging_www_bevares(self):
        # Motsatt av Vestbrygg: hos Ølbrygging ER www den kanoniske formen.
        url = f"{OL}/weyermann/101046/bohemian-pilsner-malt-4-ebc"
        self.assertEqual(_hent(finn_malt_fra_sitemap, OL, [url]), [url])


class TestDuplikaterOgDatadrevetKonfig(unittest.TestCase):

    def test_union_av_sitemap_og_kategoriside_fjerner_duplikater(self):
        # Slik store_scraper._skann_maltprodukter() kombinerer de to kildene.
        felles = f"{OL}/weyermann/101046/bohemian-pilsner-malt-4-ebc"
        kun_sitemap = f"{OL}/viking-malt/106260/carabody-max-8-ebc"
        kun_kategori = f"{OL}/weyermann/101122/carared-1-kg-knust-50-ebc"
        union = sorted({felles, kun_sitemap} | {felles, kun_kategori})
        self.assertEqual(len(union), 3, "felles URL skal telle én gang")
        self.assertEqual(union, sorted(set(union)), "ingen duplikater")

    def test_sti_listene_er_data_ikke_produktlister(self):
        # En sti-liste skal inneholde URL-SEGMENTER (merke/kategori), aldri
        # ferdige produkt-URL-er -- ellers er det en hardkodet produktliste.
        for navn, stier in [
            ("MALT", MALT_SITEMAP_PATHS),
            ("HUMLE", HUMLE_SITEMAP_PATHS),
            ("GJAER", GJAER_SITEMAP_PATHS),
        ]:
            with self.subTest(liste=navn):
                self.assertTrue(stier)
                for sti in stier:
                    self.assertTrue(sti.startswith("/"), sti)
                    self.assertTrue(sti.endswith("/"), sti)
                    self.assertNotIn("http", sti, "ingen absolutte URL-er")
                    # Et McWeb-varenummer er 4+ sammenhengende siffer. Enkelt-
                    # siffer forekommer legitimt i prosentkoding (%c3%a5 = å).
                    self.assertIsNone(re.search(r"\d{4,}", sti),
                                      f"{sti} ser ut som et varenummer/produkt")

    def test_malt_stier_dekker_de_faktiske_maltmerkene_hos_olbrygging(self):
        for merke in ["/weyermann/", "/viking-malt/", "/castle-malting/",
                      "/muntons/", "/simpsons-malt/"]:
            self.assertIn(merke, MALT_SITEMAP_PATHS)


class TestStoreScraperBrukerBeggeKilder(unittest.TestCase):
    """
    Låser at Ølbrygging-malt faktisk henter fra BEGGE kilder. Uten dette kunne
    sitemap-kallet fjernes igjen uten at noen test merket det.
    """

    def test_skann_maltprodukter_kaller_bade_sitemap_og_kategoriside(self):
        import inspect
        import modules.store_scraper as store_scraper
        kilde = inspect.getsource(store_scraper._skann_maltprodukter)
        self.assertIn("finn_malt_fra_sitemap", kilde)
        self.assertIn("ol/ingredienser/malt", kilde)
        self.assertIn("sorted(", kilde, "resultatet skal være deterministisk sortert")

    @patch("modules.store_scraper.parse_produktside")
    @patch("modules.store_scraper.finn_vestbrygg_malt_med_varianter")
    @patch("modules.store_scraper.finn_produktsider")
    @patch("modules.store_scraper.finn_malt_fra_sitemap")
    def test_union_uten_duplikater_gjennom_skann_maltprodukter(
        self, mock_sitemap, mock_kategori, mock_variant, mock_parse,
    ):
        """
        Integrasjonsnivå: sitemap + kategoriside skal forenes, felles URL skal
        skrapes ÉN gang, og en URL som kun finnes hos én av kildene skal
        fortsatt bli med. Det siste er ikke teoretisk -- fire CaraRed-varianter
        finnes kun på kategorisiden, ikke i sitemapet.
        """
        import modules.store_scraper as store_scraper

        felles = f"{OL}/weyermann/101046/bohemian-pilsner-malt-4-ebc"
        kun_sitemap = f"{OL}/viking-malt/106260/carabody-max-8-ebc"
        kun_kategori = f"{OL}/weyermann/101122/carared-1-kg-knust-50-ebc"

        mock_sitemap.return_value = [felles, kun_sitemap]
        mock_kategori.side_effect = lambda base_url, sti, kat: (
            [felles, kun_kategori] if "olbrygging" in base_url else []
        )
        mock_variant.side_effect = lambda urls: urls
        mock_parse.side_effect = lambda url, kat, butikk: {"navn": "x", "url": url}

        resultat = store_scraper._skann_maltprodukter()
        urls = [r["url"] for r in resultat]

        self.assertEqual(len(urls), len(set(urls)), "ingen URL skal skrapes to ganger")
        for u in (felles, kun_sitemap, kun_kategori):
            self.assertIn(u, urls)
        self.assertEqual(len(urls), 3)
        # Deterministisk rekkefølge mellom like kjøringer.
        self.assertEqual(urls, sorted(urls))


if __name__ == "__main__":
    unittest.main()
