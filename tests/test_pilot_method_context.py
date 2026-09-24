"""
Tests for bryggeskole/pilot_method_context.py -- the method-context-
fundamentals pilot content/questions slice (issue #380, V2.2 Goal 3I).

Synthetic invalid-shape fixtures are reused from
tests/fixtures/pilot_fermentation/ (this module's validator is a
byte-for-byte copy of pilot_fermentation.py's/pilot_mashing.py's/
pilot_boil_hop.py's/pilot_cool_transfer.py's/pilot_package.py's) together
with the same registry fixture used by those suites
(tests/fixtures/course_fact_registry/verified_consumer_mixed.json),
which conveniently carries both a verified id (FACT-TEST-0020) and a
draft (unverified) id (FACT-TEST-0023) -- exactly the two cases this
module's source_claims validation must reject identically.

Run with:
    python3 -m unittest tests.test_pilot_method_context
"""
import io
import json
import os
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError
from bryggeskole.pilot_method_context import (
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
    "FACT-MASH-0001", "FACT-BOIL-0001",
    "FACT-METHOD-0001", "FACT-METHOD-0002", "FACT-METHOD-0003",
    "FACT-METHOD-0004", "FACT-METHOD-0005",
}

_EXPECTED_CHUNK_IDS = [
    "CHUNK-METHOD-A", "CHUNK-METHOD-B", "CHUNK-METHOD-C", "CHUNK-METHOD-D", "CHUNK-METHOD-E",
]

_EXPECTED_CONCEPTS = {
    "method.shared_process", "method.biab", "method.traditional_allgrain",
    "method.all_in_one", "method.planning_variables", "method.no_hierarchy",
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
    """The shipped method-context-fundamentals pilot content against the
    real production registry (FACT-MASH-0001 + FACT-BOIL-0001 reused,
    FACT-METHOD-0001..0005 new, issue #380)."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_schema_version(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)

    def test_topic_id(self):
        self.assertEqual(self.data["topic_id"], "PILOT-METHOD-CONTEXT-FUNDAMENTALS")

    def test_exactly_five_chunks_with_expected_ids_in_order(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]], _EXPECTED_CHUNK_IDS)

    def test_at_least_one_question_per_chunk_count_is_compact(self):
        self.assertGreaterEqual(len(self.data["questions"]), 5)
        self.assertLessEqual(len(self.data["questions"]), 10)

    def test_chunk_source_claims_cover_exactly_the_seven_method_facts(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, _ALL_FACTS)

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_question_source_claims_are_subset_of_the_seven_method_facts(self):
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

    def test_exactly_six_distinct_concepts(self):
        concepts = set()
        for question in self.data["questions"]:
            concepts.update(question["concepts"])
        self.assertEqual(concepts, _EXPECTED_CONCEPTS)
        self.assertEqual(len(concepts), 6)

    def test_every_question_declares_stable_id_concepts_difficulty_and_source_claims(self):
        for question in self.data["questions"]:
            self.assertRegex(question["id"], r"^Q-[A-Z0-9]+-\d{3}$")
            self.assertTrue(question["concepts"])
            self.assertIn(question["difficulty"], DIFFICULTIES)
            self.assertTrue(question["source_claims"])

    def test_no_raw_score_field_anywhere_in_content(self):
        raw = json.dumps(self.data)
        self.assertNotIn('"score"', raw)

    def test_reuses_shared_concept_id_from_mashing_and_boil_hop_modules(self):
        # §3.5 of the module contract: method.shared_process is a
        # module-local mastery concept covering the REUSED facts
        # FACT-MASH-0001/FACT-BOIL-0001 -- the Registry `concepts` on
        # those two records themselves are unchanged (still
        # mashing.starch_conversion/boil.enzyme_inactivation), this
        # module's own question just re-teaches the same underlying facts
        # under a new, module-local concept id.
        chunk_a = next(c for c in self.data["chunks"] if c["id"] == "CHUNK-METHOD-A")
        self.assertEqual(set(chunk_a["source_claims"]), {"FACT-MASH-0001", "FACT-BOIL-0001"})
        question = next(q for q in self.data["questions"] if "method.shared_process" in q["concepts"])
        self.assertEqual(set(question["source_claims"]), {"FACT-MASH-0001", "FACT-BOIL-0001"})

    def test_wording_never_frames_biab_as_beginner_only(self):
        # Issue #380 §3 critical guardrail: never teach BIAB as
        # "beginner-only". Only authoritative text (chunk text, correct
        # feedback) is checked -- prompts/wrong-answer options may voice
        # the misconception as the thing to reject.
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("biab er bare for nybegynnere", joined)
        self.assertNotIn("biab is only for beginners", joined)
        self.assertNotIn("biab er en nybegynnermetode", joined)
        self.assertNotIn("biab is a beginner method", joined)

    def test_wording_never_frames_traditional_as_proper_or_superior(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("den ordentlige måten å brygge på", joined)
        self.assertNotIn("the proper way to brew", joined)
        self.assertNotIn("ekte brygging krever separate kar", joined)
        self.assertNotIn("real brewing requires separate vessels", joined)

    def test_wording_never_frames_all_in_one_as_inherently_better_or_worse(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("alt-i-ett gir bedre øl", joined)
        self.assertNotIn("all-in-one makes better beer", joined)
        self.assertNotIn("alt-i-ett er alltid enklere", joined)
        self.assertNotIn("all-in-one is always easier", joined)

    def test_wording_never_asserts_one_method_produces_better_beer(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("gir et bedre øl enn", joined)
        self.assertNotIn("produces better beer than", joined)

    def test_wording_never_states_a_fixed_water_or_dead_space_number(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        for banned in (r"\d+\s*liter", r"\d+\s*l\b", r"\d+\s*%"):
            self.assertNotRegex(joined, banned)

    def test_no_specific_equipment_brand_or_model_named(self):
        raw = json.dumps(self.data).lower()
        for banned in ("grainfather", "blichmann", "ss brewtech", "brewzilla", "anvil foundry"):
            self.assertNotIn(banned, raw)

    def test_no_sparge_technique_choice_lesson(self):
        # Issue #380 hard non-goal: no full batch-vs-fly sparge technique
        # lesson (that remains web/hjelp/bryggemetoder.html's own separate
        # discovery-aid content, out of this module's beginner scope).
        raw = json.dumps(self.data).lower()
        for banned in ("batch-sparge", "batch sparge", "fly-sparge", "fly sparge"):
            self.assertNotIn(banned, raw)


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
