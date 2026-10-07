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
import datetime
import io
import json
import os
import re
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


_PRODUCTION_VERIFIED_IDS = ["FACT-BREW-0001", "FACT-BREW-0002", "FACT-BREW-0003"]
_MASHING_VERIFIED_IDS = ["FACT-MASH-0001", "FACT-MASH-0002", "FACT-MASH-0004"]
_BOIL_HOP_VERIFIED_IDS = [
    "FACT-BOIL-0001", "FACT-BOIL-0002", "FACT-BOIL-0003", "FACT-BOIL-0004",
    "FACT-HOP-0001", "FACT-HOP-0002", "FACT-HOP-0003",
]
_COOL_TRANSFER_VERIFIED_IDS = [
    "FACT-COOL-0001", "FACT-COOL-0002", "FACT-COOL-0003",
    "FACT-OXY-0001", "FACT-OXY-0002", "FACT-OXY-0003",
    "FACT-TRANSFER-0001",
]
_PACKAGE_VERIFIED_IDS = [
    "FACT-PACK-0001", "FACT-PACK-0002", "FACT-PACK-0003", "FACT-PACK-0004",
]
_METHOD_CONTEXT_VERIFIED_IDS = [
    "FACT-METHOD-0001", "FACT-METHOD-0002", "FACT-METHOD-0003", "FACT-METHOD-0004", "FACT-METHOD-0005",
]
_MALT_CORE_VERIFIED_IDS = ["FACT-MALT-0001", "FACT-MALT-0002", "FACT-MALT-0003", "FACT-MALT-0004"]
_YEAST_CORE_VERIFIED_IDS = [f"FACT-YEAST-000{n}" for n in range(1, 6)]
_WATER_FOUNDATION_VERIFIED_IDS = ["FACT-WATER-0001", "FACT-WATER-0002", "FACT-WATER-0003"]
_HOP_CORE_VERIFIED_IDS = ["FACT-HOP-0004", "FACT-HOP-0005"]
_RECIPE_VERIFIED_IDS = ["FACT-RECIPE-0001", "FACT-RECIPE-0002", "FACT-RECIPE-0003"]
_MEASUREMENT_VERIFIED_IDS = ["FACT-MEAS-0001", "FACT-MEAS-0002", "FACT-MEAS-0003"]
_MEASUREMENT_KOMPETENT_VERIFIED_IDS = ["FACT-MEAS-0004", "FACT-MEAS-0005"]
_MEASUREMENT_INSTRUMENT_CHECK_VERIFIED_IDS = ["FACT-MEAS-0006"]
_FERMENTATION_KOMPETENT_VERIFIED_IDS = ["FACT-BREW-0004", "FACT-BREW-0005"]
_SAFETY_VERIFIED_IDS = ["FACT-SAFE-0001", "FACT-SAFE-0002", "FACT-SAFE-0003"]
_SENSORY_VERIFIED_IDS = ["FACT-SENSORY-0001", "FACT-SENSORY-0002", "FACT-SENSORY-0003"]
_ALL_PRODUCTION_VERIFIED_IDS = sorted(
    _PRODUCTION_VERIFIED_IDS + _MASHING_VERIFIED_IDS + _BOIL_HOP_VERIFIED_IDS
    + _COOL_TRANSFER_VERIFIED_IDS + _PACKAGE_VERIFIED_IDS + _METHOD_CONTEXT_VERIFIED_IDS
    + _MALT_CORE_VERIFIED_IDS + _YEAST_CORE_VERIFIED_IDS + _WATER_FOUNDATION_VERIFIED_IDS
    + _HOP_CORE_VERIFIED_IDS + _RECIPE_VERIFIED_IDS + _MEASUREMENT_VERIFIED_IDS
    + _MEASUREMENT_KOMPETENT_VERIFIED_IDS + _MEASUREMENT_INSTRUMENT_CHECK_VERIFIED_IDS
    + _SAFETY_VERIFIED_IDS + _SENSORY_VERIFIED_IDS + _FERMENTATION_KOMPETENT_VERIFIED_IDS
)


class TestProductionRegistryFileIsValidAndHasNoRealVerifiedClaims(unittest.TestCase):
    def test_production_registry_parses_and_validates(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        self.assertEqual(data["schema_version"], REGISTRY_SCHEMA_VERSION)
        self.assertIsInstance(data["records"], list)

    def test_production_registry_has_exactly_the_v2_2c_v337_366_370_374_and_380_verified_records(self):
        # V2-2C (issue #93): the first source-backed fermentation fact
        # pack. Issue #337 adds the second, mash-fundamentals fact pack.
        # Issue #366 adds the third, boil/hop-fundamentals fact pack
        # (FACT-BOIL-0001..0004, FACT-HOP-0001..0003). Issue #370 adds the
        # fourth, cool/transfer-fundamentals fact pack (FACT-COOL-0001..0003,
        # FACT-OXY-0001..0003, FACT-TRANSFER-0001). Issue #374 adds the
        # fifth, package-fundamentals fact pack (FACT-PACK-0001..0004),
        # per docs/development/v22_g3f_package_module_contract.md. Issue
        # #380 adds the sixth, method-context-fundamentals fact pack
        # (FACT-METHOD-0001..0005), per
        # docs/development/v22_g3h_prepare_method_module_contract.md.
        # FACT-MASH-0003 (iodine test) is deliberately NOT among these --
        # it was left at status `draft`, pending an independent second
        # source, per issue #337's own weaken-rather-than-force rule.
        data = read_registry_file(_PRODUCTION_REGISTRY)
        verified = [r for r in data["records"] if r.get("status") == "verified"]
        self.assertEqual({r["id"] for r in verified}, set(_ALL_PRODUCTION_VERIFIED_IDS))
        self.assertEqual(len(verified), len(_ALL_PRODUCTION_VERIFIED_IDS))

    def test_fact_mash_0003_exists_as_draft_not_verified(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        record = next(r for r in data["records"] if r["id"] == "FACT-MASH-0003")
        self.assertEqual(record["status"], "draft")

    def test_production_registry_classification_mix_is_exactly_23_documented_8_interpretation_2_practical(self):
        # Issue #370 (V2.2 G3E) added the fourth fact pack -- cool/transfer
        # fundamentals (FACT-COOL-0001..0003, FACT-OXY-0001..0003,
        # FACT-TRANSFER-0001): 5 documented_fact, 1 professional_interpretation
        # (FACT-OXY-0003), 1 practical_experience (FACT-TRANSFER-0001).
        # Issue #374 (V2.2 G3G) adds the fifth fact pack -- package
        # fundamentals (FACT-PACK-0001..0004): 3 documented_fact
        # (FACT-PACK-0001..0003), 1 professional_interpretation
        # (FACT-PACK-0004). Issue #380 (V2.2 G3I) adds the sixth fact pack
        # -- method-context fundamentals (FACT-METHOD-0001..0005): 3
        # documented_fact (FACT-METHOD-0001..0003), 2
        # professional_interpretation (FACT-METHOD-0004..0005). Issue #426
        # (V2.2 G3P-1) adds the malt-core pack (FACT-MALT-0001..0004): 3
        # documented_fact (FACT-MALT-0001..0003), 1
        # professional_interpretation (FACT-MALT-0004). Issue #428 (V2.2
        # G3P-2) adds the yeast-core pack (FACT-YEAST-0001..0005): 3
        # documented_fact (0001..0003), 2 professional_interpretation
        # (0004..0005).
        data = read_registry_file(_PRODUCTION_REGISTRY)
        verified = [r for r in data["records"] if r.get("status") == "verified"]
        classifications = [r["classification"] for r in verified]
        # Issue #430 (V2.2 G3P-3) adds the water-foundation pack
        # (FACT-WATER-0001..0003): 2 documented_fact (0001..0002), 1
        # professional_interpretation (0003).
        # Issue #440 (V2.2 G3P-4) adds the hops-core pack (FACT-HOP-0004,
        # FACT-HOP-0005): 2 documented_fact.
        # Issue #441 (V2.2 Goal 3 R-2) adds FACT-RECIPE-0001: 1
        # documented_fact.
        # Issue #442 (V2.2 Goal 3 R-1) adds FACT-RECIPE-0002: 1
        # documented_fact.
        # Issue #443 (V2.2 Goal 3 R-4) adds FACT-RECIPE-0003: 1
        # professional_interpretation.
        # Issue #444 (V2.2 Goal 3 Maaling M1/M2/M4) adds FACT-MEAS-0001..0003:
        # 3 documented_fact.
        # Issue #445 (V2.2 Goal 3 Maaling Kompetent M3/M6) adds
        # FACT-MEAS-0004..0005: 2 documented_fact.
        # Issue #447 (V2.2 Goal 3 Rengjoring/sikkerhet N1/N2/N3) adds
        # FACT-SAFE-0001..0003: 3 documented_fact.
        # Issue #466 (V2.2 Goal 3 Sensory S-1) adds FACT-SENSORY-0001: 1
        # documented_fact.
        # Issue #467 (V2.2 Goal 3 Sensory S-4) adds FACT-SENSORY-0002: 1
        # documented_fact.
        # Issue #470 (V2.2 Goal 3 Sensory S-2) adds FACT-SENSORY-0003: 1
        # documented_fact.
        # Gjæring Kompetent G1/G2 (offline, Chief live source spot-check
        # 2026-10-05; no GitHub issue yet) adds FACT-BREW-0004..0005: 2
        # documented_fact.
        self.assertEqual(classifications.count("documented_fact"), 45)
        # Measurement M7 (offline, Chief live source spot-check 2026-10-05;
        # no GitHub issue yet) adds FACT-MEAS-0006: 1
        # professional_interpretation.
        self.assertEqual(classifications.count("professional_interpretation"), 13)
        self.assertEqual(classifications.count("practical_experience"), 2)

    def test_fact_brew_0003_is_professional_interpretation_not_documented_fact(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        record = next(r for r in data["records"] if r["id"] == "FACT-BREW-0003")
        self.assertEqual(record["classification"], "professional_interpretation")
        self.assertEqual(record["status"], "verified")

    def test_fact_mash_0004_is_professional_interpretation_not_documented_fact(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        record = next(r for r in data["records"] if r["id"] == "FACT-MASH-0004")
        self.assertEqual(record["classification"], "professional_interpretation")
        self.assertEqual(record["status"], "verified")


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

    def test_malformed_registry_fails_closed_before_filtering(self):
        with self.assertRaises(CourseFactRegistryError):
            read_verified_records(_fixture_path("duplicate_id.json"))


class TestProductionRegistryVerifiedOnlyApi(unittest.TestCase):
    """V2-2C (issue #93): the trusted, verified-only consumer API against
    the real production registry, now that it carries its first
    source-backed fermentation fact pack (FACT-BREW-0001..0003)."""

    def test_returns_exactly_the_v2_2c_and_v337_ids_in_canonical_order(self):
        ids = [r["id"] for r in read_verified_records(_PRODUCTION_REGISTRY)]
        self.assertEqual(ids, sorted(_ALL_PRODUCTION_VERIFIED_IDS))
        self.assertEqual(ids, _ALL_PRODUCTION_VERIFIED_IDS)

    def test_ordering_is_deterministic_across_repeated_reads(self):
        first = [r["id"] for r in read_verified_records(_PRODUCTION_REGISTRY)]
        second = [r["id"] for r in read_verified_records(_PRODUCTION_REGISTRY)]
        self.assertEqual(first, second)

    def test_concept_filter_fermentation_temperature_returns_all_three(self):
        ids = {r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept="fermentation.temperature")}
        self.assertEqual(ids, set(_PRODUCTION_VERIFIED_IDS))

    def test_module_filter_fermentation_fundamentals_returns_all_three(self):
        ids = {r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, module="fermentation.fundamentals")}
        self.assertEqual(ids, set(_PRODUCTION_VERIFIED_IDS))

    def test_provenance_and_source_refs_survive_trusted_reads(self):
        expected_refs = {
            "FACT-BREW-0001": {
                "https://blog.whitelabs.com/fermentation-controls-temperature",
                "https://fermentis.com/en/news/fermentation/what-are-the-best-5-ways-to-improve-fermentation/",
            },
            "FACT-BREW-0002": {
                "https://blog.whitelabs.com/fermentation-controls-temperature",
                "https://fermentis.com/en/news/fermentation/rediscover-saflager-w-34-70/",
            },
            "FACT-BREW-0003": {
                "https://blog.whitelabs.com/fermentation-controls-temperature",
                "https://fermentis.com/en/news/fermentation/what-are-the-best-5-ways-to-improve-fermentation/",
                "https://fermentis.com/en/news/fermentation/rediscover-saflager-w-34-70/",
            },
        }
        for record in read_verified_records(_PRODUCTION_REGISTRY):
            if record["id"] not in expected_refs:
                continue  # covered by TestProductionRegistryMashingFactPackVerifiedOnlyApi instead.
            refs = {s["ref"] for s in record["sources"]}
            self.assertEqual(refs, expected_refs[record["id"]])
            self.assertTrue(all(s["tier"] == "A" for s in record["sources"]))

    def test_get_verified_record_returns_each_of_the_three(self):
        for fact_id in _PRODUCTION_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertIsNotNone(record)
            self.assertEqual(record["status"], "verified")


class TestProductionRegistryMashingFactPackVerifiedOnlyApi(unittest.TestCase):
    """Issue #337: the second source-backed fact pack, mash fundamentals
    (FACT-MASH-0001, FACT-MASH-0002, FACT-MASH-0004 -- FACT-MASH-0003
    stays `draft`, see TestProductionRegistryFileIsValidAndHasNoRealVerifiedClaims)."""

    def test_returns_exactly_the_three_mashing_ids(self):
        ids = {r["id"] for r in read_verified_records(_PRODUCTION_REGISTRY) if r["id"].startswith("FACT-MASH-")}
        self.assertEqual(ids, set(_MASHING_VERIFIED_IDS))

    def test_concept_filter_mashing_temperature_returns_expected_two(self):
        ids = {r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept="mashing.temperature")}
        self.assertEqual(ids, {"FACT-MASH-0002", "FACT-MASH-0004"})

    def test_module_filter_mashing_fundamentals_returns_all_three(self):
        ids = {r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, module="mashing.fundamentals")}
        self.assertEqual(ids, set(_MASHING_VERIFIED_IDS))

    def test_provenance_and_source_refs_survive_trusted_reads(self):
        expected = {
            "FACT-MASH-0001": {
                "Briess Technical Services (Bies, D. & Roberts, C., 2013), 'Understanding a Malt Analysis'": "A",
                "The Oxford Companion to Beer (Garrett Oliver, ed., 2011), entry 'alpha amylase'": "B",
            },
            "FACT-MASH-0002": {
                "R. Muller (1991), 'The effects of mashing temperature and mash thickness on wort carbohydrate composition', Journal of the Institute of Brewing 97(2):85-92, DOI 10.1002/j.2050-0416.1991.tb01055.x": "A",
            },
            "FACT-MASH-0004": {
                "R. Muller (1991), 'The effects of mashing temperature and mash thickness on wort carbohydrate composition', Journal of the Institute of Brewing 97(2):85-92, DOI 10.1002/j.2050-0416.1991.tb01055.x": "A",
                "Briess Technical Services (Bies, D. & Roberts, C., 2013), 'Understanding a Malt Analysis'": "A",
            },
        }
        for record in read_verified_records(_PRODUCTION_REGISTRY):
            if record["id"] not in expected:
                continue  # covered by TestProductionRegistryVerifiedOnlyApi instead.
            actual = {s["ref"]: s["tier"] for s in record["sources"]}
            self.assertEqual(actual, expected[record["id"]])

    def test_get_verified_record_returns_each_of_the_three(self):
        for fact_id in _MASHING_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertIsNotNone(record)
            self.assertEqual(record["status"], "verified")

    def test_get_verified_record_returns_none_for_the_unpromoted_iodine_claim(self):
        # FACT-MASH-0003 exists in the registry but is still `draft` --
        # the trusted lookup must never distinguish this from "id does
        # not exist" and must never leak it as if it were verified.
        self.assertIsNone(get_verified_record(_PRODUCTION_REGISTRY, "FACT-MASH-0003"))


class TestProductionRegistryBoilHopFactPackVerifiedOnlyApi(unittest.TestCase):
    """Issue #366: the third source-backed fact pack, boil/hop fundamentals
    (FACT-BOIL-0001..0004, FACT-HOP-0001..0003)."""

    def test_returns_exactly_the_seven_boil_hop_ids_plus_the_two_hop_core_ids(self):
        # Issue #440 adds FACT-HOP-0004/0005 (no `modules`, so the module
        # filter below still returns exactly the original seven).
        ids = {
            r["id"] for r in read_verified_records(_PRODUCTION_REGISTRY)
            if r["id"].startswith("FACT-BOIL-") or r["id"].startswith("FACT-HOP-")
        }
        self.assertEqual(ids, set(_BOIL_HOP_VERIFIED_IDS) | set(_HOP_CORE_VERIFIED_IDS))

    def test_module_filter_boil_hop_fundamentals_returns_all_seven(self):
        ids = {r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, module="boil_hop.fundamentals")}
        self.assertEqual(ids, set(_BOIL_HOP_VERIFIED_IDS))

    def test_concept_filter_whirlpool_technique_returns_the_two_hop_facts(self):
        ids = {r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept="hop.whirlpool_technique")}
        self.assertEqual(ids, {"FACT-HOP-0001", "FACT-HOP-0002"})

    def test_get_verified_record_returns_each_of_the_seven(self):
        for fact_id in _BOIL_HOP_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertIsNotNone(record)
            self.assertEqual(record["status"], "verified")

    def test_every_boil_hop_record_carries_a_concrete_source_ref(self):
        for fact_id in _BOIL_HOP_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertTrue(record["sources"])
            self.assertTrue(any(s.get("ref") for s in record["sources"]))


class TestProductionRegistryHopCoreFactPackVerifiedOnlyApi(unittest.TestCase):
    """Issue #440 (V2.2 G3P-4): the Raavarer P4 hops-core fact pack
    (FACT-HOP-0004, FACT-HOP-0005). HOP-0001..0003 are reused, not changed."""

    _CONCEPTS = {"FACT-HOP-0005": "hop.alpha_vs_ibu", "FACT-HOP-0004": "hop.ageing_storage"}

    def _records(self):
        return {r["id"]: r for r in read_verified_records(_PRODUCTION_REGISTRY) if r["id"] in _HOP_CORE_VERIFIED_IDS}

    def test_returns_exactly_the_two_hop_core_ids(self):
        self.assertEqual(set(self._records()), set(_HOP_CORE_VERIFIED_IDS))

    def test_each_concept_maps_to_exactly_one_record(self):
        for fact_id, concept in self._CONCEPTS.items():
            with self.subTest(concept=concept):
                ids = [r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept=concept)]
                self.assertEqual(ids, [fact_id])

    def test_both_are_documented_facts_without_modules(self):
        for fact_id, record in self._records().items():
            self.assertEqual(record["classification"], "documented_fact", fact_id)
            self.assertEqual(record["verified_at"], "2026-09-30T12:00:00Z", fact_id)
            self.assertNotIn("modules", record, fact_id)

    def test_alpha_vs_ibu_wording_and_sources(self):
        record = self._records()["FACT-HOP-0005"]
        self.assertIn("not the beer's IBU", record["claim"])
        self.assertIn("does not map to any fixed IBU", record["claim"])
        refs = [s["ref"] for s in record["sources"]]
        self.assertEqual(len(refs), 2)
        self.assertTrue(any("beerandbrewing.com/dictionary/0Mo49i2N1B" in r for r in refs))
        self.assertTrue(any("howtobrew.com/section-1/chapter-5" in r for r in refs))
        self.assertIn("2026-09-30", " ".join(s["type"] for s in record["sources"]))

    def test_alpha_vs_ibu_does_not_absorb_recipe_ibu_boundaries(self):
        claim = self._records()["FACT-HOP-0005"]["claim"].lower()
        for forbidden in ("tinseth", "utilisation", "utilization", "estimate", "perceived", "balance", "cohumulone"):
            self.assertNotIn(forbidden, claim)

    def test_ageing_storage_uses_tight_claim_without_forbidden_content(self):
        record = self._records()["FACT-HOP-0004"]
        claim = record["claim"].lower()
        self.assertIn("cold, oxygen-excluding storage slows deterioration", claim)
        for forbidden in ("cheese", "sweaty", "less bitter", "vacuum", "months", "storage index", "%"):
            self.assertNotIn(forbidden, claim)

    def test_ageing_storage_sources_mark_commercial_interest(self):
        sources = self._records()["FACT-HOP-0004"]["sources"]
        self.assertEqual(len(sources), 3)
        self.assertTrue(any("10.3390/plants12040936" in s["ref"] for s in sources))
        barthhaas = [s for s in sources if "barthhaas.com" in s["ref"]]
        self.assertEqual(len(barthhaas), 2)
        for source in barthhaas:
            self.assertIn("commercial interest", source["type"])

    def test_existing_hop_records_are_unchanged_in_id_and_concepts(self):
        expected = {
            "FACT-HOP-0001": ["hop.isomerization_time", "hop.whirlpool_technique"],
            "FACT-HOP-0002": ["hop.aroma_volatility", "hop.whirlpool_technique"],
            "FACT-HOP-0003": ["hop.addition_strategy"],
        }
        for fact_id, concepts in expected.items():
            self.assertEqual(get_verified_record(_PRODUCTION_REGISTRY, fact_id)["concepts"], concepts)


class TestProductionRegistryRecipeIbuVsPerceivedBitterness(unittest.TestCase):
    """Issue #441 (V2.2 Goal 3 R-2): FACT-RECIPE-0001 (R-1 adds -0002 below).
    FACT-HOP-0005 owns alpha % vs IBU; R-4 (balance) is not started."""

    def _record(self):
        return get_verified_record(_PRODUCTION_REGISTRY, "FACT-RECIPE-0001")

    def test_exactly_one_recipe_record_and_concept_maps_to_it(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        ids = [r["id"] for r in data["records"] if r["id"].startswith("FACT-RECIPE-")]
        self.assertEqual(ids, ["FACT-RECIPE-0001", "FACT-RECIPE-0002", "FACT-RECIPE-0003"])
        found = find_verified_records(_PRODUCTION_REGISTRY, concept="recipe.ibu_vs_perceived_bitterness")
        self.assertEqual([r["id"] for r in found], ["FACT-RECIPE-0001"])

    def test_documented_fact_without_modules(self):
        record = self._record()
        self.assertEqual(record["classification"], "documented_fact")
        self.assertNotIn("modules", record)

    def test_claim_is_conservative_and_makes_no_directional_claims(self):
        claim = self._record()["claim"]
        self.assertIn("standard bitterness index", claim)
        self.assertIn("is an estimate", claim)
        self.assertIn("beers with similar IBU can be perceived as differently bitter", claim)
        lowered = claim.lower()
        for forbidden in (
            "alcohol", "sweet", "sugar", "roast", "mineral", "hardness", "carbonation", "ph ",
            "temperature", "aroma", "alpha", "tinseth", "rager", "utilisation", "utilization",
            "bu:gu", "same ibu", "always",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_sources_and_limitations_are_explicit(self):
        record = self._record()
        refs = " ".join(s["ref"] for s in record["sources"])
        self.assertIn("10.1016/j.foodres.2016.05.018", refs)
        self.assertIn("10.1016/j.foodchem.2017.03.031", refs)
        self.assertIn("Gastl", refs)
        self.assertIn("howtobrew.com/section-1/chapter-5", refs)
        self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"])
        self.assertIn("abstracts", record["notes"])

    def test_hop_0005_is_unchanged_and_not_duplicated(self):
        hop = get_verified_record(_PRODUCTION_REGISTRY, "FACT-HOP-0005")
        self.assertEqual(hop["concepts"], ["hop.alpha_vs_ibu"])
        self.assertNotIn("estimate", hop["claim"])


class TestProductionRegistryRecipeSpecialtyFermentability(unittest.TestCase):
    """Issue #442 (V2.2 Goal 3 R-1): FACT-RECIPE-0002. Owns only the
    ingredient-side tendency; no sweetness/body/magnitude/colour claim."""

    def _record(self):
        return get_verified_record(_PRODUCTION_REGISTRY, "FACT-RECIPE-0002")

    def test_concept_maps_to_exactly_this_record(self):
        found = find_verified_records(_PRODUCTION_REGISTRY, concept="recipe.specialty_fermentability")
        self.assertEqual([r["id"] for r in found], ["FACT-RECIPE-0002"])

    def test_documented_fact_without_modules(self):
        record = self._record()
        self.assertEqual(record["classification"], "documented_fact")
        self.assertNotIn("modules", record)

    def test_claim_is_conservative_and_makes_no_forbidden_claims(self):
        claim = self._record()["claim"]
        self.assertIn("generally less fermentable", claim)
        self.assertIn("How much depends on the malt type and the amount used", claim)
        lowered = claim.lower()
        for forbidden in (
            "sweet", "body", "mouthfeel", "unfermentable", "always", "all specialty", "darker",
            "colour", "color", "lovibond", "ebc", "%", "small", "ordinary", "sticky", "engine",
            "final gravity", " fg",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_sources_and_limitations_are_explicit(self):
        record = self._record()
        refs = " ".join(s["ref"] for s in record["sources"])
        self.assertIn("10.3390/fermentation7030137", refs)
        self.assertIn("Briess", refs)
        self.assertIn("Crisp", refs)
        self.assertIn("Oxford Companion to Beer", refs)
        self.assertIn("Palmer", refs)
        self.assertNotIn("Prado", refs)
        self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"])
        self.assertIn("commercial interest", " ".join(s["type"] for s in record["sources"]))

    def test_existing_facts_do_not_carry_the_concept(self):
        for fact_id in ("FACT-MALT-0002", "FACT-MALT-0003", "FACT-MALT-0004", "FACT-MASH-0001", "FACT-YEAST-0002"):
            self.assertNotIn(
                "recipe.specialty_fermentability", get_verified_record(_PRODUCTION_REGISTRY, fact_id)["concepts"]
            )


class TestProductionRegistryRecipeBalance(unittest.TestCase):
    """Issue #443 (V2.2 Goal 3 R-4): FACT-RECIPE-0003. Relational
    professional interpretation only; no BU:GU, style or directional claims."""

    def _record(self):
        return get_verified_record(_PRODUCTION_REGISTRY, "FACT-RECIPE-0003")

    def test_concept_maps_to_exactly_this_record(self):
        found = find_verified_records(_PRODUCTION_REGISTRY, concept="recipe.balance")
        self.assertEqual([r["id"] for r in found], ["FACT-RECIPE-0003"])

    def test_professional_interpretation_without_modules(self):
        record = self._record()
        self.assertEqual(record["classification"], "professional_interpretation")
        self.assertNotIn("modules", record)

    def test_claim_is_relational_and_makes_no_forbidden_claims(self):
        claim = self._record()["claim"]
        self.assertIn("relative to one another", claim)
        self.assertIn("not by one universal number or ratio", claim)
        self.assertIn("not a quality score", claim)
        lowered = claim.lower()
        for forbidden in (
            "bu:gu", "ibu", "bjcp", "style", "alcohol", "sweet", "sugar", "fg", "roast", "mineral",
            "carbonation", "ph ", "temperature", "aroma", "acid", "hop", "malt", "equal", "better",
            "engine", "always", "harmonisk",
        ):
            self.assertNotIn(forbidden, lowered)

    def test_sources_and_limitations_are_explicit(self):
        record = self._record()
        refs = " ".join(s["ref"] for s in record["sources"])
        self.assertIn("Oxford Companion to Beer", refs)
        self.assertIn("10.23763/BRSC07-01GASTL", refs)
        self.assertIn("BJCP 2021", refs)
        self.assertIn("Weikert", refs)
        self.assertIn("context only", " ".join(s["type"] for s in record["sources"]))
        self.assertIn("no Tier A source defines 'balance'", record["notes"])
        self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"])

    def test_r1_r2_facts_are_unchanged_and_not_duplicated(self):
        for fact_id, concept in (
            ("FACT-RECIPE-0001", "recipe.ibu_vs_perceived_bitterness"),
            ("FACT-RECIPE-0002", "recipe.specialty_fermentability"),
        ):
            self.assertEqual(get_verified_record(_PRODUCTION_REGISTRY, fact_id)["concepts"], [concept])


class TestProductionRegistryMeasurementFoundation(unittest.TestCase):
    """Issue #444 (V2.2 Goal 3 Maaling Foundation): FACT-MEAS-0001..0003
    (M1 gravity, M2 fermentation complete, M4 hydrometer temperature).
    Documented facts only; no numbers, formulas or waiting rules."""

    _CONCEPTS = {
        "FACT-MEAS-0001": "measurement.gravity",
        "FACT-MEAS-0002": "measurement.fermentation_complete",
        "FACT-MEAS-0003": "measurement.hydrometer_temperature",
    }

    def test_meas_records_are_exactly_foundation_plus_kompetent(self):
        # Issue #445 appends the Kompetent M3/M6 records after the three
        # Foundation records, and M7 (FACT-MEAS-0006, offline 2026-10-05)
        # follows them; no other FACT-MEAS record may exist.
        data = read_registry_file(_PRODUCTION_REGISTRY)
        ids = [r["id"] for r in data["records"] if r["id"].startswith("FACT-MEAS-")]
        self.assertEqual(
            ids,
            _MEASUREMENT_VERIFIED_IDS + _MEASUREMENT_KOMPETENT_VERIFIED_IDS
            + _MEASUREMENT_INSTRUMENT_CHECK_VERIFIED_IDS,
        )

    def test_each_concept_maps_to_exactly_one_record(self):
        for fact_id, concept in self._CONCEPTS.items():
            with self.subTest(concept=concept):
                found = find_verified_records(_PRODUCTION_REGISTRY, concept=concept)
                self.assertEqual([r["id"] for r in found], [fact_id])

    def test_documented_facts_without_modules(self):
        for fact_id in _MEASUREMENT_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertEqual(record["classification"], "documented_fact", fact_id)
            self.assertNotIn("modules", record, fact_id)

    def test_claims_contain_no_numbers_or_formulas(self):
        for fact_id in _MEASUREMENT_VERIFIED_IDS:
            claim = get_verified_record(_PRODUCTION_REGISTRY, fact_id)["claim"]
            self.assertFalse(any(ch.isdigit() for ch in claim), fact_id)
            for forbidden in ("formula", "plato", "brix", "abv", "attenuation", "°"):
                self.assertNotIn(forbidden, claim.lower(), fact_id)

    def test_gravity_claim_boundaries(self):
        claim = get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0001")["claim"]
        self.assertIn("relative to water", claim)
        self.assertIn("stated reference temperatures", claim)
        self.assertIn("measured before fermentation", claim)
        self.assertIn("measured when fermentation has finished", claim)
        self.assertNotIn("lowest", claim)

    def test_fermentation_complete_claim_is_hedged_and_has_no_rule(self):
        claim = get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0002")["claim"]
        self.assertIn("plausibly finished", claim)
        self.assertIn("repeated measurements", claim)
        self.assertIn("Airlock activity is not a reliable indicator", claim)
        for forbidden in ("certainly", "proves", "package", "hours", "days"):
            self.assertNotIn(forbidden, claim.lower())

    def test_hydrometer_claim_uses_reference_temperature_without_values(self):
        claim = get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0003")["claim"]
        self.assertIn("reference temperature", claim)
        self.assertIn("stated on the instrument or in its instructions", claim)
        self.assertIn("measured and noted", claim)

    def test_sources_and_limitations_are_explicit(self):
        for fact_id in _MEASUREMENT_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            refs = " ".join(s["ref"] for s in record["sources"])
            self.assertIn("MISCO", refs, fact_id)
            self.assertIn("AHA", refs, fact_id)
            self.assertNotIn("ASTM", refs, fact_id)
            self.assertIn("SOURCE LIMITATIONS", record["notes"], fact_id)
            self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"], fact_id)
        airlock_refs = " ".join(
            s["ref"] for s in get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0002")["sources"]
        )
        self.assertIn("Wyeast", airlock_refs)


class TestProductionRegistryMeasurementKompetent(unittest.TestCase):
    """Issue #445 (V2.2 Goal 3 Maaling Kompetent): FACT-MEAS-0004 (M3
    instrument choice / alcohol boundary) and FACT-MEAS-0005 (M6 hot vs
    cooled volume). Documented facts only; no equations, numbers or
    system-specific rules. M5 stays out of the registry; M7 is its own
    record (FACT-MEAS-0006, TestProductionRegistryMeasurementInstrumentCheck)."""

    _CONCEPTS = {
        "FACT-MEAS-0004": "measurement.instrument_choice",
        "FACT-MEAS-0005": "measurement.volume_stages",
    }

    def test_each_concept_maps_to_exactly_one_record(self):
        for fact_id, concept in self._CONCEPTS.items():
            with self.subTest(concept=concept):
                found = find_verified_records(_PRODUCTION_REGISTRY, concept=concept)
                self.assertEqual([r["id"] for r in found], [fact_id])

    def test_documented_facts_without_modules(self):
        for fact_id in _MEASUREMENT_KOMPETENT_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertEqual(record["classification"], "documented_fact", fact_id)
            self.assertNotIn("modules", record, fact_id)

    def test_claims_contain_no_numbers_or_formulas(self):
        for fact_id in _MEASUREMENT_KOMPETENT_VERIFIED_IDS:
            claim = get_verified_record(_PRODUCTION_REGISTRY, fact_id)["claim"]
            self.assertFalse(any(ch.isdigit() for ch in claim), fact_id)
            for forbidden in ("formula", "equation", "factor", "plato", "abv", "%", "°"):
                self.assertNotIn(forbidden, claim.lower(), fact_id)

    def test_m5_is_not_a_registry_record_and_m7_is_exactly_one(self):
        # M5 (fermenter vs room temperature) is still unsourced (G3) and must
        # not exist. M7 (instrument check) became FACT-MEAS-0006 after the
        # Chief live source spot-check on 2026-10-05.
        data = read_registry_file(_PRODUCTION_REGISTRY)
        concepts = {c for r in data["records"] for c in r.get("concepts", [])}
        self.assertNotIn("measurement.fermentation_temperature", concepts)
        holders = [r["id"] for r in data["records"] if "measurement.instrument_check" in r.get("concepts", [])]
        self.assertEqual(holders, ["FACT-MEAS-0006"])

    def test_instrument_choice_claim_boundaries(self):
        claim = get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0004")["claim"]
        self.assertIn("refractive index", claim)
        self.assertIn("rather than density", claim)
        self.assertIn("once alcohol is present", claim)
        self.assertIn("hydrometer", claim)
        self.assertIn("original pre-fermentation reading", claim)
        for forbidden in ("always", "more accurate", "atc", "automatic temperature", "brand"):
            self.assertNotIn(forbidden, claim.lower())

    def test_volume_stages_claim_boundaries(self):
        claim = get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0005")["claim"]
        self.assertIn("more volume when hot than after it has cooled", claim)
        self.assertIn("not interchangeable measurements", claim)
        self.assertIn("independently of temperature", claim)
        for forbidden in ("brewzilla", "efficiency", "yield", "record"):
            self.assertNotIn(forbidden, claim.lower())

    def test_sources_and_limitations_are_explicit(self):
        for fact_id in _MEASUREMENT_KOMPETENT_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            refs = " ".join(s["ref"] for s in record["sources"])
            self.assertIn("BYO", refs, fact_id)
            self.assertNotIn("Kunze", refs, fact_id)
            self.assertIn("SOURCE LIMITATIONS", record["notes"], fact_id)
            self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"], fact_id)
        m3_refs = " ".join(
            s["ref"] for s in get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0004")["sources"]
        )
        self.assertIn("MISCO", m3_refs)
        m6_refs = " ".join(
            s["ref"] for s in get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0005")["sources"]
        )
        self.assertIn("USGS", m6_refs)


class TestProductionRegistryMeasurementInstrumentCheck(unittest.TestCase):
    """Measurement M7 (FACT-MEAS-0006): the instrument-check habit for the
    hydrometer and the refractometer only. Offline round; Chief live source
    spot-check PASS 2026-10-05 on the source pack
    docs/development/v22_measurement_m7_instrument_check_source_pack.md.
    Chief refinements: no thermometer, no universal "cannot be reset"
    claim, classification professional_interpretation."""

    def setUp(self):
        self.record = get_verified_record(_PRODUCTION_REGISTRY, "FACT-MEAS-0006")

    def test_verified_interpretation_without_modules(self):
        self.assertIsNotNone(self.record)
        self.assertEqual(self.record["status"], "verified")
        self.assertEqual(self.record["classification"], "professional_interpretation")
        self.assertEqual(self.record["concepts"], ["measurement.instrument_check"])
        self.assertNotIn("modules", self.record)
        # The local receipt of the Chief PASS (session log), not an invented clock time.
        self.assertEqual(self.record["verified_at"], "2026-10-05T00:17:37+02:00")
        self.assertIn("VERIFIED_AT PROVENANCE", self.record["notes"])

    def test_claim_scope_is_hydrometer_and_refractometer(self):
        claim = self.record["claim"]
        for needle in ("hydrometer", "distilled water", "reference temperature stated for that hydrometer",
                       "1.000 specific gravity", "consistent offset", "recorded and accounted for",
                       "refractometer is zeroed or checked", "as its instructions specify",
                       "Neither check proves that every later reading is correct",
                       "does not show that the whole hydrometer scale is right",
                       "does not remove other error sources"):
            self.assertIn(needle, claim)

    def test_claim_traps(self):
        claim = self.record["claim"].lower()
        for forbidden in ("thermometer", "ice", "cannot be reset", "can't be reset", "file", "nail polish", "tape",
                          "tolerance", "daily", "always", "more accurate", "agree", "formula", "equation",
                          "sucrose", "sugar solution", "dme", "brand", "°", "%"):
            self.assertNotIn(forbidden, claim)
        # The only number in the claim is the water point itself.
        self.assertEqual(re.findall(r"\d+(?:\.\d+)?", claim), ["1.000"])

    def test_sources_tiers_and_flags(self):
        sources = self.record["sources"]
        refs = " ".join(s["ref"] for s in sources)
        for needle in ("AHA", "Jon Stika", "Craft Beer & Brewing", "Hanna", "HI96841", "MAN96841 07/24",
                       "MISCO", "REV140407-1"):
            self.assertIn(needle, refs)
        self.assertNotIn("Dave Green", refs)
        self.assertNotIn("wsu", refs.lower())
        tiers = {s["ref"].split(",")[0]: s["tier"] for s in sources}
        self.assertEqual(tiers["Hanna Instruments"], "A")
        self.assertEqual(tiers["MISCO"], "A")
        for s in sources:
            self.assertIn("Chief live spot-check PASS 2026-10-05", s["note"], s["ref"])
            if s["tier"] == "A":
                self.assertIn("commercial interest", s["type"], s["ref"])

    def test_notes_record_limits_and_refinements(self):
        notes = self.record["notes"]
        for needle in ("SOURCE LIMITATIONS", "SOURCE-ACCESS LIMITATIONS", "THERMOMETER is deliberately NOT covered",
                       "'cannot be reset'", "FACT-MEAS-0004", "FACT-MEAS-0003", "Tier-B-only",
                       "not a tolerance and not a temperature"):
            self.assertIn(needle, notes)


class TestProductionRegistryPack0003SourceCleanup(unittest.TestCase):
    """Issue #448: FACT-PACK-0003 source-quality cleanup. Claim wording is
    unchanged; the off-topic Lallemand thiol guide is removed and the
    BA-hosted CBC keg seminar carries the 'damaged' component."""

    def test_claim_keeps_not_intended_rated_wording(self):
        record = get_verified_record(_PRODUCTION_REGISTRY, "FACT-PACK-0003")
        self.assertIn("damaged or not intended/rated for the pressure involved", record["claim"])
        self.assertNotIn("unrated", record["claim"])
        self.assertEqual(record["concepts"], ["package.pressure_safety"])

    def test_sources_after_cleanup(self):
        record = get_verified_record(_PRODUCTION_REGISTRY, "FACT-PACK-0003")
        refs = " ".join(s["ref"] for s in record["sources"])
        self.assertNotIn("lallemandbrewing.com", refs)
        self.assertIn("preventing-package-over-pressurization", refs)
        self.assertIn("howtobrew.com/section-1/chapter-11", refs)
        self.assertIn("Refillable-Kegs-Quality-Safety-and-Maintenance", refs)
        self.assertIn("no bottle-specific 'damaged' source", record["notes"])


class TestProductionRegistrySafetyFactPack(unittest.TestCase):
    """Issue #447 (V2.2 Goal 3 Rengjoring/sikkerhet): FACT-SAFE-0001 (N1
    cleaning vs sanitising + clean-first, one record / two concepts),
    FACT-SAFE-0002 (N2 generic chemical handling) and FACT-SAFE-0003 (N3
    qualitative fermentation CO2 hazard). Documented facts only."""

    _CONCEPTS = {
        "FACT-SAFE-0001": ["hygiene.clean_vs_sanitize", "hygiene.clean_first"],
        "FACT-SAFE-0002": ["safety.chem_handling"],
        "FACT-SAFE-0003": ["safety.fermentation_co2"],
    }

    def test_only_three_safe_records_exist(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        ids = [r["id"] for r in data["records"] if r["id"].startswith("FACT-SAFE-")]
        self.assertEqual(ids, _SAFETY_VERIFIED_IDS)

    def test_each_concept_maps_to_exactly_its_record(self):
        for fact_id, concepts in self._CONCEPTS.items():
            for concept in concepts:
                with self.subTest(concept=concept):
                    found = find_verified_records(_PRODUCTION_REGISTRY, concept=concept)
                    self.assertEqual([r["id"] for r in found], [fact_id])

    def test_n1_is_one_record_carrying_both_concepts(self):
        record = get_verified_record(_PRODUCTION_REGISTRY, "FACT-SAFE-0001")
        self.assertEqual(record["concepts"], self._CONCEPTS["FACT-SAFE-0001"])

    def test_documented_facts_without_modules(self):
        for fact_id in _SAFETY_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertEqual(record["classification"], "documented_fact", fact_id)
            self.assertNotIn("modules", record, fact_id)

    def test_n1_claim_boundaries(self):
        claim = get_verified_record(_PRODUCTION_REGISTRY, "FACT-SAFE-0001")["claim"]
        self.assertIn("does not make anything sterile", claim)
        self.assertIn("cleaned first and sanitised second", claim)
        self.assertIn("reduce a sanitiser's effect", claim)
        for forbidden in ("star san", "pbw", "contact time", "no-rinse", "concentration", "cannot sanitise"):
            self.assertNotIn(forbidden, claim.lower())

    def test_n2_claim_is_generic_and_product_neutral(self):
        record = get_verified_record(_PRODUCTION_REGISTRY, "FACT-SAFE-0002")
        claim = record["claim"]
        self.assertIn("Follow the product label", claim)
        self.assertIn("unless the label says it is safe", claim)
        for forbidden in ("always", "goggles", "gloves", "star san", "pbw", "chlorine", "bleach", "ammonia", "gas"):
            self.assertNotIn(forbidden, claim.lower())
        self.assertIn("NO claim about what PBW + Star San release", record["notes"])
        self.assertIn("US-format", record["notes"])

    def test_n3_claim_is_qualitative_and_keeps_interpretation_visible(self):
        record = get_verified_record(_PRODUCTION_REGISTRY, "FACT-SAFE-0003")
        claim = record["claim"]
        self.assertIn("colourless and odourless", claim)
        self.assertIn("displace oxygen", claim)
        self.assertIn("Ferment in a ventilated space", claim)
        # The CO2 subscript is not an ASCII digit; no quantity may appear.
        self.assertFalse(any(ch in "0123456789" for ch in claim))
        for forbidden in ("ppm", "%", "alarm", "buddy", "confined", "dangerous", "harmless"):
            self.assertNotIn(forbidden, claim.lower())
        self.assertIn("PROPORTIONATE INTERPRETATION", record["notes"])
        self.assertIn("CO₂ at L1 = MUST", record["notes"])

    def test_sources_and_limitations_are_explicit(self):
        for fact_id in _SAFETY_VERIFIED_IDS:
            record = get_verified_record(_PRODUCTION_REGISTRY, fact_id)
            self.assertIn("SOURCE LIMITATIONS", record["notes"], fact_id)
            self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"], fact_id)
        n1_refs = " ".join(s["ref"] for s in get_verified_record(_PRODUCTION_REGISTRY, "FACT-SAFE-0001")["sources"])
        self.assertIn("CDC", n1_refs)
        self.assertIn("Palmer", n1_refs)
        self.assertNotIn("Star San", n1_refs)
        n3_refs = " ".join(s["ref"] for s in get_verified_record(_PRODUCTION_REGISTRY, "FACT-SAFE-0003")["sources"])
        self.assertIn("HSE", n3_refs)
        self.assertIn("Ontario", n3_refs)


class TestProductionRegistrySensoryDiacetylFact(unittest.TestCase):
    """Issue #466 (V2.2 Goal 3 Sensory S-1): FACT-SENSORY-0001, the single
    narrow `sensory.diacetyl` documented_fact (source gate #463)."""

    def _record(self):
        return get_verified_record(_PRODUCTION_REGISTRY, "FACT-SENSORY-0001")

    def test_only_the_expected_sensory_records_exist(self):
        data = read_registry_file(_PRODUCTION_REGISTRY)
        ids = [r["id"] for r in data["records"] if r["id"].startswith("FACT-SENSORY-")]
        self.assertEqual(ids, _SENSORY_VERIFIED_IDS)

    def test_concept_maps_to_exactly_this_record_without_modules(self):
        found = find_verified_records(_PRODUCTION_REGISTRY, concept="sensory.diacetyl")
        self.assertEqual([r["id"] for r in found], ["FACT-SENSORY-0001"])
        record = self._record()
        self.assertEqual(record["classification"], "documented_fact")
        self.assertEqual(record["concepts"], ["sensory.diacetyl"])
        self.assertNotIn("modules", record)

    def test_claim_carries_the_accepted_elements(self):
        claim = self._record()["claim"]
        for phrase in (
            "butter or butterscotch",
            "precursor",
            "healthy yeast",
            "enough yeast",
            "Certain lactic acid bacteria",
            "some beer styles",
            "unintentionally prominent",
        ):
            self.assertIn(phrase, claim)

    def test_claim_respects_hard_exclusions(self):
        claim = self._record()["claim"]
        self.assertFalse(any(ch.isdigit() for ch in claim))
        for forbidden in (
            "threshold", "ppb", "ppm", "mg", "rest", "enzyme", "aldc", "slick",
            "oily", "mouthfeel", "proves", "always", "acetaldehyde", "sulphur", "sulfur",
        ):
            self.assertNotIn(forbidden, claim.lower())

    def test_sources_and_caveats_are_preserved(self):
        record = self._record()
        refs = " ".join(s["ref"] for s in record["sources"])
        for expected in ("10.1002/jib.84", "PMC6267509", "Oxford Companion", "Brewers Association", "Kunze"):
            self.assertIn(expected, refs)
        self.assertIn("SOURCE LIMITATIONS", record["notes"])
        self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"])
        self.assertIn("abstract only", record["notes"])
        self.assertIn("Tier B", record["notes"])


class TestProductionRegistrySensoryTypicalDescriptorsFact(unittest.TestCase):
    """Issue #467 (V2.2 Goal 3 Sensory S-4): FACT-SENSORY-0002, the single
    narrow `sensory.typical_descriptors` documented_fact (source gate #464)."""

    def _record(self):
        return get_verified_record(_PRODUCTION_REGISTRY, "FACT-SENSORY-0002")

    def test_concept_maps_to_exactly_this_record_without_modules(self):
        found = find_verified_records(_PRODUCTION_REGISTRY, concept="sensory.typical_descriptors")
        self.assertEqual([r["id"] for r in found], ["FACT-SENSORY-0002"])
        record = self._record()
        self.assertEqual(record["classification"], "documented_fact")
        self.assertEqual(record["concepts"], ["sensory.typical_descriptors"])
        self.assertNotIn("modules", record)

    def test_claim_carries_the_four_accepted_descriptor_families(self):
        claim = self._record()["claim"]
        for phrase in ("sweetcorn or cooked vegetables", "cardboard or paper", "green apple", "skunky"):
            self.assertIn(phrase, claim)

    def test_claim_respects_hard_exclusions(self):
        claim = self._record()["claim"].lower()
        self.assertFalse(any(ch.isdigit() for ch in claim))
        for forbidden in (
            "sherry", "threshold", "ppb", "ppm", "proves", "diagnos", "boil", "oxygen",
            "matur", "yeast", "riboflavin", "hop", "glass", "sulphur", "sulfur",
            "cabbage", "tomato", "cucumber",
        ):
            self.assertNotIn(forbidden, claim)

    def test_descriptor_is_not_diagnosis_lives_in_notes_not_claim(self):
        notes = self._record()["notes"]
        self.assertIn("DESCRIPTOR != DIAGNOSIS", notes)
        self.assertIn("OMITTED", notes)
        for owner in ("FACT-BOIL-0002", "FACT-OXY-0002", "S-3"):
            self.assertIn(owner, notes)

    def test_sources_and_caveats_are_preserved(self):
        record = self._record()
        refs = " ".join(s["ref"] for s in record["sources"])
        for expected in (
            "10.3390/foods14244287", "PMC12732517", "10.3390/molecules24081568",
            "Oxford Companion", "Acetaldehyde", "Dimethyl Sulfide",
        ):
            self.assertIn(expected, refs)
        self.assertNotIn("Kunze", refs)
        for expected in ("SOURCE LIMITATIONS", "SOURCE-ACCESS LIMITATIONS", "members-only", "MDPI", "truncated"):
            self.assertIn(expected, record["notes"])


class TestProductionRegistrySensorySournessFact(unittest.TestCase):
    """Issue #470 (V2.2 Goal 3 Sensory S-2): FACT-SENSORY-0003, the single
    narrow `sensory.sourness_intent_vs_spoilage` documented_fact (source gate #468)."""

    def _record(self):
        return get_verified_record(_PRODUCTION_REGISTRY, "FACT-SENSORY-0003")

    def test_concept_maps_to_exactly_this_record_without_modules(self):
        found = find_verified_records(_PRODUCTION_REGISTRY, concept="sensory.sourness_intent_vs_spoilage")
        self.assertEqual([r["id"] for r in found], ["FACT-SENSORY-0003"])
        record = self._record()
        self.assertEqual(record["classification"], "documented_fact")
        self.assertEqual(record["concepts"], ["sensory.sourness_intent_vs_spoilage"])
        self.assertNotIn("modules", record)

    def test_claim_carries_intended_sourness_and_unwanted_contamination(self):
        claim = self._record()["claim"]
        for phrase in ("intended", "sour beer", "not meant to be sour", "unwanted microbial contamination", "spoils"):
            self.assertIn(phrase, claim)

    def test_claim_respects_hard_exclusions(self):
        claim = self._record()["claim"].lower()
        self.assertFalse(any(ch.isdigit() for ch in claim))
        for forbidden in (
            "infected", "infection", "sour means", "sour =", "taste alone", "proves", "diagnos",
            "health", "safe", "undrinkable", "harm", "danger", "threshold",
            "lactobacillus", "pediococcus", "acetobacter", "brettanomyces", "yeast",
            "treat", "rescue", "pasteur", "sanitis", "sanitiz",
        ):
            self.assertNotIn(forbidden, claim)

    def test_taste_alone_boundary_lives_in_notes_not_claim(self):
        notes = self._record()["notes"]
        self.assertIn("TASTE ALONE DOES NOT ESTABLISH THE CAUSE", notes)
        self.assertIn("NOT asserted as a factual sentence", notes)
        self.assertIn("Osburn", notes)

    def test_sources_and_caveats_are_preserved(self):
        record = self._record()
        refs = " ".join(s["ref"] for s in record["sources"])
        for expected in (
            "10.3389/fmicb.2022.957167", "PMC9386357", "10.3390/foods14122043", "PMC12191484",
            "10.3390/foods14244287", "PMC12732517", "Kunze", "p. 763",
        ):
            self.assertIn(expected, refs)
        for expected in ("SOURCE LIMITATIONS", "SOURCE-ACCESS LIMITATIONS", "MDPI", "abstract-only", "members-only"):
            self.assertIn(expected, record["notes"])


class TestProductionRegistryMaltCoreFactPackVerifiedOnlyApi(unittest.TestCase):
    """Issue #426 (V2.2 G3P-1): the Raavarer P1 malt-core fact pack
    (FACT-MALT-0001..0004). Extract/enzyme relationships are reused from
    FACT-MASH-0001/FACT-MASH-0004, never duplicated."""

    _CONCEPTS = {
        "FACT-MALT-0001": "malt.what_is_malt",
        "FACT-MALT-0002": "malt.base_vs_specialty",
        "FACT-MALT-0003": "malt.colour_flavour",
        "FACT-MALT-0004": "malt.grist_percentage",
    }

    def _malt_records(self):
        return {r["id"]: r for r in read_verified_records(_PRODUCTION_REGISTRY) if r["id"].startswith("FACT-MALT-")}

    def test_returns_exactly_the_four_malt_ids(self):
        self.assertEqual(set(self._malt_records()), set(_MALT_CORE_VERIFIED_IDS))

    def test_each_concept_maps_to_exactly_one_record(self):
        for fact_id, concept in self._CONCEPTS.items():
            with self.subTest(concept=concept):
                ids = [r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept=concept)]
                self.assertEqual(ids, [fact_id])

    def test_no_duplicate_extract_or_enzyme_concept_records(self):
        # malt.extract_fermentability is covered by reuse of FACT-MASH-0001/0004.
        self.assertEqual(find_verified_records(_PRODUCTION_REGISTRY, concept="malt.extract_fermentability"), [])
        for record in self._malt_records().values():
            self.assertNotIn("mashing.starch_conversion", record["concepts"])
            self.assertNotIn("mashing.dextrins", record["concepts"])

    def test_sources_are_external_tier_a_and_never_chief_or_ai(self):
        expected_urls = {
            "FACT-MALT-0001": ["brewingwithbriess.com/malting-101/malting-process/", "10.1111/1541-4337.12806"],
            "FACT-MALT-0002": ["brewingwithbriess.com/malting-101/malting-process/"],
            "FACT-MALT-0003": [
                "brewingwithbriess.com/malting-101/malting-process/",
                "brewingwithbriess.com/blog/understanding-a-malt-analysis/",
                "10.1111/1541-4337.12806",
            ],
            "FACT-MALT-0004": ["brewingwithbriess.com/blog/hot-steep-as-a-tool-for-specialty-malt-formulation-in-beer/"],
        }
        for fact_id, record in self._malt_records().items():
            refs = [s["ref"] for s in record["sources"]]
            self.assertEqual(len(refs), len(expected_urls[fact_id]))
            for fragment in expected_urls[fact_id]:
                self.assertTrue(any(fragment in ref for ref in refs), (fact_id, fragment))
            for source in record["sources"]:
                self.assertEqual(source["tier"], "A")
                self.assertNotIn("chief", (source["ref"] + source["type"]).lower())

    def test_grist_percentage_uses_narrowed_directional_wording(self):
        record = self._malt_records()["FACT-MALT-0004"]
        self.assertEqual(record["classification"], "professional_interpretation")
        self.assertIn("relative proportion of each malt in the grist", record["claim"])
        self.assertNotIn("not one malt", record["claim"])
        self.assertIn("not a universal quantitative model", record["notes"])

    def test_base_vs_specialty_says_many_and_avoids_absolutes(self):
        record = self._malt_records()["FACT-MALT-0002"]
        self.assertIn("many specialty malts", record["claim"])
        self.assertNotIn("never converts", record["claim"])
        self.assertNotIn("no enzymes", record["claim"])
        self.assertIn("never 'all'", record["notes"])

    def test_colour_flavour_has_no_numeric_colour_ranges_and_no_one_to_one_claim(self):
        record = self._malt_records()["FACT-MALT-0003"]
        self.assertIn("not a direct one-to-one predictor", record["claim"])
        for record in self._malt_records().values():
            for unit in ("EBC ", "SRM ", "°L", "Lovibond "):
                self.assertNotIn(unit, record["claim"])

    def test_every_record_documents_scope_and_wording_trap(self):
        for record in self._malt_records().values():
            self.assertIn("Wording trap", record["notes"])


class TestProductionRegistryWaterFoundationVerified(unittest.TestCase):
    """Issue #430 (V2.2 G3P-3): the Water foundation pack
    (FACT-WATER-0001..0003), promoted to verified from the external source
    provenance in the #430 handoff. Qualitative only; the Norwegian
    chloramine prevalence gap stays explicit."""

    _CONCEPTS = {
        "FACT-WATER-0001": "water.majority_ingredient",
        "FACT-WATER-0002": "water.chlorine_chloramine",
        "FACT-WATER-0003": "water.source_awareness",
    }

    def _water_records(self):
        return {r["id"]: r for r in read_verified_records(_PRODUCTION_REGISTRY) if r["id"].startswith("FACT-WATER-")}

    def test_returns_exactly_the_three_water_ids(self):
        self.assertEqual(set(self._water_records()), set(_WATER_FOUNDATION_VERIFIED_IDS))

    def test_each_concept_maps_to_exactly_one_record(self):
        for fact_id, concept in self._CONCEPTS.items():
            with self.subTest(concept=concept):
                ids = [r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept=concept)]
                self.assertEqual(ids, [fact_id])

    def test_verified_at_is_valid_and_not_in_the_future(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        for record in self._water_records().values():
            stamp = datetime.datetime.fromisoformat(record["verified_at"].replace("Z", "+00:00"))
            self.assertLessEqual(stamp, now)

    def test_sources_are_external_https_and_never_chief_or_ai(self):
        for record in self._water_records().values():
            self.assertGreaterEqual(len(record["sources"]), 2)
            for source in record["sources"]:
                self.assertIn(source["tier"], ("A", "B"))
                self.assertNotIn("chief", (source["ref"] + source["type"]).lower())
            self.assertTrue(any("https://" in s["ref"] for s in record["sources"]))

    def test_majority_record_is_qualitative_tier_b_only(self):
        record = self._water_records()["FACT-WATER-0001"]
        self.assertEqual({s["tier"] for s in record["sources"]}, {"B"})
        self.assertNotIn("%", record["claim"])
        self.assertNotIn("key", record["claim"].lower())

    def test_chlorine_record_scopes_norway_to_some_and_keeps_prevalence_gap(self):
        record = self._water_records()["FACT-WATER-0002"]
        self.assertIn("some Norwegian waterworks", record["claim"])
        self.assertIn("not established", record["claim"])
        for word in ("common in Norway", "many", "most"):
            self.assertNotIn(word, record["claim"])
        self.assertIn("SOURCE GAP", record["notes"])
        self.assertTrue(any("fhi.no" in s["ref"] for s in record["sources"]))

    def test_no_treatment_dosing_or_chemistry_in_claims(self):
        for record in self._water_records().values():
            claim = record["claim"].lower()
            for token in ("ppm", "campden", "boil", "overnight", "salt", "dose", "dosing"):
                self.assertNotIn(token, claim)

    def test_source_awareness_does_not_generalise_bergen(self):
        record = self._water_records()["FACT-WATER-0003"]
        self.assertIn("bergen.kommune.no", " ".join(s["ref"] for s in record["sources"]))
        self.assertIn("do NOT generalise Bergen", record["notes"])

    def test_every_record_documents_source_gate_and_wording_trap(self):
        for record in self._water_records().values():
            self.assertIn("Wording trap", record["notes"])
            self.assertIn("Source gate:", record["notes"])
            self.assertNotIn("NOT verified", record["notes"])


class TestProductionRegistryYeastCoreFactPackVerifiedOnlyApi(unittest.TestCase):
    """Issue #428 (V2.2 G3P-2): the Raavarer P2 yeast-core fact pack
    (FACT-YEAST-0001..0005). Temperature/oxygen context is reused from
    FACT-BREW-0001..0003 and FACT-OXY-0001, never duplicated."""

    _CONCEPTS = {
        "FACT-YEAST-0001": "yeast.organism_role",
        "FACT-YEAST-0002": "yeast.attenuation",
        "FACT-YEAST-0003": "yeast.ale_vs_lager",
        "FACT-YEAST-0004": "yeast.pitch_principle",
        "FACT-YEAST-0005": "yeast.choice_principle",
    }

    def _yeast_records(self):
        return {r["id"]: r for r in read_verified_records(_PRODUCTION_REGISTRY) if r["id"].startswith("FACT-YEAST-")}

    def test_returns_exactly_the_five_yeast_ids(self):
        self.assertEqual(set(self._yeast_records()), set(_YEAST_CORE_VERIFIED_IDS))

    def test_each_concept_maps_to_exactly_one_record(self):
        for fact_id, concept in self._CONCEPTS.items():
            with self.subTest(concept=concept):
                ids = [r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept=concept)]
                self.assertEqual(ids, [fact_id])

    def test_no_duplicate_temperature_concept_record(self):
        self.assertEqual(find_verified_records(_PRODUCTION_REGISTRY, concept="yeast.temperature_link"), [])

    def test_sources_are_external_tier_a_and_never_chief_or_ai(self):
        for record in self._yeast_records().values():
            self.assertGreaterEqual(len(record["sources"]), 2)
            for source in record["sources"]:
                self.assertEqual(source["tier"], "A")
                self.assertIn("https://", source["ref"])
                self.assertNotIn("chief", (source["ref"] + source["type"]).lower())

    def test_pitch_and_attenuation_have_no_numeric_rules(self):
        for fact_id in ("FACT-YEAST-0002", "FACT-YEAST-0004"):
            claim = self._yeast_records()[fact_id]["claim"]
            for token in ("%", "cells/mL", "°P", "million"):
                self.assertNotIn(token, claim)
        self.assertIn("rather than on one universal cell-count rule", self._yeast_records()["FACT-YEAST-0004"]["claim"])

    def test_ale_vs_lager_is_hedged(self):
        claim = self._yeast_records()["FACT-YEAST-0003"]["claim"]
        self.assertIn("typically", claim)
        self.assertIn("rather than a universal rule", claim)

    def test_every_record_documents_scope_and_wording_trap(self):
        for record in self._yeast_records().values():
            self.assertIn("Wording trap", record["notes"])


class TestProductionRegistryFermentationKompetentG1G2(unittest.TestCase):
    """Gjæring Kompetent G1/G2 (fermentation Kompetent contract §10; source
    pack docs/development/v22_fermentation_g1_g2_source_pack.md): Chief live
    spot-check PASS 2026-10-05. BREW numbering, no FACT-FERM-* prefix. The
    claims are the bounded source-pack versions; the Chief refinement drops
    "not everything can be fixed by waiting" entirely."""

    _CONCEPTS = {"FACT-BREW-0004": "fermentation.phases", "FACT-BREW-0005": "fermentation.conditioning"}

    def _records(self):
        return {fid: get_verified_record(_PRODUCTION_REGISTRY, fid) for fid in self._CONCEPTS}

    def test_verified_documented_facts_without_modules(self):
        for fact_id, record in self._records().items():
            with self.subTest(fact_id=fact_id):
                self.assertIsNotNone(record)
                self.assertEqual(record["status"], "verified")
                self.assertEqual(record["classification"], "documented_fact")
                self.assertEqual(record["concepts"], [self._CONCEPTS[fact_id]])
                self.assertNotIn("modules", record)
                # The local receipt of the Chief PASS (session log), not an
                # invented clock time.
                self.assertEqual(record["verified_at"], "2026-10-05T09:10:01+02:00")
                self.assertIn("VERIFIED_AT PROVENANCE", record["notes"])

    def test_each_concept_maps_to_exactly_one_record_and_no_ferm_prefix(self):
        for fact_id, concept in self._CONCEPTS.items():
            ids = [r["id"] for r in find_verified_records(_PRODUCTION_REGISTRY, concept=concept)]
            self.assertEqual(ids, [fact_id])
        ids = {r["id"] for r in read_verified_records(_PRODUCTION_REGISTRY)}
        self.assertFalse(any(i.startswith("FACT-FERM-") for i in ids))

    def test_g1_keeps_the_bounded_clauses(self):
        claim = self._records()["FACT-BREW-0004"]["claim"]
        for needle in ("does not run at one steady rate", "adapts to the wort",
                       "most of the fermentable sugar is consumed", "later, slower period",
                       "overlap rather than switching sharply", "name and divide them differently",
                       "depends on the yeast, the wort and the fermentation conditions"):
            self.assertIn(needle, claim)

    def test_g2_keeps_the_bounded_clauses(self):
        claim = self._records()["FACT-BREW-0005"]["claim"]
        for needle in ("further time", "maturation or conditioning", "overlaps with the end of fermentation",
                       "reduce some of the by-products", "tend to settle", "often becomes clearer",
                       "depends on the yeast strain", "meant to stay hazy", "no single universal duration"):
            self.assertIn(needle, claim)

    def test_claims_carry_no_numbers_traps_or_named_by_products(self):
        for fact_id, record in self._records().items():
            claim = record["claim"].lower()
            with self.subTest(fact_id=fact_id):
                self.assertIsNone(re.search(r"\d", claim))
                for trap in ("krausen", "kräusen", "bubble", "airlock", "lag time", "day", "week", "hour",
                             "acetaldehyde", "sulph", "sulfur", "diacetyl", "ester", "fusel", "finings",
                             "cold condition", "lagering", "always", "all off-flavour", "fixed by waiting",
                             "not everything"):
                    self.assertNotIn(trap, claim)

    def test_sources_tiers_flags_and_spot_check(self):
        for fact_id, record in self._records().items():
            with self.subTest(fact_id=fact_id):
                sources = record["sources"]
                self.assertGreaterEqual(len(sources), 2)
                self.assertEqual(sources[0]["tier"], "A")
                self.assertIn("whitelabs.com/glossary", sources[0]["ref"])
                self.assertIn("commercial interest", sources[0]["type"])
                self.assertTrue(any("howtobrew.com" in s["ref"] for s in sources))
                for source in sources:
                    self.assertIn(source["tier"], ("A", "B"))
                    self.assertIn("https://", source["ref"])
                    self.assertIn("Chief live spot-check PASS 2026-10-05", source["note"])
                    self.assertIn("Supports:", source["note"])
                    self.assertIn("not support", source["note"])

    def test_notes_record_traps_ownership_and_limitations(self):
        records = self._records()
        for record in records.values():
            self.assertIn("Wording trap", record["notes"])
            self.assertIn("SOURCE-ACCESS LIMITATIONS", record["notes"])
            self.assertIn("expired TLS certificate", record["notes"])
            self.assertIn("FACT-MEAS-0002", record["notes"])
        self.assertIn("NOT a phase taxonomy", records["FACT-BREW-0004"]["notes"])
        self.assertIn("INDEPENDENCE", records["FACT-BREW-0004"]["notes"])
        self.assertIn("FACT-SENSORY-0001", records["FACT-BREW-0005"]["notes"])
        self.assertIn("dropped entirely", records["FACT-BREW-0005"]["notes"])


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
