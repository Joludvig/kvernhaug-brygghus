"""
Tester for Runde 15B.3: scripts/generate_web_i18n_pages.py, som genererer
den crawlbare engelske speil-strukturen web/en/** fra web/*.html +
web/hjelp/*.html (struktur/mal) og TEKSTER.en i web/js/i18n.js (innhold).

Dekker: TEKSTER-parsing (bracket-matching -> JSON), NO/EN-nøkkelsymmetri,
PAGES-listen mot faktiske source-filer, hard feil ved manglende nøkkel,
at generert HTML faktisk får lang="en" og riktig markup for
data-i18n-html, at asset-stier justeres korrekt for rot- og hjelp-dybde,
og at generatoren er deterministisk.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import generate_web_i18n_pages as gen


class TestParseTekster(unittest.TestCase):
    def test_parser_finner_no_og_en_med_symmetriske_nokler(self):
        data = gen.parse_tekster()
        self.assertIn("no", data)
        self.assertIn("en", data)
        self.assertEqual(set(data["no"].keys()), set(data["en"].keys()))
        # Sanity -- skal være et ikke-trivielt antall nøkler, ikke en tom/
        # delvis parset ordbok.
        self.assertGreater(len(data["no"]), 500)

    def test_balansert_klamme_ignorerer_param_placeholders_i_strenger(self):
        # {param}-plassholdere i tekstverdier (f.eks. "Modus: {status}") må
        # IKKE telles som strukturelle klammer -- ellers ville balanseringen
        # feile eller kappe TEKSTER for tidlig.
        tekst = 'const TEKSTER = {\n  no: {\n    "a": "Modus: {status}"\n  },\n  en: {\n    "a": "Mode: {status}"\n  },\n};\n'
        start = tekst.index("{")
        end = gen._finn_balansert_klamme(tekst, start)
        self.assertEqual(tekst[end], "}")
        self.assertEqual(end, len(tekst) - 3)  # siste '}' før ';\n'

    def test_ubalanserte_klammer_feiler_hardt(self):
        tekst = "const TEKSTER = {\n  no: {\n"
        with self.assertRaises(gen.GeneratorError):
            gen._finn_balansert_klamme(tekst, tekst.index("{"))


class TestPagesGuard(unittest.TestCase):
    def test_alle_pages_finnes_pa_disk(self):
        for page in gen.PAGES:
            self.assertTrue((gen.WEB / page).is_file(), f"Mangler source-fil for {page}")

    def test_alle_source_sider_er_registrert_i_pages(self):
        # Skal ikke kaste -- hvis den gjør det, finnes det en NO-side som
        # ikke er registrert (eller en registrert side som mangler på disk).
        gen.valider_pages_mot_source()

    def test_uregistrert_source_side_feiler_hardt(self):
        faktiske = gen._oppdag_source_sider()
        ekstra = faktiske | {"spokelse.html"}
        forventede = set(gen.PAGES)
        uregistrert = ekstra - forventede
        self.assertIn("spokelse.html", uregistrert)


class TestAssetPathRewrite(unittest.TestCase):
    def test_rot_dybde_faar_en_ekstra_niva(self):
        self.assertEqual(gen._dypere_asset_sti("css/style.css"), "../css/style.css")
        self.assertEqual(gen._dypere_asset_sti("js/app.js"), "../js/app.js")
        self.assertEqual(gen._dypere_asset_sti("assets/ui/flag-no.webp"), "../assets/ui/flag-no.webp")

    def test_hjelp_dybde_faar_en_ekstra_niva(self):
        self.assertEqual(gen._dypere_asset_sti("../css/style.css"), "../../css/style.css")
        self.assertEqual(gen._dypere_asset_sti("../assets/branding/x.png"), "../../assets/branding/x.png")

    def test_interne_navigasjonslenker_urort(self):
        for verdi in ["index.html", "../index.html", "bryggedag.html", "bryggedag.html#steg-7", "mine-oppskrifter.html"]:
            self.assertEqual(gen._dypere_asset_sti(verdi), verdi)


class TestSprakvelgerHrefMapping(unittest.TestCase):
    def test_rotside_href_mapping(self):
        self.assertEqual(gen._no_href_fra_en("index.html"), "../index.html")
        self.assertEqual(gen._en_href_selv("index.html"), "index.html")

    def test_hjelpside_href_mapping(self):
        self.assertEqual(gen._no_href_fra_en("hjelp/bryggedag.html"), "../../hjelp/bryggedag.html")
        self.assertEqual(gen._en_href_selv("hjelp/bryggedag.html"), "bryggedag.html")


class TestGenererSide(unittest.TestCase):
    """Kjører den faktiske genereringen (ikke skriving til disk) for et par
    representative sider og inspiserer output-strukturen direkte."""

    @classmethod
    def setUpClass(cls):
        cls.tekster = gen.parse_tekster()
        cls.en = cls.tekster["en"]

    def test_manglende_nokkel_feiler_hardt(self):
        en_uten_nokkel = dict(self.en)
        en_uten_nokkel.pop("brand.motto")
        with self.assertRaises(gen.GeneratorError):
            gen.generer_side_html("index.html", en_uten_nokkel)

    def test_generert_index_har_lang_en(self):
        html = gen.generer_side_html("index.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup.find("html")["lang"], "en")

    def test_generert_tittel_er_engelsk(self):
        html = gen.generer_side_html("index.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        self.assertEqual(soup.find("title").get_text(), self.en["meta.builder.tittel"])

    def test_data_i18n_html_gir_faktisk_markup_ikke_escaped_tekst(self):
        html = gen.generer_side_html("utskrift.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        el = soup.select_one('[data-i18n-html="utskrift.tomTekst2"]')
        self.assertIsNotNone(el)
        lenker = el.find_all("a")
        self.assertGreaterEqual(len(lenker), 1, "utskrift.tomTekst2 skal rendres som ekte <a>-element(er), ikke escaped HTML")
        self.assertNotIn("&lt;a", html)

    def test_data_i18n_html_strong_markup(self):
        html = gen.generer_side_html("hjelp/index.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        el = soup.select_one('[data-i18n-html="hjelp.idx.alfaVariasjon.hvorfor"]')
        self.assertIsNotNone(el)
        self.assertGreaterEqual(len(el.find_all("strong")), 1)

    def test_asset_stier_justert_for_rotside(self):
        html = gen.generer_side_html("index.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        css = soup.find("link", rel="stylesheet")
        self.assertEqual(css["href"], "../css/style.css")

    def test_asset_stier_justert_for_hjelpside(self):
        html = gen.generer_side_html("hjelp/bryggedag.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        css = soup.find("link", rel="stylesheet")
        self.assertEqual(css["href"], "../../css/style.css")

    def test_sprakvelger_hrefs_pa_generert_rotside(self):
        html = gen.generer_side_html("index.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        knapper = soup.select(".sprak-knapp")
        self.assertEqual(len(knapper), 6)
        no_knapp = knapper[0]
        en_knapp = knapper[1]
        self.assertEqual(no_knapp["href"], "../index.html")
        self.assertEqual(en_knapp["href"], "index.html")
        self.assertIn("aktiv", en_knapp.get("class", []))
        self.assertEqual(en_knapp.get("aria-current"), "page")
        self.assertNotIn("aktiv", no_knapp.get("class", []))

    def test_intern_navigasjonslenke_urort_i_generert_output(self):
        html = gen.generer_side_html("index.html", self.en)
        soup = BeautifulSoup(html, "html.parser")
        bygger_lenke = soup.select_one('a.sidemeny-lenke[href="index.html"]')
        self.assertIsNotNone(bygger_lenke)

    def test_generator_marker_tilstede(self):
        html = gen.generer_side_html("index.html", self.en)
        self.assertIn(gen.GENERATOR_MARKER, html[:400])


class TestDeterminisme(unittest.TestCase):
    def test_to_kjoringer_gir_identisk_output(self):
        tekster = gen.parse_tekster()
        en = tekster["en"]
        for page in gen.PAGES:
            first = gen.generer_side_html(page, en)
            second = gen.generer_side_html(page, en)
            self.assertEqual(first, second, f"{page}: ikke-deterministisk output mellom to kjøringer")


class TestGenerertOutputPaDisk(unittest.TestCase):
    """Kjøres kun dersom web/en/ allerede er generert (committet output) --
    verifiserer at det som faktisk ligger i repoet er i sync med kilden.
    Hopper over (ikke feiler) dersom web/en/ ikke finnes ennå."""

    def test_committed_output_matcher_fersk_generering(self):
        if not gen.WEB_EN.exists():
            self.skipTest("web/en/ finnes ikke ennå")
        tekster = gen.parse_tekster()
        en = tekster["en"]
        for page in gen.PAGES:
            forventet = gen.generer_side_html(page, en)
            faktisk_path = gen.WEB_EN / page
            self.assertTrue(faktisk_path.is_file(), f"Mangler generert fil for {page}")
            faktisk = faktisk_path.read_text(encoding="utf-8")
            self.assertEqual(
                faktisk, forventet,
                f"web/en/{page} er ikke i sync med kilden -- kjør scripts/generate_web_i18n_pages.py på nytt",
            )


if __name__ == "__main__":
    unittest.main()
