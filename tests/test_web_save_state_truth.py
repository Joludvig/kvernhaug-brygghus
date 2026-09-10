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
        self.assertRegex(kropp, r"Object\.keys\(verdi\)\s*\.filter\(\(k\)[^\n]*\)\s*\.sort\(\)")


class TestKanoniskJsonHandtererUndefined(unittest.TestCase):
    """Issue #110 -- egendefinerte malt/humle/gjær-lesere produserer valgfrie
    felt som `felt.value.trim() || undefined` (se app.js sine
    .eg-produsent/.eg-opprinnelse/.eg-type-lesere og
    gjaerEgProdusent/gjaerEgGjaertype). Den aktive kladden får dermed nøkler
    med JS-verdien undefined, mens faktisk persistering (vanlig
    JSON.stringify(), se recipe_storage.js) utelater slike nøkler helt.
    _kanoniskJson() må speile NØYAKTIG den JSON.stringify()-oppførselen,
    ellers rapporterer W3 falskt "Endret siden lagring" rett etter en
    eksplisitt vellykket lagring (B03-tillit, se #106)."""

    def _kropp(self):
        return _funksjonskropp(_app_js(), r"function _kanoniskJson\(verdi\)\s*\{")

    def test_objektnokler_med_undefined_verdi_utelates(self):
        # JSON.stringify({a: undefined, b: 1}) === '{"b":1}' -- nøyaktig
        # samme utelatelse må skje her, FØR sortering/serialisering, ellers
        # dukker "produsent":undefined opp i kladden mens den lagrede raden
        # (som gikk via ekte JSON.stringify) aldri hadde nøkkelen i det hele
        # tatt.
        kropp = self._kropp()
        self.assertRegex(kropp, r"\.filter\(\(k\)\s*=>\s*verdi\[k\]\s*!==\s*undefined\)")

    def test_array_elementer_med_undefined_blir_null_ikke_utelatt(self):
        # JSON.stringify([undefined, 1]) === '[null,1]' -- et utelatt
        # element ville forskjøvet array-lengden/indeksene og dermed brutt
        # sammenligning av f.eks. malt-/humle-/gjærlister.
        kropp = self._kropp()
        self.assertRegex(kropp, r'v\s*===\s*undefined\s*\?\s*"null"\s*:\s*_kanoniskJson\(v\)')

    def test_null_false_null_og_tom_streng_er_ikke_undefined_og_overlever(self):
        # AC7: disse er REELLE, meningsbærende verdier -- filteret over
        # sjekker eksplisitt `!== undefined`, ikke en løsere falsy-sjekk som
        # ville slukt null/false/0/"" ved en feil.
        kropp = self._kropp()
        self.assertNotRegex(kropp, r"!verdi\[k\]")
        self.assertNotRegex(kropp, r"if\s*\(!v\)")


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


class TestStaleLagretKvitteringBlankesVedEndring(unittest.TestCase):
    """Astra Audit #2, A2-04 (issue #192) -- residual fra W3 (#106): badgen
    over ("Lagret"/"Endret siden lagring") oppdateres allerede live, men den
    enkeltstående kvitteringslinjen under lagre-knappene ("Lagret ..."/
    "Lagret som variant ...") ble aldri i seg selv fjernet igjen etter videre
    redigering. _lagreStatusKvittering sporer hvilken _aktivRecipeId + tekst
    den siste kvitteringen gjaldt for, og _oppdaterLagreTilstandUI() -- samme
    boundary som allerede kjører på HVER beregning for badgen -- blanker den
    ut igjen så snart tilstanden ikke lenger er "lagret"."""

    def test_kvitteringssporing_deklarert(self):
        self.assertRegex(_app_js(), r"let _lagreStatusKvittering\s*=\s*null;")

    def test_oppdaterLagreTilstandUI_blanker_kvitteringen_ved_ikke_lagret_tilstand(self):
        kropp = _funksjonskropp(_app_js(), r"function _oppdaterLagreTilstandUI\(oppskrift\)\s*\{")
        self.assertRegex(
            kropp,
            r'if\s*\(tilstand\s*!==\s*"lagret"\s*&&\s*_lagreStatusKvittering\s*&&\s*'
            r"_lagreStatusKvittering\.recipeId\s*===\s*_aktivRecipeId\)",
        )
        self.assertIn('status.textContent === _lagreStatusKvittering.tekst', kropp)
        self.assertIn('status.textContent = "";', kropp)
        self.assertIn("_lagreStatusKvittering = null;", kropp)

    def test_blanking_skjer_kun_nar_synlig_tekst_fortsatt_er_ordrett_kvitteringen(self):
        # Skal ALDRI overskrive/fjerne en ANNEN statusmelding (feilmelding,
        # "Ny oppskrift", "Åpnet fil", ...) som har erstattet kvitteringen i
        # mellomtiden -- kun blanke ut når teksten fortsatt er den samme.
        kropp = _funksjonskropp(_app_js(), r"function _oppdaterLagreTilstandUI\(oppskrift\)\s*\{")
        self.assertRegex(kropp, r'if\s*\(status\s*&&\s*status\.textContent\s*===\s*_lagreStatusKvittering\.tekst\)\s*\{')

    def test_lagreOppskrift_registrerer_kvitteringen(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreOppskrift\(\)\s*\{")
        self.assertRegex(
            kropp,
            r"_lagreStatusKvittering\s*=\s*\{\s*recipeId:\s*_aktivRecipeId,\s*tekst:\s*status\.textContent\s*\};",
        )
        # Må settes ETTER selve kvitteringsteksten, ikke før.
        tekst_idx = kropp.index('status.textContent = t("oppskrift.lagretStatus"')
        spor_idx = kropp.index("_lagreStatusKvittering = {")
        self.assertLess(tekst_idx, spor_idx)

    def test_lagreSomVariant_registrerer_kvitteringen(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertRegex(
            kropp,
            r"_lagreStatusKvittering\s*=\s*\{\s*recipeId:\s*_aktivRecipeId,\s*tekst:\s*status\.textContent\s*\};",
        )
        tekst_idx = kropp.index('status.textContent = t("oppskrift.lagretVariantStatus"')
        spor_idx = kropp.index("_lagreStatusKvittering = {")
        self.assertLess(tekst_idx, spor_idx)


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

    def test_unngar_navnekollisjon_med_enhver_eksisterende_oppskrift(self):
        # Chief-review-fiks (PR #107, runde 3): kollisjonssjekken må dekke
        # ETHVERT eksisterende navn (finnOppskriftVedNavn), ikke bare
        # originalens -- ellers ville en bruker som manuelt endrer
        # navnefeltet til navnet på en HELT ANNEN lagret oppskrift B, og så
        # trykker "Lagre som variant", stille slette B via
        # lagreOppskriftIStore() sin navneunikhet (se
        # recipe_storage.js). Se TestLagreSomVariantUnngarKollisjonMedAlleNavn
        # for de fulle scenario-testene review'en ba om.
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertRegex(kropp, r"if\s*\(finnOppskriftVedNavn\(oppskrift\.navn\)\)")
        self.assertIn("_forslaVariantNavn(oppskrift.navn)", kropp)

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


class TestForslaVariantNavnUnikhet(unittest.TestCase):
    """Chief-review-fiks (PR #107): en andre variant fra samme original
    (fortsatt under originalens navn) må IKKE generere samme forslag som
    den første varianten allerede lagret under -- det ville stille slettet
    den første varianten via recipe_storage.js sin navneunikhet. Se
    1) original lagret, 2) første variant opprettet, 3) andre variant fra
    samme original sletter ikke den første, 4) hver variant får en distinkt
    recipeId (lagreOppskriftIStore(oppskrift, null) tvinger alltid en fersk
    id, uendret av denne fiksen), 5) originalen er urørt (samme null-id-vei
    som før), 6) NO/EN-forslagene er deterministisk avledet fra samme
    i18n-nøkler for begge språk."""

    def test_funksjon_finnes(self):
        self.assertRegex(_app_js(), r"function _forslaVariantNavn\(originalNavn\)\s*\{")

    def test_returnerer_basisforslag_nar_det_er_ledig(self):
        kropp = _funksjonskropp(_app_js(), r"function _forslaVariantNavn\(originalNavn\)\s*\{")
        self.assertIn('t("oppskrift.variantNavnForslag"', kropp)
        self.assertRegex(kropp, r"if\s*\(!finnOppskriftVedNavn\(forslag\)\)\s*return\s*forslag")

    def test_soker_neste_ledige_nummererte_navn_ved_kollisjon(self):
        # Andre variant fra samme original: basisforslaget ("(kopi)") er nå
        # opptatt av den FØRSTE varianten, så denne løkken må lete videre
        # ("(kopi 2)", "(kopi 3)", ...) i stedet for å gjenbruke det samme
        # navnet og dermed slette den første varianten.
        kropp = _funksjonskropp(_app_js(), r"function _forslaVariantNavn\(originalNavn\)\s*\{")
        self.assertIn('t("oppskrift.variantNavnForslagNummerert"', kropp)
        self.assertRegex(kropp, r"while\s*\(finnOppskriftVedNavn\(nummerertForslag\)\)")
        self.assertIn("n++", kropp)
        self.assertIn("let n = 2;", kropp)

    def test_lagreSomVariant_bruker_alltid_fersk_id_uansett_navneforslag(self):
        # 3/4/5: uansett hvilket navn _forslaVariantNavn() lander på, skal
        # lagreSomVariant() fortsatt aldri sende inn _aktivRecipeId -- det er
        # ALENE det som garanterer en distinkt recipeId per variant og at
        # originalen (identifisert av _aktivRecipeId) forblir urørt.
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertIn("lagreOppskriftIStore(oppskrift, null)", kropp)

    def test_no_og_en_navnekollisjon_bruker_samme_nokkelnavn(self):
        # 6: samme nøkkel ("oppskrift.variantNavnForslagNummerert") brukes
        # for begge språk -- selve oversettelsen (t()) er det eneste som
        # varierer, ikke hvilken logikk som avgjør NÅR den brukes.
        i18n = _les(_I18N_JS)
        self.assertEqual(i18n.count('"oppskrift.variantNavnForslagNummerert"'), 2)
        self.assertIn('"oppskrift.variantNavnForslagNummerert": "{navn} (kopi {n})"', i18n)
        self.assertIn('"oppskrift.variantNavnForslagNummerert": "{navn} (copy {n})"', i18n)


class TestLagreSomVariantUnngarKollisjonMedAlleNavn(unittest.TestCase):
    """Chief-review-fiks (PR #107, runde 3) -- runde 2 sin variant-vern
    dekket bare kollisjon med ORIGINALENS navn
    (`oppskrift.navn === original.navn`). Reviewens flaggede scenario:
    1) original A lagret;
    2) en urelatert oppskrift B lagret;
    3) A sin aktive kladd navngis manuelt om til B sitt eksakte navn;
    4) "Lagre som variant" skal IKKE slette/erstatte B;
    5) original A skal forbli urørt;
    6) den nye varianten får en distinkt recipeId og et ikke-kolliderende
       navn;
    7) NO/EN-oppførselen er deterministisk (samme i18n-nøkler begge veier).

    Uten JS-kjøretid (se filens toppkommentar) bevises dette som en
    kilde-kontrakt: kollisjonsvakten må være uttrykt over
    finnOppskriftVedNavn() -- et GLOBALT navnesøk i HELE lageret (se
    recipe_storage.js), ikke en sammenligning kun mot original.navn --
    og lagreSomVariant() skal ikke lenger hente/bruke "original" i det
    hele tatt, siden nøyaktig DEN antagelsen (at bare originalens navn
    kan kollidere) var rotårsaken reviewen flagget."""

    def test_kollisjonsvakten_bruker_ikke_lenger_original(self):
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertNotIn("original", kropp)
        self.assertNotIn("_hentSisteLagredeOppskrift()", kropp)

    def test_finnOppskriftVedNavn_soker_alle_rader_uavhengig_av_identitet(self):
        # 1/2: dekker BÅDE original A og en urelatert B, siden søket ikke
        # filtrerer bort noen rad basert på recipeId -- bare navn.
        kilde = _les(_RECIPE_STORAGE_JS)
        kropp = _funksjonskropp(kilde, r"function finnOppskriftVedNavn\(navn\)\s*\{")
        self.assertIn("alleOppskrifter().find((i) => i.recipe.navn === navn)", kropp)
        self.assertNotIn("recipeId", kropp)

    def test_forslag_beregnes_fra_kladdens_faktiske_gjeldende_navn(self):
        # 3: navnet som sjekkes/foreslås-fra er oppskrift.navn -- kladdens
        # eget, gjeldende navn (her: B sitt navn, etter manuell omdøping),
        # ikke et navn hentet fra et separat "original"-oppslag.
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertIn("if (finnOppskriftVedNavn(oppskrift.navn)) {", kropp)
        self.assertIn("navnFelt.value = _forslaVariantNavn(oppskrift.navn);", kropp)

    def test_ny_variant_far_fersk_id_original_og_b_forblir_urort(self):
        # 4/5/6: lagreOppskriftIStore(oppskrift, null) tvinger alltid en ny
        # recipeId (distinkt fra både A og B). Siden navnekollisjonen
        # allerede er løst FØR dette kallet, fjerner lagreOppskriftIStore()
        # sin navneunikhet ikke lenger noen eksisterende rad -- verken B
        # eller originalen A (identifisert av den urørte _aktivRecipeId).
        kropp = _funksjonskropp(_app_js(), r"function lagreSomVariant\(\)\s*\{")
        self.assertIn("lagreOppskriftIStore(oppskrift, null)", kropp)
        self.assertNotIn("lagreOppskriftIStore(oppskrift, _aktivRecipeId)", kropp)

    def test_no_og_en_bruker_samme_forslagsnokler_uavhengig_av_kollisjonskilde(self):
        # 7: samme i18n-nøkler (oppskrift.variantNavnForslag/
        # -Nummerert) brukes uansett HVEM sitt navn som kolliderte -- ingen
        # egen gren/nøkkel for "kolliderte med original" vs. "kolliderte
        # med en annen lagret oppskrift".
        i18n = _les(_I18N_JS)
        self.assertEqual(i18n.count('"oppskrift.variantNavnForslag"'), 2)
        self.assertEqual(i18n.count('"oppskrift.variantNavnForslagNummerert"'), 2)


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
            "oppskrift.variantNavnForslagNummerert",
            "oppskrift.lagretVariantStatus",
        ):
            self.assertEqual(
                i18n.count('"%s"' % nokkel), 2,
                "forventet nøyaktig 2 forekomster (NO + EN) av %r" % nokkel,
            )


if __name__ == "__main__":
    unittest.main()
