"""
WEB PRI 5 (issue #51) -- intended real, EXECUTED test coverage of
web/js/brew_storage.js's CRUD and .kbhbrew export/import layer, via Node
(see tests/web_js_runtime.py). This is issue #51's ".kbhbrew" scope point.

Testene bruker et minimalt, håndbygget snapshot ({recipe, predicted}) i
stedet for å kjøre hele byggBrewSnapshot()-pipelinen (som krever
recipe_engine.js sin fulle beregnOppskrift()-output pluss malt-/humle-/
gjær-masterdata) -- _gyldigSnapshot() krever kun at begge er objekter, så
dette er det minste input-et som lar CRUD- og fil-lagene testes uavhengig
av selve beregningsmotoren. Kontrakten selv:
docs/development/CORE_KBHBREW_V1.md (og PRI 3A.2/issue #22 for
passthrough-policyen).

`t` stubbes til identitetsfunksjon -- se test_web_js_kbhrecipe.py sin
docstring for samme begrunnelse.

BLOCKED (Chief review, PR #53, on head 56dcab8): tests/web_js_runtime.py's
run_web_js() shelled out to `node` from an allowed `python3 -m unittest ...`
process -- a Bridge Bash-allowlist circumvention (see that module's
docstring). run_web_js() now refuses to run, so every test below is
`@unittest.skip`-ped rather than deleted, pending a separate, explicitly
reviewed Bridge permission-model change.

Kjøres med:
    py -3 -m unittest tests.test_web_js_brew_storage
"""
import json
import unittest

from tests.web_js_runtime import run_web_js

_BREW_STORAGE = ["brew_storage.js"]
_T_STUB = "const t = (k) => k;"
_MINIMAL_SNAPSHOT = {"recipe": {"navn": "Test"}, "predicted": {"og": 1.055}}
_SKIP_REASON = (
    "Blocked pending a separate Bridge permission-model change -- see "
    "tests/web_js_runtime.py docstring (Chief review, PR #53)."
)


_BREW_NOKKEL = "kvernhaug_web_brygg"


def _kjor(expr, preset_local_storage=None):
    return run_web_js(_BREW_STORAGE, expr, prelude=_T_STUB, preset_local_storage=preset_local_storage)


@unittest.skip(_SKIP_REASON)
class TestOpprettOgLesBrygg(unittest.TestCase):
    def test_opprett_deretter_finn_og_list(self):
        expr = (
            "(function(){"
            "const created = opprettBrygg({snapshot: %s, recipeId: null, parentBrewId: null});"
            "const funnet = finnBrygg(created.brew.brewId);"
            "return {created, funnet, antall: alleBrygg().length};"
            "})()"
        ) % json.dumps(_MINIMAL_SNAPSHOT)
        result = _kjor(expr)
        self.assertTrue(result["created"]["ok"])
        brew = result["created"]["brew"]
        self.assertEqual(brew["status"], "active")
        # Nyopprettet brygg er sin egen opprinnelseshendelse.
        self.assertEqual(brew["originBrewId"], brew["brewId"])
        self.assertEqual(result["funnet"]["brewId"], brew["brewId"])
        self.assertEqual(result["antall"], 1)

    def test_ugyldig_snapshot_avvises(self):
        result = _kjor("opprettBrygg({snapshot: {recipe: {}}, recipeId: null, parentBrewId: null})")
        self.assertFalse(result["ok"])


@unittest.skip(_SKIP_REASON)
class TestKbhBrewRoundtrip(unittest.TestCase):
    def test_eksport_deretter_import_bevarer_snapshot_og_status(self):
        expr = (
            "(function(){"
            "const created = opprettBrygg({snapshot: %s, recipeId: null, parentBrewId: null});"
            "const built = byggKbhBrewInnhold(created.brew);"
            "const parsed = parseKbhBrewInnhold(JSON.stringify(built));"
            "return {built, parsed};"
            "})()"
        ) % json.dumps(_MINIMAL_SNAPSHOT)
        result = _kjor(expr)
        built = result["built"]
        self.assertEqual(built["format"], "kbhbrew")
        self.assertEqual(built["version"], 1)
        self.assertEqual(built["brew"]["snapshot"], _MINIMAL_SNAPSHOT)
        self.assertEqual(built["brew"]["status"], "active")
        self.assertNotIn("brewId", built["brew"])  # BREW_FORBUDTE_EKSPORTFELT

        parsed = result["parsed"]
        self.assertTrue(parsed["ok"])
        self.assertEqual(parsed["brew"]["snapshot"], _MINIMAL_SNAPSHOT)

    def test_import_av_samme_origin_brew_id_gir_duplikat_ikke_ny_kopi(self):
        expr = (
            "(function(){"
            "const built = {"
            "  format: 'kbhbrew', version: 1, exportedAt: '2026-01-01T00:00:00.000Z',"
            "  generator: 'g',"
            "  brew: {"
            "    originBrewId: 'brew-fast-id', parentBrewId: null, status: 'active',"
            "    createdAt: '2026-01-01T00:00:00.000Z', snapshot: %s,"
            "    actuals: {}, sensing: {}, learning: {}"
            "  }"
            "};"
            "const parsed = parseKbhBrewInnhold(JSON.stringify(built));"
            "const forste = importerBrygg(parsed.brew);"
            "const andre = importerBrygg(parsed.brew);"
            "return {forste, andre, antall: alleBrygg().length};"
            "})()"
        ) % json.dumps(_MINIMAL_SNAPSHOT)
        result = _kjor(expr)
        self.assertTrue(result["forste"]["ok"])
        self.assertFalse(result["andre"]["ok"])
        self.assertTrue(result["andre"]["duplikat"])
        self.assertEqual(result["antall"], 1)

    def test_ugyldig_json_ved_import_avvises_uten_a_krasje(self):
        result = _kjor("parseKbhBrewInnhold('dette er ikke json')")
        self.assertFalse(result["ok"])

    def test_feil_fil_format_avvises(self):
        result = _kjor("parseKbhBrewInnhold(JSON.stringify({format: 'kbhrecipe', version: 1}))")
        self.assertFalse(result["ok"])


# WEB -- localStorage safety: pantry + brew fail closed without silent
# data loss (issue #74). Se tests/test_web_js_pantry.py for samme
# kontrakt anvendt på pantry.js -- brew_storage.js sin lesBrewState()
# hadde allerede en verifiserende _skrivBrewState() (Runde 25B), men falt
# tilbake til en tom, GYLDIG state ved ugyldig JSON/feil versjon akkurat
# som pantry.js gjorde -- noe som lot en etterfølgende opprettBrygg/
# oppdaterBrygg/slettBrygg/importerBrygg stille overskrive uleselig
# rådata. Disse testene dekker den fiksen.
@unittest.skip(_SKIP_REASON)
class TestKorruptBryggloggOverskrivesAldriStille(unittest.TestCase):
    def test_ugyldig_json_gir_korrupt_flagg(self):
        result = _kjor("bryggStateErKorrupt()", preset_local_storage={_BREW_NOKKEL: "{ ikke gyldig json ]"})
        self.assertTrue(result)

    def test_ustottet_versjon_er_korrupt(self):
        lagret = {"format": "kbh-brews", "version": 99, "items": []}
        result = _kjor("bryggStateErKorrupt()", preset_local_storage={_BREW_NOKKEL: json.dumps(lagret)})
        self.assertTrue(result)

    def test_manglende_nokkel_er_ikke_korrupt(self):
        result = _kjor("bryggStateErKorrupt()", preset_local_storage={})
        self.assertFalse(result)

    def test_opprett_brygg_avvises_pa_korrupt_logg_og_rorer_ikke_radataen(self):
        raa = "{ ikke gyldig json ]"
        expr = (
            "(function(){"
            "const res = opprettBrygg({snapshot: %s, recipeId: null, parentBrewId: null});"
            "return {res, raaEtterpa: localStorage.getItem('%s')};"
            "})()"
        ) % (json.dumps(_MINIMAL_SNAPSHOT), _BREW_NOKKEL)
        result = _kjor(expr, preset_local_storage={_BREW_NOKKEL: raa})
        self.assertFalse(result["res"]["ok"])
        self.assertEqual(result["raaEtterpa"], raa, "Korrupt rådata skal ALDRI overskrives av et påfølgende normalt forsøk på å lagre")


@unittest.skip(_SKIP_REASON)
class TestBryggSkrivefeilOverflatesAldriSomSuksess(unittest.TestCase):
    _SETITEM_KASTER = "localStorage.setItem = () => { throw new Error('QuotaExceededError'); };"

    def test_opprett_brygg_gir_ok_false_ved_skrivefeil(self):
        expr = "opprettBrygg({snapshot: %s, recipeId: null, parentBrewId: null})" % json.dumps(_MINIMAL_SNAPSHOT)
        result = run_web_js(_BREW_STORAGE, expr, prelude=_T_STUB + self._SETITEM_KASTER)
        self.assertFalse(result["ok"])

    def test_slett_brygg_gir_false_ved_skrivefeil(self):
        lagret = {
            "format": "kbh-brews", "version": 1,
            "items": [{
                "brewId": "brew-1", "status": "active", "createdAt": "2026-01-01T00:00:00.000Z",
                "snapshot": _MINIMAL_SNAPSHOT, "actuals": {}, "sensing": {}, "learning": {},
            }],
        }
        result = run_web_js(
            _BREW_STORAGE, "slettBrygg('brew-1')",
            prelude=_T_STUB + self._SETITEM_KASTER,
            preset_local_storage={_BREW_NOKKEL: json.dumps(lagret)},
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
