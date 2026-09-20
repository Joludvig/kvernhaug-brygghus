"""
Tests for bryggeskole/pilot_mashing.py -- the mash-fundamentals pilot
content/questions slice (issue #337).

Synthetic invalid-shape fixtures are reused from
tests/fixtures/pilot_fermentation/ (this module's validator is a
byte-for-byte copy of pilot_fermentation.py's, so the same shape-failure
fixtures exercise it identically) together with the same registry
fixture used by that suite
(tests/fixtures/course_fact_registry/verified_consumer_mixed.json),
which conveniently carries both a verified id (FACT-TEST-0020) and a
draft (unverified) id (FACT-TEST-0023) -- exactly the two cases this
module's source_claims validation must reject identically.

Run with:
    python3 -m unittest tests.test_pilot_mashing
"""
import io
import json
import os
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError
from bryggeskole.pilot_mashing import (
    DEFAULT_PILOT_PATH,
    DEFAULT_REGISTRY_PATH,
    DIFFICULTIES,
    PILOT_SCHEMA_VERSION,
    QUESTION_TYPES,
    PilotContentError,
    evaluate_answer,
    read_pilot_file,
    render_chunk,
    render_question,
    validate_pilot_content,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURES = os.path.join(_ROOT, "tests", "fixtures", "pilot_fermentation")
_REGISTRY_FIXTURE = os.path.join(
    _ROOT, "tests", "fixtures", "course_fact_registry", "verified_consumer_mixed.json"
)
_PRODUCTION_PILOT = DEFAULT_PILOT_PATH
_PRODUCTION_REGISTRY = DEFAULT_REGISTRY_PATH


def _fixture_path(name):
    return os.path.join(_FIXTURES, name)


def _load_fixture(name):
    with io.open(_fixture_path(name), encoding="utf-8") as fh:
        return json.load(fh)


class TestValidMinimalFixturePasses(unittest.TestCase):
    def test_no_errors_against_registry_fixture(self):
        data = _load_fixture("valid_minimal.json")
        errors = validate_pilot_content(data, registry_path=_REGISTRY_FIXTURE)
        self.assertEqual(errors, [])

    def test_read_pilot_file_returns_document(self):
        data = read_pilot_file(_fixture_path("valid_minimal.json"), registry_path=_REGISTRY_FIXTURE)
        self.assertEqual(data["topic_id"], "PILOT-TEST-TOPIC")


class TestMissingClaimFailsClosed(unittest.TestCase):
    def test_reports_error(self):
        data = _load_fixture("missing_claim.json")
        errors = validate_pilot_content(data, registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("FACT-TEST-9999" in e for e in errors))

    def test_read_pilot_file_raises(self):
        with self.assertRaises(PilotContentError):
            read_pilot_file(_fixture_path("missing_claim.json"), registry_path=_REGISTRY_FIXTURE)


class TestUnverifiedClaimFailsIdenticallyToMissing(unittest.TestCase):
    def test_reports_error(self):
        data = _load_fixture("unverified_claim.json")
        errors = validate_pilot_content(data, registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("FACT-TEST-0023" in e for e in errors))

    def test_error_message_shape_matches_missing_claim_case(self):
        missing_errors = validate_pilot_content(
            _load_fixture("missing_claim.json"), registry_path=_REGISTRY_FIXTURE
        )
        unverified_errors = validate_pilot_content(
            _load_fixture("unverified_claim.json"), registry_path=_REGISTRY_FIXTURE
        )
        missing_template = missing_errors[0].replace("FACT-TEST-9999", "<id>")
        unverified_template = unverified_errors[0].replace("FACT-TEST-0023", "<id>")
        self.assertEqual(missing_template, unverified_template)


class TestMalformedRegistryPropagatesRegistryError(unittest.TestCase):
    def test_validate_pilot_content_propagates(self):
        data = _load_fixture("valid_minimal.json")
        broken_registry = os.path.join(
            _ROOT, "tests", "fixtures", "course_fact_registry", "duplicate_id.json"
        )
        with self.assertRaises(CourseFactRegistryError):
            validate_pilot_content(data, registry_path=broken_registry)


class TestProductionPilotContentIsValid(unittest.TestCase):
    """The shipped mash-fundamentals pilot content against the real
    production registry (FACT-MASH-0001, FACT-MASH-0002, FACT-MASH-0004,
    issue #337). FACT-MASH-0003 is deliberately excluded -- it was left
    at status `draft` in the registry, pending an independent second
    source, per issue #337's own weaken-rather-than-force-promote rule."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_schema_version(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)

    def test_exactly_three_chunks(self):
        self.assertEqual(len(self.data["chunks"]), 3)

    def test_exactly_three_questions(self):
        self.assertEqual(len(self.data["questions"]), 3)

    def test_chunk_source_claims_cover_exactly_fact_mash_0001_0002_0004(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, {"FACT-MASH-0001", "FACT-MASH-0002", "FACT-MASH-0004"})

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_question_source_claims_are_subset_of_fact_mash_0001_0002_0004(self):
        allowed = {"FACT-MASH-0001", "FACT-MASH-0002", "FACT-MASH-0004"}
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= allowed)

    def test_no_new_factual_claims_are_introduced(self):
        all_claims = set()
        for chunk in self.data["chunks"]:
            all_claims.update(chunk["source_claims"])
        for question in self.data["questions"]:
            all_claims.update(question["source_claims"])
        self.assertEqual(all_claims, {"FACT-MASH-0001", "FACT-MASH-0002", "FACT-MASH-0004"})

    def test_fact_mash_0003_is_never_referenced(self):
        # FACT-MASH-0003 (iodine test) is still `draft`, not `verified` --
        # a source_claims reference to it would fail validation, so its
        # absence here is a structural guarantee, not just a convention.
        raw = json.dumps(self.data)
        self.assertNotIn("FACT-MASH-0003", raw)

    def test_exactly_five_distinct_concepts(self):
        concepts = set()
        for question in self.data["questions"]:
            concepts.update(question["concepts"])
        self.assertEqual(
            concepts,
            {
                "mashing.starch_conversion",
                "mashing.dextrins",
                "mashing.temperature",
                "mashing.fermentability",
                "mashing.process_variables",
            },
        )
        self.assertEqual(len(concepts), 5)

    def test_every_question_declares_stable_id_concepts_difficulty_and_source_claims(self):
        for question in self.data["questions"]:
            self.assertRegex(question["id"], r"^Q-[A-Z0-9]+-\d{3}$")
            self.assertTrue(question["concepts"])
            self.assertIn(question["difficulty"], DIFFICULTIES)
            self.assertTrue(question["source_claims"])

    def test_no_raw_score_field_anywhere_in_content(self):
        raw = json.dumps(self.data)
        self.assertNotIn('"score"', raw)


class TestRenderChunk(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)
        self.chunk = self.data["chunks"][0]

    def test_renders_norwegian(self):
        rendered = render_chunk(self.chunk, "no")
        self.assertEqual(rendered["id"], self.chunk["id"])
        self.assertEqual(rendered["text"], self.chunk["text"]["no"])

    def test_renders_english(self):
        rendered = render_chunk(self.chunk, "en")
        self.assertEqual(rendered["text"], self.chunk["text"]["en"])

    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_chunk(self.chunk, "de")


class TestRenderQuestion(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)
        self.question = self.data["questions"][0]

    def test_renders_prompt_and_options_in_requested_language(self):
        rendered = render_question(self.question, "en")
        self.assertEqual(rendered["prompt"], self.question["prompt"]["en"])
        self.assertEqual(
            [o["text"] for o in rendered["options"]],
            [o["text"]["en"] for o in self.question["options"]],
        )

    def test_never_reveals_which_option_is_correct(self):
        rendered = render_question(self.question, "no")
        for option in rendered["options"]:
            self.assertNotIn("correct", option)

    def test_never_reveals_feedback_up_front(self):
        rendered = render_question(self.question, "no")
        self.assertNotIn("feedback_correct", rendered)
        self.assertNotIn("feedback_incorrect", rendered)

    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_question(self.question, "de")


class TestEvaluateAnswer(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)
        self.question = self.data["questions"][0]
        self.correct_option_id = next(
            o["id"] for o in self.question["options"] if o["correct"]
        )
        self.incorrect_option_id = next(
            o["id"] for o in self.question["options"] if not o["correct"]
        )

    def test_correct_answer_returns_correct_feedback(self):
        result = evaluate_answer(self.question, self.correct_option_id, "en")
        self.assertTrue(result["correct"])
        self.assertEqual(result["feedback"], self.question["feedback_correct"]["en"])
        self.assertEqual(result["question_id"], self.question["id"])

    def test_incorrect_answer_returns_explanatory_feedback(self):
        result = evaluate_answer(self.question, self.incorrect_option_id, "no")
        self.assertFalse(result["correct"])
        self.assertEqual(result["feedback"], self.question["feedback_incorrect"]["no"])

    def test_unknown_option_id_raises(self):
        with self.assertRaises(ValueError):
            evaluate_answer(self.question, "no-such-option", "en")

    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            evaluate_answer(self.question, self.correct_option_id, "de")

    def test_result_never_carries_a_raw_numeric_score(self):
        result = evaluate_answer(self.question, self.correct_option_id, "en")
        self.assertNotIn("score", result)


if __name__ == "__main__":
    unittest.main()
