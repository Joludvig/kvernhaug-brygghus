"""
Tests for bryggeskole/pilot_boil_hop.py -- the boil/hop-fundamentals
pilot content/questions slice (issue #366, V2.2 Goal 3C).

Synthetic invalid-shape fixtures are reused from
tests/fixtures/pilot_fermentation/ (this module's validator is a
byte-for-byte copy of pilot_fermentation.py's/pilot_mashing.py's, so the
same shape-failure fixtures exercise it identically) together with the
same registry fixture used by those suites
(tests/fixtures/course_fact_registry/verified_consumer_mixed.json),
which conveniently carries both a verified id (FACT-TEST-0020) and a
draft (unverified) id (FACT-TEST-0023) -- exactly the two cases this
module's source_claims validation must reject identically.

Run with:
    python3 -m unittest tests.test_pilot_boil_hop
"""
import io
import json
import os
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError
from bryggeskole.pilot_boil_hop import (
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

_ALL_FACTS = {
    "FACT-BOIL-0001", "FACT-BOIL-0002", "FACT-BOIL-0003", "FACT-BOIL-0004",
    "FACT-HOP-0001", "FACT-HOP-0002", "FACT-HOP-0003",
}

_EXPECTED_CHUNK_IDS = [
    "CHUNK-BOILHOP-A", "CHUNK-BOILHOP-B", "CHUNK-BOILHOP-C",
    "CHUNK-BOILHOP-D", "CHUNK-BOILHOP-E", "CHUNK-BOILHOP-F",
]

_EXPECTED_CONCEPTS = {
    "boil.enzyme_inactivation", "boil.volatile_removal", "boil.hot_break", "boil.observation",
    "hop.isomerization_time", "hop.aroma_volatility", "hop.addition_strategy", "hop.whirlpool_technique",
}


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
    """The shipped boil/hop-fundamentals pilot content against the real
    production registry (FACT-BOIL-0001..0004, FACT-HOP-0001..0003,
    issue #366)."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_schema_version(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)

    def test_topic_id(self):
        self.assertEqual(self.data["topic_id"], "PILOT-BOIL-HOP-FUNDAMENTALS")

    def test_exactly_six_chunks_with_expected_ids_in_order(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]], _EXPECTED_CHUNK_IDS)

    def test_at_least_one_question_per_chunk_count_is_compact(self):
        # "compact set sufficient to cover the six chunks" (issue #366) --
        # not pinned to an exact count elsewhere, but bounded here so a
        # future accidental duplication/explosion of questions is caught.
        self.assertGreaterEqual(len(self.data["questions"]), 6)
        self.assertLessEqual(len(self.data["questions"]), 10)

    def test_chunk_source_claims_cover_exactly_the_seven_boil_hop_facts(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, _ALL_FACTS)

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_question_source_claims_are_subset_of_the_seven_boil_hop_facts(self):
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= _ALL_FACTS)

    def test_no_new_factual_claims_are_introduced(self):
        all_claims = set()
        for chunk in self.data["chunks"]:
            all_claims.update(chunk["source_claims"])
        for question in self.data["questions"]:
            all_claims.update(question["source_claims"])
        self.assertEqual(all_claims, _ALL_FACTS)

    def test_every_fact_is_referenced_by_at_least_one_question(self):
        referenced = set()
        for question in self.data["questions"]:
            referenced.update(question["source_claims"])
        self.assertEqual(referenced, _ALL_FACTS)

    def test_exactly_eight_distinct_concepts(self):
        concepts = set()
        for question in self.data["questions"]:
            concepts.update(question["concepts"])
        self.assertEqual(concepts, _EXPECTED_CONCEPTS)
        self.assertEqual(len(concepts), 8)

    def test_every_question_declares_stable_id_concepts_difficulty_and_source_claims(self):
        for question in self.data["questions"]:
            self.assertRegex(question["id"], r"^Q-[A-Z0-9]+-\d{3}$")
            self.assertTrue(question["concepts"])
            self.assertIn(question["difficulty"], DIFFICULTIES)
            self.assertTrue(question["source_claims"])

    def test_no_raw_score_field_anywhere_in_content(self):
        raw = json.dumps(self.data)
        self.assertNotIn('"score"', raw)

    def test_no_ibu_calculation_task_anywhere_in_content(self):
        # §1's explicit non-goal: not an IBU math lesson -- no learning
        # task should ask the learner to compute or recite an IBU number.
        # (A bare "ibu" substring check is too broad: it false-positives
        # inside ordinary English words like "contribute"/"distribute".)
        raw = json.dumps(self.data).lower()
        self.assertNotIn(" ibu ", raw)
        self.assertNotIn("ibu-", raw)
        self.assertNotIn("-ibu", raw)

    def test_dms_precursor_volatility_trap_question_has_correct_explanation(self):
        # The issue's own critical factual guardrail: never teach that the
        # DMS precursor itself is volatile/boiled off -- DMS is what is
        # volatile, the precursor is what forms it. CHUNK-BOILHOP-B's text
        # and Q-BOILHOP-002's *correct* feedback must state the guardrail
        # directly; the false claim legitimately appears elsewhere in that
        # question only as a wrong-answer distractor, so this test checks
        # the authoritative explanatory text, not a blanket string ban.
        chunk_b = next(c for c in self.data["chunks"] if c["id"] == "CHUNK-BOILHOP-B")
        question = next(q for q in self.data["questions"] if q["id"] == "Q-BOILHOP-002")
        correct_option_id = next(o["id"] for o in question["options"] if o["correct"])
        for lang in ("no", "en"):
            self.assertIn("DMS", chunk_b["text"][lang])
            self.assertIn("DMS", question["feedback_correct"][lang])
        self.assertEqual(correct_option_id, "a")

    def test_dms_precursor_never_asserted_as_volatile_in_authoritative_text(self):
        # Only chunk text and feedback are authoritative teaching text (the
        # question prompt and wrong-answer options are allowed to state the
        # false claim as the thing to reject).
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
            authoritative.extend(question["feedback_incorrect"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("precursor is volatile", joined)
        self.assertNotIn("precursor itself is volatile", joined)
        self.assertNotIn("precursoren er flyktig", joined)
        self.assertNotIn("precursoren selv er flyktig", joined)


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
