"""
WEB PRI 5 (issue #51) -- intended real, EXECUTED test coverage of
web/js/kbhrecipe.js (byggKbhRecipeInnhold/parseKbhRecipeInnhold), via Node
(see tests/web_js_runtime.py). This is issue #51's ".kbhrecipe" scope
point. Kontrakten selv: docs/development/CORE_KBHRECIPE_V1.md.

BLOCKED (Chief review, PR #53, on head 56dcab8): tests/web_js_runtime.py's
run_web_js() shelled out to `node` from an allowed `python3 -m unittest ...`
process -- a Bridge Bash-allowlist circumvention (see that module's
docstring). run_web_js() now refuses to run, so every test below is
`@unittest.skip`-ped rather than deleted, pending a separate, explicitly
reviewed Bridge permission-model change.

`t` (i18n-oppslag) stubbes til identitetsfunksjon i alle tester her --
kbhrecipe.js kaller kun t() for brukervendte feilmeldinger ved avvist
import, og disse testene bryr seg om AVVISNINGEN (ok:false), ikke den
faktiske norske/engelske teksten (dekket av
tests/test_generate_web_i18n_pages.py).

Kjøres med:
    py -3 -m unittest tests.test_web_js_kbhrecipe
"""
import json
import unittest

from tests.web_js_runtime import run_web_js

_KBHRECIPE = ["kbhrecipe.js"]
_T_STUB = "const t = (k) => k;"
_SKIP_REASON = (
    "Blocked pending a separate Bridge permission-model change -- see "
    "tests/web_js_runtime.py docstring (Chief review, PR #53)."
)


def _bygg(oppskrift):
    return run_web_js(_KBHRECIPE, "byggKbhRecipeInnhold(%s)" % json.dumps(oppskrift), prelude=_T_STUB)


def _parse(tekst_kilde_expr):
    return run_web_js(_KBHRECIPE, "parseKbhRecipeInnhold(%s)" % tekst_kilde_expr, prelude=_T_STUB)


def _parse_obj(obj):
    return _parse("JSON.stringify(%s)" % json.dumps(obj))


@unittest.skip(_SKIP_REASON)
class TestByggKbhRecipeInnhold(unittest.TestCase):
    def test_kun_kjente_eksporterbare_felt_tas_med(self):
        # bryggerStil er et gyldig Core V1-felt, men Web har bevisst ingen
        # dedikert state for det (se kbhrecipe.js sin egen kommentar om
        # PR #3) -- det skal derfor IKKE overleve som et toppnivå-felt.
        built = _bygg(
            {
                "recipeSchemaVersion": 1,
                "navn": "Test-øl",
                "volum": 20,
                "malt": [{"id": "pilsner", "mengde": 5}],
                "humle": [],
                "bryggerStil": "skal-bort",
            }
        )
        self.assertEqual(built["format"], "kbhrecipe")
        self.assertEqual(built["version"], 1)
        self.assertNotIn("bryggerStil", built["recipe"])
        self.assertEqual(built["recipe"]["navn"], "Test-øl")

    def test_forbudte_felt_eksporteres_aldri_selv_via_passthrough(self):
        built = _bygg(
            {
                "recipeSchemaVersion": 1,
                "navn": "X",
                "malt": [],
                "humle": [],
                "_kbhUkjenteFelt": {"recipeId": "should-not-survive", "stats": {"x": 1}, "ok_field": "keep"},
            }
        )
        self.assertNotIn("recipeId", built["recipe"])
        self.assertNotIn("stats", built["recipe"])
        self.assertEqual(built["recipe"]["ok_field"], "keep")


@unittest.skip(_SKIP_REASON)
class TestRoundtrip(unittest.TestCase):
    def test_ukjente_felt_overlever_eksport_og_import(self):
        built = _bygg(
            {
                "recipeSchemaVersion": 1,
                "navn": "Test-øl",
                "malt": [],
                "humle": [],
                "_kbhUkjenteFelt": {"vann": {"ca": 50}, "prosess": "decoction"},
            }
        )
        self.assertEqual(built["recipe"]["vann"], {"ca": 50})
        self.assertEqual(built["recipe"]["prosess"], "decoction")

        parsed = _parse_obj(built)
        self.assertTrue(parsed["ok"])
        self.assertFalse(parsed["legacy"])
        self.assertEqual(
            parsed["oppskrift"]["_kbhUkjenteFelt"],
            {"vann": {"ca": 50}, "prosess": "decoction"},
        )

    def test_kjent_felt_editert_av_bruker_vinner_over_gammel_passthrough(self):
        built = _bygg(
            {
                "recipeSchemaVersion": 1,
                "navn": "Nytt navn",
                "malt": [],
                "humle": [],
                "_kbhUkjenteFelt": {"navn": "Gammelt navn skal ikke vinne"},
            }
        )
        self.assertEqual(built["recipe"]["navn"], "Nytt navn")


@unittest.skip(_SKIP_REASON)
class TestParseKbhRecipeInnhold(unittest.TestCase):
    def test_gammel_ra_json_uten_wrapper_gjenkjennes_som_legacy(self):
        parsed = _parse_obj({"navn": "Gammel oppskrift", "malt": [], "humle": [], "volum": 20})
        self.assertTrue(parsed["ok"])
        self.assertTrue(parsed["legacy"])

    def test_vilkarlig_json_uten_kjente_felt_avvises(self):
        parsed = _parse_obj({"foo": "bar"})
        self.assertFalse(parsed["ok"])

    def test_ugyldig_json_avvises_uten_a_krasje(self):
        parsed = _parse("'dette er ikke json'")
        self.assertFalse(parsed["ok"])

    def test_nyere_envelope_versjon_avvises(self):
        built = _bygg({"recipeSchemaVersion": 1, "navn": "X", "malt": [], "humle": []})
        built["version"] = 99
        parsed = _parse_obj(built)
        self.assertFalse(parsed["ok"])

    def test_eldre_ustottet_envelope_versjon_avvises(self):
        built = _bygg({"recipeSchemaVersion": 1, "navn": "X", "malt": [], "humle": []})
        built["version"] = 0
        parsed = _parse_obj(built)
        self.assertFalse(parsed["ok"])

    def test_manglende_recipe_schema_versjon_avvises(self):
        built = _bygg({"recipeSchemaVersion": 1, "navn": "X", "malt": [], "humle": []})
        del built["recipe"]["recipeSchemaVersion"]
        parsed = _parse_obj(built)
        self.assertFalse(parsed["ok"])

    def test_ustottet_recipe_schema_versjon_avvises(self):
        built = _bygg({"recipeSchemaVersion": 1, "navn": "X", "malt": [], "humle": []})
        built["recipe"]["recipeSchemaVersion"] = 2
        parsed = _parse_obj(built)
        self.assertFalse(parsed["ok"])


if __name__ == "__main__":
    unittest.main()
