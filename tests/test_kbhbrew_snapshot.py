"""
PRI 3B1 (issue #24) -- frosset snapshot-tester for
modules/kbhbrew.py::bygg_ny_brew_snapshot()/bygg_ny_brew()
(docs/development/CORE_KBHBREW_V1.md Section 5.5).

Dekker (issue #24 Section 7 "Snapshot"):
  - et nytt brygg fanger recipe/ingredients/equipment/predicted/
    provenance ved opprettelse;
  - senere mutasjon av KILDE-oppskriften etterlater snapshotet uendret;
  - senere mutasjon av kilde-master-/utstyrsdata etterlater snapshotet
    uendret;
  - manglende provenance fabrikeres ALDRI -- en ærlig utelatelse i
    stedet.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_snapshot -b
"""
import copy
import unittest

from modules.recipe import bygg_recipe_object
from modules.kbhbrew import bygg_ny_brew, bygg_ny_brew_snapshot


def _recipe():
    return bygg_recipe_object(
        "Snapshottest", 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}],
        [{"id": "cascade", "gram": 30.0, "tid": 60}],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8,
        {"Maltfylde": 5.0, "Sitrus": 2.0},
    )


def _dbs():
    malt_db = {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}}
    humle_db = {"cascade": {"display_name": "Cascade", "alfa_typisk": 6.0}}
    gjaer_db = {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}}
    return malt_db, humle_db, gjaer_db


def _predicted():
    return {
        "og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20.0, "ebc": 8.0, "buGu": 0.9,
        "flavorProfile": {"Maltfylde": 5.0, "Sitrus": 2.0},
        "style": {"stil": "Test IPA", "score": 80, "balanse": ["skal ikke fryses"], "problemer": ["skal ikke fryses"]},
    }


def _equipment():
    return {"efficiency": 0.75, "kettle_capacity_l": 35.0, "boil_off_l_per_hour": 4.0}


_MANIFEST_DATASETS = {
    "malt": {"schema_version": 1, "data_version": 3, "checksum": {"algorithm": "sha256", "value": "abc"}},
    "humle": {"schema_version": 1, "data_version": 2, "checksum": {"algorithm": "sha256", "value": "def"}},
    "gjaer": {"schema_version": 1, "data_version": 1, "checksum": {"algorithm": "sha256", "value": "ghi"}},
}


class TestSnapshotCapturesEverythingAtCreation(unittest.TestCase):
    def test_snapshot_captures_recipe_ingredients_equipment_predicted_provenance(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00", engine_version=1, manifest_datasets=_MANIFEST_DATASETS,
        )

        self.assertEqual(snapshot["recipe"]["navn"], "Snapshottest")
        self.assertEqual(snapshot["ingredients"]["malt"]["weyermann_pilsner"]["display_name"], "Weyermann Pilsner")
        self.assertEqual(snapshot["ingredients"]["humle"]["cascade"]["alfa_typisk"], 6.0)
        self.assertEqual(snapshot["ingredients"]["gjaer"]["safale_us_05"]["attenuation"], 0.75)
        self.assertEqual(snapshot["equipment"]["kettle_capacity_l"], 35.0)
        self.assertEqual(snapshot["predicted"]["og"], 1.050)
        self.assertEqual(snapshot["predicted"]["style"], {"stil": "Test IPA", "score": 80})
        self.assertEqual(snapshot["provenance"]["engineVersion"], 1)
        self.assertEqual(snapshot["provenance"]["recipeSchemaVersion"], 1)
        self.assertEqual(snapshot["provenance"]["capturedAt"], "2026-03-01T09:00:00+00:00")
        self.assertEqual(snapshot["provenance"]["datasets"]["malt"]["data_version"], 3)

    def test_style_is_reduced_to_stil_and_score_only(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00",
        )
        self.assertNotIn("balanse", snapshot["predicted"]["style"])
        self.assertNotIn("problemer", snapshot["predicted"]["style"])

    def test_equipment_none_when_no_active_profile(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, None, _predicted(),
            captured_at="2026-03-01T09:00:00+00:00",
        )
        self.assertIsNone(snapshot["equipment"])

    def test_predicted_empty_when_nothing_supplied(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, _equipment(), None,
            captured_at="2026-03-01T09:00:00+00:00",
        )
        self.assertEqual(snapshot["predicted"], {})

    def test_ingredient_not_found_in_database_is_skipped_not_fabricated(self):
        recipe = bygg_recipe_object(
            "Ukjent Malt", 20.0, 0.75, [{"id": "ikke_i_databasen", "mengde": 5.0}], [], None,
            1.050, 1.012, 5.0, 0, 8, {},
        )
        malt_db, humle_db, gjaer_db = {}, {}, {}
        snapshot = bygg_ny_brew_snapshot(
            recipe, malt_db, humle_db, gjaer_db, None, {}, captured_at="2026-03-01T09:00:00+00:00",
        )
        self.assertEqual(snapshot["ingredients"]["malt"], {})


class TestSnapshotImmutability(unittest.TestCase):
    def test_mutating_source_recipe_after_creation_leaves_snapshot_unchanged(self):
        recipe = _recipe()
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            recipe, malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00",
        )
        before = copy.deepcopy(snapshot)

        recipe["name"] = "Endret Etter Frysing"
        recipe["malts"][0]["mengde"] = 999.0
        recipe["malts"].append({"id": "ny_malt_lagt_til_senere", "mengde": 1.0})

        self.assertEqual(snapshot, before)
        self.assertEqual(snapshot["recipe"]["navn"], "Snapshottest")

    def test_mutating_source_masterdata_after_creation_leaves_snapshot_unchanged(self):
        recipe = _recipe()
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            recipe, malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00",
        )
        before = copy.deepcopy(snapshot)

        malt_db["weyermann_pilsner"]["ebc"] = 999.0
        malt_db["weyermann_pilsner"]["display_name"] = "Endret Malt"
        humle_db["cascade"]["alfa_typisk"] = 999.0
        gjaer_db["safale_us_05"]["attenuation"] = 0.99

        self.assertEqual(snapshot, before)
        self.assertEqual(snapshot["ingredients"]["malt"]["weyermann_pilsner"]["ebc"], 3.5)

    def test_mutating_source_equipment_after_creation_leaves_snapshot_unchanged(self):
        recipe = _recipe()
        malt_db, humle_db, gjaer_db = _dbs()
        equipment = _equipment()
        snapshot = bygg_ny_brew_snapshot(
            recipe, malt_db, humle_db, gjaer_db, equipment, _predicted(),
            captured_at="2026-03-01T09:00:00+00:00",
        )
        equipment["kettle_capacity_l"] = 999.0
        self.assertEqual(snapshot["equipment"]["kettle_capacity_l"], 35.0)

    def test_mutating_source_predicted_after_creation_leaves_snapshot_unchanged(self):
        recipe = _recipe()
        malt_db, humle_db, gjaer_db = _dbs()
        predicted = _predicted()
        snapshot = bygg_ny_brew_snapshot(
            recipe, malt_db, humle_db, gjaer_db, _equipment(), predicted,
            captured_at="2026-03-01T09:00:00+00:00",
        )
        predicted["flavorProfile"]["Maltfylde"] = 999.0
        self.assertEqual(snapshot["predicted"]["flavorProfile"]["Maltfylde"], 5.0)

    def test_bygg_ny_brew_top_level_snapshot_is_also_immune_to_later_mutation(self):
        recipe = _recipe()
        malt_db, humle_db, gjaer_db = _dbs()
        brew = bygg_ny_brew(
            recipe, malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            created_at="2026-03-01T09:00:00+00:00", brew_id="brew-immutability-test",
        )
        recipe["name"] = "Endret"
        malt_db["weyermann_pilsner"]["ebc"] = 999.0
        self.assertEqual(brew["snapshot"]["recipe"]["navn"], "Snapshottest")
        self.assertEqual(brew["snapshot"]["ingredients"]["malt"]["weyermann_pilsner"]["ebc"], 3.5)


class TestProvenanceIsHonestNeverFabricated(unittest.TestCase):
    def test_missing_manifest_datasets_omits_datasets_key_entirely(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00", manifest_datasets=None,
        )
        self.assertNotIn("datasets", snapshot["provenance"])

    def test_empty_manifest_datasets_omits_datasets_key_entirely(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00", manifest_datasets={},
        )
        self.assertNotIn("datasets", snapshot["provenance"])

    def test_default_engine_version_is_used_when_not_supplied(self):
        malt_db, humle_db, gjaer_db = _dbs()
        snapshot = bygg_ny_brew_snapshot(
            _recipe(), malt_db, humle_db, gjaer_db, _equipment(), _predicted(),
            captured_at="2026-03-01T09:00:00+00:00",
        )
        self.assertIsInstance(snapshot["provenance"]["engineVersion"], int)


if __name__ == "__main__":
    unittest.main()
