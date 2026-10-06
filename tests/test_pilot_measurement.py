"""
Tests for bryggeskole/pilot_measurement.py -- the Måling og bryggelogg
module, Foundation slice (V2.2, contract
docs/development/v22_measurement_brewlog_module_contract.md §21.2 and the
§22 implementation draft; offline implementation, no GitHub issue yet).

Covers:
1. the locked shape: exactly CHUNK-MEAS-A..E and Q-MEAS-001..006, all
   beginner, with the exact basis / concepts / source_claims per §22;
2. the module's own scoped basis rule and closed methodology allow-list
   (shared concept sensory.observation_vs_interpretation, never a
   duplicate log.observation_vs_interpretation);
3. the binding wording traps (§19, §21.4, §22 content rules) as guardrails.

Run with:
    python3 -m unittest tests.test_pilot_measurement
"""
import copy
import json
import os
import re
import tempfile
import unittest

from bryggeskole.course_fact_registry import get_verified_record
from bryggeskole.pilot_measurement import (
    BASES,
    DEFAULT_PILOT_PATH,
    DEFAULT_REGISTRY_PATH,
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

# Contract §22 tables, verbatim.
_CHUNKS = [
    ("CHUNK-MEAS-A", "methodology", []),
    ("CHUNK-MEAS-B", "fact", ["FACT-MEAS-0001"]),
    ("CHUNK-MEAS-C", "fact", ["FACT-MEAS-0002"]),
    ("CHUNK-MEAS-D", "fact", ["FACT-MEAS-0003"]),
    ("CHUNK-MEAS-E", "methodology", []),
]
_QUESTIONS = [
    ("Q-MEAS-001", "concept_check", "fact", ["measurement.gravity"], ["FACT-MEAS-0001"]),
    ("Q-MEAS-002", "scenario", "fact", ["measurement.fermentation_complete"], ["FACT-MEAS-0002"]),
    ("Q-MEAS-003", "scenario", "methodology", ["log.planned_vs_actual"], []),
    ("Q-MEAS-004", "scenario", "methodology", ["measurement.temperature"], []),
    ("Q-MEAS-005", "concept_check", "fact", ["measurement.hydrometer_temperature"], ["FACT-MEAS-0003"]),
    ("Q-MEAS-006", "scenario", "methodology", ["sensory.observation_vs_interpretation"], []),
]
_ALLOWED_FACTS = {"FACT-MEAS-0001", "FACT-MEAS-0002", "FACT-MEAS-0003", "FACT-YEAST-0002"}


def _bi(no, en):
    return {"no": no, "en": en}


def _doc():
    return {
        "schema_version": 1,
        "topic_id": "PILOT-TEST",
        "chunks": [
            {"id": "CHUNK-TEST-A", "basis": "methodology", "source_claims": [], "text": _bi("Metode.", "Method.")},
            {"id": "CHUNK-TEST-B", "basis": "fact", "source_claims": [_VERIFIED_FIXTURE_FACT],
             "text": _bi("Fakta.", "Fact.")},
        ],
        "questions": [{
            "id": "Q-TEST-001", "type": "scenario", "basis": "methodology",
            "concepts": ["log.planned_vs_actual"], "difficulty": "beginner", "source_claims": [],
            "prompt": _bi("Spørsmål?", "Question?"),
            "options": [
                {"id": "a", "text": _bi("Riktig", "Right"), "correct": True},
                {"id": "b", "text": _bi("Feil", "Wrong"), "correct": False},
            ],
            "feedback_correct": _bi("Riktig.", "Correct."),
            "feedback_incorrect": _bi("Ikke helt.", "Not quite."),
        }],
    }


def _validate(doc):
    return validate_pilot_content(doc, registry_path=_REGISTRY_FIXTURE)


class TestScopedBasisRules(unittest.TestCase):
    def test_minimal_document_is_valid(self):
        self.assertEqual(_validate(_doc()), [])

    def test_bases_and_allow_list_are_exactly_the_locked_sets(self):
        self.assertEqual(BASES, ("fact", "methodology"))
        self.assertEqual(set(METHODOLOGY_CONCEPTS), {
            "log.planned_vs_actual", "measurement.temperature", "sensory.observation_vs_interpretation",
        })
        self.assertNotIn("log.observation_vs_interpretation", METHODOLOGY_CONCEPTS)

    def test_methodology_with_claims_fails(self):
        doc = _doc()
        doc["chunks"][0]["source_claims"] = [_VERIFIED_FIXTURE_FACT]
        self.assertTrue(any("empty list" in e for e in _validate(doc)))

    def test_missing_or_unknown_basis_fails(self):
        doc = _doc()
        del doc["chunks"][0]["basis"]
        self.assertTrue(any("missing required field 'basis'" in e for e in _validate(doc)))
        doc = _doc()
        doc["questions"][0]["basis"] = "opinion"
        self.assertTrue(any("invalid basis" in e for e in _validate(doc)))

    def test_unapproved_methodology_concept_fails(self):
        for concept in ("log.observation_vs_interpretation", "measurement.volume", "log.hypothesis_next_change",
                        "sensory.tasting_sequence"):
            with self.subTest(concept=concept):
                doc = _doc()
                doc["questions"][0]["concepts"] = [concept]
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


class TestProductionPilotContent(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)

    def test_schema_version_and_topic_id(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)
        self.assertEqual(self.data["topic_id"], "PILOT-MEASUREMENT-FUNDAMENTALS")

    def test_exact_chunks_in_order(self):
        self.assertEqual(
            [(c["id"], c["basis"], c["source_claims"]) for c in self.data["chunks"]],
            [(i, b, s) for i, b, s in _CHUNKS],
        )

    def test_exact_questions_in_order(self):
        self.assertEqual(
            [(q["id"], q["type"], q["basis"], q["concepts"], q["source_claims"]) for q in self.data["questions"]],
            [tuple(row) for row in _QUESTIONS],
        )

    def test_all_questions_beginner_with_three_options_one_correct(self):
        for q in self.data["questions"]:
            self.assertEqual(q["difficulty"], "beginner", q["id"])
            self.assertEqual(len(q["options"]), 3, q["id"])
            self.assertEqual(sum(1 for o in q["options"] if o["correct"]), 1, q["id"])

    def test_every_fact_claim_is_verified_and_allowed(self):
        for item in self.data["chunks"] + self.data["questions"]:
            for claim in item["source_claims"]:
                self.assertIn(claim, _ALLOWED_FACTS, item["id"])
                self.assertIsNotNone(get_verified_record(DEFAULT_REGISTRY_PATH, claim), claim)
        # FACT-YEAST-0002 is optional and only ever allowed on CHUNK-MEAS-B.
        for item in self.data["chunks"][2:] + self.data["questions"]:
            self.assertNotIn("FACT-YEAST-0002", item["source_claims"], item["id"])

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

    def test_minimum_log_lists_the_seven_locked_items(self):
        # Contract §9: brew date, OG, fermentation temperature + where/how,
        # FG, volume into the fermenter, package date, observation notes.
        log_no = self.data["chunks"][4]["text"]["no"].lower()
        log_en = self.data["chunks"][4]["text"]["en"].lower()
        for needle in ("bryggedato", "og (målt før gjæren tilsettes)", "gjæringstemperatur og hvor eller hvordan",
                       "fg (målt etter gjentatte stabile målinger)", "volumet som gikk inn i gjæringskaret",
                       "pakkedato", "observasjoner"):
            self.assertIn(needle, log_no)
        for needle in ("brew date", "og (measured before the yeast goes in)", "fermentation temperature and where or how",
                       "fg (measured after repeated stable readings)", "volume that went into the fermenter",
                       "package date", "observations"):
            self.assertIn(needle, log_en)

    def test_no_raw_score_field(self):
        self.assertNotIn('"score"', json.dumps(self.data))


class TestWordingGuardrails(unittest.TestCase):
    """Binding wording traps: contract §19, §21.2-§21.4 and §22."""

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

    def test_no_numbers_units_or_time_spans(self):
        self.assertNotRegex(self.visible, r"[0-9]")
        for banned in ("°", "døgn", " dager", " dag ", " timer", " days", " day ", " hours", " uke", " week"):
            self.assertNotIn(banned, self.visible)

    def test_no_formulas_or_kompetent_measurement_depth(self):
        for banned in ("abv", "alkoholprosent", "formel", "formula", "plato", "brix", "effektivitet", "efficiency",
                       "utbytte", "yield", "refraktometer", "refractometer", "korreksjonsfaktor", "correction factor",
                       "kalibrer", "calibrat", "mesketemperatur", "mash temperature", "hypotese", "hypothesis",
                       "neste endring", "next change"):
            self.assertNotIn(banned, self.visible)

    def test_no_room_vs_beer_temperature_claim(self):
        # Removed from Foundation until a verified fact supports it (§21.4, M5).
        for banned in ("romtemperatur", "room temperature", "varmer opp ølet", "warms the beer",
                       "ikke det samme som ølets temperatur", "not the same as the beer"):
            self.assertNotIn(banned, self.visible)

    def test_volume_is_never_mapped_to_the_app_field(self):
        for banned in ("volumel", "volume_l", "bryggedag", "brew day panel", "appen lagrer", "the app stores",
                       "post-boil", "etter koking"):
            self.assertNotIn(banned, self.visible)
        self.assertIn("volumet som gikk inn i gjæringskaret", self.teaching)
        self.assertIn("bryggeloggen eller notatene dine", self.teaching)

    def test_og_fg_are_measurements_not_targets(self):
        self.assertIn("begge er **målinger**", self.teaching)
        self.assertIn("det er en plan, ikke en måling", self.teaching)
        for banned in ("fg er den laveste", "fg is the lowest", "fg er tallet oppskriften", "fg is the number the recipe"):
            self.assertNotIn(banned, self.teaching)

    def test_completion_needs_repeated_readings_and_airlock_is_not_proof(self):
        self.assertIn("én måling alene sier ikke det", self.teaching)
        self.assertIn("luftlåsen er ikke et pålitelig tegn", self.teaching)
        self.assertIn("med litt tid imellom", self.teaching)
        self.assertIn("ikke automatisk den fg-en oppskriften planla", self.teaching)
        for banned in ("luftlåsen har stoppet, så", "the airlock stopped, so"):
            self.assertNotIn(banned, self.visible)

    def test_raw_reading_is_never_overwritten(self):
        self.assertIn("skriv aldri over en målt verdi", self.teaching)
        self.assertIn("never write over a measured value", self.teaching)

    def test_plan_vs_actual_is_evidence_not_a_grade(self):
        self.assertIn("ikke en karakter og ikke en diagnose", self.teaching)
        for banned in ("godt brygg", "dårlig brygg", "good brew", "bad brew"):
            self.assertNotIn(banned, self.visible)
        self.assertNotRegex(self.visible, r"\b(poeng|points|score|karakteren din|your grade)\b")

    def test_no_duplicate_observation_concept(self):
        self.assertNotIn("log.observation_vs_interpretation", json.dumps(self.data))

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
        self.assertEqual(render_chunk(self.data["chunks"][1], "en")["basis"], "fact")
        self.assertEqual(render_question(self.data["questions"][2], "en")["basis"], "methodology")

    def test_render_question_never_reveals_answer_or_feedback(self):
        rendered = render_question(self.data["questions"][0], "no")
        self.assertNotIn("feedback_correct", rendered)
        for option in rendered["options"]:
            self.assertNotIn("correct", option)

    def test_evaluate_answer(self):
        for question in self.data["questions"]:
            question = copy.deepcopy(question)
            correct = next(o["id"] for o in question["options"] if o["correct"])
            wrong = next(o["id"] for o in question["options"] if not o["correct"])
            self.assertTrue(evaluate_answer(question, correct, "en")["correct"])
            self.assertFalse(evaluate_answer(question, wrong, "no")["correct"])


class TestNoStreamlitImport(unittest.TestCase):
    def test_module_is_pure(self):
        import bryggeskole.pilot_measurement as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+streamlit", source, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
