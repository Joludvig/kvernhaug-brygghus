"""
WEB STAB W4 (issue #108) -- regresjonstest for B05 fra web-auditen:
egendefinert gjær kunne vises synlig og redigerbart mens et bibliotek-gjær
fortsatt var den faktiske, aktive identiteten i selve oppskrift-payloaden
(`gjaerId` fortsatt satt, `gjaerCustom` stille ignorert av
`_lesGjaerEgendefinert()` fordi `gjaerCombobox.getValue()` fortsatt var
sann) -- se issue-teksten for full rotårsak-analyse mot
`0eaf4703aacbe8f9d1564366fa751f21acf8d2bd`.

VIKTIG METODEMERKNAD (samme prinsipp som
test_web_custom_ingredient_id_active_draft.py): dette repoet har ingen
JavaScript-kjøretid i dette miljøet, så disse testene kan ikke faktisk
kjøre web/js/app.js og observere et ekte DOM-klikk. I stedet er dette
KILDE-KONTRAKT-tester: de leser den FAKTISKE, kjørende kildefilen og
verifiserer -- via presise, snevert avgrensede mønstre -- at gjær nå har
akkurat ÉN eksplisitt tilstandsflagg (samme mønster som
rad.dataset.egendefinert allerede bruker for malt/humle, se
_settMaltEgendefinert()), og at HVER kode-vei som kan aktivere/deaktivere
egendefinert gjær eller lese den aktive identiteten faktisk går via det
flagget -- aldri via en avledning av gjaerCombobox sin verdi alene. Ekte
browserverifisering av selve interaksjonen er dekket separat (se
PR-rapporten for denne runden).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_JS = os.path.join(_REPO_ROOT, "web", "js", "app.js")


def _les(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _funksjonskropp(kilde, funksjonssignatur_regex):
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestEksplisitteOvergangsfunksjoner(unittest.TestCase):
    """_gjaerCustomAktiv()/_aktiverGjaerCustom()/_deaktiverGjaerCustom() skal
    finnes og _aktiverGjaerCustom() skal alltid oppheve gjaerCombobox --
    dette ER selve fiksen for B05."""

    def test_gjaer_custom_aktiv_leser_hidden_flagget(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _gjaerCustomAktiv\(\)\s*\{")
        self.assertIn("!gjaerEgendefinertFelt.hidden", kropp)

    def test_aktivering_opphever_biblioteksvalg(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _aktiverGjaerCustom\(\)\s*\{")
        self.assertIn(
            "gjaerCombobox.clear();",
            kropp,
            "_aktiverGjaerCustom() må tømme gjaerCombobox -- ellers kan et "
            "biblioteksvalg forbli aktivt samtidig med synlige egendefinerte "
            "felt (B05)",
        )
        self.assertIn("gjaerEgendefinertFelt.hidden = false;", kropp)
        # gjaerCombobox må tømmes FØR feltet vises, ikke etter -- ellers er
        # det et kort vindu der begge fremstår aktive.
        self.assertLess(
            kropp.index("gjaerCombobox.clear()"),
            kropp.index("gjaerEgendefinertFelt.hidden = false"),
        )

    def test_deaktivering_skjuler_feltet(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _deaktiverGjaerCustom\(\)\s*\{")
        self.assertIn("gjaerEgendefinertFelt.hidden = true;", kropp)


class TestLesGjaerEgendefinertBrukerEttFlagg(unittest.TestCase):
    """_lesGjaerEgendefinert() skal IKKE lenger returnere null bare fordi
    gjaerCombobox tilfeldigvis har en verdi -- det var nøyaktig B05-bug-en:
    en synlig, utfylt egendefinert-seksjon som stille ble ignorert fordi et
    gammelt biblioteksvalg fortsatt lå igjen i comboboxen."""

    def test_sjekker_kun_gjaer_custom_aktiv(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function _lesGjaerEgendefinert\(\)\s*\{")
        self.assertRegex(kropp, r"if \(!_gjaerCustomAktiv\(\)\) return null;")
        self.assertNotIn(
            "gjaerCombobox.getValue()",
            kropp,
            "_lesGjaerEgendefinert() skal ikke lenger sjekke gjaerCombobox "
            "direkte -- _gjaerCustomAktiv() er nå den ENE kilden til sannhet",
        )


class TestSamleOppskriftGjaerIdRespektererCustomFlagget(unittest.TestCase):
    """samleOppskrift() sin gjaerId-linje skal sjekke _gjaerCustomAktiv()
    FØRST (samme mønster som lesMaltRader()/lesHumleRader() sjekker
    rad.dataset.egendefinert FØRST) -- en gjenværende comboboks-verdi kan
    aldri lekke inn som gjaerId mens egendefinert gjær er aktiv."""

    def test_gjaer_id_sjekker_custom_flagget_forst(self):
        kilde = _les(_APP_JS)
        kropp = _funksjonskropp(kilde, r"function samleOppskrift\(\)\s*\{")
        self.assertRegex(
            kropp,
            r"gjaerId:\s*_gjaerCustomAktiv\(\)\s*\?\s*null\s*:\s*\(gjaerCombobox\.getValue\(\)\s*\|\|\s*null\)",
        )


class TestOvergangerBrukerHelperfunksjonene(unittest.TestCase):
    """Både comboboxens onSelect og togglekapp-klikkhandleren i init() skal
    gå via de eksplisitte overgangsfunksjonene -- ingen rå
    `gjaerEgendefinertFelt.hidden = ...`-tildeling utenfor
    _gjenopprettOppskrift() (som eksplisitt setter begge feltene samtidig,
    se den funksjonens egen dokumentasjon)."""

    def test_onselect_deaktiverer_custom_ved_biblioteksvalg(self):
        kilde = _les(_APP_JS)
        init_kropp = _funksjonskropp(kilde, r"async function init\(\)\s*\{")
        self.assertIn("if (gjaerCombobox.getValue()) _deaktiverGjaerCustom();", init_kropp)

    def test_knapp_klikk_bruker_aktiver_og_deaktiver(self):
        kilde = _les(_APP_JS)
        init_kropp = _funksjonskropp(kilde, r"async function init\(\)\s*\{")
        knapp_idx = init_kropp.index('"gjaer-egendefinert-knapp"')
        knapp_handler = init_kropp[knapp_idx : knapp_idx + 300]
        self.assertIn("if (_gjaerCustomAktiv()) _deaktiverGjaerCustom();", knapp_handler)
        self.assertIn("else _aktiverGjaerCustom();", knapp_handler)
        # Ingen rå hidden-toggle igjen her -- det var nøyaktig B05-bug-en
        # (kun synlighet ble endret, biblioteksvalget ble aldri opphevet).
        self.assertNotIn("gjaerEgendefinertFelt.hidden = !gjaerEgendefinertFelt.hidden", knapp_handler)


if __name__ == "__main__":
    unittest.main()
