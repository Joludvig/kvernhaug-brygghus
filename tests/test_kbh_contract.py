"""
Tester for modules/kbh_contract.py — ren Python, ingen Streamlit-
avhengighet, ingen disk-I/O. Dekker oversettelsen fra Streamlit sitt
interne Recipe Object til KBH Core Recipe Payload V1
(docs/development/KBH_CORE_CONTRACT.md).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import unittest

from modules.recipe import bygg_recipe_object
from modules.kbh_contract import (
    recipe_to_kbhrecipe_payload,
    bygg_kbhrecipe_konvolutt,
    UgyldigOppskriftForEksport,
    KBHRECIPE_FORMAT,
    KBHRECIPE_VERSION,
)


def _full_oppskrift():
    return bygg_recipe_object(
        navn="Eldsvenn V1",
        batch_size=20.0,
        efficiency=0.75,
        malts=[
            {"id": "weyermann_pilsner", "mengde": 5.0},
            {"id": "rauchmalz", "mengde": 1.5},
        ],
        hops=[
            {"id": "east_kent_goldings", "gram": 25.0, "tid": 60},
        ],
        yeast="wyeast_1318",
        og=1.0918, fg=1.0248, abv=8.8, ibu=9.9, ebc=29.3,
        flavor_profile={"røkt": 3, "bitter": 2},
        brygger_stil="Min egen røkt variant",
        process_profile={
            "process_id": "hochkurz",
            "mash_steps": [{"temperatur": 63, "varighet": 40}],
        },
        water_source_profile={"ca": 10, "mg": 5},
        water_target_profile={"ca": 80, "mg": 10},
        water_treatment={"salter": [{"id": "gips", "gram": 4.0}]},
        water_measurements={"ph_mesk": 5.3},
    )


def _minimal_oppskrift():
    return bygg_recipe_object(
        navn="Enkel Ale",
        batch_size=10.0,
        efficiency=0.70,
        malts=[{"id": "weyermann_pilsner", "mengde": 2.0}],
        hops=[{"id": "east_kent_goldings", "gram": 20.0, "tid": 60}],
        yeast="wyeast_1318",
        og=1.045, fg=1.010, abv=4.5, ibu=20.0, ebc=8.0,
        flavor_profile={},
    )


class TestRecipeToKbhrecipePayload(unittest.TestCase):

    # ── 1. Full oppskrift ────────────────────────────────────────────────
    def test_full_oppskrift_inneholder_riktig_data(self):
        payload = recipe_to_kbhrecipe_payload(_full_oppskrift())

        self.assertEqual(payload["recipeSchemaVersion"], 1)
        self.assertEqual(payload["navn"], "Eldsvenn V1")
        self.assertEqual(payload["volum"], 20.0)
        self.assertEqual(
            payload["malt"],
            [
                {"id": "weyermann_pilsner", "mengde": 5.0},
                {"id": "rauchmalz", "mengde": 1.5},
            ],
        )
        self.assertEqual(
            payload["humle"],
            [{"id": "east_kent_goldings", "gram": 25.0, "tid": 60}],
        )
        self.assertEqual(payload["gjaerId"], "wyeast_1318")
        self.assertEqual(payload["bryggerStil"], "Min egen røkt variant")
        self.assertEqual(payload["prosess"]["process_id"], "hochkurz")
        self.assertEqual(
            payload["vann"],
            {
                "kilde": {"ca": 10, "mg": 5},
                "maal": {"ca": 80, "mg": 10},
                "behandling": {"salter": [{"id": "gips", "gram": 4.0}]},
                "maalinger": {"ph_mesk": 5.3},
            },
        )

    # ── 2. Effektivitet ──────────────────────────────────────────────────
    def test_effektivitet_konverteres_til_prosent(self):
        payload = recipe_to_kbhrecipe_payload(_full_oppskrift())
        self.assertEqual(payload["effektivitet"], 75)

    def test_effektivitet_faktor_100_kan_ikke_falle_ut(self):
        recipe = _minimal_oppskrift()
        recipe["efficiency"] = 0.823
        payload = recipe_to_kbhrecipe_payload(recipe)
        # Hvis x100 faller ut ville dette vært 0.823, ikke 82.3 —
        # sjekk eksplisitt at verdien er i prosentskala, ikke brøk.
        self.assertAlmostEqual(payload["effektivitet"], 82.3)
        self.assertGreater(payload["effektivitet"], 1.0)

    def test_efficiency_0_75_gir_75_ikke_75000_eller_0_75(self):
        recipe = _minimal_oppskrift()
        recipe["efficiency"] = 0.75
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertEqual(payload["effektivitet"], 75)

    # ── 3. Hviteliste ────────────────────────────────────────────────────
    def test_stats_eksporteres_aldri(self):
        recipe = _full_oppskrift()
        self.assertIn("stats", recipe)  # forutsetning: kilden faktisk har feltet
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertNotIn("stats", payload)

    def test_flavor_profile_eksporteres_aldri(self):
        recipe = _full_oppskrift()
        self.assertIn("flavor_profile", recipe)
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertNotIn("flavor_profile", payload)

    def test_ukjente_fremtidige_felt_lekker_ikke_inn(self):
        recipe = _minimal_oppskrift()
        recipe["fremtidig_ukjent_felt"] = "skal aldri dukke opp i payload"
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertNotIn("fremtidig_ukjent_felt", payload)

    # ── 4. Ingrediens-ID ─────────────────────────────────────────────────
    def test_ingrediens_id_beholdes_uendret(self):
        payload = recipe_to_kbhrecipe_payload(_full_oppskrift())
        malt_ider = [rad["id"] for rad in payload["malt"]]
        humle_ider = [rad["id"] for rad in payload["humle"]]
        self.assertEqual(malt_ider, ["weyermann_pilsner", "rauchmalz"])
        self.assertEqual(humle_ider, ["east_kent_goldings"])
        self.assertEqual(payload["gjaerId"], "wyeast_1318")

    # ── 5. Vann/prosess videreføres uendret ─────────────────────────────
    def test_vann_og_prosess_videreforst_uendret(self):
        recipe = _full_oppskrift()
        payload = recipe_to_kbhrecipe_payload(recipe)

        self.assertEqual(payload["prosess"], recipe["process_profile"])
        self.assertEqual(payload["vann"]["kilde"], recipe["water_source_profile"])
        self.assertEqual(payload["vann"]["maal"], recipe["water_target_profile"])
        self.assertEqual(payload["vann"]["behandling"], recipe["water_treatment"])
        self.assertEqual(payload["vann"]["maalinger"], recipe["water_measurements"])

    def test_vann_og_prosess_er_uavhengige_kopier(self):
        # Ren funksjon: payload skal ikke dele muterbar tilstand med kilden.
        recipe = _full_oppskrift()
        payload = recipe_to_kbhrecipe_payload(recipe)
        payload["prosess"]["mash_steps"].append({"temperatur": 99, "varighet": 1})
        self.assertEqual(len(recipe["process_profile"]["mash_steps"]), 1)

    # ── 6. Minimal oppskrift ─────────────────────────────────────────────
    def test_minimal_oppskrift_uten_vann_prosess_gir_gyldig_payload(self):
        payload = recipe_to_kbhrecipe_payload(_minimal_oppskrift())

        self.assertEqual(payload["recipeSchemaVersion"], 1)
        self.assertEqual(payload["navn"], "Enkel Ale")
        self.assertNotIn("vann", payload)
        self.assertNotIn("prosess", payload)
        self.assertNotIn("bryggerStil", payload)  # brygger_stil default er "" -> falsy
        self.assertIn("malt", payload)
        self.assertIn("humle", payload)

    def test_gammel_oppskrift_uten_water_prosess_felt_i_det_hele_tatt(self):
        # Speiler ekte recipes/*.json fra før vannkjemi/prosessprofil ble
        # innført: feltene mangler helt (ikke bare None), henting via
        # .get() skal fortsatt fungere.
        recipe = {
            "name": "Gamleguten Klone",
            "batch_size": 20.0,
            "efficiency": 0.75,
            "malts": [{"id": "weyermann_pilsner", "mengde": 5.0}],
            "hops": [{"id": "east_kent_goldings", "gram": 25.0, "tid": 60}],
            "yeast": "wyeast_1318",
            "stats": {"og": 1.05, "fg": 1.01, "abv": 5.0, "ibu": 20.0, "ebc": 10.0},
            "flavor_profile": {},
        }
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertNotIn("vann", payload)
        self.assertNotIn("prosess", payload)

    # ── Validering (§9 — ingen gjetting) ────────────────────────────────
    def test_ugyldig_recipe_type_kaster(self):
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(["ikke", "en", "dict"])

    def test_malts_ikke_liste_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["malts"] = "weyermann_pilsner"
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_hops_ikke_liste_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["hops"] = None
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_maltrad_uten_id_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["malts"] = [{"mengde": 5.0}]
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_maltrad_med_ugyldig_mengde_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["malts"] = [{"id": "weyermann_pilsner", "mengde": 0}]
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_maltrad_med_tekst_som_mengde_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["malts"] = [{"id": "weyermann_pilsner", "mengde": "fem kilo"}]
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_humlerad_uten_id_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["hops"] = [{"gram": 20.0, "tid": 60}]
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_humlerad_med_negativ_tid_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["hops"] = [{"id": "east_kent_goldings", "gram": 20.0, "tid": -5}]
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_humlerad_med_negativ_gram_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["hops"] = [{"id": "east_kent_goldings", "gram": -1.0, "tid": 60}]
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_humlerad_med_null_gram_er_gyldig(self):
        # gram >= 0 er gyldig (f.eks. en rad under redigering) —
        # kun negative verdier skal avvises.
        recipe = _minimal_oppskrift()
        recipe["hops"] = [{"id": "east_kent_goldings", "gram": 0.0, "tid": 60}]
        payload = recipe_to_kbhrecipe_payload(recipe)
        self.assertEqual(payload["humle"][0]["gram"], 0.0)

    def test_ugyldig_efficiency_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["efficiency"] = 0
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)

    def test_ugyldig_batch_size_kaster(self):
        recipe = _minimal_oppskrift()
        recipe["batch_size"] = -20.0
        with self.assertRaises(UgyldigOppskriftForEksport):
            recipe_to_kbhrecipe_payload(recipe)


class TestByggKbhrecipeKonvolutt(unittest.TestCase):

    def test_wrapper_format(self):
        konvolutt = bygg_kbhrecipe_konvolutt(_full_oppskrift(), "2026-08-15T12:00:00.000Z")
        self.assertEqual(
            set(konvolutt.keys()),
            {"format", "version", "exportedAt", "generator", "recipe"},
        )
        self.assertEqual(konvolutt["format"], "kbhrecipe")
        self.assertEqual(konvolutt["format"], KBHRECIPE_FORMAT)
        self.assertEqual(konvolutt["version"], 1)
        self.assertEqual(konvolutt["version"], KBHRECIPE_VERSION)
        self.assertEqual(konvolutt["exportedAt"], "2026-08-15T12:00:00.000Z")
        self.assertIsInstance(konvolutt["generator"], str)
        self.assertTrue(konvolutt["generator"])

    def test_json_struktur_er_serialiserbar(self):
        # download_button skal kunne json.dumps() konvolutten direkte —
        # verifiser at ingen ikke-serialiserbare typer (dato-objekter o.l.)
        # sniker seg inn i output.
        konvolutt = bygg_kbhrecipe_konvolutt(_full_oppskrift(), "2026-08-15T12:00:00.000Z")
        rundtur = json.loads(json.dumps(konvolutt, ensure_ascii=False))
        self.assertEqual(rundtur, konvolutt)

    def test_download_data_bygger_paa_kbh_core_payload(self):
        recipe = _full_oppskrift()
        payload = recipe_to_kbhrecipe_payload(recipe)
        konvolutt = bygg_kbhrecipe_konvolutt(recipe, "2026-08-15T12:00:00.000Z")
        self.assertEqual(konvolutt["recipe"], payload)

    def test_stats_eksporteres_aldri_i_konvolutt(self):
        recipe = _full_oppskrift()
        konvolutt = bygg_kbhrecipe_konvolutt(recipe, "2026-08-15T12:00:00.000Z")
        self.assertNotIn("stats", konvolutt["recipe"])

    def test_flavor_profile_eksporteres_aldri_i_konvolutt(self):
        recipe = _full_oppskrift()
        konvolutt = bygg_kbhrecipe_konvolutt(recipe, "2026-08-15T12:00:00.000Z")
        self.assertNotIn("flavor_profile", konvolutt["recipe"])

    def test_ugyldig_oppskrift_kaster_ved_konvoluttbygging(self):
        recipe = _minimal_oppskrift()
        recipe["malts"] = []
        recipe["malts"].append({"id": "weyermann_pilsner", "mengde": -1})
        with self.assertRaises(UgyldigOppskriftForEksport):
            bygg_kbhrecipe_konvolutt(recipe, "2026-08-15T12:00:00.000Z")


if __name__ == "__main__":
    unittest.main()
