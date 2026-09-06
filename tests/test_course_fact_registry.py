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
    find_verified_records,
    get_verified_record,
    read_registry_file,
    read_verified_records,
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

    def test_verified_with_source_metadata_but_no_ref_rejected(self):
        # tier/type alone describe what KIND of source is claimed, not
        # WHICH source it is -- this must not pass as provenance.
        raw = _load_json(_fixture_path("verified_without_ref.json"))
        errors = validate_registry(raw)
        self.assertTrue(any("concrete, non-empty 'ref'" in e for e in errors))

    def test_verified_with_real_ref_passes(self):
        data = read_registry_file(_fixture_path("valid_verified_full.json"))
        record = data["records"][0]
        self.assertTrue(record["sources"][0]["ref"])


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


class TestReadVerifiedRecordsReturnsOnlyVerified(unittest.TestCase):
    _PATH = _fixture_path("verified_consumer_mixed.json")

    def test_returns_only_verified_status(self):
        records = read_verified_records(self._PATH)
        self.assertEqual({r["status"] for r in records}, {"verified"})

    def test_draft_reviewed_deprecated_are_excluded(self):
        ids = {r["id"] for r in read_verified_records(self._PATH)}
        self.assertNotIn("FACT-TEST-0023", ids)  # draft
        self.assertNotIn("FACT-TEST-0025", ids)  # deprecated
        self.assertNotIn("FACT-TEST-0026", ids)  # reviewed

    def test_ordering_is_canonical_id_order_independent_of_source_array_order(self):
        ids = [r["id"] for r in read_verified_records(self._PATH)]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(
            ids,
            ["FACT-TEST-0020", "FACT-TEST-0021", "FACT-TEST-0022", "FACT-TEST-0024"],
        )

    def test_full_source_provenance_is_preserved(self):
        records = read_verified_records(self._PATH)
        record = next(r for r in records if r["id"] == "FACT-TEST-0020")
        self.assertEqual(record["sources"][0]["ref"], "https://example.invalid/consumer-0020")
        self.assertEqual(record["sources"][0]["tier"], "A")

    def test_empty_production_registry_returns_zero_verified_records(self):
        self.assertEqual(read_verified_records(_PRODUCTION_REGISTRY), [])

    def test_malformed_registry_fails_closed_before_filtering(self):
        with self.assertRaises(CourseFactRegistryError):
            read_verified_records(_fixture_path("duplicate_id.json"))


class TestGetVerifiedRecordLookup(unittest.TestCase):
    _PATH = _fixture_path("verified_consumer_mixed.json")

    def test_verified_id_is_returned(self):
        record = get_verified_record(self._PATH, "FACT-TEST-0020")
        self.assertIsNotNone(record)
        self.assertEqual(record["status"], "verified")

    def test_missing_id_returns_none(self):
        self.assertIsNone(get_verified_record(self._PATH, "FACT-TEST-9999"))

    def test_draft_id_returns_none_not_the_raw_record(self):
        # FACT-TEST-0023 exists in the registry as a draft record -- the
        # trusted lookup must never distinguish this from "id does not
        # exist" and must never leak it as if it were safe/verified.
        self.assertIsNone(get_verified_record(self._PATH, "FACT-TEST-0023"))

    def test_deprecated_id_returns_none(self):
        self.assertIsNone(get_verified_record(self._PATH, "FACT-TEST-0025"))

    def test_reviewed_id_returns_none(self):
        self.assertIsNone(get_verified_record(self._PATH, "FACT-TEST-0026"))

    def test_malformed_registry_fails_closed(self):
        with self.assertRaises(CourseFactRegistryError):
            get_verified_record(_fixture_path("invalid_document_shape.json"), "FACT-TEST-0001")


class TestFindVerifiedRecordsFiltering(unittest.TestCase):
    _PATH = _fixture_path("verified_consumer_mixed.json")

    def test_no_filter_returns_all_verified_in_canonical_order(self):
        ids = [r["id"] for r in find_verified_records(self._PATH)]
        self.assertEqual(
            ids,
            ["FACT-TEST-0020", "FACT-TEST-0021", "FACT-TEST-0022", "FACT-TEST-0024"],
        )

    def test_concept_filter_excludes_non_matching_and_unverified(self):
        ids = {r["id"] for r in find_verified_records(self._PATH, concept="c.a")}
        self.assertEqual(ids, {"FACT-TEST-0020", "FACT-TEST-0021"})

    def test_module_filter_excludes_non_matching_and_unverified(self):
        ids = {r["id"] for r in find_verified_records(self._PATH, module="m.a")}
        self.assertEqual(ids, {"FACT-TEST-0020", "FACT-TEST-0022"})

    def test_combined_concept_and_module_is_and_semantics(self):
        ids = [r["id"] for r in find_verified_records(self._PATH, concept="c.a", module="m.a")]
        self.assertEqual(ids, ["FACT-TEST-0020"])

    def test_concept_with_zero_verified_matches_returns_empty_list(self):
        self.assertEqual(find_verified_records(self._PATH, concept="no-such-concept"), [])

    def test_module_with_zero_verified_matches_returns_empty_list(self):
        self.assertEqual(find_verified_records(self._PATH, module="no-such-module"), [])

    def test_malformed_registry_fails_closed_before_filtering(self):
        with self.assertRaises(CourseFactRegistryError):
            find_verified_records(_fixture_path("duplicate_id.json"), concept="anything")


class TestTrustedApiNeverLeaksSharedMutableState(unittest.TestCase):
    _PATH = _fixture_path("verified_consumer_mixed.json")

    def test_mutating_a_looked_up_record_does_not_affect_the_next_lookup(self):
        record = get_verified_record(self._PATH, "FACT-TEST-0020")
        record["claim"] = "MUTATED BY CALLER"
        record["sources"][0]["ref"] = "MUTATED"
        fresh = get_verified_record(self._PATH, "FACT-TEST-0020")
        self.assertNotEqual(fresh["claim"], "MUTATED BY CALLER")
        self.assertNotEqual(fresh["sources"][0]["ref"], "MUTATED")

    def test_mutating_one_result_does_not_affect_a_later_read(self):
        records = read_verified_records(self._PATH)
        records[0]["concepts"] = ["mutated"]
        fresh = read_verified_records(self._PATH)
        self.assertNotEqual(fresh[0].get("concepts"), ["mutated"])


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

    def test_contract_doc_documents_the_verified_only_consumer_api(self):
        with io.open(_CONTRACT_DOC, encoding="utf-8") as fh:
            text = fh.read()
        for name in ("read_verified_records", "get_verified_record", "find_verified_records"):
            self.assertIn(name, text)


if __name__ == "__main__":
    unittest.main()
