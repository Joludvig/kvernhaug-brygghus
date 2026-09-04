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

Round 4 (Chief review, PR #53, head 3837d32) found that the literal-/
comparator-sequence comparison above is blind to arithmetic operators,
operand structure, and calls: a Web-only mutation such as `+=` -> `-=`,
`*` -> `/`, or `1 + (...)` -> `1 - (...)` preserves every numeric literal
and every comparison operator, so it would still pass. TestBeregningsstruktur-
Paritet below adds a real structural (operator/operand-tree) comparison for
each formula's core arithmetic expressions -- both languages' expression
text is parsed, via one small shared grammar (numbers, identifiers,
`+ - * / **`, unary minus, function calls), into an operator/operand tree,
after normalizing each side's language-specific spelling (camelCase<->
snake_case variable names, `Math.pow`/`**`, `Math.exp`/`math.exp`, and
leading-underscore Python constant naming) -- so the trees themselves, not
just a flat token bag, must match. TestMutasjonerFeiler then proves, for
each of the three mutation kinds the review named, that this structural
comparison actually rejects them (mutating only an in-memory copy of the
calc.js source text, never the file itself).

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


# ---------------------------------------------------------------------------
# Round 4 (Chief review, PR #53, head 3837d32): structural (operator/operand
# tree) parity -- see module docstring above for why this is needed.
#
# Both languages' extracted expression text is fed through the SAME small
# expression grammar below (numbers, identifiers, + - * / **, unary minus,
# function calls) after normalizing away purely-spelling differences
# (camelCase<->snake_case identifiers, Math.pow(a, b)<->a ** b,
# Math.exp<->math.exp, leading-underscore Python constant names), so the two
# sides produce directly comparable canonical tuples. A change to WHICH
# operator/operand structure a formula uses -- not just which numbers or
# comparisons it contains -- now makes the trees themselves unequal.
# ---------------------------------------------------------------------------

_NUM_TOKEN = re.compile(r"\d+\.\d+|\d+")
_NAME_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class _Uttrykksfeil(AssertionError):
    pass


def _tokeniser_uttrykk(tekst):
    tokens = []
    i = 0
    n = len(tekst)
    while i < n:
        c = tekst[i]
        if c.isspace():
            i += 1
            continue
        if tekst.startswith("**", i):
            tokens.append(("**", "**"))
            i += 2
            continue
        if c in "+-*/(),":
            tokens.append((c, c))
            i += 1
            continue
        if c.isdigit():
            m = _NUM_TOKEN.match(tekst, i)
            tokens.append(("NUM", m.group(0)))
            i = m.end()
            continue
        m = _NAME_TOKEN.match(tekst, i)
        if m:
            tokens.append(("NAME", m.group(0)))
            i = m.end()
            continue
        raise _Uttrykksfeil("uventet tegn %r i uttrykk %r" % (c, tekst))
    return tokens


class _UttrykksParser:
    """Rekursiv nedstigningsparser for et lite, felles uttrykksgrammatikk
    (tall, identifikatorer, + - * / **, unær minus, funksjonskall) som
    BEGGE språksidene normaliseres til før parsing -- se
    _js_uttrykk_kanonisk()/_python_uttrykk_kanonisk() under."""

    def __init__(self, tokens):
        self._tokens = tokens
        self._pos = 0

    def _peek(self):
        return self._tokens[self._pos] if self._pos < len(self._tokens) else (None, None)

    def _spis(self, forventet_type=None):
        tok = self._peek()
        if forventet_type is not None and tok[0] != forventet_type:
            raise _Uttrykksfeil("forventet %r, fikk %r" % (forventet_type, tok))
        self._pos += 1
        return tok

    def parse(self):
        node = self._expr()
        if self._pos != len(self._tokens):
            raise _Uttrykksfeil("ufullstendig parsing, gjenstår token %r" % (self._peek(),))
        return node

    def _expr(self):
        node = self._term()
        while self._peek()[0] in ("+", "-"):
            op = self._spis()[0]
            node = ("BINOP", op, node, self._term())
        return node

    def _term(self):
        node = self._power()
        while self._peek()[0] in ("*", "/"):
            op = self._spis()[0]
            node = ("BINOP", op, node, self._power())
        return node

    def _power(self):
        node = self._unary()
        if self._peek()[0] == "**":
            self._spis()
            node = ("CALL", "POW", [node, self._power()])
        return node

    def _unary(self):
        if self._peek()[0] == "-":
            self._spis()
            return ("NEG", self._unary())
        return self._atom()

    def _atom(self):
        tok_type, tok_verdi = self._peek()
        if tok_type == "NUM":
            self._spis()
            return ("NUM", float(tok_verdi))
        if tok_type == "(":
            self._spis()
            node = self._expr()
            self._spis(")")
            return node
        if tok_type == "NAME":
            navn = self._spis()[1]
            if self._peek()[0] == "(":
                self._spis()
                args = [self._expr()]
                while self._peek()[0] == ",":
                    self._spis()
                    args.append(self._expr())
                self._spis(")")
                return ("CALL", navn.upper(), args)
            return ("VAR", navn.lstrip("_"))
        raise _Uttrykksfeil("uventet token %r" % (self._peek(),))


def _parse_uttrykk(tekst):
    return _UttrykksParser(_tokeniser_uttrykk(tekst)).parse()


def _js_uttrykk_kanonisk(uttrykk, navnemap=None):
    """Normaliserer og parser et JS-uttrykk til en kanonisk tuppel: erstatter
    Math.pow(/Math.exp( med de felles kallnavnene POW(/EXP( som Python-siden
    (via `**`/math.exp) også normaliseres til, og oversetter deretter kjente
    camelCase-identifikatorer (og evt. `obj.felt`-tilganger) til sine
    snake_case-motstykker via navnemap, lengste nøkkel først slik at et
    lengre navn ikke delvis overskygges av et kortere."""
    tekst = uttrykk.replace("Math.pow(", "POW(").replace("Math.exp(", "EXP(")
    for js_navn in sorted(navnemap or {}, key=len, reverse=True):
        tekst = re.sub(r"\b%s\b" % re.escape(js_navn), (navnemap or {})[js_navn], tekst)
    return _parse_uttrykk(tekst)


def _python_uttrykk_kanonisk(uttrykk):
    tekst = uttrykk.replace("math.exp(", "EXP(")
    return _parse_uttrykk(tekst)


def _uttrykk(mal, kropp, beskrivelse):
    m = re.search(mal, kropp)
    if not m:
        raise _Uttrykksfeil("fant ikke mønster %r (%s)" % (mal, beskrivelse))
    return m.group(1).strip()


def _uttrykk_med_operator(js_mal, js_kropp, python_mal, python_kropp, beskrivelse):
    js_m = re.search(js_mal, js_kropp)
    if not js_m:
        raise _Uttrykksfeil("fant ikke JS-mønster %r (%s)" % (js_mal, beskrivelse))
    python_m = re.search(python_mal, python_kropp)
    if not python_m:
        raise _Uttrykksfeil("fant ikke Python-mønster %r (%s)" % (python_mal, beskrivelse))
    return (js_m.group(1), js_m.group(2).strip()), (python_m.group(1), python_m.group(2).strip())


def _og_komponenter(js_kilde=None):
    js_kropp = _js_funksjonskropp(js_kilde if js_kilde is not None else _les(_CALC_JS), "beregnOG")
    python_kropp = _python_funksjonskropp(calculations.beregn_og)
    navnemap = {"m.mengde": "mengde", "totalePoeng": "totale_poeng"}

    (js_op, js_uttr), (py_op, py_uttr) = _uttrykk_med_operator(
        r"totalePoeng (\+=|-=) ([^;]+);", js_kropp,
        r"totale_poeng (\+=|-=) (.+)", python_kropp,
        "OG-akkumulator",
    )
    akkumulator = (
        (js_op, _js_uttrykk_kanonisk(js_uttr, navnemap)),
        (py_op, _python_uttrykk_kanonisk(py_uttr)),
    )
    retur = (
        _js_uttrykk_kanonisk(
            _uttrykk(r"return ([^;]*totalePoeng[^;]*);", js_kropp, "OG-returuttrykk, JS"), navnemap
        ),
        _python_uttrykk_kanonisk(
            _uttrykk(r"return (.*totale_poeng.*)", python_kropp, "OG-returuttrykk, Python")
        ),
    )
    return [akkumulator, retur]


def _ebc_komponenter(js_kilde=None):
    js_kropp = _js_funksjonskropp(js_kilde if js_kilde is not None else _les(_CALC_JS), "beregnEBC")
    python_kropp = _python_funksjonskropp(calculations.beregn_ebc)
    navnemap = {
        "mengdeLb": "mengde_lb",
        "maltLovibond": "malt_lovibond",
        "volumGal": "volum_gal",
    }

    (js_op, js_uttr), (py_op, py_uttr) = _uttrykk_med_operator(
        r"mcu (\+=|-=) ([^;]+);", js_kropp,
        r"mcu (\+=|-=) (.+)", python_kropp,
        "EBC-akkumulator",
    )
    akkumulator = (
        (js_op, _js_uttrykk_kanonisk(js_uttr, navnemap)),
        (py_op, _python_uttrykk_kanonisk(py_uttr)),
    )
    srm = (
        _js_uttrykk_kanonisk(_uttrykk(r"const srm = ([^;]+);", js_kropp, "srm, JS"), navnemap),
        _python_uttrykk_kanonisk(_uttrykk(r"srm = (.+)", python_kropp, "srm, Python")),
    )
    retur = (
        _js_uttrykk_kanonisk(_uttrykk(r"return (srm [^;]+);", js_kropp, "EBC-returuttrykk, JS"), navnemap),
        _python_uttrykk_kanonisk(_uttrykk(r"return (srm .+)", python_kropp, "EBC-returuttrykk, Python")),
    )
    return [akkumulator, srm, retur]


def _gram_komponenter(js_kilde=None):
    js_kropp = _js_funksjonskropp(js_kilde if js_kilde is not None else _les(_CALC_JS), "beregnGramFraIBU")
    python_kropp = _python_funksjonskropp(calculations.beregn_gram_fra_ibu)
    python_kropp_uinnpakket = _python_kropp_med_uinnpakket_siste_retur(calculations.beregn_gram_fra_ibu)
    navnemap = {
        "beregnetOg": "beregnet_og",
        "maalIbu": "maal_ibu",
        "alfaProsent": "alfa_prosent",
    }

    par = [
        (
            _uttrykk(r"const bigness = ([^;]+);", js_kropp, "bigness, JS"),
            _uttrykk(r"bigness = (.+)", python_kropp, "bigness, Python"),
        ),
        (
            _uttrykk(r"const times = ([^;]+);", js_kropp, "times, JS"),
            _uttrykk(r"times = (.+)", python_kropp, "times, Python"),
        ),
        (
            _uttrykk(r"const utnyttelse = ([^;]+);", js_kropp, "utnyttelse, JS"),
            _uttrykk(r"utnyttelse = (.+)", python_kropp, "utnyttelse, Python"),
        ),
        (
            _uttrykk(r"const gram = ([^;]+);", js_kropp, "gram, JS"),
            _uttrykk(r"return (.*maal_ibu.*)", python_kropp_uinnpakket, "gram, Python"),
        ),
    ]
    return [(_js_uttrykk_kanonisk(js_uttr, navnemap), _python_uttrykk_kanonisk(py_uttr)) for js_uttr, py_uttr in par]


def _fgabv_komponenter(js_kilde=None):
    js_kropp = _js_funksjonskropp(js_kilde if js_kilde is not None else _les(_CALC_JS), "beregnFgOgAbv")
    python_kropp = _python_funksjonskropp(calculations.beregn_fg_og_abv)

    par = [
        (
            _uttrykk(r"const fg = ([^;]+);", js_kropp, "fg, JS"),
            _uttrykk(r"(?m)^fg = (.+)$", python_kropp, "fg, Python"),
        ),
        (
            _uttrykk(r"const abv = ([^;]+);", js_kropp, "abv, JS"),
            _uttrykk(r"(?m)^abv = (.+)$", python_kropp, "abv, Python"),
        ),
    ]
    return [(_js_uttrykk_kanonisk(js_uttr, {}), _python_uttrykk_kanonisk(py_uttr)) for js_uttr, py_uttr in par]


class TestBeregningsstrukturParitet(unittest.TestCase):
    """Ekte operator-/operandtre-paritet, ikke bare tall-/sammenlignings-
    operator-sekvens over -- se modulens docstring for hvorfor dette trengs
    (Chief review, PR #53, head 3837d32)."""

    def test_beregn_og_strukturell_paritet(self):
        for i, (js_kanon, python_kanon) in enumerate(_og_komponenter()):
            with self.subTest(komponent=i):
                self.assertEqual(js_kanon, python_kanon)

    def test_beregn_ebc_strukturell_paritet(self):
        for i, (js_kanon, python_kanon) in enumerate(_ebc_komponenter()):
            with self.subTest(komponent=i):
                self.assertEqual(js_kanon, python_kanon)

    def test_beregn_gram_fra_ibu_strukturell_paritet(self):
        for i, (js_kanon, python_kanon) in enumerate(_gram_komponenter()):
            with self.subTest(komponent=i):
                self.assertEqual(js_kanon, python_kanon)

    def test_beregn_fg_og_abv_strukturell_paritet(self):
        for i, (js_kanon, python_kanon) in enumerate(_fgabv_komponenter()):
            with self.subTest(komponent=i):
                self.assertEqual(js_kanon, python_kanon)


class TestMutasjonerFeiler(unittest.TestCase):
    """Beviser at TestBeregningsstrukturParitet faktisk fanger opp de tre
    representative mutasjonstypene Chief-reviewen (PR #53, head 3837d32)
    eksplisitt navngir som usynlige for tall-/operator-sekvens-testen alene
    -- uten dette ville strukturtesten over vært en ubevist påstand.
    Muterer kun en in-memory kopi av calc.js sin kildetekst; selve filen
    (og web/**-produktkoden) røres aldri."""

    def _mutert_kilde(self, gammelt, nytt):
        kilde = _les(_CALC_JS)
        self.assertIn(gammelt, kilde, "forventet substreng ikke funnet i calc.js")
        return kilde.replace(gammelt, nytt, 1)

    def test_pluss_er_til_minus_er_i_akkumulator_feiler(self):
        mutert = self._mutert_kilde(
            "totalePoeng += m.mengde * (potensiale - 1) * 1000;",
            "totalePoeng -= m.mengde * (potensiale - 1) * 1000;",
        )
        js_akkumulator, python_akkumulator = _og_komponenter(js_kilde=mutert)[0]
        self.assertNotEqual(js_akkumulator, python_akkumulator)

    def test_multiplikasjon_til_divisjon_i_ebc_srm_feiler(self):
        mutert = self._mutert_kilde(
            "const srm = 1.4922 * Math.pow(mcu, 0.6859);",
            "const srm = 1.4922 / Math.pow(mcu, 0.6859);",
        )
        js_srm, python_srm = _ebc_komponenter(js_kilde=mutert)[1]
        self.assertNotEqual(js_srm, python_srm)

    def test_pluss_til_minus_i_fg_returuttrykk_feiler(self):
        mutert = self._mutert_kilde(
            "const fg = 1 + (og - 1) * (1 - attenuation);",
            "const fg = 1 - (og - 1) * (1 - attenuation);",
        )
        js_fg, python_fg = _fgabv_komponenter(js_kilde=mutert)[0]
        self.assertNotEqual(js_fg, python_fg)


if __name__ == "__main__":
    unittest.main()
