"""
Regresjonstest for issue #112 -- "library hop alpha fallback becomes false
explicit override on restore".

Samme metodemerknad som tests/test_web_save_state_truth.py: dette repoet har
ingen JavaScript-kjøretid i dette miljøet (se tests/web_js_runtime.py), så
dette er en KILDE-KONTRAKT-test: den leser den faktiske, kjørende
web/js/app.js og verifiserer, via presise regex-mønstre, at de eksakte
kodestykkene som skiller "bibliotek-fallback-alfa" fra "eksplisitt
alfa-override" fortsatt har riktig form.

Bakgrunn (se issue #112): en biblioteks-humle lagret med `alfaOverride: null`
betyr "ingen eksplisitt override -- bruk gjeldende biblioteks-alfa".
leggTilHumleRad() fyller likevel det synlige alfa-feltet med biblioteks-
verdien for brukervennlighet ved gjenoppretting. Før denne fiksen leste
lesHumleRader() det synlige feltet tilbake ukritisk, og en ren
visnings-fallback ble dermed en "fabrikkert" eksplisitt override -- recipe
fremstod som "Endret siden lagring" (W3, issue #106) uten at brukeren hadde
gjort noe. Fiksen skiller "vist" fra "eksplisitt" via et eget
rad.dataset.alfaEksplisitt-flagg, satt KUN av ekte brukerinntasting
(input-lytteren) eller ved gjenoppretting av en allerede eksplisitt
alfaOverride -- aldri av en biblioteks-fallback-fylling.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import io
import os
import re
import unittest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_JS = os.path.join(_REPO_ROOT, "web", "js", "app.js")


def _les(sti):
    with io.open(sti, encoding="utf-8") as f:
        return f.read()


def _app_js():
    return _les(_APP_JS)


def _funksjonskropp(kilde, funksjonssignatur_regex):
    """Samme hjelper som test_web_save_state_truth.py: henter kroppen til en
    toppnivå-funksjon fra 'function ... {' til den avsluttende '}' i kolonne
    0."""
    m = re.search(funksjonssignatur_regex, kilde)
    assert m, "fant ikke funksjonssignaturen: %r" % funksjonssignatur_regex
    start = m.end()
    slutt = kilde.index("\n}", start)
    return kilde[start:slutt]


class TestLeggTilHumleRadSkillerFallbackFraEksplisitt(unittest.TestCase):
    """AC1-6/AC10 -- gjenoppretting av en biblioteks-humle må aldri merke en
    visnings-fallback-alfa som eksplisitt, mens en faktisk persistert
    override fortsatt skal gjenopprettes som eksplisitt."""

    def _kropp(self):
        return _funksjonskropp(_app_js(), r"function leggTilHumleRad\(forhandsutfylt\)\s*\{")

    def test_gjenopprettet_eksplisitt_override_merkes_eksplisitt(self):
        kropp = self._kropp()
        self.assertRegex(
            kropp,
            r'if\s*\(forhandsutfylt\.alfaOverride\s*!=\s*null\)\s*\{\s*'
            r'alfaInput\.value\s*=\s*forhandsutfylt\.alfaOverride;\s*'
            r'rad\.dataset\.alfaEksplisitt\s*=\s*"1";',
        )

    def test_gjenopprettet_bibliotek_fallback_merkes_ikke_eksplisitt(self):
        kropp = self._kropp()
        self.assertRegex(
            kropp,
            r'\}\s*else\s*\{\s*'
            r'if\s*\(humleData\[forhandsutfylt\.id\]\)\s*alfaInput\.value\s*=\s*humleData\[forhandsutfylt\.id\]\.alfa;\s*'
            r'rad\.dataset\.alfaEksplisitt\s*=\s*"0";',
        )

    def test_combobox_onselect_fallback_fylling_merkes_ikke_eksplisitt(self):
        # En helt ny/tom rad der brukeren velger en biblioteks-humle: den
        # autofylte default-alfaen er samme slags fallback som ved
        # gjenoppretting, og skal derfor heller ikke telle som en override.
        kropp = self._kropp()
        self.assertRegex(
            kropp,
            r'if\s*\(info\s*&&\s*alfaInput\.value\s*===\s*""\)\s*\{[\s\S]*?'
            r'alfaInput\.value\s*=\s*info\.alfa;[\s\S]*?'
            r'rad\.dataset\.alfaEksplisitt\s*=\s*"0";',
        )

    def test_ekte_brukerinntasting_merker_eksplisitt(self):
        # Selve input-lytteren på alfa-feltet -- den ENESTE plassen et ekte
        # tastetrykk fra brukeren fanges opp -- må sette flagget til "1".
        kropp = self._kropp()
        self.assertRegex(
            kropp,
            r'alfaInput\.addEventListener\("input",\s*\(\)\s*=>\s*\{[\s\S]*?'
            r'rad\.dataset\.alfaEksplisitt\s*=\s*"1";[\s\S]*?'
            r'beregnOgVisResultat\(\);[\s\S]*?\}\);',
        )


class TestLesHumleRaderBrukerEksplisittFlagg(unittest.TestCase):
    """AC7-9 -- alfaOverride skal kun bli en tallverdi når raden faktisk er
    merket eksplisitt, aldri utelukkende basert på at feltet ikke er tomt."""

    def _kropp(self):
        return _funksjonskropp(_app_js(), r"function lesHumleRader\(\)\s*\{")

    def test_alfaoverride_gates_pa_datasettflagget(self):
        kropp = self._kropp()
        self.assertRegex(kropp, r'const\s+alfaEksplisitt\s*=\s*rad\.dataset\.alfaEksplisitt\s*===\s*"1";')
        self.assertRegex(
            kropp,
            r'alfaOverride:\s*alfaEksplisitt\s*&&\s*isFinite\(alfa\)\s*\?\s*alfa\s*:\s*null',
        )

    def test_gammel_utelukkende_isfinite_gate_er_fjernet(self):
        # Den opprinnelige feilen: override ble avgjort av isFinite(alfa)
        # alene (dvs. "feltet er ikke tomt"), uavhengig av om verdien kom fra
        # en ekte brukerhandling eller en ren visnings-fallback.
        kropp = self._kropp()
        self.assertNotRegex(kropp, r'alfaOverride:\s*isFinite\(alfa\)\s*\?\s*alfa\s*:\s*null')


if __name__ == "__main__":
    unittest.main()
