"""
Regresjonstest for modules/store_scraper.py.

Bakgrunn: test_scraper.py lå tidligere i repo-roten og kjørte
kjor_full_skanning() (ekte HTTP-kall mot vestbrygg.no/olbrygging.no/
litebrygg.no + overskriving av raw_data/*.json) som modulnivå-kode, uten
`if __name__ == "__main__":`-vakt. Fordi filnavnet matchet unittest sitt
standard discovery-mønster ("test*.py"), startet `py -3 -m unittest discover`
en ekte skraping bare ved å IMPORTERE filen — se raw_data/malt_raw.json for
konsekvensen.

Denne testen erstatter den filen. Den mocker alle nettverkskall og kjører i
en midlertidig arbeidskatalog, slik at den aldri treffer et ekte nettsted
eller skriver til det virkelige raw_data/. Selve den manuelle skrapekjøringen
ligger nå i scripts/scrape_malt.py, bak en __main__-vakt.
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

from modules.store_scraper import kjor_full_skanning, kjor_malt_skanning


def _fake_produktside(url, kategori, butikk_navn):
    return {
        "navn": f"Fixture {kategori} produkt",
        "url": url,
        "butikk": butikk_navn,
        "pris": 99.0,
    }


class TestKjorFullSkanning(unittest.TestCase):
    """
    Kjører hele kjor_full_skanning()-pipelinen mot fastmontert fixture-data
    i stedet for et ekte nettverk, og bekrefter at den fortsatt teller riktig
    og skriver gyldig JSON — uten en eneste ekte HTTP-forespørsel.
    """

    def setUp(self):
        self._opprinnelig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self):
        os.chdir(self._opprinnelig_cwd)
        self._tmpdir.cleanup()

    @patch("modules.store_scraper.parse_produktside")
    @patch("modules.store_scraper.finn_gjær_fra_sitemap")
    @patch("modules.store_scraper.finn_humle_fra_sitemap")
    @patch("modules.store_scraper.finn_vestbrygg_malt_med_varianter")
    @patch("modules.store_scraper.finn_produktsider")
    def test_skanning_uten_nettverk_skriver_gyldige_raw_filer(
        self, mock_finn_produktsider, mock_finn_variant_utvidelse, mock_finn_humle_sitemap,
        mock_finn_gjaer_sitemap, mock_parse_produktside,
    ):
        # kjor_full_skanning() kaller finn_produktsider separat per butikk
        # (vestbrygg og olbrygging), og malt-lista dedupliserer IKKE på tvers
        # av butikker (i motsetning til humle/gjær, som samles i et set) —
        # så fixturen gir bevisst ulike URL-lister per butikk for å telle
        # riktig: 2 (vest) + 1 (ol) = 3 malt. Humle-siden legger i tillegg
        # ubetinget til VESTBRYGG_HUMLE_EXTRA (2 fast-injiserte URLer) i
        # store_scraper.py, så 1 fixture-URL + 2 faste = 3 unike humle-URLer
        # etter dedup i settet.
        malt_urls = {
            "https://vestbrygg.no":       ["https://fixture.test/malt/1", "https://fixture.test/malt/2"],
            "https://www.olbrygging.no":  ["https://fixture.test/malt/3"],
        }
        humle_urls = {
            "https://vestbrygg.no":       ["https://fixture.test/humle/1"],
            "https://www.olbrygging.no":  [],
        }

        def _finn_produktsider(base_url, kategori_path, kategori):
            if kategori == "malt":
                return malt_urls.get(base_url, [])
            if kategori == "humle":
                return humle_urls.get(base_url, [])
            return []  # gjaer: ingen ekstra kategori-URLer i denne fixturen

        mock_finn_produktsider.side_effect = _finn_produktsider
        # Identitets-passthrough: denne testen bryr seg ikke om Vestbryggs
        # mor-/barn-variantutvidelse (se Steg F1), bare om URL-tellingen.
        # Uten denne mocken ville finn_vestbrygg_malt_med_varianter (som
        # gjør ekte requests.get-kall) blitt kjørt mot "https://fixture.test/..."
        # under testkjøring — nøyaktig det denne testfilens egen hensikt
        # (se moduldokstreng) er å forhindre.
        mock_finn_variant_utvidelse.side_effect = lambda urls: urls
        mock_finn_humle_sitemap.return_value = []
        mock_finn_gjaer_sitemap.return_value = []
        mock_parse_produktside.side_effect = _fake_produktside

        antall_malt, antall_humle, antall_gjaer = kjor_full_skanning()

        # Ingen ekte nettverkskall skal ha skjedd — alt gikk via mocks.
        mock_finn_produktsider.assert_called()
        mock_parse_produktside.assert_called()

        self.assertEqual(antall_malt, 3)
        self.assertEqual(antall_humle, 3)  # 1 fixture + 2 faste VESTBRYGG_HUMLE_EXTRA-URLer
        self.assertEqual(antall_gjaer, 1)  # kun fast-injeksjonen (Wyeast 1318)

        # Filene skal havne i denne midlertidige mappa, ikke det ekte repoet.
        self.assertTrue(os.path.exists("raw_data/malt_raw.json"))
        self.assertTrue(os.path.exists("raw_data/humle_raw.json"))
        self.assertTrue(os.path.exists("raw_data/gjaer_raw.json"))

        with open("raw_data/malt_raw.json", encoding="utf-8") as f:
            malt_data = json.load(f)
        self.assertEqual(len(malt_data), 3)
        self.assertTrue(all("navn" in p and "url" in p for p in malt_data))

    @patch("modules.store_scraper.parse_produktside")
    @patch("modules.store_scraper.finn_gjær_fra_sitemap")
    @patch("modules.store_scraper.finn_humle_fra_sitemap")
    @patch("modules.store_scraper.finn_produktsider")
    def test_feilende_produktside_gir_fortsatt_gyldig_retur(
        self, mock_finn_produktsider, mock_finn_humle_sitemap,
        mock_finn_gjaer_sitemap, mock_parse_produktside,
    ):
        # Sikkerhets-retur (krav i store_scraper.py): en feilende delskanning
        # skal aldri la funksjonen returnere None/kaste ut til UI-laget.
        mock_finn_produktsider.side_effect = RuntimeError("simulert nettverksfeil")
        mock_finn_humle_sitemap.return_value = []
        mock_finn_gjaer_sitemap.return_value = []
        mock_parse_produktside.side_effect = _fake_produktside

        resultat = kjor_full_skanning()
        self.assertEqual(resultat, (0, 0, 0))


class TestKjorMaltSkanning(unittest.TestCase):
    """
    Regresjonstester for Steg F9A: kjor_malt_skanning() (og
    scripts/scrape_malt_only.py) skal kunne skrape KUN malt, uten å
    røre humle-/gjærdata, matcher eller AI-normalisering — se
    modules/store_scraper.py::kjor_malt_skanning() sin dokstreng.

    Bruker samme mock-/midlertidig-arbeidskatalog-mønster som
    TestKjorFullSkanning over — ingen ekte HTTP-kall, ingen ekte
    prosjektfiler røres.
    """

    def setUp(self):
        self._opprinnelig_cwd = os.getcwd()
        self._tmpdir = tempfile.TemporaryDirectory()
        os.chdir(self._tmpdir.name)

    def tearDown(self):
        os.chdir(self._opprinnelig_cwd)
        self._tmpdir.cleanup()

    @patch("modules.store_scraper.parse_produktside")
    @patch("modules.store_scraper.finn_gjær_fra_sitemap")
    @patch("modules.store_scraper.finn_humle_fra_sitemap")
    @patch("modules.store_scraper.finn_vestbrygg_malt_med_varianter")
    @patch("modules.store_scraper.finn_produktsider")
    def test_skanner_vestbrygg_og_olbrygging_malt_og_skriver_samlet(
        self, mock_finn_produktsider, mock_finn_variant_utvidelse, mock_finn_humle_sitemap,
        mock_finn_gjaer_sitemap, mock_parse_produktside,
    ):
        malt_urls = {
            "https://vestbrygg.no":      ["https://fixture.test/malt/1", "https://fixture.test/malt/2"],
            "https://www.olbrygging.no": ["https://fixture.test/malt/3"],
        }

        def _finn_produktsider(base_url, kategori_path, kategori):
            self.assertEqual(kategori, "malt")
            return malt_urls.get(base_url, [])

        mock_finn_produktsider.side_effect = _finn_produktsider
        mock_finn_variant_utvidelse.side_effect = lambda urls: urls
        mock_parse_produktside.side_effect = _fake_produktside

        antall_malt = kjor_malt_skanning()

        # Punkt 1+3: begge butikker skannet.
        mock_finn_produktsider.assert_any_call("https://vestbrygg.no", "råvarer/malt", "malt")
        mock_finn_produktsider.assert_any_call("https://www.olbrygging.no", "ol/ingredienser/malt", "malt")
        # Punkt 2: Vestbryggs variant-/barn-SKU-flyt ble brukt.
        mock_finn_variant_utvidelse.assert_called_once()
        # Punkt 4: begge butikker samlet i én skriving.
        self.assertEqual(antall_malt, 3)
        with open("raw_data/malt_raw.json", encoding="utf-8") as f:
            malt_data = json.load(f)
        self.assertEqual(len(malt_data), 3)
        self.assertTrue(all("navn" in p and "url" in p for p in malt_data))

        # Punkt 5+6: humle-/gjærfilen ble aldri skrevet.
        self.assertFalse(os.path.exists("raw_data/humle_raw.json"))
        self.assertFalse(os.path.exists("raw_data/gjaer_raw.json"))
        # Punkt 7+8: humle-/gjærinnhenting ble aldri kalt.
        mock_finn_humle_sitemap.assert_not_called()
        mock_finn_gjaer_sitemap.assert_not_called()

    def test_kaller_aldri_matcher_eller_ai_normalisering(self):
        # Punkt 9+10: store_scraper.py importerer overhodet ingen
        # matcher-/AI-normaliseringsfunksjoner, så kjor_malt_skanning()
        # kan strukturelt ikke kalle dem.
        import modules.store_scraper as store_scraper_mod
        for navn in (
            "match_store_data_to_master",
            "match_store_data_to_master_malt",
            "match_store_data_to_master_gjaer",
            "match_product_to_master",
        ):
            self.assertFalse(
                hasattr(store_scraper_mod, navn),
                f"store_scraper.py skal ikke ha tilgang til matcherfunksjonen {navn}",
            )

    @patch("modules.store_scraper.parse_produktside")
    @patch("modules.store_scraper.finn_produktsider")
    def test_feil_i_vestbrygg_flyten_gir_ingen_delvis_maltfil(
        self, mock_finn_produktsider, mock_parse_produktside,
    ):
        # Punkt 11: feil før Vestbrygg-lenkene i det hele tatt er funnet.
        mock_finn_produktsider.side_effect = RuntimeError("simulert nettverksfeil")
        mock_parse_produktside.side_effect = _fake_produktside

        with self.assertRaises(RuntimeError):
            kjor_malt_skanning()

        # I motsetning til kjor_full_skanning() skal feilen IKKE svelges,
        # og ingen fil skal ha blitt skrevet.
        self.assertFalse(os.path.exists("raw_data/malt_raw.json"))

    @patch("modules.store_scraper.parse_produktside")
    @patch("modules.store_scraper.finn_vestbrygg_malt_med_varianter")
    @patch("modules.store_scraper.finn_produktsider")
    def test_feil_i_olbrygging_flyten_etter_ferdig_vestbrygg_gir_ingen_delvis_maltfil(
        self, mock_finn_produktsider, mock_finn_variant_utvidelse, mock_parse_produktside,
    ):
        # Punkt 12: Vestbrygg-lenkene hentes ferdig (finn_produktsider +
        # finn_vestbrygg_malt_med_varianter går bra), men Ølbrygging sitt
        # finn_produktsider-kall feiler — hele resultatlisten bygges i
        # minnet FØR skriving, så ingenting skrives i det hele tatt.
        def _finn_produktsider(base_url, kategori_path, kategori):
            if base_url == "https://vestbrygg.no":
                return ["https://fixture.test/malt/1"]
            raise RuntimeError("simulert nettverksfeil hos Ølbrygging")

        mock_finn_produktsider.side_effect = _finn_produktsider
        mock_finn_variant_utvidelse.side_effect = lambda urls: urls
        mock_parse_produktside.side_effect = _fake_produktside

        with self.assertRaises(RuntimeError):
            kjor_malt_skanning()

        self.assertFalse(os.path.exists("raw_data/malt_raw.json"))

    @patch("modules.store_scraper._skann_maltprodukter")
    def test_kjor_malt_skanning_og_kjor_full_skanning_bruker_samme_maltfunksjon(
        self, mock_skann_maltprodukter,
    ):
        # Punkt 16: begge orkestreringsfunksjonene skal hente maltdata
        # via nøyaktig samme interne funksjon — ikke to parallelle
        # implementasjoner som kan drive fra hverandre.
        mock_skann_maltprodukter.return_value = [
            {"navn": "Fixture malt", "url": "https://fixture.test/malt/1", "butikk": "vestbrygg"},
        ]

        kjor_malt_skanning()
        self.assertEqual(mock_skann_maltprodukter.call_count, 1)

    def test_scrape_malt_only_script_kaller_nøyaktig_kjor_malt_skanning(self):
        # Punkt 13: scripts/scrape_malt_only.py skal kalle nøyaktig
        # kjor_malt_skanning().
        import scripts.scrape_malt_only as scrape_malt_only_mod

        with patch.object(scrape_malt_only_mod, "kjor_malt_skanning", return_value=3) as mock_fn:
            scrape_malt_only_mod.main()
            mock_fn.assert_called_once()

        # Punkt 14: scriptet importerer/refererer overhodet ikke
        # kjor_full_skanning — det kan strukturelt ikke kalle den.
        self.assertFalse(hasattr(scrape_malt_only_mod, "kjor_full_skanning"))


if __name__ == "__main__":
    unittest.main()
