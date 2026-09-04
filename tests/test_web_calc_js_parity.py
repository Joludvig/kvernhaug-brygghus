"""
WEB PRI 5 (issue #51) -- active, deterministic parity coverage between
web/js/calc.js and its authoritative Python source, modules/calculations.py.

Chief review (PR #53, head 92e2ba2) rejected the round-1 approach
(tests/test_web_js_calc.py, real JS execution via Node) because, once
`node` execution was correctly blocked as a Bash-allowlist circumvention
(see tests/web_js_runtime.py), all 30 tests were unconditionally skipped
-- zero active coverage. The review required "one smallest coherent
increment of active, deterministic coverage that runs through commands
already authorized by the Bridge", reusing the repository's existing
browser-independent/source-contract approach, targeting at least one
high-risk area from issue #51 with real pass/fail assertions.

calc.js's own header comment states it is a manual, hand-kept-in-sync
port of modules/calculations.py ("Beregningsformler portert fra
modules/calculations.py ... hold i sync manuelt hvis formlene endres i
Python-siden"). modules/calculations.py already has extensive, real,
EXECUTED golden-vector coverage elsewhere (test_calculation_golden_vectors.py,
test_calculations_gravity.py, test_calculations_ibu_alfa.py,
test_ebc_calculation.py); what issue #51 identifies as still missing is
coverage that the JS PORT has not silently drifted from that
already-verified Python source -- exactly the "calculation
semantics/golden vectors" risk issue #51 names first in its scope list.

This module reads the real, live web/js/calc.js source (regex, same
technique as test_web_custom_ingredient_id_active_draft.py) and the real,
live modules/calculations.py source (via ast/inspect, never a hand-copied
snippet), then asserts, with real value/sequence equality assertions --
not just "pattern exists" checks -- that every shared numeric constant and
the ordered sequence of numeric literals and comparison operators in each
ported function body are identical between the two languages (docstrings
and comments excluded on both sides, since neither is executable). A
constant or formula edited on one side and not the other fails this test
deterministically, without ever invoking `node`.

Kjøres med:
    py -3 -m unittest tests.test_web_calc_js_parity
"""
import ast
import inspect
import io
import os
import re
import unittest

from modules import calculations

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CALC_JS = os.path.join(_REPO_ROOT, "web", "js", "calc.js")

_TALL_REGEX = re.compile(r"-?\d+\.\d+|-?\d+")
_OPERATOR_REGEX = re.compile(r"===|!==|<=|>=|==|!=|<|>")


def _les(path):
    with io.open(path, encoding="utf-8") as f:
        return f.read()


def _js_funksjonskropp(kilde, navn, ekskluder_siste_linje=False):
    """Henter kroppen til en toppnivå JS-funksjon (fra 'function navn(...) {'
    til linjen med den avsluttende '}' i kolonne 0), med linjekommentarer
    fjernet -- samme prinsipp som _funksjonskropp() i
    test_web_custom_ingredient_id_active_draft.py. `ekskluder_siste_linje`
    dropper kroppens siste (ikke-tomme) linje -- se
    TestBeregnGramFraIbuParitet for hvorfor."""
    m = re.search(r"function %s\([^)]*\)\s*\{" % re.escape(navn), kilde)
    assert m, "fant ikke JS-funksjonen %r i calc.js" % navn
    start = m.end()
    slutt = kilde.index("\n}", start)
    kropp = kilde[start:slutt]
    kropp = re.sub(r"//[^\n]*", "", kropp)
    if ekskluder_siste_linje:
        kropp = kropp.rstrip().rsplit("\n", 1)[0]
    return kropp


def _python_funksjonssetninger(funksjon):
    """Parser en Python-funksjon med ast og returnerer (kildetekst,
    setningsliste) MINUS en eventuell docstring -- docstrings i
    modules/calculations.py inneholder forklarende tall (produsent-
    datablad-eksempler o.l.) som ikke er del av selve beregningen og som
    ville forstyrret tall-/operatorsekvensene tallene under sammenligner."""
    kilde = inspect.getsource(funksjon)
    tre = ast.parse(kilde)
    funksjonsnode = tre.body[0]
    setninger = funksjonsnode.body
    forste = setninger[0] if setninger else None
    if (
        isinstance(forste, ast.Expr)
        and isinstance(getattr(forste, "value", None), ast.Constant)
        and isinstance(forste.value.value, str)
    ):
        setninger = setninger[1:]
    return kilde, setninger


def _python_funksjonskropp(funksjon):
    kilde, setninger = _python_funksjonssetninger(funksjon)
    return "\n".join(ast.get_source_segment(kilde, s) for s in setninger)


def _python_kropp_med_uinnpakket_siste_retur(funksjon):
    """Som _python_funksjonskropp(), men med siste setning -- forutsatt at
    den er `return et_kall(uttrykk)` -- pakket ut til `return uttrykk`.
    calculations.py sin beregn_gram_fra_ibu() kombinerer gram-formelen og
    avrundingskallet i ÉN return-setning (`return
    _avrund_gram_half_up(<uttrykk>)`), mens calc.js sin beregnGramFraIBU()
    skriver dem som to atskilte setninger (`const gram = <uttrykk>; return
    Math.round(gram * 10) / 10;`). Denne pakker ut avrundingskallet slik at
    kun selve gram-formelen -- ikke innpakningen -- sammenlignes tall-for-
    tall mot JS sin `const gram = ...`-linje (selve avrundingsuttrykket
    dekkes separat og eksplisitt, se
    TestBeregnGramFraIbuParitet.test_avrunding_er_dokumentert_bitidentisk)."""
    kilde, setninger = _python_funksjonssetninger(funksjon)
    biter = [ast.get_source_segment(kilde, s) for s in setninger[:-1]]
    siste = setninger[-1]
    assert isinstance(siste, ast.Return) and isinstance(siste.value, ast.Call), (
        "forventet siste setning å være `return et_kall(...)`"
    )
    uttrykk = ast.get_source_segment(kilde, siste.value.args[0])
    biter.append("return " + uttrykk)
    return "\n".join(biter)


def _tall_sekvens(tekst):
    return [float(t) for t in _TALL_REGEX.findall(tekst)]


def _operator_sekvens(tekst):
    return [
        {"===": "==", "!==": "!="}.get(op, op)
        for op in _OPERATOR_REGEX.findall(tekst)
    ]


class TestDelteKonstanterParitet(unittest.TestCase):
    """De fem navngitte konverteringskonstantene i calc.js sin beregnEBC()
    skal ha eksakt samme tallverdi som sine private motstykker i
    modules/calculations.py -- en drift her ville feiltolke ELLERS
    identisk kildekode."""

    def test_konstanter_matcher_python_kilden(self):
        kilde = _les(_CALC_JS)
        par = (
            ("KG_TIL_LB", calculations._KG_TIL_LB),
            ("LITER_TIL_US_GALLON", calculations._LITER_TIL_US_GALLON),
            ("SRM_TIL_EBC_FAKTOR", calculations._SRM_TIL_EBC_FAKTOR),
            ("MALT_EBC_TIL_LOVIBOND_A", calculations._MALT_EBC_TIL_LOVIBOND_A),
            ("MALT_EBC_TIL_LOVIBOND_B", calculations._MALT_EBC_TIL_LOVIBOND_B),
        )
        for js_navn, python_verdi in par:
            with self.subTest(konstant=js_navn):
                m = re.search(r"const %s = ([\d.]+);" % js_navn, kilde)
                self.assertIsNotNone(m, "fant ikke `const %s = ...;` i calc.js" % js_navn)
                self.assertEqual(float(m.group(1)), python_verdi)


class _ParitetTestCase(unittest.TestCase):
    """Felles sammenligning: for et gitt (js_navn, python_funksjon)-par skal
    den ORDNEDE sekvensen av tallitteraler og sammenligningsoperatorer i
    funksjonskroppene være identisk -- uavhengig av variabelnavnsstil
    (camelCase/snake_case) og språkspesifikk kallsyntaks (Math.pow/**,
    Math.exp/math.exp, ?? / .get(..., default)), som aldri endrer selve
    tallene eller sammenligningene en formelendring ville påvirke."""

    js_navn = None
    python_funksjon = None

    def _kropper(self):
        js_kropp = _js_funksjonskropp(_les(_CALC_JS), self.js_navn)
        python_kropp = _python_funksjonskropp(self.python_funksjon)
        return js_kropp, python_kropp

    def test_tallsekvens_matcher(self):
        # unittest's egen discovery plukker opp DENNE basisklassen som en
        # kjørbar testklasse også (uten et js_navn/python_funksjon-par å
        # sammenligne) -- skip trygt i stedet for å late som et par finnes.
        if self.js_navn is None:
            self.skipTest("abstrakt basisklasse -- ingen js_navn/python_funksjon satt")
        js_kropp, python_kropp = self._kropper()
        self.assertEqual(_tall_sekvens(js_kropp), _tall_sekvens(python_kropp))

    def test_operatorsekvens_matcher(self):
        if self.js_navn is None:
            self.skipTest("abstrakt basisklasse -- ingen js_navn/python_funksjon satt")
        js_kropp, python_kropp = self._kropper()
        self.assertEqual(_operator_sekvens(js_kropp), _operator_sekvens(python_kropp))


class TestBeregnOgParitet(_ParitetTestCase):
    js_navn = "beregnOG"
    python_funksjon = staticmethod(calculations.beregn_og)


class TestBeregnEbcParitet(_ParitetTestCase):
    js_navn = "beregnEBC"
    python_funksjon = staticmethod(calculations.beregn_ebc)


class TestBeregnGramFraIbuParitet(_ParitetTestCase):
    js_navn = "beregnGramFraIBU"
    python_funksjon = staticmethod(calculations.beregn_gram_fra_ibu)

    def _kropper(self):
        # calculations.py sin siste setning kaller _avrund_gram_half_up()
        # (math.floor(verdi * 10 + 0.5) / 10) i stedet for å avrunde
        # inline, som en BEVISST, dokumentert (se den funksjonens docstring
        # og docs/development/CORE_CALCULATION_CONTRACT.md CALC-002)
        # bit-identisk erstatning for JS sin `Math.round(gram * 10) / 10`
        # -- de to avrundingsuttrykkene er derfor tekstlig ulike selv om de
        # er verifisert semantisk like, så selve avrundings-setningen
        # ekskluderes her fra tall-/operatorsekvens-sammenligningen (dekket
        # separat og eksplisitt av test_avrunding_er_dokumentert_bitidentisk
        # under) mens resten av formelen (guard, bigness, times, gram) skal
        # matche eksakt som alle de andre funksjonene.
        js_kropp = _js_funksjonskropp(_les(_CALC_JS), self.js_navn, ekskluder_siste_linje=True)
        python_kropp = _python_kropp_med_uinnpakket_siste_retur(self.python_funksjon)
        return js_kropp, python_kropp

    def test_avrunding_er_dokumentert_bitidentisk(self):
        # Den ekskluderte siste setningen på hver side skal fortsatt finnes,
        # og fortsatt være nøyaktig den formen CALC-002-kontrakten forutsetter
        # -- en endring av avrundingsuttrykket på EN side uten den andre skal
        # fortsatt feile, bare via et eget, presist regex-treff i stedet for
        # tall-/operatorsekvensen over.
        js_kropp = _js_funksjonskropp(_les(_CALC_JS), self.js_navn)
        python_kropp = _python_funksjonskropp(self.python_funksjon)
        self.assertRegex(js_kropp, r"return Math\.round\(gram \* 10\) / 10;\s*\Z")
        self.assertRegex(python_kropp, r"return _avrund_gram_half_up\(")
        avrund_kilde = inspect.getsource(calculations._avrund_gram_half_up)
        self.assertRegex(avrund_kilde, r"math\.floor\(verdi \* 10 \+ 0\.5\) / 10")

    def test_de_fem_guard_betingelsene_er_i_samme_rekkefolge(self):
        # Denne 5-betingelses-guarden er selve CALC-002-omradet (se
        # docs/development/CORE_CALCULATION_CONTRACT.md) -- tall-/
        # operatorsekvensen over dekker verdiene, men rekkefolgen på HVILKEN
        # variabel hver betingelse gjelder er semantisk viktig i seg selv
        # (fem identiske "<= 0"-sjekker ville gitt samme tall-/
        # operatorsekvens selv om variablene ble stokket om).
        js_kropp, python_kropp = self._kropper()
        js_guard = re.search(r"if \(([^)]+)\) return 0\.0;", js_kropp).group(1)
        python_guard = re.search(r"if ([^:]+):\s*\n\s*return 0\.0", python_kropp).group(1)
        js_til_python_navn = {
            "alfaProsent": "alfa_prosent",
            "volum": "volum",
            "beregnetOg": "beregnet_og",
            "maalIbu": "maal_ibu",
            "tid": "tid",
        }
        js_rekkefolge = re.findall(r"(\w+)\s*<=", js_guard)
        python_rekkefolge = re.findall(r"(\w+)\s*<=", python_guard)
        self.assertEqual(len(js_rekkefolge), 5, "forventet nøyaktig 5 betingelser i JS-guarden")
        self.assertEqual(
            [js_til_python_navn[navn] for navn in js_rekkefolge],
            python_rekkefolge,
        )


class TestBeregnFgOgAbvParitet(_ParitetTestCase):
    js_navn = "beregnFgOgAbv"
    python_funksjon = staticmethod(calculations.beregn_fg_og_abv)


if __name__ == "__main__":
    unittest.main()
