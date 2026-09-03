"""
Core custom-ingredient identity V1 contract tests (issue #38 / PRI 4A).

Proves that core/ingredient_identity_v1.schema.json actually encodes the
contract in docs/development/CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md:
  - the new kbh-custom-<uuidv4> format (Section 3) is recognized, and
    malformed variants are rejected;
  - all three grandfathered legacy custom-ID shapes (Section 9) are
    recognized;
  - real canonical master IDs (data/master_malt.json, master_humle_v2.json,
    master_gjaer_v2.json) match the canonical pattern and never match the
    custom-ID union -- the Section 8 disjoint-alphabet invariant, checked
    against actual data, not just examples;
  - no reserved prefix (Section 9's table) can ever be a valid canonical
    master ID.

Run with:
    python3 -m unittest tests.test_core_ingredient_identity_schema -b
"""
import json
import os
import unittest

import jsonschema

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SCHEMA_PATH = os.path.join(_ROOT, "core", "ingredient_identity_v1.schema.json")
_CORE_DOC = os.path.join(
    _ROOT, "docs", "development", "CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md"
)
_MASTER_DATA_FILES = [
    os.path.join(_ROOT, "data", "master_malt.json"),
    os.path.join(_ROOT, "data", "master_humle_v2.json"),
    os.path.join(_ROOT, "data", "master_gjaer_v2.json"),
]


def _load_json(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_schema():
    return _load_json(_SCHEMA_PATH)


def _def_validator(def_name):
    schema = _load_schema()
    ref_schema = {"$defs": schema["$defs"], "$ref": f"#/$defs/{def_name}"}
    return jsonschema.Draft202012Validator(ref_schema)


def _matches(def_name, value):
    return _def_validator(def_name).is_valid(value)


class TestSchemaDocumentItself(unittest.TestCase):
    def test_schema_is_a_valid_draft202012_schema(self):
        schema = _load_schema()
        jsonschema.Draft202012Validator.check_schema(schema)

    def test_all_expected_defs_present(self):
        schema = _load_schema()
        for name in (
            "kbhCustomIngredientId",
            "legacyAppCustomIngredientId",
            "legacyWebCustomIngredientId",
            "legacyCustomIngredientId",
            "customIngredientId",
            "canonicalMasterIngredientId",
        ):
            self.assertIn(name, schema["$defs"])


class TestNewKbhCustomFormat(unittest.TestCase):
    def test_valid_kbh_custom_id_matches(self):
        valid = "kbh-custom-3fa85f64-5717-4562-b3fc-2c963f66afa6"
        self.assertTrue(_matches("kbhCustomIngredientId", valid))
        self.assertTrue(_matches("customIngredientId", valid))

    def test_uppercase_is_rejected(self):
        self.assertFalse(
            _matches(
                "kbhCustomIngredientId",
                "kbh-custom-3FA85F64-5717-4562-B3FC-2C963F66AFA6",
            )
        )

    def test_wrong_uuid_version_nibble_is_rejected(self):
        # version nibble must be "4" per Section 3's pattern.
        self.assertFalse(
            _matches(
                "kbhCustomIngredientId",
                "kbh-custom-3fa85f64-5717-1562-b3fc-2c963f66afa6",
            )
        )

    def test_missing_prefix_is_rejected(self):
        self.assertFalse(
            _matches("kbhCustomIngredientId", "3fa85f64-5717-4562-b3fc-2c963f66afa6")
        )

    def test_malformed_uuid_remainder_is_rejected(self):
        self.assertFalse(_matches("kbhCustomIngredientId", "kbh-custom-not-a-uuid"))


class TestGrandfatheredLegacyShapes(unittest.TestCase):
    """Exact example shapes captured live in the PRI 4A research (issue #38)."""

    def test_app_custom_underscore_hex_id(self):
        example = "custom_1a2b3c4d5e6f"
        self.assertTrue(_matches("legacyAppCustomIngredientId", example))
        self.assertTrue(_matches("legacyCustomIngredientId", example))
        self.assertTrue(_matches("customIngredientId", example))

    def test_web_recipe_level_egen_malt_id(self):
        example = "egen_malt_1700000000000_1"
        self.assertTrue(_matches("legacyWebCustomIngredientId", example))
        self.assertTrue(_matches("customIngredientId", example))

    def test_web_recipe_level_egen_humle_id(self):
        self.assertTrue(
            _matches("legacyWebCustomIngredientId", "egen_humle_1700000000000_2")
        )

    def test_web_pantry_level_egen_pantry_id_current_shape(self):
        example = "egen_pantry_humle-3fa85f64-5717-4562-b3fc-2c963f66afa6"
        self.assertTrue(_matches("legacyWebCustomIngredientId", example))

    def test_web_pantry_level_egen_pantry_id_frozen_fixture_shape(self):
        # tests/fixtures/legacy/web/pantry_store_v1.json:14 -- historical
        # underscore/timestamp shape, distinct from the current hyphen/UUID
        # generator; both must remain recognized as custom (Section 9).
        example = "egen_pantry_humle_1700000000000_1"
        self.assertTrue(_matches("legacyWebCustomIngredientId", example))


class TestLegacyGrandfatheringIsBroadButBoundsTheBarePrefix(unittest.TestCase):
    """Section 9's normative choice: broad prefix-family grandfathering
    (any positive-length suffix), not an exact historical generator
    shape -- but a bare prefix with no suffix at all is malformed, not a
    wildcard match."""

    def test_bare_custom_prefix_is_rejected(self):
        self.assertFalse(_matches("legacyAppCustomIngredientId", "custom_"))
        self.assertFalse(_matches("customIngredientId", "custom_"))

    def test_bare_egen_prefix_is_rejected(self):
        self.assertFalse(_matches("legacyWebCustomIngredientId", "egen_"))
        self.assertFalse(_matches("customIngredientId", "egen_"))

    def test_custom_suffix_shorter_than_todays_generator_is_still_accepted(self):
        # Today's App generator always emits 12 hex chars
        # (modules/pantry.py:296), but Section 9 grandfathers any
        # positive hex length, not only that one length.
        self.assertTrue(_matches("legacyAppCustomIngredientId", "custom_a"))

    def test_custom_suffix_longer_than_todays_generator_is_still_accepted(self):
        self.assertTrue(
            _matches("legacyAppCustomIngredientId", "custom_" + "a1b2c3" * 10)
        )

    def test_custom_suffix_with_non_hex_characters_is_rejected(self):
        # The App generator only ever emits lowercase hex
        # (uuid.uuid4().hex); a non-hex suffix does not match the
        # grandfathered App shape.
        self.assertFalse(_matches("legacyAppCustomIngredientId", "custom_zzzz"))
        self.assertFalse(_matches("legacyAppCustomIngredientId", "custom_ABCD"))

    def test_egen_suffix_of_any_content_is_accepted(self):
        # Web's egen_ family has produced more than one exact historical
        # suffix shape (hyphenated UUID vs. underscore/timestamp) -- the
        # contract grandfathers the family, not one exact shape.
        self.assertTrue(_matches("legacyWebCustomIngredientId", "egen_x"))
        self.assertTrue(
            _matches("legacyWebCustomIngredientId", "egen_pantry_humle-anything")
        )


class TestCanonicalMasterIdsAgainstRealData(unittest.TestCase):
    def test_every_real_canonical_id_matches_canonical_pattern(self):
        for path in _MASTER_DATA_FILES:
            data = _load_json(path)
            self.assertTrue(data, f"{path} unexpectedly empty")
            for ingredient_id in data.keys():
                with self.subTest(file=os.path.basename(path), id=ingredient_id):
                    self.assertTrue(
                        _matches("canonicalMasterIngredientId", ingredient_id)
                    )
                    self.assertFalse(_matches("customIngredientId", ingredient_id))

    def test_reserved_prefixes_can_never_be_canonical(self):
        for candidate in (
            "kbh-custom-3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "custom_1a2b3c4d5e6f",
            "egen_malt_1700000000000_1",
        ):
            self.assertFalse(_matches("canonicalMasterIngredientId", candidate))


class TestDocCrossReference(unittest.TestCase):
    def test_contract_doc_references_this_schema(self):
        with open(_CORE_DOC, "r", encoding="utf-8") as f:
            doc = f.read()
        self.assertIn("core/ingredient_identity_v1.schema.json", doc)

    def test_schema_references_the_contract_doc(self):
        schema = _load_schema()
        self.assertIn(
            "CORE_CUSTOM_INGREDIENT_IDENTITY_V1.md", schema["description"]
        )


if __name__ == "__main__":
    unittest.main()
