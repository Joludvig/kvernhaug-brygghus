"""
Tests for bryggeskole/pilot_cleaning_safety.py -- the Rengjøring og
sikkerhet Foundation module content/questions slice (issue #473, V2.2
Goal 3R, contract docs/development/v22_g3r_cleaning_safety_module_contract.md
§10 slice 4).

Synthetic invalid-shape fixtures are reused from
tests/fixtures/pilot_fermentation/ (this module's validator is a
byte-for-byte copy of pilot_raw_materials.py's) together with the same
registry fixture used by the other pilot suites.

Run with:
    python3 -m unittest tests.test_pilot_cleaning_safety
"""
import io
import json
import os
import re
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError, read_registry_file
from bryggeskole.pilot_cleaning_safety import (
    DEFAULT_PILOT_PATH,
    DEFAULT_REGISTRY_PATH,
    DIFFICULTIES,
    PILOT_SCHEMA_VERSION,
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

_ALLOWED_FACTS = {
    "FACT-SAFE-0001", "FACT-SAFE-0002", "FACT-SAFE-0003",
    "FACT-COOL-0001", "FACT-COOL-0003", "FACT-BOIL-0004", "FACT-PACK-0003",
}
_CHUNK_IDS = [f"CHUNK-SAFE-{letter}" for letter in "ABCDEFG"]
_QUESTION_IDS = [f"Q-SAFE-{n:03d}" for n in range(1, 9)]
_EXPECTED_CONCEPTS = {
    "hygiene.clean_vs_sanitize", "hygiene.clean_first", "cool.sanitation_boundary",
    "safety.chem_handling", "safety.fermentation_co2", "package.pressure_safety",
}


def _fixture_path(name):
    return os.path.join(_FIXTURES, name)


def _load_fixture(name):
    with io.open(_fixture_path(name), encoding="utf-8") as fh:
        return json.load(fh)


def _authoritative_text(data):
    """Chunk text plus correct-answer feedback: the text that teaches.
    Prompts/wrong options may voice a misconception as the thing to
    reject, so they are deliberately excluded."""
    parts = []
    for chunk in data["chunks"]:
        parts.extend(chunk["text"].values())
    for question in data["questions"]:
        parts.extend(question["feedback_correct"].values())
        parts.extend(o["text"][lang] for o in question["options"] if o["correct"] for lang in ("no", "en"))
    return " ".join(parts).lower()


class TestValidMinimalFixturePasses(unittest.TestCase):
    def test_no_errors_against_registry_fixture(self):
        data = _load_fixture("valid_minimal.json")
        self.assertEqual(validate_pilot_content(data, registry_path=_REGISTRY_FIXTURE), [])


class TestUnverifiedOrMissingClaimFailsClosed(unittest.TestCase):
    def test_missing_claim_reports_error(self):
        errors = validate_pilot_content(_load_fixture("missing_claim.json"), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("FACT-TEST-9999" in e for e in errors))

    def test_unverified_claim_reports_error(self):
        errors = validate_pilot_content(_load_fixture("unverified_claim.json"), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("FACT-TEST-0023" in e for e in errors))

    def test_read_pilot_file_raises_on_invalid(self):
        with self.assertRaises(PilotContentError):
            read_pilot_file(_fixture_path("missing_claim.json"), registry_path=_REGISTRY_FIXTURE)

    def test_malformed_registry_propagates_registry_error(self):
        broken = os.path.join(_ROOT, "tests", "fixtures", "course_fact_registry", "duplicate_id.json")
        with self.assertRaises(CourseFactRegistryError):
            validate_pilot_content(_load_fixture("valid_minimal.json"), registry_path=broken)


class TestProductionPilotContentIsValid(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)

    def test_schema_version_and_topic_id(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)
        self.assertEqual(self.data["topic_id"], "PILOT-CLEANING-SAFETY-FUNDAMENTALS")

    def test_exactly_seven_chunks_in_order(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]], _CHUNK_IDS)

    def test_exactly_eight_questions_in_order(self):
        self.assertEqual([q["id"] for q in self.data["questions"]], _QUESTION_IDS)

    def test_only_the_seven_verified_facts_are_used_and_all_are_taught(self):
        chunk_claims = set().union(*(set(c["source_claims"]) for c in self.data["chunks"]))
        question_claims = set().union(*(set(q["source_claims"]) for q in self.data["questions"]))
        self.assertEqual(chunk_claims, _ALLOWED_FACTS)
        self.assertTrue(question_claims <= _ALLOWED_FACTS)
        registry = read_registry_file(DEFAULT_REGISTRY_PATH)
        status = {r["id"]: r["status"] for r in registry["records"]}
        for fact_id in chunk_claims | question_claims:
            self.assertEqual(status.get(fact_id), "verified", fact_id)

    def test_every_question_source_claim_appears_in_a_chunk(self):
        chunk_claims = set().union(*(set(c["source_claims"]) for c in self.data["chunks"]))
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= chunk_claims, question["id"])

    def test_boil_over_is_text_only_never_a_question(self):
        # Owner decision (#473): boil-over awareness is a chunk, not a quiz question.
        boil_chunks = [c["id"] for c in self.data["chunks"] if "FACT-BOIL-0004" in c["source_claims"]]
        self.assertEqual(boil_chunks, ["CHUNK-SAFE-E"])
        for question in self.data["questions"]:
            self.assertNotIn("FACT-BOIL-0004", question["source_claims"], question["id"])
            self.assertNotIn("boil.observation", question["concepts"], question["id"])

    def test_fermentation_co2_is_explicitly_taught_and_tested(self):
        # Owner decision (contract §13): CO2 at L1 = MUST, never buried.
        co2_chunks = [c for c in self.data["chunks"] if "FACT-SAFE-0003" in c["source_claims"]]
        self.assertEqual(len(co2_chunks), 1)
        self.assertIn("CO₂", co2_chunks[0]["text"]["no"])
        self.assertIn("ventilasjon", co2_chunks[0]["text"]["no"])
        co2_questions = [q for q in self.data["questions"] if "safety.fermentation_co2" in q["concepts"]]
        self.assertEqual(len(co2_questions), 1)

    def test_concepts_are_exactly_the_contract_mastery_ids(self):
        concepts = set().union(*(set(q["concepts"]) for q in self.data["questions"]))
        self.assertEqual(concepts, _EXPECTED_CONCEPTS)

    def test_mix_of_concept_check_and_scenario(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_every_question_declares_id_concepts_difficulty_and_claims(self):
        for question in self.data["questions"]:
            self.assertRegex(question["id"], r"^Q-SAFE-\d{3}$")
            self.assertTrue(question["concepts"])
            self.assertIn(question["difficulty"], DIFFICULTIES)
            self.assertTrue(question["source_claims"])

    def test_every_question_has_three_options_with_one_correct(self):
        for question in self.data["questions"]:
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


class TestWordingGuardrails(unittest.TestCase):
    """Guardrails from the registry records' own notes (FACT-SAFE-0001..0003,
    FACT-COOL-0003, FACT-BOIL-0004, FACT-PACK-0003) and contract §7."""

    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)
        self.text = _authoritative_text(self.data)
        self.everything = json.dumps(self.data, ensure_ascii=False).lower()

    def test_sanitering_is_glossed_at_first_use(self):
        # Locked decision (#473) + FACT-SAFE-0001 notes: keep "sanitering"
        # and gloss it where the learner first meets it (chunks are read
        # before questions, in order).
        reading_order = [c["text"]["no"].lower() for c in self.data["chunks"]]
        first_use = next(i for i, text in enumerate(reading_order) if "saniter" in text)
        self.assertEqual(first_use, 0)
        gloss = reading_order[0]
        self.assertIn("*sanitering* om å redusere mengden mikroorganismer", gloss)
        self.assertIn("ikke det samme som sterilisering", gloss)

    def test_sanitering_not_presented_as_official_or_as_desinfeksjon(self):
        for banned in ("desinfeksjon", "offisielle", "official norwegian"):
            self.assertNotIn(banned, self.everything)

    def test_never_teaches_sanitised_equals_sterile(self):
        for banned in ("blir steril", "becomes sterile", "is sterile", "er sterilt", "sanitizing sterilizes", "steriliserer"):
            self.assertNotIn(banned, self.text)

    def test_no_numbers_doses_or_contact_times(self):
        # Learner-visible text only (ids like FACT-SAFE-0001 legitimately
        # contain digits). [0-9], not str.isdigit(): the subscript in CO₂
        # counts as a digit for isdigit().
        visible = []
        for chunk in self.data["chunks"]:
            visible.extend(chunk["text"].values())
        for q in self.data["questions"]:
            for field in ("prompt", "feedback_correct", "feedback_incorrect"):
                visible.extend(q[field].values())
            for o in q["options"]:
                visible.extend(o["text"].values())
        self.assertNotRegex(" ".join(visible), r"[0-9]")
        for banned in ("ppm", "mg/l", "%", "kontakttid", "contact time", "psi", "konsentrasjon", "concentration"):
            self.assertNotIn(banned, self.everything)

    def test_no_brand_or_product_names(self):
        for banned in ("star san", "pbw", "five star", "chemipro", "iodophor", "jodofor", "klorin"):
            self.assertNotIn(banned, self.everything)

    def test_co2_neither_dangerous_nor_harmless_and_no_procedures(self):
        for banned in ("farlig", "dangerous", "harmless", "heavier than air", "tyngre enn luft",
                       "alarm", "monitor", "måler", "confined space"):
            self.assertNotIn(banned, self.everything)

    def test_no_spoiled_beer_health_claim(self):
        for banned in ("make you sick", "gjøre deg syk", "nothing survives", "ingenting overlever"):
            self.assertNotIn(banned, self.everything)

    def test_no_first_aid_cip_or_chlorine_gas_rule(self):
        for banned in ("first aid", "førstehjelp", "brannskade", "burn", "klorgass", "chlorine gas"):
            self.assertNotIn(banned, self.everything)
        self.assertNotRegex(self.everything, r"\bcip\b")

    def test_damaged_is_not_broadened_to_bottles_and_no_unrated(self):
        # FACT-PACK-0003 notes (#448): 'damaged' evidence is keg/valve/coupler
        # scope; no bottle-specific 'damaged' source exists.
        for banned in ("damaged bottle", "skadet flaske", "skadede flasker", "cracked", "sprukne", "chipped", "unrated"):
            self.assertNotIn(banned, self.everything)

    def test_no_questions_use_negation_trap_stems(self):
        for question in self.data["questions"]:
            for lang in ("no", "en"):
                prompt = question["prompt"][lang].lower()
                self.assertNotRegex(prompt, r"\b(except|not true|which is not|unntatt|hvilket er ikke|hva er ikke)\b")


class TestRender(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)

    def test_render_chunk_both_languages(self):
        chunk = self.data["chunks"][0]
        self.assertEqual(render_chunk(chunk, "no")["text"], chunk["text"]["no"])
        self.assertEqual(render_chunk(chunk, "en")["text"], chunk["text"]["en"])

    def test_render_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_chunk(self.data["chunks"][0], "de")
        with self.assertRaises(ValueError):
            render_question(self.data["questions"][0], "de")

    def test_render_question_never_reveals_answer_or_feedback(self):
        rendered = render_question(self.data["questions"][0], "no")
        self.assertNotIn("feedback_correct", rendered)
        self.assertNotIn("feedback_incorrect", rendered)
        for option in rendered["options"]:
            self.assertNotIn("correct", option)


class TestEvaluateAnswer(unittest.TestCase):
    def setUp(self):
        self.question = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)["questions"][0]

    def test_correct_and_incorrect_feedback(self):
        correct = next(o["id"] for o in self.question["options"] if o["correct"])
        wrong = next(o["id"] for o in self.question["options"] if not o["correct"])
        ok = evaluate_answer(self.question, correct, "en")
        bad = evaluate_answer(self.question, wrong, "no")
        self.assertTrue(ok["correct"])
        self.assertEqual(ok["feedback"], self.question["feedback_correct"]["en"])
        self.assertFalse(bad["correct"])
        self.assertEqual(bad["feedback"], self.question["feedback_incorrect"]["no"])
        self.assertNotIn("score", ok)

    def test_unknown_option_and_language_raise(self):
        with self.assertRaises(ValueError):
            evaluate_answer(self.question, "zzz", "en")
        with self.assertRaises(ValueError):
            evaluate_answer(self.question, "a", "de")


class TestNoStreamlitImport(unittest.TestCase):
    def test_module_is_pure(self):
        import bryggeskole.pilot_cleaning_safety as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+streamlit", source, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
