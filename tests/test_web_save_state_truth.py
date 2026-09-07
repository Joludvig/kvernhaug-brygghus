"""
Regresjonstest for WEB STAB W3 (issue #106) -- "make draft / saved / variant
state truthful".

VIKTIG METODEMERKNAD (samme som tests/test_web_mode_storage_fix.py): dette
repoet har ingen JavaScript-kjøretid i dette miljøet (ingen Node.js, ingen
npm, ingen jsdom/Playwright) -- tests/web_js_runtime.py::run_web_js er
eksplisitt blokkert (Chief review, PR #53) fordi det ville krevd å shelle ut
til `node`, som ikke står på Claude Agent Bridge sin --allowedTools-liste.

Disse testene er derfor KILDE-KONTRAKT-tester: de leser den FAKTISKE,
kjørende web/js/app.js (ikke en kopi/reimplementasjon) og verifiserer, via
presise regex-mønstre, at de eksakte kodestykkene som avgjør lagre-
tilstanden (kladd/lagret/endret) og "Lagre som variant"-handlingen fortsatt
har riktig form. Ekte, live browser-verifisering av selve tilstands-
overgangene (acceptance criterion E, issue #106) er en egen, manuell
Playwright-sweep (se web-full-regression-skillet) -- ikke noe denne testen
kan bevise.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_JS = os.path.join(_REPO_ROOT, "web", "js", "app.js")
_RECIPE_STORAGE_JS = os.path.join(_REPO_ROOT, "web", "js", "recipe_storage.js")
_INDEX_HTML = os.path.join(_REPO_ROOT, "web", "index.html")
_I18N_JS = os.path.join(_REPO_ROOT, "web", "js", "i18n.js")


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


def _app_js():
    return _les(_APP_JS)


def _funksjonskropp(kilde, funksjonssignatur_regex):
    """Samme hjelper som test_web_mode_storage_fix.py: henter kroppen til en
    toppnivå-funksjon fra 'function ... {' til den avsluttende '}' i kolonne
    0."""
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestLagreTilstandForOppskrift(unittest.TestCase):
    """A -- "kladd"/"lagret"/"endret" avgjøres av _aktivRecipeId + faktisk
    likhet mot den lagrede raden, aldri av en statisk one-shot-melding."""

    def test_funksjon_finnes(self):
        self.assertRegex(_app_js(), r"function lagreTilstandForOppskrift\(oppskrift\)\s*\{")

    def test_ingen_aktiv_recipe_id_gir_kladd(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreTilstandForOppskrift\(oppskrift\)\s*\{")
        self.assertRegex(kropp, r'if\s*\(!_aktivRecipeId\)\s*return\s*"kladd"')

    def test_manglende_lagret_rad_gir_endret_ikke_lagret(self):
        # Slettet et annet sted (Mine oppskrifter, annen fane): "lagret" skal
        # ALDRI kunne påstås uten bevis mot lageret.
        kropp = _funksjonskropp(_app_js(), r"function lagreTilstandForOppskrift\(oppskrift\)\s*\{")
        self.assertRegex(kropp, r'if\s*\(!lagret\)\s*return\s*"endret"')

    def test_bruker_erOppskriftLikLagret_for_avgjorelsen(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreTilstandForOppskrift\(oppskrift\)\s*\{")
        self.assertRegex(kropp, r'_erOppskriftLikLagret\(oppskrift,\s*lagret\)\s*\?\s*"lagret"\s*:\s*"endret"')

    def test_slar_opp_direkte_i_lageret_ikke_egen_cache(self):
        # _hentSisteLagredeOppskrift() må lese finnOppskrift() (recipe_storage.js),
        # ikke en egen variabel som kan bli utdatert.
        kilde = _app_js()
        kropp = _funksjonskropp(kilde, r"function _hentSisteLagredeOppskrift\(\)\s*\{")
        self.assertIn("finnOppskrift(_aktivRecipeId)", kropp)


class TestSammenligningIgnorererTransientLagretDato(unittest.TestCase):
    """A5 -- lagretDato settes til "nå" på HVERT samleOppskrift()-kall (se
    samleOppskrift()) og er derfor ren bokføring, aldri reelt oppskrifts-
    innhold -- må IKKE kunne gjøre en ellers uendret kladd "endret"."""

    def test_lagretdato_destruktureres_bort_for_sammenligning(self):
        kropp = _funksjonskropp(_app_js(), r"function _oppskriftInnholdForSammenligning\(oppskrift\)\s*\{")
        self.assertRegex(kropp, r"const\s*\{\s*lagretDato,\s*\.\.\.resten\s*\}\s*=\s*oppskrift")
        self.assertIn("return resten", kropp)

    def test_erOppskriftLikLagret_bruker_innhold_for_sammenligning_pa_begge_sider(self):
        kropp = _funksjonskropp(_app_js(), r"function _erOppskriftLikLagret\(oppskrift,\s*lagretOppskrift\)\s*\{")
        self.assertEqual(kropp.count("_oppskriftInnholdForSammenligning("), 2)

    def test_kanonisk_json_sorterer_nokler_uavhengig_av_rekkefolge(self):
        kropp = _funksjonskropp(_app_js(), r"function _kanoniskJson\(verdi\)\s*\{")
        self.assertIn("Object.keys(verdi).sort()", kropp)


class TestBeregnOgVisResultatOppdatererBadge(unittest.TestCase):
    """B -- lagre-tilstanden skal oppdateres LIVE ved hver eneste beregning
    (samme kroken som allerede autolagrer aktiv kladd), ikke bare rett etter
    et eksplisitt Lagre-klikk."""

    def test_oppdaterLagreTilstandUI_kalles_fra_beregnOgVisResultat(self):
        kropp = _funksjonskropp(_app_js(), r"function beregnOgVisResultat\(\)\s*\{")
        self.assertIn("_oppdaterLagreTilstandUI(oppskrift);", kropp)

    def test_badge_tekst_og_klasse_er_tilstandsavhengig(self):
        kropp = _funksjonskropp(_app_js(), r"function _oppdaterLagreTilstandUI\(oppskrift\)\s*\{")
        self.assertIn('t("identitet.lagretilstand." + tilstand)', kropp)
        self.assertIn('"identitet-lagretilstand identitet-lagretilstand-" + tilstand', kropp)

    def test_variant_knapp_synlighet_folger_aktiv_recipe_id(self):
        kropp = _funksjonskropp(_app_js(), r"function _oppdaterLagreTilstandUI\(oppskrift\)\s*\{")
        self.assertRegex(kropp, r"variantKnapp\.hidden\s*=\s*!_aktivRecipeId")
        self.assertRegex(kropp, r"variantHjelp\.hidden\s*=\s*!_aktivRecipeId")


class TestLagreOppskriftOppdatererStatusLive(unittest.TestCase):
    """A1/A3/A4 -- et eksplisitt Lagre skal umiddelbart vise "Lagret" (via
    beregnOgVisResultat() -> _oppdaterLagreTilstandUI()), og satt
    _aktivRecipeId FØR den rerenderes, ikke etterpå."""

    def test_rekkefolge_settId_for_rerender(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreOppskrift\(\)\s*\{")
        id_idx = kropp.index("_aktivRecipeId = res.recipeId;")
        rerender_idx = kropp.index("beregnOgVisResultat();")
        self.assertLess(id_idx, rerender_idx)


class TestLagreSomVariant(unittest.TestCase):
    """C -- AC11/AC12: én eksplisitt handling som oppretter en NY lagret
    identitet uten å røre originalen."""

    def test_funksjon_finnes(self):
        self.assertRegex(_app_js(), r"function lagreSomVariant\(\)\s*\{")

    def test_bruker_null_recipeid_ikke_aktivRecipeId(self):
        # AC12: må ALDRI sende inn _aktivRecipeId (det ville upsertet/
        # overskrevet originalen i stedet for å opprette en ny rad).
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertIn("lagreOppskriftIStore(oppskrift, null)", kropp)
        self.assertNotIn("lagreOppskriftIStore(oppskrift, _aktivRecipeId)", kropp)

    def test_unngar_navnekollisjon_med_originalen(self):
        # lagreOppskriftIStore() fjerner enhver ANNEN rad med samme navn
        # (se recipe_storage.js) -- uten dette navnesjekk-/forslag-steget
        # ville en variant lagret under SAMME navn som originalen derfor
        # STILLE SLETTET originalen. Se recipe_storage.js sin dokumenterte
        # navneunikhet.
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertRegex(kropp, r"if\s*\(original\s*&&\s*oppskrift\.navn\s*===\s*original\.navn\)")
        self.assertIn('t("oppskrift.variantNavnForslag"', kropp)

    def test_recipe_storage_har_fortsatt_navneunikhet_variantguarden_forutsetter(self):
        # FREEZE: hvis recipe_storage.js sin navne-dedup noensinne fjernes,
        # blir navnekollisjons-vernet over overflødig (men ikke farlig) --
        # denne testen dokumenterer AVHENGIGHETEN eksplisitt slik at en
        # fremtidig endring i recipe_storage.js blir synlig her også.
        kilde = _les(_RECIPE_STORAGE_JS)
        kropp = _funksjonskropp(kilde, r"function lagreOppskriftIStore\(recipe,\s*recipeId\)\s*\{")
        self.assertIn("i.recipe.navn !== normalisert.navn", kropp)

    def test_setter_aktivRecipeId_til_ny_id_etter_lagring(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        id_idx = kropp.index("_aktivRecipeId = res.recipeId;")
        rerender_idx = kropp.index("beregnOgVisResultat();")
        self.assertLess(id_idx, rerender_idx)


class TestModusBytteRorerIkkeOppskriftsinnhold(unittest.TestCase):
    """AC18 -- Learner/Master-bytte skal ikke i seg selv kunne markere
    oppskriften "endret". Siden lagreTilstandForOppskrift() sammenligner
    INNHOLD (samleOppskrift()), ikke modus, holder det å bekrefte at
    settModus() aldri kaller beregnOgVisResultat() eller på annen måte
    skriver til skjemafeltene samleOppskrift() leser fra."""

    def test_settmodus_kaller_ikke_beregnOgVisResultat(self):
        kilde = _app_js()
        kropp = _funksjonskropp(kilde, r"function settModus\(modus,\s*persister\s*=\s*true\)\s*\{")
        self.assertNotIn("beregnOgVisResultat", kropp)


class TestMarkupOgI18n(unittest.TestCase):
    """B/C -- badge og variant-knapp/hjelpetekst må faktisk finnes i
    kildemarkup-et, koblet via id til det app.js leser/skriver, med
    NO-tekst for begge de nye i18n-navnerommene."""

    def test_badge_element_finnes_i_identitetskortet(self):
        html = _les(_INDEX_HTML)
        self.assertIn('id="identitet-lagretilstand"', html)

    def test_variant_knapp_og_hjelpetekst_finnes_skjult_som_default(self):
        html = _les(_INDEX_HTML)
        self.assertRegex(html, r'<button[^>]*id="lagre-variant-knapp"[^>]*hidden')
        self.assertRegex(html, r'id="lagre-variant-hjelpetekst"[^>]*hidden')

    def test_variant_knapp_klikk_kobles_til_lagreSomVariant(self):
        kilde = _app_js()
        self.assertIn(
            'document.getElementById("lagre-variant-knapp").addEventListener("click", lagreSomVariant);',
            kilde,
        )

    def test_no_og_en_har_lagretilstand_nokler(self):
        i18n = _les(_I18N_JS)
        for nokkel in (
            "identitet.lagretilstand.kladd",
            "identitet.lagretilstand.lagret",
            "identitet.lagretilstand.endret",
            "builder.handling.lagreVariant",
            "builder.handling.variantHjelpetekst",
            "oppskrift.variantNavnForslag",
            "oppskrift.lagretVariantStatus",
        ):
            self.assertEqual(
                i18n.count('"%s"' % nokkel), 2,
                "forventet nøyaktig 2 forekomster (NO + EN) av %r" % nokkel,
            )


if __name__ == "__main__":
    unittest.main()
