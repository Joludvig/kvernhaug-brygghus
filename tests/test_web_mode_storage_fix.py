"""
Regresjonstest for Web Mode Storage Fix V1.

VIKTIG METODEMERKNAD: Dette repoet har ingen JavaScript-kjøretid (ingen
Node.js, ingen npm, ingen jsdom/Playwright/tilsvarende er installert i
dette miljøet -- verifisert eksplisitt før denne testen ble skrevet).
Disse testene kan derfor IKKE faktisk kjøre web/js/app.js og observere
at localStorage.setItem() kalles eller ikke kalles ved runtime, slik
Python-testene ellers i denne mappen kjører ekte Streamlit-kode.

I stedet er dette KILDE-KONTRAKT-tester: de leser den FAKTISKE,
kjørende kildefilen web/js/app.js (ikke en kopi, ikke en
reimplementasjon) og verifiserer -- via presise, snevert avgrensede
mønstre -- at de eksakte kodelinjene som avgjør oppførselen A-E fortsatt
har riktig form. Dette er en svakere garanti enn et ekte kjørt
JS-unit-test ville gitt, men det er langt sterkere enn ingen test i det
hele tatt, og det fanger opp enhver fremtidig endring som utilsiktet
fjerner persister-skillet eller gjeninnfører den ubetingede skrivingen.

Selve atferden (A-E under) er i tillegg verifisert manuelt ved
kode-sporing i BREWDAY-rapporten for denne runden, siden JS-kontrollflyten
her er enkel nok (ren ternary + if, ingen async, ingen skjult tilstand)
til at en presis manuell sporing er pålitelig.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import re
import unittest

_APP_JS = r"D:\Development\Kvernhaug Brygghus\web\js\app.js"


def _kildekode():
    with io.open(_APP_JS, encoding="utf-8") as f:
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


class TestSettModusPersisterParameter(unittest.TestCase):
    """settModus() skal skille "vis i UI" fra "brukeren valgte dette" via
    en persister-parameter som defaulter til True (bevarer eksisterende
    oppførsel for alle kallsteder som IKKE eksplisitt sier false)."""

    def test_signatur_har_persister_default_true(self):
        kilde = _kildekode()
        self.assertRegex(
            kilde,
            r"function settModus\(modus,\s*persister\s*=\s*true\)\s*\{",
            "settModus() mangler persister-parameter med default true",
        )

    def test_localstorage_write_er_betinget_av_persister(self):
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function settModus\(modus,\s*persister\s*=\s*true\)\s*\{")
        self.assertRegex(
            kropp,
            r"if\s*\(persister\)\s*localStorage\.setItem\(MODUS_NOKKEL,\s*modus\)",
            "localStorage.setItem for MODUS_NOKKEL er ikke (lenger) betinget av persister",
        )
        # Skal IKKE finnes noen ubetinget setItem-linje for MODUS_NOKKEL
        # inni funksjonen (dvs. bare den ene, betingede forekomsten over).
        alle_setitem = re.findall(r"localStorage\.setItem\(MODUS_NOKKEL", kropp)
        self.assertEqual(len(alle_setitem), 1, "forventet nøyaktig én setItem-referanse i settModus()")

    def test_visning_og_ui_oppdateres_uavhengig_av_persister(self):
        # Selve visningslogikken (body-klasser, aria-pressed, statustekst)
        # skal IKKE stå bak persister-sjekken -- kun selve skrivingen.
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function settModus\(modus,\s*persister\s*=\s*true\)\s*\{")
        for uendret_linje in (
            'classList.toggle("modus-laerling"',
            'classList.toggle("modus-mester"',
            'setAttribute("aria-pressed"',
            "statusEl.textContent",
        ):
            self.assertIn(uendret_linje, kropp)
            # Ingen av disse skal stå INNI en "if (persister)"-blokk --
            # kun selve setItem-linjen skal være betinget.
            idx = kropp.index(uendret_linje)
            linje_med_context = kropp[max(0, idx - 40):idx]
            self.assertNotIn("if (persister)", linje_med_context)


class TestInitModusSkriverIkkeDefault(unittest.TestCase):
    """A + B + D: initModus() skal gjenopprette/vise modus (inkl. default
    "laerling") uten å skrive til localStorage, og førstegangsdialog-
    logikken skal stå helt uendret."""

    def test_initmodus_kaller_settmodus_med_persister_false(self):
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function initModus\(\)\s*\{")
        self.assertRegex(
            kropp,
            r'settModus\(lagret === "mester" \? "mester" : "laerling",\s*false\)',
            "initModus() sender ikke lenger persister:false til settModus()",
        )

    def test_default_er_fortsatt_laerling(self):
        # Selve default-verdien ("laerling" når ingenting er lagret) skal
        # IKKE være endret av denne runden.
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function initModus\(\)\s*\{")
        self.assertIn('lagret === "mester" ? "mester" : "laerling"', kropp)

    def test_forstegangsdialog_logikk_uendret(self):
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function initModus\(\)\s*\{")
        self.assertIn("if (!lagret) {", kropp)
        self.assertIn('getElementById("modus-forstegang").hidden = false', kropp)
        self.assertIn('getElementById("modus-forstegang-bakteppe").hidden = false', kropp)

    def test_lagret_leses_fortsatt_fra_samme_nokkel_foer_settmodus_kalles(self):
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function initModus\(\)\s*\{")
        les_idx = kropp.index("localStorage.getItem(MODUS_NOKKEL)")
        kall_idx = kropp.index("settModus(")
        self.assertLess(les_idx, kall_idx, "lesingen skal skje FØR settModus() kalles")


class TestEksplisittBrukervalgPersisterFortsatt(unittest.TestCase):
    """C + E: et faktisk klikk på en .modus-knapp (Bryggelærling ELLER
    Bryggmester) skal fortsatt kalle settModus() UTEN persister:false --
    dvs. bruke default (true) og dermed fortsatt skrive til localStorage."""

    def test_modus_knapp_klikk_kaller_settmodus_uten_persister_argument(self):
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function initModus\(\)\s*\{")
        m = re.search(r"addEventListener\(\"click\",\s*\(\)\s*=>\s*\{\s*settModus\(([^)]*)\)", kropp)
        self.assertIsNotNone(m, "fant ikke klikk-handleren som kaller settModus()")
        argumenter = m.group(1)
        self.assertEqual(
            argumenter.strip(), "knapp.dataset.modus",
            "klikk-handleren skal fortsatt kalle settModus() med ETT argument "
            "(persister skal defaulte til true -- et faktisk brukervalg skal lagres)",
        )

    def test_klikk_handler_lukker_forstegangsdialog(self):
        # Uendret atferd for øvrig: valget skal fortsatt lukke dialogen.
        kilde = _kildekode()
        kropp = _funksjonskropp(kilde, r"function initModus\(\)\s*\{")
        self.assertIn("_lukkModusForstegang();", kropp)


class TestSprakendretRefreshPersisterFalse(unittest.TestCase):
    """Samme prinsipp gjelder kvernhaug:sprakendret-lytterens rene
    visningsoppdatering av modus-teksten -- den skal heller ikke kunne
    skrive kvernhaug_web_modus for en bruker som ennå ikke har valgt
    modus (f.eks. bytter språk mens førstegangsdialogen står åpen)."""

    def test_sprakendret_kaller_settmodus_med_persister_false(self):
        kilde = _kildekode()
        i = kilde.index('addEventListener("kvernhaug:sprakendret"')
        # Se kun på de ~600 tegnene rett etter selve lytter-registreringen
        # -- nok til å dekke settModus()-kallet uten å risikere å plukke
        # opp en annen, urelatert del av filen.
        vindu = kilde[i:i + 900]
        self.assertRegex(
            vindu,
            r'settModus\(document\.body\.classList\.contains\("modus-mester"\) \? "mester" : "laerling",\s*false\)',
            "sprakendret-lytteren sender ikke lenger persister:false til settModus()",
        )


class TestAndreLocalStorageNoklerUrort(unittest.TestCase):
    """FREEZE: ingen andre localStorage-nøkler skal ha fått noen
    persister-lignende mekanisme eller på annen måte være endret av
    denne runden."""

    def test_andre_nokler_skriver_fortsatt_ubetinget_som_foer(self):
        # SPRAK_NOKKEL/PREFERANSER_NOKKEL skrives i i18n.js/preferences.js,
        # ikke i app.js -- utenfor denne rundens filscope. Sjekker her kun
        # de to andre app.js-interne nøklene som IKKE skal ha fått noen
        # persister-mekanisme.
        kilde = _kildekode()
        for setitem_linje in (
            "localStorage.setItem(IDENTITET_NOKKEL,",
            "localStorage.setItem(AKTIV_KLADD_NOKKEL,",
        ):
            self.assertIn(setitem_linje, kilde)
            idx = kilde.index(setitem_linje)
            linje_start = kilde.rindex("\n", 0, idx) + 1
            linje = kilde[linje_start:kilde.index("\n", idx)]
            self.assertNotIn("if (persister)", linje)
            self.assertNotIn("persister", linje)

    def test_modus_nokkel_navn_uendret(self):
        kilde = _kildekode()
        self.assertIn('const MODUS_NOKKEL = "kvernhaug_web_modus";', kilde)

    def test_sprak_og_preferanser_filer_urort(self):
        # SPRAK_NOKKEL (i18n.js) og PREFERANSER_NOKKEL (preferences.js)
        # ligger i EGNE filer denne runden ikke rørte -- bekreft at deres
        # skriving fortsatt er ubetinget, som et ekstra vern mot at noen
        # senere feilaktig antar persister-mønsteret gjelder der også.
        for sti, setitem_linje in (
            (r"D:\Development\Kvernhaug Brygghus\web\js\i18n.js",
             "localStorage.setItem(SPRAK_NOKKEL, kode);"),
            (r"D:\Development\Kvernhaug Brygghus\web\js\preferences.js",
             "localStorage.setItem(PREFERANSER_NOKKEL, JSON.stringify(pref));"),
        ):
            with io.open(sti, encoding="utf-8") as f:
                fil_kilde = f.read()
            self.assertIn(setitem_linje, fil_kilde)
            self.assertNotIn("persister", fil_kilde)


if __name__ == "__main__":
    unittest.main()
