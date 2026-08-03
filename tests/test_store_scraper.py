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

from modules.store_scraper import kjor_full_skanning


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


if __name__ == "__main__":
    unittest.main()
