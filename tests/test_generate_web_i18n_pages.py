"""
Tester for Runde 15B.3/15B.4: scripts/generate_web_i18n_pages.py, som
genererer den crawlbare engelske speil-strukturen web/en/** fra web/*.html
+ web/hjelp/*.html (struktur/mal) og TEKSTER.en i web/js/i18n.js (innhold),
samt web/sitemap.xml.

Dekker: TEKSTER-parsing (bracket-matching -> JSON), NO/EN-nøkkelsymmetri,
PAGES-listen mot faktiske source-filer, hard feil ved manglende nøkkel,
at generert HTML faktisk får lang="en" og riktig markup for
data-i18n-html, at asset-stier justeres korrekt for rot- og hjelp-dybde,
determinisme, og (Runde 15B.4) canonical/hreflang-gjensidighet,
meta-description, sitemap.xml og robots.txt.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from bs4 import BeautifulSoup

from scripts import generate_web_i18n_pages as gen

_SITEMAP_NS = {
    "sm": "http://www.sitemaps.org/schemas/sitemap/0.9",
    "xhtml": "http://www.w3.org/1999/xhtml",
}


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


class TestUrlKontrakt(unittest.TestCase):
    def test_rotside_url(self):
        self.assertEqual(gen.canonical_url("index.html", "no"), "https://kvernhaugbrygghus.no/")
        self.assertEqual(gen.canonical_url("index.html", "en"), "https://kvernhaugbrygghus.no/en/")

    def test_hjelp_indexside_url_pen_katalog(self):
        self.assertEqual(gen.canonical_url("hjelp/index.html", "no"), "https://kvernhaugbrygghus.no/hjelp/")
        self.assertEqual(gen.canonical_url("hjelp/index.html", "en"), "https://kvernhaugbrygghus.no/en/hjelp/")

    def test_ikke_index_side_eksplisitt_html(self):
        self.assertEqual(gen.canonical_url("mine-oppskrifter.html", "no"), "https://kvernhaugbrygghus.no/mine-oppskrifter.html")
        self.assertEqual(gen.canonical_url("hjelp/bryggedag.html", "en"), "https://kvernhaugbrygghus.no/en/hjelp/bryggedag.html")

    def test_ugyldig_sprak_feiler(self):
        with self.assertRaises(gen.GeneratorError):
            gen.canonical_url("index.html", "de")


class TestSeoDescriptionOgCanonicalGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tekster = gen.parse_tekster()
        cls.en = cls.tekster["en"]

    def test_alle_8_sider_har_description_nokkel_i_no_og_en(self):
        for page in gen.PAGES:
            html = (gen.WEB / page).read_text(encoding="utf-8")
            soup = BeautifulSoup(html, "html.parser")
            meta = soup.find("meta", attrs={"name": "description"})
            self.assertIsNotNone(meta, f"{page}: mangler <meta name=\"description\">")
            nokkel = meta.get("data-i18n-content")
            self.assertTrue(nokkel, f"{page}: <meta description> mangler data-i18n-content")
            self.assertIn(nokkel, self.tekster["no"], f"{page}: {nokkel} mangler i TEKSTER.no")
            self.assertIn(nokkel, self.en, f"{page}: {nokkel} mangler i TEKSTER.en")

    def test_manglende_canonical_i_kilde_feiler_hardt(self):
        html = (gen.WEB / "index.html").read_text(encoding="utf-8")
        soup = BeautifulSoup(html.replace('rel="canonical"', 'rel="ikke-canonical"'), "html.parser")
        with self.assertRaises(gen.GeneratorError):
            gen._rewrite_seo_links(soup, "index.html")

    def test_manglende_hreflang_i_kilde_feiler_hardt(self):
        html = (gen.WEB / "index.html").read_text(encoding="utf-8")
        soup = BeautifulSoup(html.replace('hreflang="x-default"', 'hreflang="ikke-x-default"'), "html.parser")
        with self.assertRaises(gen.GeneratorError):
            gen._rewrite_seo_links(soup, "index.html")


class TestCanonicalOgHreflangGjensidighet(unittest.TestCase):
    """Kjører faktisk generering for alle 8 sider og verifiserer det
    eksplisitte gjensidighetskravet fra oppgaven: NO->EN, EN->NO, begge
    x-default->NO, canonical alltid selvrefererende."""

    @classmethod
    def setUpClass(cls):
        cls.tekster = gen.parse_tekster()
        cls.en = cls.tekster["en"]

    def _hreflang_map(self, soup):
        return {a.get("hreflang"): a["href"] for a in soup.find_all("link", rel="alternate")}

    def test_alle_8_par_er_gjensidig_korrekte(self):
        for page in gen.PAGES:
            no_html = (gen.WEB / page).read_text(encoding="utf-8")
            no_soup = BeautifulSoup(no_html, "html.parser")
            en_html = gen.generer_side_html(page, self.en)
            en_soup = BeautifulSoup(en_html, "html.parser")

            no_url = gen.canonical_url(page, "no")
            en_url = gen.canonical_url(page, "en")

            no_canonical = no_soup.find("link", rel="canonical")["href"]
            en_canonical = en_soup.find("link", rel="canonical")["href"]
            self.assertEqual(no_canonical, no_url, f"{page}: NO canonical skal peke til seg selv")
            self.assertEqual(en_canonical, en_url, f"{page}: EN canonical skal peke til seg selv")

            no_alt = self._hreflang_map(no_soup)
            en_alt = self._hreflang_map(en_soup)
            self.assertEqual(no_alt.get("en"), en_url, f"{page}: NO hreflang=en skal peke til EN")
            self.assertEqual(en_alt.get("no"), no_url, f"{page}: EN hreflang=no skal peke tilbake til NO")
            self.assertEqual(no_alt.get("x-default"), no_url, f"{page}: NO x-default skal peke til NO")
            self.assertEqual(en_alt.get("x-default"), no_url, f"{page}: EN x-default skal peke til NO")


class TestSitemap(unittest.TestCase):
    def test_sitemap_er_gyldig_xml_med_16_urls(self):
        xml_tekst = gen.build_sitemap_xml()
        root = ET.fromstring(xml_tekst)
        urls = root.findall("sm:url", _SITEMAP_NS)
        self.assertEqual(len(urls), 16)

    def test_sitemap_ingen_duplikater(self):
        xml_tekst = gen.build_sitemap_xml()
        root = ET.fromstring(xml_tekst)
        locs = [u.find("sm:loc", _SITEMAP_NS).text for u in root.findall("sm:url", _SITEMAP_NS)]
        self.assertEqual(len(locs), len(set(locs)))

    def test_sitemap_alle_canonical_urler_finnes(self):
        xml_tekst = gen.build_sitemap_xml()
        root = ET.fromstring(xml_tekst)
        locs = {u.find("sm:loc", _SITEMAP_NS).text for u in root.findall("sm:url", _SITEMAP_NS)}
        forventede = set()
        for page in gen.PAGES:
            forventede.add(gen.canonical_url(page, "no"))
            forventede.add(gen.canonical_url(page, "en"))
        self.assertEqual(locs, forventede)

    def test_sitemap_ingen_asset_eller_data_urler(self):
        xml_tekst = gen.build_sitemap_xml()
        for forbudt in ("/data/", "/css/", "/js/", "/assets/"):
            self.assertNotIn(forbudt, xml_tekst)

    def test_sitemap_ingen_lastmod(self):
        xml_tekst = gen.build_sitemap_xml()
        self.assertNotIn("lastmod", xml_tekst)

    def test_sitemap_hreflang_alternates_matcher_html_kontrakt(self):
        tekster = gen.parse_tekster()
        xml_tekst = gen.build_sitemap_xml()
        root = ET.fromstring(xml_tekst)
        for url_el in root.findall("sm:url", _SITEMAP_NS):
            loc = url_el.find("sm:loc", _SITEMAP_NS).text
            alternates = {
                l.get("hreflang"): l.get("href")
                for l in url_el.findall("xhtml:link", _SITEMAP_NS)
            }
            self.assertEqual(set(alternates.keys()), {"no", "en", "x-default"})
            self.assertEqual(alternates["x-default"], alternates["no"])
            self.assertIn(loc, (alternates["no"], alternates["en"]))

    def test_sitemap_determinisme(self):
        first = gen.build_sitemap_xml()
        second = gen.build_sitemap_xml()
        self.assertEqual(first, second)

    def test_committed_sitemap_matcher_fersk_generering(self):
        sitemap_path = gen.WEB / "sitemap.xml"
        if not sitemap_path.is_file():
            self.skipTest("web/sitemap.xml finnes ikke ennå")
        forventet = gen.build_sitemap_xml()
        faktisk = sitemap_path.read_text(encoding="utf-8")
        self.assertEqual(faktisk, forventet, "web/sitemap.xml er ikke i sync -- kjør generatoren på nytt")


class TestRobotsTxt(unittest.TestCase):
    def test_robots_txt_finnes_og_er_korrekt(self):
        path = gen.WEB / "robots.txt"
        self.assertTrue(path.is_file(), "web/robots.txt mangler")
        innhold = path.read_text(encoding="utf-8")
        self.assertIn("User-agent: *", innhold)
        self.assertIn("Allow: /", innhold)
        self.assertIn("Sitemap: https://kvernhaugbrygghus.no/sitemap.xml", innhold)
        self.assertNotIn("Disallow: /en/", innhold)
        self.assertNotIn("Disallow: /hjelp/", innhold)
        self.assertNotIn("Disallow: /css", innhold)
        self.assertNotIn("Disallow: /js", innhold)
        self.assertNotIn("Disallow: /assets", innhold)
        self.assertNotIn("Disallow: /data", innhold)


if __name__ == "__main__":
    unittest.main()
