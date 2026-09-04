"""
WEB PRI 5 (issue #51) -- intended real, EXECUTED test coverage of
web/js/custom_ingredient_id.js (nyCustomIngredientId()), via Node (see
tests/web_js_runtime.py). This is issue #51's "custom ingredient
identity/adapters" scope point -- intended to prove, via a scripted
crypto.randomUUID() collision (the harness's `uuid_queue`), that the
regenerate loop actually runs until it finds a free id, complementary to
the existing regex-based test_web_custom_ingredient_id_active_draft.py
(which documents the implementation, not the observable behavior).
Kontrakten selv: docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md.

BLOCKED (Chief review, PR #53, on head 56dcab8): tests/web_js_runtime.py's
run_web_js() shelled out to `node` from an allowed `python3 -m unittest ...`
process -- a Bridge Bash-allowlist circumvention (see that module's
docstring). run_web_js() now refuses to run, so every test below is
`@unittest.skip`-ped rather than deleted, pending a separate, explicitly
reviewed Bridge permission-model change. The existing regex-based test
(test_web_custom_ingredient_id_active_draft.py) is unaffected and remains
the current, valid guard for this contract.

Kjøres med:
    py -3 -m unittest tests.test_web_js_custom_ingredient_id
"""
import re
import unittest

from tests.web_js_runtime import run_web_js

_MODUL = ["custom_ingredient_id.js"]
_UUID_V4_REGEX = re.compile(
    r"^kbh-custom-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
_SKIP_REASON = (
    "Blocked pending a separate Bridge permission-model change -- see "
    "tests/web_js_runtime.py docstring (Chief review, PR #53)."
)


@unittest.skip(_SKIP_REASON)
class TestNyCustomIngredientIdFormat(unittest.TestCase):
    def test_returnerer_kontraktens_format_uten_lokale_kilder_lastet(self):
        # Ingen av allePantryItems/alleOppskrifter/alleBrygg/AKTIV_KLADD_NOKKEL
        # finnes -- feature-detection skal gjøre dette trygt (tom kollisjonssjekk),
        # ikke krasje.
        result = run_web_js(_MODUL, "nyCustomIngredientId()")
        self.assertRegex(result, _UUID_V4_REGEX)


@unittest.skip(_SKIP_REASON)
class TestKollisjonMotAktivKladd(unittest.TestCase):
    """AKTIV_KLADD_NOKKEL (Chief-runde, PR #52/issue #50) -- se
    test_web_custom_ingredient_id_active_draft.py for kilde-kontrakten
    denne oppførselen skal bevise stemmer."""

    _PRELUDE = 'const AKTIV_KLADD_NOKKEL = "active_draft";'
    _COLLIDING = "11111111-1111-4111-8111-111111111111"
    _FRESH = "22222222-2222-4222-8222-222222222222"

    def test_regenererer_ved_kollisjon_mot_aktiv_kladd(self):
        preset = {
            "active_draft": '{"malt":[{"id":"kbh-custom-%s","custom":true}]}' % self._COLLIDING,
        }
        result = run_web_js(
            _MODUL,
            "nyCustomIngredientId()",
            prelude=self._PRELUDE,
            preset_local_storage=preset,
            uuid_queue=[self._COLLIDING, self._FRESH],
        )
        self.assertEqual(result, "kbh-custom-%s" % self._FRESH)

    def test_ingen_kollisjon_bruker_forste_uuid_direkte(self):
        result = run_web_js(
            _MODUL,
            "nyCustomIngredientId()",
            prelude=self._PRELUDE,
            preset_local_storage={},
            uuid_queue=[self._FRESH],
        )
        self.assertEqual(result, "kbh-custom-%s" % self._FRESH)


@unittest.skip(_SKIP_REASON)
class TestAlleFireKilderSjekkes(unittest.TestCase):
    """Kontraktens §6 -- kollisjonssjekken skal dekke pantry, lagrede
    oppskrifter, brygg-snapshots OG den aktive kladden samtidig, ikke bare
    én av gangen. Mocker alle fire kilder med hver sin kjente
    kollisjons-id og krever at regenerer-løkka går forbi alle fire før den
    returnerer en ledig id."""

    _PANTRY = "aaaaaaaa-0000-4000-8000-000000000000"
    _RECIPE = "bbbbbbbb-0000-4000-8000-000000000000"
    _BREW = "cccccccc-0000-4000-8000-000000000000"
    _DRAFT = "dddddddd-0000-4000-8000-000000000000"
    _FRESH = "eeeeeeee-0000-4000-8000-000000000000"

    _PRELUDE = (
        'const AKTIV_KLADD_NOKKEL = "active_draft";\n'
        "function allePantryItems() { return [{id: 'kbh-custom-%s', custom: true}]; }\n"
        "function alleOppskrifter() { return [{recipe: {malt: [{id: 'kbh-custom-%s', custom: true}], humle: [], gjaerId: 'x'}}]; }\n"
        "function alleBrygg() { return [{snapshot: {recipe: {malt: [], humle: [{id: 'kbh-custom-%s', custom: true}], gjaerId: 'x'}}}]; }\n"
    ) % (_PANTRY, _RECIPE, _BREW)

    def test_regenererer_forbi_alle_fire_kilder(self):
        preset = {"active_draft": '{"malt":[{"id":"kbh-custom-%s","custom":true}]}' % self._DRAFT}
        result = run_web_js(
            _MODUL,
            "nyCustomIngredientId()",
            prelude=self._PRELUDE,
            preset_local_storage=preset,
            uuid_queue=[self._PANTRY, self._RECIPE, self._BREW, self._DRAFT, self._FRESH],
        )
        self.assertEqual(result, "kbh-custom-%s" % self._FRESH)


if __name__ == "__main__":
    unittest.main()
