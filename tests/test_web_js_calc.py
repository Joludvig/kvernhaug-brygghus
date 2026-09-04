"""
WEB PRI 5 (issue #51) -- første runde med ekte, KJØRENDE test-dekning av
web/js/calc.js sine beregningsformler (OG/EBC/invers-Tinseth/FG-ABV), via
Node (tests/web_js_runtime.py -- se den filens docstring for hvorfor og
hvordan). Dette er "calculation semantics/golden vectors" fra issue #51 sin
scope-liste: golden-vektorene under er faktiske returverdier fra den ekte,
kjørende kildefilen (fanget via harnesset, ikke regnet ut for hånd), så en
fremtidig regresjon i selve formelen fanges -- i motsetning til de
eksisterende regex-baserte "kilde-kontrakt"-testene (f.eks.
test_web_custom_ingredient_id_active_draft.py), som kun kan bevise at visse
tekstmønstre finnes i kildekoden, aldri hva koden faktisk RETURNERER.

Kjøres med:
    py -3 -m unittest tests.test_web_js_calc
"""
import unittest

from tests.web_js_runtime import run_web_js

_CALC = ["calc.js"]


class TestBeregnOG(unittest.TestCase):
    def test_golden_vector_single_malt(self):
        og = run_web_js(
            _CALC,
            "beregnOG([{id:'pilsner', mengde: 5}], {pilsner:{potensiale:1.037, ebc:3}}, 20, 0.72)",
        )
        self.assertAlmostEqual(og, 1.0555803639999999, places=9)

    def test_zero_volume_returns_1(self):
        og = run_web_js(_CALC, "beregnOG([], {}, 0, 0.75)")
        self.assertEqual(og, 1.0)

    def test_unknown_malt_id_contributes_nothing(self):
        og = run_web_js(
            _CALC,
            "beregnOG([{id:'ukjent', mengde: 5}], {pilsner:{potensiale:1.037, ebc:3}}, 20, 0.72)",
        )
        self.assertEqual(og, 1.0)


class TestBeregnEBC(unittest.TestCase):
    def test_golden_vector_single_malt(self):
        ebc = run_web_js(
            _CALC,
            "beregnEBC([{id:'pilsner', mengde: 5}], {pilsner:{potensiale:1.037, ebc:3}}, 20)",
        )
        self.assertAlmostEqual(ebc, 6.676416492755132, places=6)

    def test_non_positive_volume_returns_0(self):
        self.assertEqual(run_web_js(_CALC, "beregnEBC([], {}, 0)"), 0)
        self.assertEqual(run_web_js(_CALC, "beregnEBC([], {}, -5)"), 0)


class TestBeregnGramFraIBU(unittest.TestCase):
    def test_golden_vector(self):
        gram = run_web_js(_CALC, "beregnGramFraIBU(30, 12.5, 60, 20, 1.055)")
        self.assertAlmostEqual(gram, 21.8, places=6)

    def test_guards_reject_invalid_inputs(self):
        # (maalIbu, alfaProsent, tid, volum, beregnetOg) -- each variant
        # violates exactly one of the function's five guard conditions.
        variants = [
            (0, 12.5, 60, 20, 1.055),  # maalIbu <= 0
            (30, 0, 60, 20, 1.055),  # alfaProsent <= 0
            (30, 12.5, 0, 20, 1.055),  # tid <= 0
            (30, 12.5, 60, 0, 1.055),  # volum <= 0
            (30, 12.5, 60, 20, 1.0),  # beregnetOg <= 1.0
        ]
        for maal_ibu, alfa, tid, volum, og in variants:
            args = "%s, %s, %s, %s, %s" % (maal_ibu, alfa, tid, volum, og)
            with self.subTest(args=args):
                self.assertEqual(run_web_js(_CALC, "beregnGramFraIBU(%s)" % args), 0.0)


class TestBeregnFgOgAbv(unittest.TestCase):
    def test_golden_vector(self):
        result = run_web_js(_CALC, "beregnFgOgAbv(1.055, 0.75)")
        self.assertAlmostEqual(result["fg"], 1.01375, places=9)
        self.assertAlmostEqual(result["abv"], 5.414062500000001, places=9)

    def test_og_at_or_below_1_returns_zeroed_result(self):
        result = run_web_js(_CALC, "beregnFgOgAbv(1.0, 0.75)")
        self.assertEqual(result, {"fg": 1.0, "abv": 0.0})


if __name__ == "__main__":
    unittest.main()
