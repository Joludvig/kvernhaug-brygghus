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


# The temperature chunks use FACT-BREW-0001..0003 (#95). The Foundation
# completion slice (stage allocation contract §D.9) adds only already
# verified records: FACT-YEAST-0001 (yeast makes alcohol and CO2) and
# FACT-MEAS-0001/0002 (gravity falls during fermentation; stable repeated
# readings = plausibly finished; airlock not a reliable indicator).
_ALLOWED_FACTS = {
    "FACT-BREW-0001", "FACT-BREW-0002", "FACT-BREW-0003",
    "FACT-YEAST-0001", "FACT-MEAS-0001", "FACT-MEAS-0002",
}

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

    def test_exactly_four_chunks(self):
        # Three temperature chunks (#95) plus the Foundation completion
        # chunk CHUNK-FERM-D (stage allocation contract §D.9).
        self.assertEqual([c["id"] for c in self.data["chunks"]],
                         ["CHUNK-FERM-A", "CHUNK-FERM-B", "CHUNK-FERM-C", "CHUNK-FERM-D"])

    def test_chunk_source_claims_cover_exactly_the_allowed_facts(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, _ALLOWED_FACTS)
        self.assertEqual(self.data["chunks"][3]["source_claims"],
                         ["FACT-YEAST-0001", "FACT-MEAS-0001", "FACT-MEAS-0002"])

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)
        self.assertGreaterEqual(len(self.data["questions"]), 2)

    def test_question_source_claims_are_subset_of_the_allowed_facts(self):
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= _ALLOWED_FACTS)

    def test_no_new_factual_claims_are_introduced(self):
        all_claims = set()
        for chunk in self.data["chunks"]:
            all_claims.update(chunk["source_claims"])
        for question in self.data["questions"]:
            all_claims.update(question["source_claims"])
        self.assertEqual(all_claims, _ALLOWED_FACTS)

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



class TestFoundationCompletionSlice(unittest.TestCase):
    """Stage allocation contract §D.9: after pitching, airlock not proof,
    finished = repeated stable gravity readings, link to Måling -- only
    within FACT-YEAST-0001 and FACT-MEAS-0001/0002."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)
        self.chunk = self.data["chunks"][3]
        self.question = self.data["questions"][2]
        self.new_text = " ".join(
            list(self.chunk["text"].values())
            + [t for f in ("prompt", "feedback_correct", "feedback_incorrect") for t in self.question[f].values()]
            + [t for o in self.question["options"] for t in o["text"].values()]
        ).lower()
        self.teaching = " ".join(
            list(self.chunk["text"].values()) + list(self.question["feedback_correct"].values())
        ).lower()

    def test_exact_question_mapping_reuses_the_maaling_concept(self):
        q = self.question
        self.assertEqual((q["id"], q["type"], q["difficulty"]), ("Q-FERM-003", "scenario", "beginner"))
        self.assertEqual(q["concepts"], ["measurement.fermentation_complete"])
        self.assertEqual(q["source_claims"], ["FACT-MEAS-0002"])
        concepts = {c for qq in self.data["questions"] for c in qq["concepts"]}
        self.assertNotIn("fermentation.complete", concepts)
        self.assertNotIn("fermentation.completion", concepts)

    def test_no_en_symmetry(self):
        for bilingual in [self.chunk["text"], self.question["prompt"], self.question["feedback_correct"],
                          self.question["feedback_incorrect"]] + [o["text"] for o in self.question["options"]]:
            self.assertEqual(set(bilingual), {"no", "en"})
            self.assertTrue(bilingual["no"].strip() and bilingual["en"].strip())

    def test_after_pitching_wording(self):
        self.assertIn("etter pitching gjærer gjæren det forgjærbare sukkeret", self.teaching)
        self.assertIn("lager alkohol og co₂", self.teaching)
        self.assertIn("after pitching, the yeast ferments the fermentable sugar", self.teaching)

    def test_stable_readings_and_maaling_link(self):
        self.assertIn("som har sluttet å endre seg, tyder på at gjæringen sannsynligvis er ferdig", self.teaching)
        self.assertIn("that have stopped changing indicate that fermentation has plausibly finished", self.teaching)
        self.assertIn("med litt tid imellom", self.teaching)
        self.assertIn("måling og bryggelogg", self.teaching)
        self.assertIn("measurement and brew log", self.teaching)

    def test_airlock_is_never_proof_or_an_activity_diagnostic(self):
        self.assertIn("luftlåsen er ikke et pålitelig tegn", self.teaching)
        self.assertIn("the airlock is not a reliable sign", self.teaching)
        for banned in ("bobler betyr", "bubbles mean", "bubbling means", "sunn gjæring", "healthy fermentation",
                       "ingen bobler betyr", "no bubbles means", "har stoppet, så", "stopped, so",
                       "luftlåsen viser", "the airlock shows"):
            self.assertNotIn(banned, self.teaching)

    def test_no_unsupported_signs_phases_days_or_kompetent_depth(self):
        self.assertNotRegex(self.new_text, r"[0-9]")
        for banned in ("skum", "krausen", "foam", "lukt", "smell", "lyd", "sound", "synlig", "visible",
                       "fase", "phase", "lag-", "døgn", "dag", "day", "timer", "hour", "uke", "week",
                       "diacetyl", "modning", "conditioning", "maturation", "starter", "viabilitet", "viability",
                       "pitchemengde", "pitch rate", "trykkgjæring", "pressure", "høst", "harvest",
                       "glykolyse", "glycolysis", "stuck", "stall", "hengt seg", "flaskebombe", "bottle bomb", "eksplo"):
            self.assertNotRegex(self.new_text, r"\b" + banned)

    def test_stable_is_not_package_now_and_not_the_planned_fg(self):
        for banned in ("pakk med en gang", "package immediately", "klar til å pakkes", "ready to package",
                       "planlagte fg", "planned fg", "bevist", "proven", "proves"):
            self.assertNotIn(banned, self.new_text)


if __name__ == "__main__":
    unittest.main()
