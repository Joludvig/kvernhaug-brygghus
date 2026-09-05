"""
WEB -- localStorage safety: pantry fail-closed without silent data loss
(issue #74). Intended real, EXECUTED test coverage of web/js/pantry.js's
read/write safety contract, via Node (see tests/web_js_runtime.py).

BLOCKED (Chief review, PR #53, on head 56dcab8): tests/web_js_runtime.py's
run_web_js() shelled out to `node` from an allowed `python3 -m unittest ...`
process -- a Bridge Bash-allowlist circumvention (see that module's
docstring). run_web_js() now refuses to run, so every test below is
`@unittest.skip`-ped rather than deleted, pending a separate, explicitly
reviewed Bridge permission-model change -- same status as every other
tests/test_web_js_*.py module.

`t` stubbes til identitetsfunksjon -- se test_web_js_kbhrecipe.py sin
docstring for samme begrunnelse. Skrivefeil simuleres ved å overstyre
localStorage.setItem i `prelude` til å kaste -- eval_web_js.js sin
buildLocalStorage() har ingen innebygd kvote-simulering, så dette er den
naturlige måten å reprodusere "privat nettlesing / full lagringskvote" på
i denne test-riggen.

Kjøres med:
    py -3 -m unittest tests.test_web_js_pantry
"""
import json
import unittest

from tests.web_js_runtime import run_web_js

_PANTRY = ["pantry.js"]
_T_STUB = "const t = (k) => k; function nyCustomIngredientId() { return 'kbh-custom-test'; }"
_PANTRY_NOKKEL = "kvernhaug_web_pantry"
_SKIP_REASON = (
    "Blocked pending a separate Bridge permission-model change -- see "
    "tests/web_js_runtime.py docstring (Chief review, PR #53)."
)
_GYLDIG_TILLEGG = {
    "ingredientType": "malt",
    "id": "weyermann_pilsner",
    "custom": None,
    "mengde": 5.0,
    "notat": "",
}


def _kjor(expr, preset_local_storage=None):
    return run_web_js(_PANTRY, expr, prelude=_T_STUB, preset_local_storage=preset_local_storage)


@unittest.skip(_SKIP_REASON)
class TestGyldigPantryLastesOgLagres(unittest.TestCase):
    def test_legg_til_deretter_les_tilbake(self):
        expr = "(function(){const res = leggTilPantryItem(%s); return {res, alle: allePantryItems()};})()" % json.dumps(_GYLDIG_TILLEGG)
        result = _kjor(expr)
        self.assertTrue(result["res"]["ok"])
        self.assertEqual(len(result["alle"]), 1)
        self.assertEqual(result["alle"][0]["id"], "weyermann_pilsner")

    def test_eksisterende_gyldig_lager_lastes_uendret(self):
        lagret = {"format": "kbh-pantry", "version": 1, "items": [
            {"pantryItemId": "pantryitem-1", "ingredientType": "gjaer", "id": "safale-us05", "mengde": 2},
        ]}
        result = _kjor("allePantryItems()", preset_local_storage={_PANTRY_NOKKEL: json.dumps(lagret)})
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], "safale-us05")


@unittest.skip(_SKIP_REASON)
class TestKorruptLagerOverskrivesAldriStille(unittest.TestCase):
    def test_ugyldig_json_gir_korrupt_flagg_ikke_tom_gyldig_state(self):
        preset = {_PANTRY_NOKKEL: "{ dette er ikke gyldig json ]"}
        result = _kjor("pantryStateErKorrupt()", preset_local_storage=preset)
        self.assertTrue(result)

    def test_ustottet_versjon_er_korrupt(self):
        lagret = {"format": "kbh-pantry", "version": 99, "items": []}
        preset = {_PANTRY_NOKKEL: json.dumps(lagret)}
        result = _kjor("pantryStateErKorrupt()", preset_local_storage=preset)
        self.assertTrue(result)

    def test_manglende_nokkel_er_ikke_korrupt(self):
        result = _kjor("pantryStateErKorrupt()", preset_local_storage={})
        self.assertFalse(result)

    def test_tom_streng_er_korrupt_ikke_manglende_nokkel(self):
        # Chief review, PR #75: `localStorage.getItem` returnerer "" for en
        # nøkkel som FAKTISK inneholder en tom streng -- det skiller seg fra
        # `null` (nøkkelen mangler) og må derfor behandles som uleselig
        # rådata, ikke en ekte tom pantry.
        result = _kjor("pantryStateErKorrupt()", preset_local_storage={_PANTRY_NOKKEL: ""})
        self.assertTrue(result)

    def test_en_ugyldig_rad_gjor_hele_lageret_korrupt(self):
        # Chief review, PR #75: et lager med ÉN strukturelt ugyldig rad skal
        # IKKE stille normaliseres til en redusert, men "gyldig", liste --
        # det ville la en påfølgende normal lagring persistere den reduserte
        # listen og dermed ødelegge den ugyldige raden for godt.
        lagret = {"format": "kbh-pantry", "version": 1, "items": [
            {"pantryItemId": "pantryitem-1", "ingredientType": "malt", "id": "weyermann_pilsner", "mengde": 1},
            {"pantryItemId": "pantryitem-2", "ingredientType": "ugyldig-type", "id": "x", "mengde": 1},
        ]}
        preset = {_PANTRY_NOKKEL: json.dumps(lagret)}
        result = _kjor("pantryStateErKorrupt()", preset_local_storage=preset)
        self.assertTrue(result)

    def test_blandet_gyldig_ugyldig_liste_overskrives_ikke_av_normal_lagring(self):
        raa = json.dumps({"format": "kbh-pantry", "version": 1, "items": [
            {"pantryItemId": "pantryitem-1", "ingredientType": "malt", "id": "weyermann_pilsner", "mengde": 1},
            {"pantryItemId": "pantryitem-2", "ingredientType": "ugyldig-type", "id": "x", "mengde": 1},
        ]})
        preset = {_PANTRY_NOKKEL: raa}
        expr = (
            "(function(){"
            "const res = leggTilPantryItem(%s);"
            "return {res, raaEtterpa: localStorage.getItem('%s')};"
            "})()"
        ) % (json.dumps(_GYLDIG_TILLEGG), _PANTRY_NOKKEL)
        result = _kjor(expr, preset_local_storage=preset)
        self.assertFalse(result["res"]["ok"])
        self.assertEqual(result["raaEtterpa"], raa, "Den opprinnelige raden med den ugyldige naboen skal ALDRI reduseres bort av et normalt lagringsforsøk")

    def test_legg_til_avvises_pa_korrupt_lager_og_rorer_ikke_radataen(self):
        raa = "{ dette er ikke gyldig json ]"
        preset = {_PANTRY_NOKKEL: raa}
        expr = (
            "(function(){"
            "const res = leggTilPantryItem(%s);"
            "return {res, raaEtterpa: localStorage.getItem('%s')};"
            "})()"
        ) % (json.dumps(_GYLDIG_TILLEGG), _PANTRY_NOKKEL)
        result = _kjor(expr, preset_local_storage=preset)
        self.assertFalse(result["res"]["ok"])
        self.assertEqual(result["raaEtterpa"], raa, "Korrupt rådata skal ALDRI overskrives av et påfølgende normalt forsøk på å lagre")

    def test_erstattpantryitems_overskriver_bevisst_korrupt_lager(self):
        # erstattPantryItems() er den EKSPLISitte, brukerbekreftede
        # gjenopprettingshandlingen (backup-restore) -- eneste unntaket fra
        # korrupt-sperren, se pantry.js sin egen dokumentasjon av dette.
        preset = {_PANTRY_NOKKEL: "{ ugyldig ]"}
        expr = "erstattPantryItems([{pantryItemId: 'p1', ingredientType: 'malt', id: 'x', mengde: 1}])"
        result = _kjor(expr, preset_local_storage=preset)
        self.assertTrue(result["ok"])
        self.assertEqual(len(result["items"]), 1)


@unittest.skip(_SKIP_REASON)
class TestSkrivefeilOverflatesAldriSomSuksess(unittest.TestCase):
    _SETITEM_KASTER = "localStorage.setItem = () => { throw new Error('QuotaExceededError'); };"

    def test_legg_til_gir_ok_false_ved_skrivefeil(self):
        result = run_web_js(
            _PANTRY, "leggTilPantryItem(%s)" % json.dumps(_GYLDIG_TILLEGG),
            prelude=_T_STUB + self._SETITEM_KASTER,
        )
        self.assertFalse(result["ok"])

    def test_slett_gir_false_ved_skrivefeil(self):
        lagret = {"format": "kbh-pantry", "version": 1, "items": [
            {"pantryItemId": "pantryitem-1", "ingredientType": "malt", "id": "weyermann_pilsner", "mengde": 1},
        ]}
        expr = "slettPantryItem('pantryitem-1')"
        result = run_web_js(
            _PANTRY, expr,
            prelude=_T_STUB + self._SETITEM_KASTER,
            preset_local_storage={_PANTRY_NOKKEL: json.dumps(lagret)},
        )
        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
