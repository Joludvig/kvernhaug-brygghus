"""
PRI 3B1 (issue #24) -- rundtur-/interoperabilitetstester for App sin
`.kbhbrew` V1-motor (modules/kbhbrew.py) mot Core/Web V1-bevis.

Dekker (issue #24 Section 7 "Round-trip/interoperability" + Section 8):
  - App-native NY brew -> App-skriver -> App-leser -> re-eksport uten
    semantisk tap for støttet V1-data;
  - representative Core/Web V1-fixturer -> App-leser -> App-skriver
    forblir Core-gyldig (validert mot core/kbhbrew_v1.schema.json) og
    bevarer påkrevde ukjente felt.

Bruker `jsonschema` (allerede en prosjektavhengighet, se
tests/test_kbhbrew_schema_contract.py) til å validere App-skriverens
faktiske output mot den ratifiserte kontrakten -- ikke bare mot App sin
egen forståelse av formen.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_roundtrip -b
"""
import copy
import json
import os
import unittest

import jsonschema

from modules.recipe import bygg_recipe_object
from modules.kbhbrew import bygg_kbhbrew_konvolutt, bygg_ny_brew, parse_kbhbrew_json

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCHEMA_PATH = os.path.join(_ROOT, "core", "kbhbrew_v1.schema.json")
_CORE_FIXTURES = os.path.join(_ROOT, "tests", "fixtures", "core", "kbhbrew")
_LEGACY_WEB_FIXTURE = os.path.join(_ROOT, "tests", "fixtures", "legacy", "web", "kbhbrew_v1.json")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_schema():
    return _load_json(_SCHEMA_PATH)


def _load_core_fixture(name):
    return _load_json(os.path.join(_CORE_FIXTURES, f"{name}.json"))


def _recipe():
    return bygg_recipe_object(
        "Rundturtest", 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}],
        [{"id": "cascade", "gram": 30.0, "tid": 60}],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8,
        {"Maltfylde": 5.0, "Sitrus": 2.0},
    )


def _dbs():
    return (
        {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}},
        {"cascade": {"display_name": "Cascade", "alfa_typisk": 6.0}},
        {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}},
    )


def _predicted():
    return {
        "og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20.0, "ebc": 8.0, "buGu": 0.9,
        "flavorProfile": {"Maltfylde": 5.0, "Sitrus": 2.0},
        "style": {"stil": "Test IPA", "score": 80},
    }


class TestAppNativeRoundTripWithoutSemanticLoss(unittest.TestCase):
    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(_load_schema())

    def test_new_app_brew_export_validates_against_core_schema(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = bygg_ny_brew(
            _recipe(), malt_db, humle_db, gjaer_db, {"efficiency": 0.75}, _predicted(),
            created_at="2026-03-01T09:00:00+00:00", brew_id="brew-roundtrip-0001", recipe_id="rundturtest.json",
        )
        brew["actuals"] = {"og": 1.053, "fg": 1.011, "volumeL": 22.5, "notes": "Notat"}
        brew["sensing"] = {"judgment": "yes", "notes": "Smakte bra"}
        brew["learning"] = {"nextTime": "Samme igjen"}
        brew["status"] = "done"

        envelope = bygg_kbhbrew_konvolutt(brew, "2026-03-10T00:00:00+00:00")
        self.validator.validate(envelope)  # raises on any contract violation

    def test_write_read_write_again_is_stable(self):
        malt_db, humle_db, gjaer_db = _dbs()
        brew = bygg_ny_brew(
            _recipe(), malt_db, humle_db, gjaer_db, {"efficiency": 0.75}, _predicted(),
            created_at="2026-03-01T09:00:00+00:00", brew_id="brew-roundtrip-0002",
        )
        brew["actuals"] = {"og": 1.053, "fg": 1.011, "volumeL": 22.0}

        first_export = bygg_kbhbrew_konvolutt(brew, "2026-03-10T00:00:00+00:00")
        native_again = parse_kbhbrew_json(json.dumps(first_export))
        second_export = bygg_kbhbrew_konvolutt(native_again, "2026-03-11T00:00:00+00:00")

        self.assertEqual(first_export["brew"]["snapshot"], second_export["brew"]["snapshot"])
        self.assertEqual(first_export["brew"]["actuals"], second_export["brew"]["actuals"])
        self.assertEqual(first_export["brew"]["originBrewId"], second_export["brew"]["originBrewId"])
        self.assertEqual(first_export["brew"]["status"], second_export["brew"]["status"])
        # Only exportedAt (explicitly supplied by the caller each time) differs.
        self.assertNotEqual(first_export["exportedAt"], second_export["exportedAt"])


class TestCoreFixturesReadableAndReexportRemainsCoreValid(unittest.TestCase):
    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(_load_schema())

    def _assert_reads_and_reexports_validly(self, fixture):
        native = parse_kbhbrew_json(json.dumps(fixture))
        envelope = bygg_kbhbrew_konvolutt(native, "2026-03-12T00:00:00+00:00")
        self.validator.validate(envelope)
        return envelope

    def test_core_minimal_v1_fixture_round_trips_and_remains_core_valid(self):
        envelope = self._assert_reads_and_reexports_validly(_load_core_fixture("minimal_v1"))
        self.assertEqual(envelope["brew"]["originBrewId"], "brew-11111111-1111-4111-8111-111111111111")

    def test_core_full_v1_fixture_round_trips_and_remains_core_valid(self):
        fixture = _load_core_fixture("full_v1")
        envelope = self._assert_reads_and_reexports_validly(fixture)
        self.assertEqual(envelope["brew"]["snapshot"], fixture["brew"]["snapshot"])
        self.assertEqual(envelope["brew"]["actuals"], fixture["brew"]["actuals"])
        self.assertEqual(envelope["brew"]["sensing"], fixture["brew"]["sensing"])
        self.assertEqual(envelope["brew"]["learning"], fixture["brew"]["learning"])

    def test_legacy_web_export_fixture_round_trips_and_remains_core_valid(self):
        fixture = _load_json(_LEGACY_WEB_FIXTURE)
        envelope = self._assert_reads_and_reexports_validly(fixture)
        # The Web fixture's snapshot has a custom-ingredient malt row and
        # rich butikk_match/aliases data nested inside snapshot.recipe --
        # proving the frozen-snapshot copy is genuinely lossless, not just
        # the top-level shape.
        self.assertEqual(envelope["brew"]["snapshot"], fixture["brew"]["snapshot"])
        # Web's legacy masterdata entry-count provenance proxy survives
        # untouched too (Section 5.12 -- App writer never rewrites it).
        self.assertEqual(
            envelope["brew"]["snapshot"]["provenance"]["masterdata"],
            fixture["brew"]["snapshot"]["provenance"]["masterdata"],
        )

    def test_legacy_web_fixture_forbidden_and_unknown_fields_behave_correctly(self):
        # Deliberately inject a foreign actual_abv onto the Web fixture
        # (simulating a hand-edited/foreign file) plus a genuine unknown
        # top-level brew field, then prove the re-export keeps the unknown
        # field but strips the forbidden one -- interoperability must not
        # weaken the ratified Section 8 #3 rule.
        fixture = copy.deepcopy(_load_json(_LEGACY_WEB_FIXTURE))
        fixture["brew"]["actuals"]["actual_abv"] = 5.5
        fixture["brew"]["futureBatchTag"] = "B-2026-099"

        native = parse_kbhbrew_json(json.dumps(fixture))
        envelope = bygg_kbhbrew_konvolutt(native, "2026-03-13T00:00:00+00:00")
        self.validator.validate(envelope)

        self.assertNotIn("actual_abv", envelope["brew"]["actuals"])
        self.assertEqual(envelope["brew"]["futureBatchTag"], "B-2026-099")


if __name__ == "__main__":
    unittest.main()
