"""
Tests for bryggeskole/pilot_sensory.py -- the Smak og evaluering module,
first slice: methodology chunks 1, 2, 6 and 7 (issue #472, V2.2 Goal 3S).

Two things are tested here:
1. the scoped `basis` extension (Chief decision D1 on #472) -- only this
   pilot accepts basis "methodology", which must carry source_claims == []
   and may only use the closed METHODOLOGY_CONCEPTS allow-list; basis
   "fact" keeps the normal verified-claims rule; a missing/unknown basis
   fails;
2. regression: every EXISTING pilot still rejects methodology records, so
   no old validator was relaxed.

The shared tests/fixtures/pilot_fermentation/ documents carry no `basis`,
so this suite builds its small fixtures in-test against the same registry
fixture the other pilot suites use.

Run with:
    python3 -m unittest tests.test_pilot_sensory
"""
import copy
import importlib
import json
import os
import re
import tempfile
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError
from bryggeskole.pilot_sensory import (
    BASES,
    DEFAULT_PILOT_PATH,
    DEFAULT_REGISTRY_PATH,
    DIFFICULTIES,
    METHODOLOGY_CONCEPTS,
    PILOT_SCHEMA_VERSION,
    PilotContentError,
    evaluate_answer,
    read_pilot_file,
    render_chunk,
    render_question,
    validate_pilot_content,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REGISTRY_FIXTURE = os.path.join(
    _ROOT, "tests", "fixtures", "course_fact_registry", "verified_consumer_mixed.json"
)
_VERIFIED_FIXTURE_FACT = "FACT-TEST-0020"
_DRAFT_FIXTURE_FACT = "FACT-TEST-0023"

_APPROVED_METHODOLOGY_CONCEPTS = {
    "sensory.tasting_sequence",
    "sensory.observation_vs_interpretation",
    "sensory.evaluate_against_intent",
    "sensory.fault_vs_character",
    "sensory.tasting_habits",
    "sensory.expectation_note",
}

_EXISTING_PILOTS = (
    "pilot_boil_hop", "pilot_cleaning_safety", "pilot_cool_transfer", "pilot_fermentation",
    "pilot_mashing", "pilot_method_context", "pilot_package", "pilot_raw_materials",
)


def _bi(no, en):
    return {"no": no, "en": en}


def _question(basis="methodology", concepts=("sensory.tasting_sequence",), claims=()):
    return {
        "id": "Q-TEST-001",
        "type": "concept_check",
        "basis": basis,
        "concepts": list(concepts),
        "difficulty": "beginner",
        "source_claims": list(claims),
        "prompt": _bi("Spørsmål?", "Question?"),
        "options": [
            {"id": "a", "text": _bi("Riktig", "Right"), "correct": True},
            {"id": "b", "text": _bi("Feil", "Wrong"), "correct": False},
        ],
        "feedback_correct": _bi("Riktig.", "Correct."),
        "feedback_incorrect": _bi("Ikke helt.", "Not quite."),
    }


def _doc():
    """A minimal valid sensory document: one methodology chunk, one fact
    chunk (verified fixture claim), one methodology question."""
    return {
        "schema_version": 1,
        "topic_id": "PILOT-TEST",
        "chunks": [
            {"id": "CHUNK-TEST-A", "basis": "methodology", "source_claims": [], "text": _bi("Metode.", "Method.")},
            {"id": "CHUNK-TEST-B", "basis": "fact", "source_claims": [_VERIFIED_FIXTURE_FACT],
             "text": _bi("Fakta.", "Fact.")},
        ],
        "questions": [_question()],
    }


def _validate(doc):
    return validate_pilot_content(doc, registry_path=_REGISTRY_FIXTURE)


class TestScopedBasisRules(unittest.TestCase):
    def test_minimal_mixed_document_is_valid(self):
        self.assertEqual(_validate(_doc()), [])

    def test_bases_and_allow_list_are_exactly_the_locked_sets(self):
        self.assertEqual(BASES, ("fact", "methodology"))
        self.assertEqual(set(METHODOLOGY_CONCEPTS), _APPROVED_METHODOLOGY_CONCEPTS)

    def test_methodology_chunk_with_claims_fails(self):
        doc = _doc()
        doc["chunks"][0]["source_claims"] = [_VERIFIED_FIXTURE_FACT]
        errors = _validate(doc)
        self.assertTrue(any("requires 'source_claims' to be an empty list" in e for e in errors), errors)

    def test_methodology_question_with_claims_fails(self):
        doc = _doc()
        doc["questions"][0]["source_claims"] = [_VERIFIED_FIXTURE_FACT]
        self.assertTrue(any("empty list" in e for e in _validate(doc)))

    def test_fact_chunk_keeps_normal_source_requirements(self):
        for claims, expected in (([], "must be a non-empty list"),
                                 ([_DRAFT_FIXTURE_FACT], _DRAFT_FIXTURE_FACT),
                                 (["FACT-TEST-9999"], "FACT-TEST-9999")):
            with self.subTest(claims=claims):
                doc = _doc()
                doc["chunks"][1]["source_claims"] = claims
                self.assertTrue(any(expected in e for e in _validate(doc)), _validate(doc))

    def test_fact_question_keeps_normal_source_requirements(self):
        doc = _doc()
        doc["questions"][0] = _question(basis="fact", concepts=("any.concept",), claims=())
        self.assertTrue(any("must be a non-empty list" in e for e in _validate(doc)))
        doc["questions"][0] = _question(basis="fact", concepts=("any.concept",), claims=(_VERIFIED_FIXTURE_FACT,))
        self.assertEqual(_validate(doc), [])

    def test_missing_basis_fails_for_chunk_and_question(self):
        doc = _doc()
        del doc["chunks"][0]["basis"]
        del doc["questions"][0]["basis"]
        errors = _validate(doc)
        self.assertTrue(any("chunks[0]: missing required field 'basis'" in e for e in errors), errors)
        self.assertTrue(any("questions[0]: missing required field 'basis'" in e for e in errors), errors)

    def test_missing_basis_never_relaxes_the_claim_rule(self):
        # Fail-closed: without a valid basis, empty claims are still rejected.
        doc = _doc()
        del doc["chunks"][0]["basis"]
        self.assertTrue(any("must be a non-empty list" in e for e in _validate(doc)))

    def test_unknown_basis_fails(self):
        for bad in ("opinion", "Methodology", "", None):
            with self.subTest(basis=bad):
                doc = _doc()
                doc["chunks"][0]["basis"] = bad
                self.assertTrue(any("invalid basis" in e for e in _validate(doc)))

    def test_only_approved_methodology_concepts_are_accepted(self):
        for concept in sorted(_APPROVED_METHODOLOGY_CONCEPTS):
            with self.subTest(concept=concept):
                doc = _doc()
                doc["questions"][0] = _question(concepts=(concept,))
                self.assertEqual(_validate(doc), [])
        for concept in ("sensory.diacetyl", "sensory.typical_descriptors", "sensory.new_idea", "malt.colour_flavour"):
            with self.subTest(concept=concept):
                doc = _doc()
                doc["questions"][0] = _question(concepts=(concept,))
                self.assertTrue(any("not an approved methodology concept" in e for e in _validate(doc)))

    def test_read_pilot_file_raises_on_invalid(self):
        doc = _doc()
        doc["chunks"][0]["basis"] = "opinion"
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "invalid.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(doc, fh)
            with self.assertRaises(PilotContentError):
                read_pilot_file(path, registry_path=_REGISTRY_FIXTURE)

    def test_malformed_registry_propagates_registry_error(self):
        broken = os.path.join(_ROOT, "tests", "fixtures", "course_fact_registry", "duplicate_id.json")
        with self.assertRaises(CourseFactRegistryError):
            validate_pilot_content(_doc(), registry_path=broken)


class TestExistingPilotsUnchanged(unittest.TestCase):
    """Regression for D1's scope: no existing pilot accepts methodology
    records, and their production content still validates."""

    def _methodology_doc(self):
        doc = _doc()
        del doc["chunks"][1]
        return doc

    def test_every_existing_pilot_rejects_methodology_records(self):
        for name in _EXISTING_PILOTS:
            with self.subTest(pilot=name):
                module = importlib.import_module(f"bryggeskole.{name}")
                self.assertFalse(hasattr(module, "METHODOLOGY_CONCEPTS"))
                errors = module.validate_pilot_content(self._methodology_doc(), registry_path=_REGISTRY_FIXTURE)
                self.assertTrue(any("unknown field(s) ['basis']" in e for e in errors), errors)
                self.assertTrue(any("must be a non-empty list" in e for e in errors), errors)

    def test_every_existing_pilot_production_content_still_valid(self):
        for name in _EXISTING_PILOTS:
            with self.subTest(pilot=name):
                module = importlib.import_module(f"bryggeskole.{name}")
                module.read_pilot_file()


class TestProductionPilotContent(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)

    def test_schema_version_and_topic_id(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)
        self.assertEqual(self.data["topic_id"], "PILOT-SENSORY-EVALUATION")

    def test_chunks_are_a_b_f_g_with_c_to_e_reserved(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]],
                         ["CHUNK-SENS-A", "CHUNK-SENS-B", "CHUNK-SENS-F", "CHUNK-SENS-G"])

    def test_six_questions_in_order(self):
        self.assertEqual([q["id"] for q in self.data["questions"]], [f"Q-SENS-{n:03d}" for n in range(1, 7)])

    def test_this_slice_is_methodology_only_with_no_fact_claims(self):
        for item in self.data["chunks"] + self.data["questions"]:
            self.assertEqual(item["basis"], "methodology", item["id"])
            self.assertEqual(item["source_claims"], [], item["id"])

    def test_question_concepts_match_the_prep_table(self):
        self.assertEqual(
            [q["concepts"] for q in self.data["questions"]],
            [["sensory.tasting_sequence"], ["sensory.tasting_habits"],
             ["sensory.observation_vs_interpretation"], ["sensory.observation_vs_interpretation"],
             ["sensory.fault_vs_character"], ["sensory.evaluate_against_intent"]],
        )

    def test_mix_of_concept_check_and_scenario(self):
        types = {q["type"] for q in self.data["questions"]}
        self.assertEqual(types, {"concept_check", "scenario"})

    def test_every_question_has_three_options_with_one_correct(self):
        for question in self.data["questions"]:
            self.assertIn(question["difficulty"], DIFFICULTIES)
            self.assertEqual(len(question["options"]), 3, question["id"])
            self.assertEqual(sum(1 for o in question["options"] if o["correct"]), 1, question["id"])

    def test_no_en_symmetry_no_empty_text(self):
        def texts(data):
            for chunk in data["chunks"]:
                yield chunk["text"]
            for q in data["questions"]:
                yield q["prompt"]
                yield q["feedback_correct"]
                yield q["feedback_incorrect"]
                for o in q["options"]:
                    yield o["text"]

        for bilingual in texts(self.data):
            self.assertEqual(set(bilingual), {"no", "en"})
            self.assertTrue(bilingual["no"].strip())
            self.assertTrue(bilingual["en"].strip())

    def test_no_raw_score_field(self):
        self.assertNotIn('"score"', json.dumps(self.data))


class TestContentSafetyGuardrails(unittest.TestCase):
    """Locked content-safety rules (#472) and contract §§16-20, 24, 33."""

    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)
        visible = []
        for chunk in self.data["chunks"]:
            visible.extend(chunk["text"].values())
        for q in self.data["questions"]:
            for field in ("prompt", "feedback_correct", "feedback_incorrect"):
                visible.extend(q[field].values())
            for o in q["options"]:
                visible.extend(o["text"].values())
        self.visible = " ".join(visible).lower()
        self.teaching = " ".join(
            [t for c in self.data["chunks"] for t in c["text"].values()]
            + [t for q in self.data["questions"] for t in q["feedback_correct"].values()]
        ).lower()

    def test_no_numbers_or_units(self):
        self.assertNotRegex(self.visible, r"[0-9]")
        self.assertNotIn("°", self.visible)

    def test_no_compound_or_fault_names_in_this_slice(self):
        for banned in ("diacetyl", "dms", "dimetyl", "dimethyl", "acetaldehyd", "oksid", "oxid", "lightstruck",
                       "light-struck", "lyspåvirket", "skunk", "smør", "butter", "papp", "cardboard", "sulf", "svovel"):
            self.assertNotIn(banned, self.visible)

    def test_no_contamination_or_microbiology_claims(self):
        for banned in ("infeksjon", "infection", "infected", "forurens", "contaminat", "bakterie", "bacteria",
                       "spoil", "bederv"):
            self.assertNotIn(banned, self.visible)

    def test_no_scores_sliders_bjcp_or_automatic_diagnosis(self):
        for banned in ("poeng", "points", "score", "slider", "glidebryter", "flavorprofile", "bjcp",
                       "appen diagnostiserer", "the app diagnoses", "automatic diagnosis"):
            self.assertNotIn(banned, self.visible)

    def test_expectation_note_never_claims_bias_is_removed(self):
        for banned in ("removes bias", "fjerner påvirkningen", "eliminates", "fjerner all"):
            self.assertNotIn(banned, self.visible)
        self.assertIn("kan redusere noe av den effekten", self.teaching)

    def test_teaching_never_equates_preference_or_style_with_fault(self):
        for banned in ("hvis noen ikke liker det, er det en feil", "if someone does not like it, it is a fault"):
            self.assertNotIn(banned, self.teaching)
        self.assertIn("gjør det ikke til en feil", self.teaching)
        self.assertIn("ikke i seg selv en feil", self.teaching)

    def test_teaching_keeps_one_observation_from_becoming_proof(self):
        self.assertIn("én observasjon beviser aldri en årsak", self.teaching)
        self.assertIn("«jeg vet ikke ennå» er et fullverdig svar", self.teaching)

    def test_no_questions_use_negation_trap_stems(self):
        for question in self.data["questions"]:
            for lang in ("no", "en"):
                prompt = question["prompt"][lang].lower()
                self.assertNotRegex(prompt, r"\b(except|not true|which is not|unntatt|hvilket er ikke|hva er ikke)\b")


class TestRenderAndEvaluate(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)

    def test_render_exposes_basis_for_the_ui_label(self):
        self.assertEqual(render_chunk(self.data["chunks"][0], "no")["basis"], "methodology")
        self.assertEqual(render_question(self.data["questions"][0], "en")["basis"], "methodology")

    def test_render_question_never_reveals_answer_or_feedback(self):
        rendered = render_question(self.data["questions"][0], "no")
        self.assertNotIn("feedback_correct", rendered)
        for option in rendered["options"]:
            self.assertNotIn("correct", option)

    def test_render_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_chunk(self.data["chunks"][0], "de")

    def test_evaluate_answer(self):
        question = copy.deepcopy(self.data["questions"][0])
        correct = next(o["id"] for o in question["options"] if o["correct"])
        wrong = next(o["id"] for o in question["options"] if not o["correct"])
        self.assertTrue(evaluate_answer(question, correct, "en")["correct"])
        self.assertFalse(evaluate_answer(question, wrong, "no")["correct"])


class TestNoStreamlitImport(unittest.TestCase):
    def test_module_is_pure(self):
        import bryggeskole.pilot_sensory as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+streamlit", source, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
