"""
Core `.kbhbrew` V1 contract tests (issue #22 / PRI 3A.2).

Proves that core/kbhbrew_v1.schema.json actually encodes the ratified
contract in docs/development/CORE_KBHBREW_V1.md:
  - a minimal and a representative full V1 brew both validate;
  - the still-frozen legacy Web `.kbhbrew` fixture
    (tests/fixtures/legacy/web/kbhbrew_v1.json) remains readable against
    the new schema -- required Web backwards-compatibility proof;
  - unknown fields at every relevant layer (envelope, brew, actuals,
    sensing, learning) do not fail validation -- the schema-level half
    of the unknown-field passthrough requirement (Owner decision #2);
  - an unsupported envelope format/version is rejected;
  - the required identity/snapshot rules are enforced;
  - no canonical `actual_abv` or V1 actual-process field was
    introduced (Owner decisions #3/#5).

This is a contract test for the SCHEMA, not a test of
web/js/brew_storage.js's own passthrough implementation -- that is
covered separately in tests/js/test_kbhbrew_contract.js, run with
Node (no Python JS runtime available here, same reasoning already
established for tests/js/test_kbhrecipe_contract.js).

Run with:
    python3 -m unittest tests.test_kbhbrew_schema_contract -b
"""
import copy
import json
import os
import unittest

import jsonschema

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCHEMA_PATH = os.path.join(_ROOT, "core", "kbhbrew_v1.schema.json")
_CORE_FIXTURES = os.path.join(_ROOT, "tests", "fixtures", "core", "kbhbrew")
_LEGACY_WEB_FIXTURE = os.path.join(
    _ROOT, "tests", "fixtures", "legacy", "web", "kbhbrew_v1.json"
)
_CORE_DOC = os.path.join(_ROOT, "docs", "development", "CORE_KBHBREW_V1.md")


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_schema():
    return _load_json(_SCHEMA_PATH)


def _load_fixture(name):
    return _load_json(os.path.join(_CORE_FIXTURES, f"{name}.json"))


class TestSchemaDocumentItself(unittest.TestCase):
    def test_schema_is_a_valid_draft202012_schema(self):
        schema = _load_schema()
        jsonschema.Draft202012Validator.check_schema(schema)

    def test_schema_envelope_pins_format_and_version(self):
        schema = _load_schema()
        self.assertEqual(schema["properties"]["format"]["const"], "kbhbrew")
        self.assertEqual(schema["properties"]["version"]["const"], 1)

    def test_schema_permits_unknown_top_level_envelope_fields(self):
        schema = _load_schema()
        self.assertNotIn("additionalProperties", ["false"])  # sanity
        self.assertTrue(schema.get("additionalProperties", False) is True)

    def test_schema_does_not_define_actual_abv_as_a_canonical_actuals_field(self):
        schema = _load_schema()
        actuals_props = schema["$defs"]["actuals"]["properties"]
        for forbidden in ("abv", "actual_abv", "actualAbv"):
            self.assertNotIn(
                forbidden,
                actuals_props,
                f"{forbidden} must not be a canonical actuals property (Owner decision #3)",
            )
        # additionalProperties stays open for genuine forward-compatible
        # passthrough -- that must not be confused with defining the field.
        self.assertTrue(schema["$defs"]["actuals"].get("additionalProperties") is True)

    def test_schema_does_not_define_a_v1_actual_process_field(self):
        schema = _load_schema()
        actuals_props = schema["$defs"]["actuals"]["properties"]
        for forbidden in ("processUsed", "process_profile_navn", "process", "actualProcess"):
            self.assertNotIn(
                forbidden,
                actuals_props,
                f"{forbidden} must not be a canonical V1 field (Owner decision #5)",
            )

    def test_schema_brew_identity_fields_are_optional_not_required(self):
        # brewId/recipeId are LOCAL identity -- a canonical exported file
        # never carries them (Section 5.3), so the schema must not require
        # either, or the frozen legacy Web fixture (which omits both)
        # would stop validating.
        schema = _load_schema()
        required = schema["$defs"]["brew"]["required"]
        self.assertNotIn("brewId", required)
        self.assertNotIn("recipeId", required)
        self.assertIn("originBrewId", required)

    def test_schema_ingredient_snapshot_is_full_embed_not_a_reference(self):
        # Owner decision #1 (Option A): full embed. A reference-by-id
        # shape would constrain ingredientMap values to an id/version
        # pointer; this schema instead leaves entry values entirely
        # unconstrained objects, matching "the full record, not a
        # hand-picked subset".
        schema = _load_schema()
        ingredient_map = schema["$defs"]["ingredientMap"]
        self.assertEqual(ingredient_map["additionalProperties"]["type"], "object")
        self.assertTrue(ingredient_map["additionalProperties"]["additionalProperties"] is True)


class TestFixturesValidateAgainstSchema(unittest.TestCase):
    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(_load_schema())

    def test_minimal_v1_fixture_validates(self):
        self.validator.validate(_load_fixture("minimal_v1"))

    def test_full_v1_fixture_validates(self):
        self.validator.validate(_load_fixture("full_v1"))

    def test_full_v1_fixture_uses_normative_manifest_provenance_shape(self):
        full = _load_fixture("full_v1")
        datasets = full["brew"]["snapshot"]["provenance"]["datasets"]
        for name in ("malt", "humle", "gjaer"):
            self.assertIn("schema_version", datasets[name])
            self.assertIn("data_version", datasets[name])
            self.assertIn("checksum", datasets[name])

    def test_neither_core_fixture_carries_actual_abv(self):
        for name in ("minimal_v1", "full_v1"):
            raw = json.dumps(_load_fixture(name))
            self.assertNotIn("actual_abv", raw)
            self.assertNotIn("actualAbv", raw)

    def test_legacy_web_kbhbrew_v1_fixture_still_validates(self):
        # Required Web backwards-compatibility proof (issue #22 acceptance
        # criterion 4): today's actual Web export shape -- which has no
        # provenance.datasets, no brewId/recipeId, and only the legacy
        # masterdata entry-count proxy -- must remain readable under the
        # new V1 schema without any change to the frozen fixture itself.
        legacy = _load_json(_LEGACY_WEB_FIXTURE)
        self.validator.validate(legacy)
        self.assertNotIn("datasets", legacy["brew"]["snapshot"]["provenance"])
        self.assertIn("masterdata", legacy["brew"]["snapshot"]["provenance"])


class TestUnknownFieldPassthroughIsSchemaCompatible(unittest.TestCase):
    """Schema-level half of Owner decision #2 (passthrough required in V1):
    an unrecognized field at any of these layers must not, by itself, make
    an otherwise-valid record fail validation. The Web *implementation*
    half (that such fields actually survive read/normalize/write/import/
    export) is covered in tests/js/test_kbhbrew_contract.js.
    """

    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(_load_schema())

    def test_unknown_envelope_field_survives_validation(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["futureEnvelopeField"] = {"anything": True}
        self.validator.validate(doc)

    def test_unknown_brew_top_level_field_survives_validation(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["brew"]["batchNumber"] = "B-2026-014"
        self.validator.validate(doc)

    def test_unknown_snapshot_field_survives_validation(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["snapshot"]["futureSnapshotField"] = {"nested": [1, 2, 3]}
        self.validator.validate(doc)

    def test_unknown_actuals_field_survives_validation(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["actuals"]["mashPh"] = 5.4
        self.validator.validate(doc)

    def test_unknown_sensing_field_survives_validation(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["sensing"]["aromaNotes"] = "syntetisk"
        self.validator.validate(doc)

    def test_unknown_learning_field_survives_validation(self):
        doc = copy.deepcopy(_load_fixture("full_v1"))
        doc["brew"]["learning"]["equipmentNotes"] = "syntetisk"
        self.validator.validate(doc)


class TestEnvelopeRejection(unittest.TestCase):
    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(_load_schema())

    def test_unsupported_format_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["format"] = "kbhrecipe"
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_unsupported_version_is_rejected(self):
        for bad_version in (0, 2, 1.5, "1"):
            with self.subTest(version=bad_version):
                doc = copy.deepcopy(_load_fixture("minimal_v1"))
                doc["version"] = bad_version
                with self.assertRaises(jsonschema.exceptions.ValidationError):
                    self.validator.validate(doc)


class TestRequiredIdentityAndSnapshotRules(unittest.TestCase):
    def setUp(self):
        self.validator = jsonschema.Draft202012Validator(_load_schema())

    def test_missing_origin_brew_id_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["originBrewId"]
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_missing_status_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["status"]
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_invalid_status_value_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["brew"]["status"] = "brewing"
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_missing_created_at_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["createdAt"]
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_missing_snapshot_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["snapshot"]
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_snapshot_missing_recipe_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["snapshot"]["recipe"]
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_snapshot_missing_predicted_is_rejected(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        del doc["brew"]["snapshot"]["predicted"]
        with self.assertRaises(jsonschema.exceptions.ValidationError):
            self.validator.validate(doc)

    def test_parent_brew_id_reserved_field_accepts_null(self):
        doc = copy.deepcopy(_load_fixture("minimal_v1"))
        doc["brew"]["parentBrewId"] = None
        self.validator.validate(doc)


class TestRatificationIsReflectedInTheNormativeDoc(unittest.TestCase):
    """Guards against the schema/fixtures existing while the normative doc
    still reads as an unadopted proposal -- acceptance criterion 1."""

    def setUp(self):
        with open(_CORE_DOC, "r", encoding="utf-8") as f:
            self.doc = f.read()
        self.doc_lines = self.doc.splitlines()

    def test_doc_declares_version_1_0(self):
        # Line-anchored, not a bare substring check: "Status: Active" (etc.)
        # appears elsewhere in the doc as descriptive prose even before
        # ratification (e.g. quoting what the header *would* say), so only
        # the actual header line counts as proof.
        self.assertIn("Version: 1.0", self.doc_lines)

    def test_doc_declares_status_active(self):
        self.assertIn("Status: Active", self.doc_lines)

    def test_doc_no_longer_carries_owner_decision_required_language(self):
        self.assertNotIn("OWNER DECISION REQUIRED", self.doc)

    def test_doc_references_the_schema_file(self):
        self.assertIn("core/kbhbrew_v1.schema.json", self.doc)


if __name__ == "__main__":
    unittest.main()
