"""
Tests for bryggeskole/pilot_fermentation.py -- the fermentation-temperature
pilot content/questions slice (V2-3A, issue #95).

Synthetic invalid-shape fixtures under tests/fixtures/pilot_fermentation/
reference a registry fixture that already exists for the Course Fact
Registry's own consumer-API tests
(tests/fixtures/course_fact_registry/verified_consumer_mixed.json), which
conveniently carries both a verified id (FACT-TEST-0020) and a draft
(unverified) id (FACT-TEST-0023) -- exactly the two cases this module's
source_claims validation must reject identically.

Run with:
    python3 -m unittest tests.test_pilot_fermentation
"""
import io
import json
import os
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError
from bryggeskole.pilot_fermentation import (
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
        # Same error template, only the claim id differs -- the trusted
        # boundary must never distinguish "missing" from "not verified".
        missing_template = missing_errors[0].replace("FACT-TEST-9999", "<id>")
        unverified_template = unverified_errors[0].replace("FACT-TEST-0023", "<id>")
        self.assertEqual(missing_template, unverified_template)


class TestEmptySourceClaimsFailsClosed(unittest.TestCase):
    def test_reports_error(self):
        errors = validate_pilot_content(
            _load_fixture("empty_source_claims.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("source_claims" in e and "non-empty" in e for e in errors))


class TestQuestionIdFailsClosed(unittest.TestCase):
    def test_bad_id_pattern(self):
        errors = validate_pilot_content(
            _load_fixture("bad_question_id.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("invalid id" in e for e in errors))

    def test_missing_id(self):
        errors = validate_pilot_content(
            _load_fixture("missing_question_id.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("missing required field 'id'" in e for e in errors))

    def test_duplicate_id(self):
        errors = validate_pilot_content(
            _load_fixture("duplicate_question_id.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("duplicate id" in e for e in errors))


class TestChunkIdFailsClosed(unittest.TestCase):
    def test_duplicate_chunk_id(self):
        errors = validate_pilot_content(
            _load_fixture("duplicate_chunk_id.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("duplicate id" in e and "chunks" in e for e in errors))


class TestBilingualTextFailsClosed(unittest.TestCase):
    def test_missing_no_text_in_question_prompt(self):
        errors = validate_pilot_content(
            _load_fixture("missing_no_text.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("missing or empty 'no' text" in e for e in errors))

    def test_missing_en_text_in_chunk(self):
        errors = validate_pilot_content(
            _load_fixture("missing_en_text.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("missing or empty 'en' text" in e for e in errors))


class TestMalformedOptionsFailClosed(unittest.TestCase):
    def test_too_few_options(self):
        errors = validate_pilot_content(
            _load_fixture("malformed_options_too_few.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("at least 2 entries" in e for e in errors))

    def test_wrong_correct_count(self):
        errors = validate_pilot_content(
            _load_fixture("malformed_options_wrong_correct_count.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("exactly one option must have 'correct': true" in e for e in errors))


class TestMissingFeedbackFailsClosed(unittest.TestCase):
    def test_missing_feedback_incorrect(self):
        errors = validate_pilot_content(
            _load_fixture("missing_feedback_incorrect.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("missing required field 'feedback_incorrect'" in e for e in errors))


class TestUnknownFieldFailsClosed(unittest.TestCase):
    def test_reports_error(self):
        errors = validate_pilot_content(
            _load_fixture("unknown_field.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("unknown top-level field" in e.lower() for e in errors))


class TestMalformedDocumentShapeFailsClosed(unittest.TestCase):
    def test_non_object_document(self):
        errors = validate_pilot_content(
            _load_fixture("invalid_document_shape.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("must be a JSON object", errors[0])


class TestEnumeratedFieldsFailClosed(unittest.TestCase):
    def test_bad_difficulty(self):
        errors = validate_pilot_content(
            _load_fixture("bad_difficulty.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("invalid difficulty" in e for e in errors))

    def test_bad_type(self):
        errors = validate_pilot_content(
            _load_fixture("bad_type.json"), registry_path=_REGISTRY_FIXTURE
        )
        self.assertTrue(any("invalid type" in e for e in errors))

    def test_value_sets_are_as_documented(self):
        self.assertEqual(DIFFICULTIES, ("beginner", "intermediate", "advanced"))
        self.assertEqual(QUESTION_TYPES, ("concept_check", "scenario"))


class TestMalformedRegistryPropagatesRegistryError(unittest.TestCase):
    """A malformed *registry* (not pilot content) is a distinct failure
    category -- claim resolution has no meaningful fallback, so
    CourseFactRegistryError propagates rather than being downgraded to a
    pilot-content error string."""

    def test_validate_pilot_content_propagates(self):
        data = _load_fixture("valid_minimal.json")
        broken_registry = os.path.join(
            _ROOT, "tests", "fixtures", "course_fact_registry", "duplicate_id.json"
        )
        with self.assertRaises(CourseFactRegistryError):
            validate_pilot_content(data, registry_path=broken_registry)


class TestProductionPilotContentIsValid(unittest.TestCase):
    """The shipped V2-3A pilot content against the real production
    registry (which now carries FACT-BREW-0001..0003, issue #93)."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_schema_version(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)

    def test_exactly_three_chunks(self):
        self.assertEqual(len(self.data["chunks"]), 3)

    def test_chunk_source_claims_cover_exactly_fact_brew_0001_to_0003(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, {"FACT-BREW-0001", "FACT-BREW-0002", "FACT-BREW-0003"})

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)
        self.assertGreaterEqual(len(self.data["questions"]), 2)

    def test_question_source_claims_are_subset_of_fact_brew_0001_to_0003(self):
        allowed = {"FACT-BREW-0001", "FACT-BREW-0002", "FACT-BREW-0003"}
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= allowed)

    def test_no_new_factual_claims_are_introduced(self):
        all_claims = set()
        for chunk in self.data["chunks"]:
            all_claims.update(chunk["source_claims"])
        for question in self.data["questions"]:
            all_claims.update(question["source_claims"])
        self.assertEqual(all_claims, {"FACT-BREW-0001", "FACT-BREW-0002", "FACT-BREW-0003"})

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
