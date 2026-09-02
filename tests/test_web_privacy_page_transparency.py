"""
Regresjonstest for Privacy Page Transparency Update V1.

Ren innholdstest -- ingen JS-kjøretid involvert her (i motsetning til de
andre web-testene i denne mappen), siden dette kun er statisk HTML/i18n-
tekst. Leser de faktiske, publiserte kildefilene direkte: web/personvern.html
(NO-kilde), web/en/personvern.html (100% generert av
scripts/generate_web_i18n_pages.py -- IKKE håndredigert), og
web/js/i18n.js (tekstinnholdet for begge språk).

Formålet er å hindre at siden på nytt kommer i utakt med faktisk kode
(slik den var før denne runden -- "Oppskriftene dine" beskrev kun
oppskrifter, ikke bryggelogg/pantry/utstyr/identitet), og å hindre at
feilaktige analytics-/cookie-/trackingpåstander sniker seg inn.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import os
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PERSONVERN_NO = os.path.join(_REPO_ROOT, "web", "personvern.html")
_PERSONVERN_EN = os.path.join(_REPO_ROOT, "web", "en", "personvern.html")
_I18N_JS = os.path.join(_REPO_ROOT, "web", "js", "i18n.js")


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


class TestNoInnholdDekkerFaktiskLagring(unittest.TestCase):
    """B: siden skal nevne ALLE dagens lagrede datatyper i vanlig språk,
    ikke bare oppskrifter (slik den gjorde før denne runden)."""

    def test_alle_datatyper_nevnt(self):
        kilde = _les(_PERSONVERN_NO)
        for ord in ("oppskrift", "bryggelogg", "lagerbeholdning", "utstyrsprofil", "måleenhet"):
            self.assertIn(ord, kilde.lower(), f"Mangler omtale av «{ord}» i personvern.html")

    def test_autosave_forklart_uten_overlovnad(self):
        # C: skal nevne automatisk lagring og reload/lukket fane/omstart --
        # men IKKE love mer enn lokal nettleserlagring faktisk gir (f.eks.
        # ikke "på tvers av enheter" eller "i skyen").
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("lagres automatisk", kilde)
        self.assertIn("omstart av nettleseren", kilde)
        self.assertNotIn("på tvers av enheter", kilde)
        self.assertNotIn(" i skyen", kilde)

    def test_husk_bryggerinformasjon_beskrevet_korrekt(self):
        # Seksjon 6: AV som standard, eksplisitt valg, kan slås av,
        # IKKE omtalt som konto/profil i skyen.
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("Husk bryggerinformasjon på denne enheten", kilde)
        self.assertIn("avslått som standard", kilde)
        self.assertIn("kan slås av igjen", kilde)
        self.assertNotIn("konto i skyen", kilde.lower())
        self.assertNotIn("skyprofil", kilde.lower())

    def test_ingen_overforing_av_bryggedata_forklart(self):
        # D: eksplisitt at data ikke sendes til KBH, ingen sentral database.
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("sendes ikke til Kvernhaug Brygghus", kilde)
        self.assertIn("ingen brukerkonto eller sentral database", kilde.lower())

    def test_eksport_og_sletting_forklart(self):
        # E + seksjon 7.
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("som filer på egen maskin", kilde)
        self.assertIn("Tømmer du nettstedsdata", kilde)
        self.assertIn("Eksporter det du vil beholde", kilde)

    def test_eksportpastand_lover_ikke_bryggeloggeksport(self):
        # PRIVACY PAGE EXPORT CLAIM CHECK V1: dagens Web har ingen faktisk
        # bryggelogg-eksportfunksjon koblet til noen knapp (.kbhbrew-
        # funksjonene i brew_storage.js er uwired, kommentert som
        # "et fremtidig" format). Eksportsetningen skal derfor kun love
        # oppskrifter og lagerbeholdning, ikke bryggeloggen.
        kilde = _les(_PERSONVERN_NO)
        i = kilde.index("som filer på egen maskin")
        setning = kilde[max(0, i - 150):i]
        self.assertIn("eksportere oppskrifter og lagerbeholdning", setning)
        self.assertNotIn("bryggeloggen", setning)


class TestIngenFeilaktigeTrackingPastander(unittest.TestCase):
    """F: konkrete, korrekte påstander om analytics/reklame/cookies --
    og at "ingen cookies" ikke fremstilles som "ingen lokal lagring"."""

    def test_analytics_reklame_tracking_navngitt(self):
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("Google Analytics", kilde)
        self.assertIn("reklame", kilde.lower())
        self.assertIn("tredjeparts sporing", kilde)

    def test_ingen_cookies_men_ikke_forvekslet_med_localstorage(self):
        kilde = _les(_PERSONVERN_NO)
        i = kilde.index("ingen cookies")
        omgivelse = kilde[max(0, i - 50):i + 250]
        # Skal eksplisitt referere TILBAKE til lagringen forklart tidligere
        # på siden, ikke late som ingen lokal lagring skjer i det hele tatt.
        self.assertIn("lagringen beskrevet over", omgivelse)


class TestHostingOrdlydForsiktig(unittest.TestCase):
    """G: Domeneshop nevnt, generisk om serverlogger -- ingen konkret
    loggretensjon eller serverplassering påstått."""

    def test_domeneshop_nevnt_generisk(self):
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("Domeneshop", kilde)
        self.assertIn("serverlogger", kilde)
        self.assertIn("IP-adresse", kilde)

    def test_ingen_konkret_retensjon_eller_plassering_pastatt(self):
        kilde = _les(_PERSONVERN_NO)
        # Ingen tidsangivelse ("2 år" e.l.) eller landspåstand ("Norge")
        # knyttet til hosting/serverlogger -- disse ble eksplisitt IKKE
        # verifisert i denne runden og skal derfor ikke påstås.
        i = kilde.index("Domeneshop")
        seksjon = kilde[max(0, i - 100):i + 400]
        self.assertNotIn(" år", seksjon)
        self.assertNotIn("Norge", seksjon)


class TestKontaktUendret(unittest.TestCase):
    """A: kontaktpunktet skal fortsatt være post@kvernhaugbrygghus.no,
    og e-post-forklaringen skal fortsatt finnes."""

    def test_epost_adresse_uendret(self):
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("mailto:post@kvernhaugbrygghus.no", kilde)

    def test_epost_forklaring_finnes(self):
        kilde = _les(_PERSONVERN_NO)
        self.assertIn("mottar vi naturligvis e-postadressen din", kilde)


class TestEnSideKorrektGenerert(unittest.TestCase):
    """Bekreft at web/en/personvern.html faktisk er produsert av
    generatoren med riktig engelsk innhold -- IKKE håndredigert."""

    def test_en_side_har_oppdatert_engelsk_innhold(self):
        kilde = _les(_PERSONVERN_EN)
        self.assertIn("What's stored in your browser", kilde)
        self.assertIn("brew log", kilde)
        self.assertIn("inventory", kilde)
        self.assertIn("equipment profiles", kilde)
        self.assertIn("Remember brewer information on this device", kilde)
        self.assertIn("This data is not sent to Kvernhaug Brygghus", kilde)
        self.assertIn("Google Analytics", kilde)
        self.assertIn("Domeneshop", kilde)

    def test_en_side_ikke_lover_mer_enn_no(self):
        kilde = _les(_PERSONVERN_EN)
        self.assertNotIn("across devices", kilde)
        self.assertNotIn("in the cloud", kilde)

    def test_en_eksportpastand_lover_ikke_bryggeloggeksport(self):
        kilde = _les(_PERSONVERN_EN)
        i = kilde.index("own machine")
        setning = kilde[max(0, i - 150):i]
        self.assertIn("export recipes and your inventory", setning)
        self.assertNotIn("brew log", setning)

    def test_kontakt_epost_uendret_paa_engelsk_side(self):
        kilde = _les(_PERSONVERN_EN)
        self.assertIn("mailto:post@kvernhaugbrygghus.no", kilde)


class TestI18nNoklerSymmetriske(unittest.TestCase):
    """Alle personvern.*-nøkler skal finnes på begge språk (samme mønster
    som generatorens egen symmetri-sjekk, men verifisert direkte her
    også, som et uavhengig vern)."""

    def test_alle_personvern_nokler_finnes_paa_begge_sprak(self):
        kilde = _les(_I18N_JS)
        nokler = [
            "personvern.kontaktTittel", "personvern.kontaktTekst",
            "personvern.oppskrifterTittel",
            "personvern.oppskrifterTekst1", "personvern.oppskrifterTekst2",
            "personvern.oppskrifterTekst3", "personvern.oppskrifterTekst4",
            "personvern.oppskrifterTekst5",
            "personvern.personvernTittel",
            "personvern.personvernTekst1", "personvern.personvernTekst2",
            "personvern.personvernTekst3", "personvern.personvernTekst4",
        ]
        for nokkel in nokler:
            antall = kilde.count(f'"{nokkel}":')
            self.assertEqual(antall, 2, f"{nokkel} skal finnes nøyaktig 2 ganger (NO+EN), fant {antall}")


if __name__ == "__main__":
    unittest.main()
