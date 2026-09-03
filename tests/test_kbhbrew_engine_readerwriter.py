"""
PRI 3B1 (issue #24) -- reader/writer-tester for modules/kbhbrew.py, App
sin rene `.kbhbrew` V1-motor (docs/development/CORE_KBHBREW_V1.md).

Dekker (se issue #24 Section 7 "Core V1 reader/writer"):
  - minimal og representativ full V1 les/skriv;
  - avvisning av ugyldig format/versjon;
  - håndheving av påkrevde identitets-/snapshot-regler;
  - overlevelse av ukjente felt på konvolutt-, brew- og
    actuals-/sensing-/learning-lag gjennom en lese->skrive-rundtur;
  - at forbudt `actual_abv`/`abv`/`actualAbv` ALDRI kan eksporteres,
    selv via passthrough;
  - at intet V1 "actual process"-felt noensinne skrives.

Ren enhetstesting av modules/kbhbrew.py -- ingen disk-I/O, ingen
Streamlit. Persistens-/identitetslaget (modules/kbhbrew_storage.py)
dekkes separat i tests/test_kbhbrew_storage_identity.py.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_engine_readerwriter -b
"""
import copy
import json
import os
import unittest

from modules.recipe import bygg_recipe_object
from modules.kbhbrew import (
    KATEGORI_INVALID_BREW,
    KATEGORI_INVALID_ENVELOPE,
    KATEGORI_INVALID_JSON,
    KATEGORI_INVALID_SNAPSHOT,
    KATEGORI_UNSUPPORTED_VERSION,
    UgyldigKbhbrewForImport,
    bygg_kbhbrew_konvolutt,
    bygg_ny_brew,
    brew_to_kbhbrew_payload,
    parse_kbhbrew_json,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CORE_FIXTURES = os.path.join(_ROOT, "tests", "fixtures", "core", "kbhbrew")


def _load_fixture(name):
    with open(os.path.join(_CORE_FIXTURES, f"{name}.json"), "r", encoding="utf-8") as f:
        return json.load(f)


def _recipe():
    return bygg_recipe_object(
        "Testbrygg", 20.0, 0.75,
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


def _ny_brew(brew_id="brew-test-0001"):
    malt_db, humle_db, gjaer_db = _dbs()
    return bygg_ny_brew(
        _recipe(), malt_db, humle_db, gjaer_db, {"efficiency": 0.75, "kettle_capacity_l": 35.0}, _predicted(),
        created_at="2026-03-01T09:00:00+00:00", brew_id=brew_id, recipe_id="testbrygg.json",
    )


class TestMinimalValidReadWrite(unittest.TestCase):
    def test_minimal_fixture_reads_and_reexports_without_loss(self):
        fixture = _load_fixture("minimal_v1")
        native = parse_kbhbrew_json(json.dumps(fixture))
        self.assertEqual(native["originBrewId"], fixture["brew"]["originBrewId"])
        self.assertEqual(native["status"], "active")
        self.assertEqual(native["snapshot"]["recipe"]["navn"], "Core V1 minimal (syntetisk fixture)")

        envelope = bygg_kbhbrew_konvolutt(native, "2026-03-02T00:00:00+00:00")
        self.assertEqual(envelope["format"], "kbhbrew")
        self.assertEqual(envelope["version"], 1)
        self.assertEqual(envelope["brew"]["originBrewId"], fixture["brew"]["originBrewId"])
        self.assertEqual(envelope["brew"]["snapshot"], fixture["brew"]["snapshot"])
        # A canonical export never carries local identity.
        self.assertNotIn("brewId", envelope["brew"])
        self.assertNotIn("recipeId", envelope["brew"])


class TestFullValidReadWrite(unittest.TestCase):
    def test_new_apps_brew_exports_all_five_layers(self):
        brew = _ny_brew()
        brew["actuals"] = {"og": 1.053, "fg": 1.011, "volumeL": 22.5, "notes": "Kokte over litt."}
        brew["sensing"] = {"judgment": "yes", "flavorProfile": {"Maltfylde": 5.0}, "notes": "Bedre enn ventet."}
        brew["learning"] = {"whatWorked": "Meskeprofil", "whatChanged": "Mer humle", "nextTime": "Samme oppskrift"}
        brew["status"] = "done"
        brew["brewedAt"] = "2026-03-01T10:00:00+00:00"

        envelope = bygg_kbhbrew_konvolutt(brew, "2026-03-05T00:00:00+00:00")
        payload = envelope["brew"]

        self.assertEqual(payload["status"], "done")
        self.assertEqual(payload["brewedAt"], "2026-03-01T10:00:00+00:00")
        self.assertEqual(payload["actuals"], {"og": 1.053, "fg": 1.011, "volumeL": 22.5, "notes": "Kokte over litt."})
        self.assertEqual(payload["sensing"]["judgment"], "yes")
        self.assertEqual(payload["learning"]["nextTime"], "Samme oppskrift")
        self.assertEqual(payload["snapshot"]["predicted"]["style"], {"stil": "Test IPA", "score": 80})

        # Full round trip: re-parse what was just written.
        reparsed = parse_kbhbrew_json(json.dumps(envelope))
        self.assertEqual(reparsed["actuals"]["og"], 1.053)
        self.assertEqual(reparsed["sensing"]["notes"], "Bedre enn ventet.")
        self.assertEqual(reparsed["learning"]["whatChanged"], "Mer humle")
        self.assertEqual(reparsed["status"], "done")


class TestInvalidFormatVersionRejected(unittest.TestCase):
    def test_invalid_json_rejected(self):
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json("{not valid json")
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_JSON)

    def test_wrong_format_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["format"] = "kbhrecipe"
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_ENVELOPE)

    def test_missing_format_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["format"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_ENVELOPE)

    def test_unsupported_version_rejected(self):
        for bad_version in (0, 2, 1.5, "1", None):
            with self.subTest(version=bad_version):
                doc = copy.deepcopy(_load_fixture("minimal_v1"))
                doc["version"] = bad_version
                with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
                    parse_kbhbrew_json(json.dumps(doc))
                self.assertEqual(ctx.exception.kategori, KATEGORI_UNSUPPORTED_VERSION)

    def test_missing_brew_object_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_ENVELOPE)


class TestRequiredIdentityAndSnapshotRulesEnforced(unittest.TestCase):
    def test_missing_origin_brew_id_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["originBrewId"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_BREW)

    def test_missing_status_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["status"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_BREW)

    def test_invalid_status_value_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["brew"]["status"] = "brewing"
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_BREW)

    def test_missing_created_at_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["createdAt"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_BREW)

    def test_missing_snapshot_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["snapshot"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_SNAPSHOT)

    def test_snapshot_missing_recipe_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["snapshot"]["recipe"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_SNAPSHOT)

    def test_snapshot_missing_predicted_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["snapshot"]["predicted"]
        with self.assertRaises(UgyldigKbhbrewForImport) as ctx:
            parse_kbhbrew_json(json.dumps(doc))
        self.assertEqual(ctx.exception.kategori, KATEGORI_INVALID_SNAPSHOT)

    def test_writer_rejects_brew_without_snapshot(self):
        brew = _ny_brew()
        del brew["snapshot"]
        with self.assertRaises(ValueError):
            brew_to_kbhbrew_payload(brew)

    def test_writer_rejects_invalid_status(self):
        brew = _ny_brew()
        brew["status"] = "brewing"
        with self.assertRaises(ValueError):
            brew_to_kbhbrew_payload(brew)


class TestUnknownFieldPassthroughSurvivesRoundTrip(unittest.TestCase):
    def _round_trip(self, doc):
        native = parse_kbhbrew_json(json.dumps(doc))
        return bygg_kbhbrew_konvolutt(native, "2026-03-06T00:00:00+00:00")

    def test_unknown_envelope_field_survives(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["futureEnvelopeField"] = {"anything": True}
        out = self._round_trip(doc)
        self.assertEqual(out["futureEnvelopeField"], {"anything": True})

    def test_unknown_brew_top_level_field_survives(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["batchNumber"] = "B-2026-014"
        out = self._round_trip(doc)
        self.assertEqual(out["brew"]["batchNumber"], "B-2026-014")

    def test_unknown_snapshot_field_survives(self):
        # The frozen snapshot is copied unfiltered -- proves it round-trips
        # even without a dedicated passthrough container (Section 5.13).
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["snapshot"]["futureSnapshotField"] = {"nested": [1, 2, 3]}
        out = self._round_trip(doc)
        self.assertEqual(out["brew"]["snapshot"]["futureSnapshotField"], {"nested": [1, 2, 3]})

    def test_unknown_actuals_field_survives(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["actuals"]["mashPh"] = 5.4
        out = self._round_trip(doc)
        self.assertEqual(out["brew"]["actuals"]["mashPh"], 5.4)

    def test_unknown_sensing_field_survives(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["sensing"]["aromaNotes"] = "syntetisk"
        out = self._round_trip(doc)
        self.assertEqual(out["brew"]["sensing"]["aromaNotes"], "syntetisk")

    def test_unknown_learning_field_survives(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["learning"]["equipmentNotes"] = "syntetisk"
        out = self._round_trip(doc)
        self.assertEqual(out["brew"]["learning"]["equipmentNotes"], "syntetisk")

    def test_known_fields_always_win_over_stale_passthrough(self):
        native = parse_kbhbrew_json(json.dumps(_load_fixture("full_v1")))
        # Simulate a stale/corrupt passthrough container claiming a value
        # for a field the writer already builds explicitly.
        native["_kbh_brew_passthrough"] = {"status": "discarded", "genuineExtra": "kept"}
        payload = brew_to_kbhbrew_payload(native)
        self.assertEqual(payload["status"], "done")  # native value wins, not the stale passthrough
        self.assertEqual(payload["genuineExtra"], "kept")


class TestForbiddenActualAbvNeverEmitted(unittest.TestCase):
    def test_writer_strips_forbidden_fields_smuggled_via_passthrough(self):
        brew = _ny_brew()
        brew["actuals"] = {
            "og": 1.053, "fg": 1.011,
            "_kbh_brew_actuals_passthrough": {
                "actual_abv": 5.5, "abv": 5.5, "actualAbv": 5.5, "mashPh": 5.4,
            },
        }
        payload = brew_to_kbhbrew_payload(brew)
        self.assertNotIn("actual_abv", payload["actuals"])
        self.assertNotIn("abv", payload["actuals"])
        self.assertNotIn("actualAbv", payload["actuals"])
        self.assertEqual(payload["actuals"]["mashPh"], 5.4)  # genuine unknown field survives

    def test_reader_preserves_but_writer_strips_hand_edited_actual_abv(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["actuals"]["actual_abv"] = 5.5  # a foreign/hand-edited file
        native = parse_kbhbrew_json(json.dumps(doc))
        # Reader preserves it opaquely (read-side round-trip safety)...
        self.assertEqual(native["actuals"]["_kbh_brew_actuals_passthrough"]["actual_abv"], 5.5)
        # ...but a canonical writer must NEVER re-emit it.
        envelope = bygg_kbhbrew_konvolutt(native, "2026-03-07T00:00:00+00:00")
        self.assertNotIn("actual_abv", envelope["brew"]["actuals"])
        raw = json.dumps(envelope)
        self.assertNotIn("actual_abv", raw)
        self.assertNotIn("actualAbv", raw)

    def test_no_new_brew_ever_carries_actual_abv_on_export(self):
        brew = _ny_brew()
        brew["actuals"] = {"og": 1.053, "fg": 1.011}
        envelope = bygg_kbhbrew_konvolutt(brew, "2026-03-08T00:00:00+00:00")
        raw = json.dumps(envelope)
        self.assertNotIn("actual_abv", raw)
        self.assertNotIn("actualAbv", raw)
        # predicted.abv (the PREDICTED value, Section 5.7) legitimately
        # appears on the wire -- only the ACTUALS layer must never carry
        # an abv-shaped key of any spelling.
        self.assertNotIn("abv", envelope["brew"]["actuals"])


class TestNoV1ActualProcessFieldEmitted(unittest.TestCase):
    def test_actuals_never_contains_a_process_field(self):
        brew = _ny_brew()
        brew["actuals"] = {"og": 1.053, "fg": 1.011, "notes": "notat"}
        payload = brew_to_kbhbrew_payload(brew)
        for forbidden in ("processUsed", "process_profile_navn", "process", "actualProcess"):
            self.assertNotIn(forbidden, payload["actuals"])


if __name__ == "__main__":
    unittest.main()
