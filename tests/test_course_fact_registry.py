"""
Tests for bryggeskole/course_fact_registry.py and the governing contract
docs/development/BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md (Course Fact
Registry V1, issue #89).

All fixtures under tests/fixtures/course_fact_registry/ use clearly
synthetic FACT-TEST-#### ids and example.invalid source references --
none of them are real brewing claims, and none of them are marked
verified as a real claim (the one verified fixture is explicitly
synthetic, see valid_verified_full.json).

Run with:
    python3 -m unittest tests.test_course_fact_registry
"""
import io
import json
import os
import unittest

from bryggeskole.course_fact_registry import (
    CLASSIFICATIONS,
    REGISTRY_SCHEMA_VERSION,
    SOURCE_TIERS,
    STATUSES,
    CourseFactRegistryError,
    read_registry_file,
    validate_registry,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURES = os.path.join(_ROOT, "tests", "fixtures", "course_fact_registry")
_PRODUCTION_REGISTRY = os.path.join(_ROOT, "bryggeskole", "data", "course_fact_registry.json")
_CONTRACT_DOC = os.path.join(_ROOT, "docs", "development", "BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md")


def _fixture_path(name):
    return os.path.join(_FIXTURES, name)


def _load_json(path):
    with io.open(path, encoding="utf-8") as fh:
        return json.load(fh)


class TestValueSetsAreExplicitAndDistinct(unittest.TestCase):
    def test_classification_and_status_are_disjoint(self):
        self.assertEqual(set(CLASSIFICATIONS) & set(STATUSES), set())

    def test_classification_values_exact(self):
        self.assertEqual(
            CLASSIFICATIONS,
            ("documented_fact", "professional_interpretation", "practical_experience", "hypothesis"),
        )

    def test_status_values_exact(self):
        self.assertEqual(STATUSES, ("draft", "reviewed", "verified", "deprecated"))

    def test_source_tier_values_exact(self):
        self.assertEqual(SOURCE_TIERS, ("A", "B", "C", "D"))


class TestValidRecordsPass(unittest.TestCase):
    def test_minimal_valid_draft_record_passes(self):
        data = read_registry_file(_fixture_path("valid_minimal.json"))
        self.assertEqual(len(data["records"]), 1)

    def test_fully_populated_verified_record_passes(self):
        data = read_registry_file(_fixture_path("valid_verified_full.json"))
        record = data["records"][0]
        self.assertEqual(record["status"], "verified")
        self.assertEqual(record["sources"][0]["tier"], "A")


class TestDuplicateIdFailsClosed(unittest.TestCase):
    def test_duplicate_id_rejected(self):
        raw = _load_json(_fixture_path("duplicate_id.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("duplicate id" in e for e in errors))

    def test_read_registry_file_raises(self):
        with self.assertRaises(CourseFactRegistryError):
            read_registry_file(_fixture_path("duplicate_id.json"))


class TestBadIdFailsClosed(unittest.TestCase):
    def test_lowercase_id_rejected(self):
        raw = _load_json(_fixture_path("bad_id.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("invalid id" in e for e in errors))

    def test_ids_are_never_silently_regenerated(self):
        raw = _load_json(_fixture_path("bad_id.json"))
        before = json.dumps(raw, sort_keys=True)
        validate_registry(raw)
        after = json.dumps(raw, sort_keys=True)
        self.assertEqual(before, after)


class TestBadClassificationFailsClosed(unittest.TestCase):
    def test_invalid_classification_rejected(self):
        raw = _load_json(_fixture_path("bad_classification.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("invalid classification" in e for e in errors))


class TestBadStatusFailsClosed(unittest.TestCase):
    def test_invalid_status_rejected(self):
        raw = _load_json(_fixture_path("bad_status.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("invalid status" in e for e in errors))


class TestBadSourceTierFailsClosed(unittest.TestCase):
    def test_invalid_tier_rejected(self):
        raw = _load_json(_fixture_path("bad_tier.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("invalid source tier" in e for e in errors))


class TestVerifiedRequiresSourceAndTimestamp(unittest.TestCase):
    def test_verified_without_source_rejected(self):
        raw = _load_json(_fixture_path("verified_without_source.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("requires at least one source" in e for e in errors))

    def test_verified_without_timestamp_rejected(self):
        raw = _load_json(_fixture_path("verified_without_timestamp.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("requires a valid 'verified_at' timestamp" in e for e in errors))


class TestMalformedReferenceCollectionsFailClosed(unittest.TestCase):
    def test_non_list_concepts_rejected(self):
        raw = _load_json(_fixture_path("malformed_references.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("'concepts' must be a list" in e for e in errors))

    def test_duplicate_module_entry_rejected(self):
        raw = _load_json(_fixture_path("malformed_references.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("duplicate value" in e and "modules" in e for e in errors))


class TestMalformedSourcesFailClosed(unittest.TestCase):
    def test_non_list_sources_rejected(self):
        raw = _load_json(_fixture_path("malformed_sources.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("'sources' must be a list" in e for e in errors))

    def test_source_missing_required_fields_rejected(self):
        raw = _load_json(_fixture_path("malformed_sources.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("missing required source field 'tier'" in e for e in errors))
        self.assertTrue(any("missing required source field 'type'" in e for e in errors))


class TestAiSourceRejected(unittest.TestCase):
    def test_ai_model_name_as_source_type_rejected(self):
        raw = _load_json(_fixture_path("ai_as_source.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("cannot be declared as a source" in e for e in errors))

    def test_various_ai_names_are_all_detected(self):
        from bryggeskole.course_fact_registry import _looks_like_ai_source

        for candidate in ("ChatGPT", "OpenAI", "Claude", "an LLM", "Sóti", "GPT-4", "a large language model"):
            with self.subTest(candidate=candidate):
                self.assertTrue(_looks_like_ai_source(candidate))

    def test_legitimate_source_names_are_not_flagged(self):
        from bryggeskole.course_fact_registry import _looks_like_ai_source

        for candidate in (
            "Palmer, How to Brew (3rd ed.)",
            "White Labs technical datasheet",
            "American Society of Brewing Chemists",
            "r/Homebrewing forum thread (hypothesis-tier)",
        ):
            with self.subTest(candidate=candidate):
                self.assertFalse(_looks_like_ai_source(candidate))


class TestUnknownFieldsFailClosed(unittest.TestCase):
    def test_unknown_record_field_rejected(self):
        raw = _load_json(_fixture_path("unknown_field.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("unknown field(s)" in e and "confidence" in e for e in errors))


class TestMalformedDocumentShapeFailsClosed(unittest.TestCase):
    def test_wrong_schema_version_and_non_list_records_rejected(self):
        raw = _load_json(_fixture_path("invalid_document_shape.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("schema_version" in e for e in errors))
        self.assertTrue(any("'records' must be a list" in e for e in errors))

    def test_top_level_non_object_rejected(self):
        errors = validate_registry(["not", "an", "object"])
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a JSON object", errors[0])

    def test_invalid_json_raises(self):
        with self.assertRaises(CourseFactRegistryError):
            read_registry_file(_fixture_path("invalid_json.json"))


class TestReaderNeverCallsNetwork(unittest.TestCase):
    def test_module_has_no_network_imports(self):
        module_path = os.path.join(_ROOT, "bryggeskole", "course_fact_registry.py")
        with io.open(module_path, encoding="utf-8") as fh:
            source = fh.read()
        for forbidden in ("urllib", "requests", "socket", "http.client"):
            self.assertNotIn(forbidden, source)


class TestProductionRegistryFileIsValidAndHasNoRealVerifiedClaims(unittest.TestCase):
    def test_production_registry_parses_and_validates(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        self.assertEqual(data["schema_version"], REGISTRY_SCHEMA_VERSION)
        self.assertIsInstance(data["records"], list)

    def test_production_registry_has_zero_verified_records(self):
        # V2-2A deliverable preference: zero real verified claims
        # introduced by this foundation round.
        data = read_registry_file(_PRODUCTION_REGISTRY)
        verified = [r for r in data["records"] if r.get("status") == "verified"]
        self.assertEqual(verified, [])


class TestContractDocExistsAndIsInternallyConsistent(unittest.TestCase):
    def test_contract_doc_exists(self):
        self.assertTrue(os.path.exists(_CONTRACT_DOC))

    def test_contract_doc_states_ai_is_never_a_source(self):
        with io.open(_CONTRACT_DOC, encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("never", text.lower())
        self.assertIn("AI", text)

    def test_contract_doc_lists_all_classification_values(self):
        with io.open(_CONTRACT_DOC, encoding="utf-8") as fh:
            text = fh.read()
        for value in CLASSIFICATIONS:
            self.assertIn(value, text)

    def test_contract_doc_lists_all_status_values(self):
        with io.open(_CONTRACT_DOC, encoding="utf-8") as fh:
            text = fh.read()
        for value in STATUSES:
            self.assertIn(value, text)

    def test_contract_doc_lists_all_source_tiers(self):
        with io.open(_CONTRACT_DOC, encoding="utf-8") as fh:
            text = fh.read()
        for value in SOURCE_TIERS:
            self.assertIn(f"**{value}**", text)


if __name__ == "__main__":
    unittest.main()
