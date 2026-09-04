"""
Regresjonstest for Chief-runden på PR #52 (issue #50, WEB PRI 4C).

Blokker fra reviewen: `alleLokaleCustomIngredientIder()` i
`web/js/custom_ingredient_id.js` utelot den aktive kladden
(`AKTIV_KLADD_NOKKEL`), slik at et generasjonstids-kollisjon-forsøk mot en
custom-ingrediens-id som KUN finnes i den ulagrede aktive kladden ville bli
akseptert -- i strid med issue #50 punkt 6-7 / akseptansekriterium 5 og
Core-kontraktens (`docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md`)
§6-krav om at kollisjonssjekken skal dekke ETHVERT lokalt lagringssted som
kan holde en slik id.

VIKTIG METODEMERKNAD (samme prinsipp som test_web_mode_storage_fix.py):
dette repoet har ingen JavaScript-kjøretid i dette miljøet (ingen Node.js,
ingen jsdom/Playwright), så disse testene kan ikke faktisk kjøre
web/js/custom_ingredient_id.js og observere et ekte mocket kollisjonsforsøk
mot localStorage. I stedet er dette KILDE-KONTRAKT-tester: de leser den
FAKTISKE, kjørende kildefilen og verifiserer -- via presise, snevert
avgrensede mønstre -- at

  1. den aktive kladden nå faktisk inngår i kollisjonssettet
     (`_aktivKladdCustomIngredientIder()` finnes, leser riktig nøkkel, og
     kalles inn i `alleLokaleCustomIngredientIder()`), og
  2. `nyCustomIngredientId()` sin regenerer-løkke sjekker MOT nettopp det
     fullstendige, sammenslåtte settet (`kjente.has(id)`) uten noen
     snarvei som ville reuse/overskrive i stedet for å regenerere,

som sammen deterministisk beviser at et mocket/forsert kollisjonsforsøk mot
en draft-only id vil regenerere: id-en havner i `kjente` via steg 1, og
løkken i steg 2 fortsetter til den ikke lenger gjør det.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CUSTOM_ID_JS = os.path.join(_REPO_ROOT, "web", "js", "custom_ingredient_id.js")
_APP_JS = os.path.join(_REPO_ROOT, "web", "js", "app.js")
_PANTRY_PAGE_JS = os.path.join(_REPO_ROOT, "web", "js", "pantry_page.js")
_INDEX_HTML = os.path.join(_REPO_ROOT, "web", "index.html")
_PANTRY_HTML = os.path.join(_REPO_ROOT, "web", "pantry.html")


def _les(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _funksjonskropp(kilde, funksjonssignatur_regex):
    """Henter kroppen til en toppnivå-funksjon (fra 'function ... {' til
    linjen med den avsluttende '}' i kolonne 0), for å kunne lete etter
    mønstre KUN inni akkurat den funksjonen."""
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestAktivKladdCustomIngredientIder(unittest.TestCase):
    """_aktivKladdCustomIngredientIder() skal lese AKTIV_KLADD_NOKKEL
    trygt (feature-detected + try/catch) og gjenbruke den eksisterende
    _customIngredientIderIOppskrift()-ekstraksjonen -- ingen ny,
    parallell parsing-logikk for malt/humle/gjaerCustom."""

    def test_funksjonen_finnes_og_guarder_pa_typeof(self):
        kilde = _les(_CUSTOM_ID_JS)
        self.assertRegex(
            kilde,
            r"function _aktivKladdCustomIngredientIder\(\)\s*\{",
            "_aktivKladdCustomIngredientIder() mangler i custom_ingredient_id.js",
        )
        kropp = _funksjonskropp(kilde, r"function _aktivKladdCustomIngredientIder\(\)\s*\{")
        self.assertRegex(
            kropp,
            r'typeof AKTIV_KLADD_NOKKEL === "undefined"',
            "mangler feature-detection-guard på AKTIV_KLADD_NOKKEL",
        )

    def test_leser_riktig_nokkel_og_gjenbruker_ekstraksjonen(self):
        kilde = _les(_CUSTOM_ID_JS)
        kropp = _funksjonskropp(kilde, r"function _aktivKladdCustomIngredientIder\(\)\s*\{")
        self.assertRegex(
            kropp,
            r"_customIngredientIderIOppskrift\(JSON\.parse\(localStorage\.getItem\(AKTIV_KLADD_NOKKEL\)\)\)",
            "leser ikke AKTIV_KLADD_NOKKEL via den delte _customIngredientIderIOppskrift()-ekstraksjonen",
        )
        # Skal IKKE finnes en egen, parallell malt/humle/gjaerCustom-parsing
        # her -- gjenbruk er poenget, ikke duplisering.
        self.assertNotIn(".malt", kropp)
        self.assertNotIn(".humle", kropp)

    def test_feiler_trygt_til_tom_liste(self):
        kilde = _les(_CUSTOM_ID_JS)
        kropp = _funksjonskropp(kilde, r"function _aktivKladdCustomIngredientIder\(\)\s*\{")
        self.assertIn("try {", kropp)
        self.assertRegex(kropp, r"catch\s*\{\s*return \[\];\s*\}")


class TestAllelokaleCustomIngredientIderInkludererAktivKladd(unittest.TestCase):
    """alleLokaleCustomIngredientIder() skal slå sammen den aktive kladden
    inn i NØYAKTIG samme Set som pantry/oppskrifter/brygg -- ikke et eget,
    filtrert sett som en senere kollisjonssjekk kunne hoppe forbi."""

    def test_kollisjonssettet_merger_inn_aktiv_kladd(self):
        kilde = _les(_CUSTOM_ID_JS)
        kropp = _funksjonskropp(kilde, r"function alleLokaleCustomIngredientIder\(\)\s*\{")
        self.assertRegex(
            kropp,
            r"for \(const id of _aktivKladdCustomIngredientIder\(\)\) ider\.add\(id\)",
            "alleLokaleCustomIngredientIder() slår ikke lenger sammen aktiv kladd inn i settet",
        )

    def test_merge_kommer_etter_de_tre_eksisterende_kildene(self):
        # Regresjonsvakt mot at en fremtidig omskriving ved et uhell flytter
        # merge-linjen inn i en av if-blokkene over (og dermed kun kjører
        # den betinget av at f.eks. allePantryItems finnes).
        kilde = _les(_CUSTOM_ID_JS)
        kropp = _funksjonskropp(kilde, r"function alleLokaleCustomIngredientIder\(\)\s*\{")
        pantry_idx = kropp.index("allePantryItems")
        brygg_idx = kropp.index("alleBrygg")
        merge_idx = kropp.index("_aktivKladdCustomIngredientIder()")
        self.assertGreater(merge_idx, pantry_idx)
        self.assertGreater(merge_idx, brygg_idx)
        # Linjen skal stå på funksjonens toppnivå (ikke innrykket inni en
        # if-blokk) -- nøyaktig to mellomrom, samme som "return ider;".
        linje = [l for l in kropp.splitlines() if "_aktivKladdCustomIngredientIder()" in l][0]
        self.assertTrue(linje.startswith("  for ("), "merge-linjen er ikke lenger på funksjonens toppnivå")


class TestNyCustomIngredientIdRegenererAldriGjenbruker(unittest.TestCase):
    """Selve regenerer-løkka i nyCustomIngredientId() skal sjekke mot det
    FULLSTENDIGE, sammenslåtte settet fra alleLokaleCustomIngredientIder()
    (som nå inkluderer aktiv kladd) uten noen snarvei som reuser/overskriver
    i stedet for å regenerere -- dette er selve mekanismen som gjør et
    kollisjonsforsøk mot en draft-only id deterministisk trygt."""

    def test_kjente_er_det_fullstendige_settet(self):
        kilde = _les(_CUSTOM_ID_JS)
        kropp = _funksjonskropp(kilde, r"function nyCustomIngredientId\(\)\s*\{")
        self.assertIn("const kjente = alleLokaleCustomIngredientIder();", kropp)
        self.assertRegex(kropp, r"while\s*\(kjente\.has\(id\)\)")

    def test_ingen_reuse_eller_overskriv_snarvei(self):
        kilde = _les(_CUSTOM_ID_JS)
        kropp = _funksjonskropp(kilde, r"function nyCustomIngredientId\(\)\s*\{")
        # Ingen tidlig return før løkka (som ville omgått kollisjonssjekken),
        # og ingen mutasjon av kjente-settet (som ville "brukt opp" en
        # kollisjon i stedet for å regenerere en ny id).
        for_de_ikke_lov = ("kjente.delete", "kjente.clear", "kjente.add")
        for mønster in for_de_ikke_lov:
            self.assertNotIn(mønster, kropp)
        # Løkkekroppen skal utelukkende regenerere id -- ingen "break"/
        # "return" inni while-blokka som kunne kortslutte regenereringen.
        while_start = kropp.index("while (kjente.has(id))")
        while_kropp = kropp[while_start:]
        self.assertNotIn("break", while_kropp)
        self.assertNotIn("return", while_kropp[: while_kropp.index("}")])


class TestAktivKladdNokkelNavnErKonsistent(unittest.TestCase):
    """AKTIV_KLADD_NOKKEL må hete akkurat likt (samme nøkkelstreng) i
    app.js og pantry_page.js som det custom_ingredient_id.js implisitt
    forutsetter via typeof-guarden -- ellers ville feature-detection-
    guarden slå til (variabelen "finnes" som en annen konstant et annet
    sted), men lese feil/ingen data."""

    def test_samme_nokkelstreng_i_app_og_pantry_page(self):
        app_kilde = _les(_APP_JS)
        pantry_page_kilde = _les(_PANTRY_PAGE_JS)
        app_match = re.search(r'const AKTIV_KLADD_NOKKEL = "([^"]+)"', app_kilde)
        pantry_match = re.search(r'const AKTIV_KLADD_NOKKEL = "([^"]+)"', pantry_page_kilde)
        self.assertIsNotNone(app_match, "AKTIV_KLADD_NOKKEL mangler i app.js")
        self.assertIsNotNone(pantry_match, "AKTIV_KLADD_NOKKEL mangler i pantry_page.js")
        self.assertEqual(app_match.group(1), pantry_match.group(1))

    def test_custom_ingredient_id_js_lastes_for_konstanten_defineres(self):
        # Skript-rekkefølgen må fortsatt garantere at AKTIV_KLADD_NOKKEL
        # (definert i app.js/pantry_page.js) er en gyldig, initialisert
        # global på kalletidspunktet -- selv om den ikke er det på
        # PARSE-tidspunktet til custom_ingredient_id.js. Regresjonsvakt mot
        # at noen fjerner/omordner en av disse <script>-taggene.
        index_html = _les(_INDEX_HTML)
        pantry_html = _les(_PANTRY_HTML)
        for html, siste_konstant_fil in ((index_html, "app.js"), (pantry_html, "pantry_page.js")):
            custom_idx = html.index('src="js/custom_ingredient_id.js"')
            konst_idx = html.index('src="js/%s"' % siste_konstant_fil)
            self.assertLess(
                custom_idx,
                konst_idx,
                "custom_ingredient_id.js må fortsatt lastes før %s" % siste_konstant_fil,
            )


if __name__ == "__main__":
    unittest.main()
