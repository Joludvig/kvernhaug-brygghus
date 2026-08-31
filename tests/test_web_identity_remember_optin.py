"""
Regresjonstest for Web Identity Remember Opt-in V1.

Samme metodemerknad som tests/test_web_mode_storage_fix.py: dette
miljøet har ingen JavaScript-kjøretid (ingen Node.js/npm, ingen jsdom/
Playwright/tilsvarende, ingen Python-JS-bro -- verifisert på nytt før
denne runden). Testene under er derfor KILDE-KONTRAKT-tester: de leser
de FAKTISKE, kjørende kildefilene (web/js/app.js, web/js/i18n.js,
web/index.html, web/en/index.html, web/js/recipe_storage.js) og
verifiserer -- via presise, snevert avgrensede mønstre -- at de
eksakte kodelinjene/markup-linjene som avgjør produktkontrakten A-G
(se brief "WEB IDENTITY REMEMBER OPT-IN V1") har riktig form.

Selve atferden er i tillegg verifisert manuelt ved kode-sporing i
sluttrapporten for denne runden. Ekte browser-verifikasjon gjøres av
brukeren før commit, se MANUAL BROWSER TEST PLAN i rapporten.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import re
import unittest

_APP_JS = r"D:\Development\Kvernhaug Brygghus\web\js\app.js"
_I18N_JS = r"D:\Development\Kvernhaug Brygghus\web\js\i18n.js"
_INDEX_NO = r"D:\Development\Kvernhaug Brygghus\web\index.html"
_INDEX_EN = r"D:\Development\Kvernhaug Brygghus\web\en\index.html"
_RECIPE_STORAGE_JS = r"D:\Development\Kvernhaug Brygghus\web\js\recipe_storage.js"


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


def _funksjonskropp(kilde, funksjonssignatur_regex):
    """Henter kroppen til en toppnivå-funksjon (fra 'function ... {' til
    linjen med den avsluttende '}' i kolonne 0)."""
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestLegacyDataSafetyBevis(unittest.TestCase):
    """Forutsetning for HELE denne runden (brief pkt. 5): bekreft at
    IDENTITET_NOKKEL faktisk KUN er en separat forhåndsutfyllings-cache,
    og at brygger/bryggeri alltid også lever i selve oppskriften -- slik
    at fjerning av IDENTITET_NOKKEL aldri kan røre oppskriftsdata."""

    def test_brygger_bryggeri_er_anerkjente_oppskriftsfelt(self):
        kilde = _les(_RECIPE_STORAGE_JS)
        self.assertIn('"brygger"', kilde)
        self.assertIn('"bryggeri"', kilde)

    def test_identitet_nokkel_kun_referert_i_app_js(self):
        # Ingen annen web-fil skal lese/skrive IDENTITET_NOKKEL --
        # bekrefter at den er en isolert, redundant cache uten andre
        # avhengigheter noe annet sted i kodebasen.
        for sti in (
            r"D:\Development\Kvernhaug Brygghus\web\js\recipe_storage.js",
            r"D:\Development\Kvernhaug Brygghus\web\js\kbhrecipe.js",
            r"D:\Development\Kvernhaug Brygghus\web\js\brew_storage.js",
        ):
            kilde = _les(sti)
            self.assertNotIn("IDENTITET_NOKKEL", kilde)
            self.assertNotIn("kvernhaug_web_identitet", kilde)


class TestOptInDefaultOff(unittest.TestCase):
    """A: fravær av IDENTITET_HUSK_NOKKEL = AV. Skriving i identitetsfelt
    skal IKKE opprette identity-prefill uten eksplisitt opt-in."""

    def test_husk_nokkel_definert(self):
        kilde = _les(_APP_JS)
        self.assertIn('const IDENTITET_HUSK_NOKKEL = "kvernhaug_web_identitet_husk";', kilde)

    def test_har_identitet_husk_sjekker_streng_verdi(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _harIdentitetHusk\(\)\s*\{")
        self.assertIn('localStorage.getItem(IDENTITET_HUSK_NOKKEL) === "1"', kropp)

    def test_lagre_identitetspreferanse_gates_paa_opt_in(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function lagreIdentitetsPreferanse\(\)\s*\{")
        self.assertRegex(
            kropp.lstrip(),
            r"^if \(!_harIdentitetHusk\(\)\) return;",
            "lagreIdentitetsPreferanse() må avvise tidlig når opt-in er AV",
        )

    def test_input_lyttere_uendret_kaller_fortsatt_lagre(self):
        # Selve kallstedene (typing i feltene) skal IKKE ha noen egen
        # opt-in-sjekk -- gatingen skal ligge INNI lagreIdentitetsPreferanse()
        # (én kontrollpunkt), ikke spredt ut på hvert kallsted.
        kilde = _les(_APP_JS)
        for felt_id in ("brygger-navn", "bryggeri-navn"):
            self.assertRegex(
                kilde,
                r'getElementById\("%s"\)\.addEventListener\("input", \(\) => \{\s*'
                r"lagreIdentitetsPreferanse\(\);" % re.escape(felt_id),
            )


class TestOptIn(unittest.TestCase):
    """B: aktiv avkrysning lagrer remember-state, fanger nåværende
    identitetsverdier som prefill, og videre typing oppdaterer dem
    (via den allerede gatede lagreIdentitetsPreferanse())."""

    def test_sett_identitet_husk_paa_setter_nokkel_foer_lagring(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _settIdentitetHusk\(paa\)\s*\{")
        m = re.search(r"if \(paa\) \{(.*?)\} else \{", kropp, re.S)
        self.assertIsNotNone(m, "fant ikke if(paa)-grenen i _settIdentitetHusk()")
        paa_gren = m.group(1)
        self.assertIn('localStorage.setItem(IDENTITET_HUSK_NOKKEL, "1");', paa_gren)
        # Nøkkelen MÅ settes FØR lagreIdentitetsPreferanse() kalles, ellers
        # ville dens egen opt-in-sjekk (se TestOptInDefaultOff) avvist kallet.
        idx_set = paa_gren.index("localStorage.setItem(IDENTITET_HUSK_NOKKEL")
        idx_lagre = paa_gren.index("lagreIdentitetsPreferanse();")
        self.assertLess(idx_set, idx_lagre)

    def test_checkbox_change_kaller_sett_identitet_husk(self):
        kilde = _les(_APP_JS)
        self.assertRegex(
            kilde,
            r'identitetHuskCheckbox\.addEventListener\("change", \(\) => \{\s*'
            r"_settIdentitetHusk\(identitetHuskCheckbox\.checked\);",
        )

    def test_checkbox_finnes_i_init_med_riktig_id(self):
        kilde = _les(_APP_JS)
        self.assertIn(
            'const identitetHuskCheckbox = document.getElementById("identitet-husk-checkbox");',
            kilde,
        )


class TestReloadGjenoppretterState(unittest.TestCase):
    """C: remember-state gjenopprettes ved init, og identity-prefill
    brukes når relevant (dvs. når opt-in er ON)."""

    def test_checkbox_checked_settes_fra_har_identitet_husk_ved_init(self):
        kilde = _les(_APP_JS)
        self.assertIn("identitetHuskCheckbox.checked = _harIdentitetHusk();", kilde)

    def test_forhandsutfyll_gates_paa_opt_in(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function forhandsutfyllIdentitetsPreferanse\(\)\s*\{")
        self.assertRegex(
            kropp.lstrip(),
            r"^if \(!_harIdentitetHusk\(\)\) return;",
            "forhandsutfyllIdentitetsPreferanse() må avvise tidlig når opt-in er AV",
        )

    def test_checkbox_state_leses_foer_forhandsutfylling_i_init(self):
        kilde = _les(_APP_JS)
        idx_checkbox = kilde.index("identitetHuskCheckbox.checked = _harIdentitetHusk();")
        idx_forhandsutfyll = kilde.index("forhandsutfyllIdentitetsPreferanse();", idx_checkbox)
        self.assertGreater(idx_forhandsutfyll, idx_checkbox)


class TestOptOut(unittest.TestCase):
    """D: opt-out fjerner BÅDE remember-state og den separate
    identity-cachen, men rører ALDRI feltverdiene i den aktive
    oppskriften."""

    def test_sett_identitet_husk_av_fjerner_begge_nokler(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _settIdentitetHusk\(paa\)\s*\{")
        m = re.search(r"\} else \{(.*?)\}\s*$", kropp, re.S)
        self.assertIsNotNone(m, "fant ikke else-grenen i _settIdentitetHusk()")
        av_gren = m.group(1)
        self.assertIn("localStorage.removeItem(IDENTITET_HUSK_NOKKEL);", av_gren)
        self.assertIn("localStorage.removeItem(IDENTITET_NOKKEL);", av_gren)
        # Skal IKKE røre selve feltverdiene -- "husk av" != "tøm feltet".
        self.assertNotIn('getElementById("brygger-navn")', av_gren)
        self.assertNotIn('getElementById("bryggeri-navn")', av_gren)
        self.assertNotIn("AKTIV_KLADD_NOKKEL", av_gren)


class TestLegacyMigrering(unittest.TestCase):
    """E: gammel identity-cache uten eksplisitt remember-state regnes
    IKKE som opt-in. Migreringen rydder KUN den separate legacy-cachen,
    aldri oppskriftsdata/aktiv kladd."""

    def test_rydd_legacy_funksjon_sjekker_fravaer_av_husk_nokkel(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _ryddLegacyIdentitetHvisIkkeOptInn\(\)\s*\{")
        self.assertIn("localStorage.getItem(IDENTITET_HUSK_NOKKEL) === null", kropp)
        self.assertIn("localStorage.removeItem(IDENTITET_NOKKEL);", kropp)
        # Skal aldri røre aktiv kladd, modus, språk eller preferanser.
        for frossen_nokkel in ("AKTIV_KLADD_NOKKEL", "MODUS_NOKKEL", "SPRAK_NOKKEL", "PREFERANSER_NOKKEL"):
            self.assertNotIn(frossen_nokkel, kropp)

    def test_rydd_legacy_kalles_i_init_foer_checkbox_og_forhandsutfylling(self):
        kilde = _les(_APP_JS)
        idx_rydd = kilde.index("_ryddLegacyIdentitetHvisIkkeOptInn();")
        idx_checkbox = kilde.index("identitetHuskCheckbox.checked = _harIdentitetHusk();")
        idx_forhandsutfyll = kilde.index("forhandsutfyllIdentitetsPreferanse();", idx_rydd)
        self.assertLess(idx_rydd, idx_checkbox)
        self.assertLess(idx_checkbox, idx_forhandsutfyll)


class TestPrefillOverstyrerIkkeEksisterendeIdentitet(unittest.TestCase):
    """F: eksisterende bryggerdata fra aktiv kladd/lagret/importert
    oppskrift skal ikke overskrives av prefill. Selve prioriterings-
    rekkefølgen (kladd-gjenoppretting SKJER ETTER identitets-blokken i
    init, og overskriver feltene ubetinget) er UENDRET av denne runden
    -- disse testene bekrefter at den fortsatt står slik."""

    def test_import_kaller_ikke_forhandsutfylling_etter_gjenoppretting(self):
        kilde = _les(_APP_JS)
        i = kilde.index("function apneOppskriftsfil(fil)")
        m = re.search(r"\n(?:async )?function ", kilde[i + 10:])
        self.assertIsNotNone(m, "fant ikke neste toppnivå-funksjon etter apneOppskriftsfil()")
        slutt = i + 10 + m.start()
        kropp = kilde[i:slutt]
        self.assertIn("_gjenopprettOppskrift(resultat.oppskrift);", kropp)
        self.assertNotIn("forhandsutfyllIdentitetsPreferanse()", kropp)

    def test_ny_oppskrift_kaller_forhandsutfylling_rett_etter_blank(self):
        # "Ny oppskrift" ER produktlogikkens eksplisitte "tom identitet"-
        # tilfelle -- prefill skal fortsatt gjelde akkurat her.
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function nyOppskrift\(\)\s*\{")
        idx_blank = kropp.index("_gjenopprettOppskrift(_blankOppskrift());")
        idx_forhandsutfyll = kropp.index("forhandsutfyllIdentitetsPreferanse();")
        self.assertLess(idx_blank, idx_forhandsutfyll)

    def test_aktiv_kladd_gjenopprettes_etter_identitetsblokken_i_init(self):
        # Init-rekkefølgen (uendret): identitets-checkbox/forhåndsutfylling
        # FØR "const kladd = hentAktivKladd()"-blokken -- slik at en
        # eksisterende kladds EGNE brygger/bryggeri-verdier (også tomme
        # strenger) alltid vinner ved unødvendig overskriving i
        # _gjenopprettOppskrift(kladd).
        kilde = _les(_APP_JS)
        idx_forhandsutfyll = kilde.index("forhandsutfyllIdentitetsPreferanse();")
        idx_kladd = kilde.index("const kladd = hentAktivKladd();")
        idx_gjenopprett_kladd = kilde.index("_gjenopprettOppskrift(kladd);")
        self.assertLess(idx_forhandsutfyll, idx_kladd)
        self.assertLess(idx_kladd, idx_gjenopprett_kladd)


class TestNoEnUI(unittest.TestCase):
    """G: korrekt label finnes på begge språk, i både i18n-ordboken og
    i den faktiske (NO-kilde + generert EN-speil) HTML-en."""

    def test_i18n_nokler_finnes_paa_begge_sprak(self):
        kilde = _les(_I18N_JS)
        self.assertIn(
            '"builder.grunndata.huskLabel": "Husk bryggerinformasjon på denne enheten",', kilde,
        )
        self.assertIn('"builder.grunndata.huskHjelp": "Lagres bare i denne nettleseren.",', kilde)
        self.assertIn(
            '"builder.grunndata.huskLabel": "Remember brewer information on this device",', kilde,
        )
        self.assertIn('"builder.grunndata.huskHjelp": "Stored only in this browser.",', kilde)

    def test_no_html_har_checkbox_med_riktig_i18n_referanse(self):
        kilde = _les(_INDEX_NO)
        self.assertIn('<input type="checkbox" id="identitet-husk-checkbox">', kilde)
        self.assertIn('data-i18n="builder.grunndata.huskLabel"', kilde)
        self.assertIn('data-i18n="builder.grunndata.huskHjelp"', kilde)

    def test_checkbox_ligger_i_egen_label_ikke_i_felt_rad(self):
        # Kritisk for at generatorens el.clear()-baserte data-i18n-
        # innsetting ALDRI kan slette selve <input>-elementet: teksten må
        # stå i et eget <span data-i18n>, ikke direkte på <label>.
        kilde = _les(_INDEX_NO)
        i = kilde.index('id="identitet-husk-checkbox"')
        omgivelse = kilde[max(0, i - 200):i + 300]
        self.assertIn('<span data-i18n="builder.grunndata.huskLabel">', omgivelse)

    def test_en_html_generert_med_engelsk_tekst_og_bevart_checkbox(self):
        # web/en/index.html er 100% generert (scripts/generate_web_i18n_pages.py)
        # -- denne testen bekrefter at generatoren faktisk produserte riktig
        # innhold, IKKE at filen ble håndredigert.
        kilde = _les(_INDEX_EN)
        self.assertIn('id="identitet-husk-checkbox"', kilde)
        self.assertIn("Remember brewer information on this device", kilde)
        self.assertIn("Stored only in this browser.", kilde)
        # Selve checkbox-inputen skal fortsatt finnes ved siden av
        # tekst-spanet -- bekrefter at el.clear() ikke spiste den.
        self.assertIn('type="checkbox"', kilde)


if __name__ == "__main__":
    unittest.main()
