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

from bryggeskole.course_fact_registry import CourseFactRegistryError, get_verified_record
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
# pilot_fermentation now carries its own scoped basis rule (fermentation
# Kompetent contract §12: absent basis = fact, closed methodology allow-list),
# tested in tests/test_pilot_fermentation.py; the others still reject it.
# pilot_package likewise (package Kompetent contract §7).
_NO_METHODOLOGY_PILOTS = tuple(p for p in _EXISTING_PILOTS if p not in ("pilot_fermentation", "pilot_package"))

# Second slice: the fact-based fault chunks C-E and their questions. Every
# other item stays methodology with source_claims == [].
_FACT_CLAIMS = {
    "CHUNK-SENS-C": ["FACT-SENSORY-0001", "FACT-SENSORY-0002"],
    "CHUNK-SENS-D": ["FACT-SENSORY-0002", "FACT-BOIL-0002", "FACT-OXY-0002"],
    "CHUNK-SENS-E": ["FACT-SENSORY-0003"],
    "Q-SENS-007": ["FACT-SENSORY-0001"],
    "Q-SENS-008": ["FACT-SENSORY-0002", "FACT-BOIL-0002"],
    "Q-SENS-009": ["FACT-SENSORY-0002", "FACT-OXY-0002"],
    "Q-SENS-010": ["FACT-SENSORY-0003"],
}
_METHODOLOGY_IDS = {
    "CHUNK-SENS-A", "CHUNK-SENS-B", "CHUNK-SENS-F", "CHUNK-SENS-G",
    "Q-SENS-001", "Q-SENS-002", "Q-SENS-003", "Q-SENS-004", "Q-SENS-005", "Q-SENS-006",
}

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
        for name in _NO_METHODOLOGY_PILOTS:
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

    def test_chunks_are_a_to_g_in_contract_order(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]],
                         [f"CHUNK-SENS-{x}" for x in "ABCDEFG"])

    def test_questions_follow_chunk_order(self):
        # A, A, B, B, then the fault chunks C, D, D, E, then F, G.
        self.assertEqual([q["id"] for q in self.data["questions"]],
                         ["Q-SENS-001", "Q-SENS-002", "Q-SENS-003", "Q-SENS-004", "Q-SENS-007", "Q-SENS-008",
                          "Q-SENS-009", "Q-SENS-010", "Q-SENS-005", "Q-SENS-006"])

    def test_methodology_items_carry_no_fact_claims(self):
        for item in self.data["chunks"] + self.data["questions"]:
            if item["id"] in _METHODOLOGY_IDS:
                self.assertEqual(item["basis"], "methodology", item["id"])
                self.assertEqual(item["source_claims"], [], item["id"])

    def test_fault_items_have_the_exact_fact_basis_and_claims(self):
        items = {i["id"]: i for i in self.data["chunks"] + self.data["questions"]}
        for item_id, claims in _FACT_CLAIMS.items():
            self.assertEqual(items[item_id]["basis"], "fact", item_id)
            self.assertEqual(items[item_id]["source_claims"], claims, item_id)
            for claim in claims:
                self.assertIsNotNone(get_verified_record(DEFAULT_REGISTRY_PATH, claim), claim)
        self.assertEqual(set(items) - set(_FACT_CLAIMS), _METHODOLOGY_IDS)

    def test_question_concepts_match_the_prep_table(self):
        self.assertEqual(
            [q["concepts"] for q in self.data["questions"]],
            [["sensory.tasting_sequence"], ["sensory.tasting_habits"],
             ["sensory.observation_vs_interpretation"], ["sensory.observation_vs_interpretation"],
             ["sensory.diacetyl"], ["sensory.dms_recognition"], ["sensory.oxidation_recognition"],
             ["sensory.sourness_intent_vs_spoilage"],
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
        method_visible = []
        for chunk in self.data["chunks"]:
            visible.extend(chunk["text"].values())
            if chunk["id"] in _METHODOLOGY_IDS:
                method_visible.extend(chunk["text"].values())
        for q in self.data["questions"]:
            texts = [t for field in ("prompt", "feedback_correct", "feedback_incorrect") for t in q[field].values()]
            texts += [t for o in q["options"] for t in o["text"].values()]
            visible.extend(texts)
            if q["id"] in _METHODOLOGY_IDS:
                method_visible.extend(texts)
        self.visible = " ".join(visible).lower()
        self.method_visible = " ".join(method_visible).lower()
        self.teaching = " ".join(
            [t for c in self.data["chunks"] for t in c["text"].values()]
            + [t for q in self.data["questions"] for t in q["feedback_correct"].values()]
        ).lower()

    def test_no_numbers_or_units(self):
        self.assertNotRegex(self.visible, r"[0-9]")
        self.assertNotIn("°", self.visible)

    def test_no_compound_or_fault_names_in_the_methodology_items(self):
        # The methodology chunks/questions (A, B, F, G; Q-SENS-001..006) stay
        # free of compound and fault names; those live only in C-E.
        for banned in ("diacetyl", "dms", "dimetyl", "dimethyl", "acetaldehyd", "oksid", "oxid", "lightstruck",
                       "light-struck", "lyspåvirket", "skunk", "smør", "butter", "papp", "cardboard", "sulf", "svovel"):
            self.assertNotIn(banned, self.method_visible)

    def test_no_light_struck_content_anywhere(self):
        # Light-struck is DEFERRED until the S-3 record exists (#471 unknown).
        for banned in ("lightstruck", "light-struck", "light struck", "lyspåvirket", "lysskadet", "skunk",
                       "riboflavin", "brunt glass", "brown glass", "grønt glass", "green glass", "klart glass",
                       "clear glass", "sollys", "sunlight", "uv-lys", "uv light", "ultrafiolett", "ultraviolet"):
            self.assertIsNone(re.search(r"\b" + re.escape(banned), self.visible), banned)

    def test_no_infection_wording_and_no_microbiology_in_methodology(self):
        for banned in ("infeksjon", "infection", "infected", "infisert"):
            self.assertNotIn(banned, self.visible)
        for banned in ("forurens", "contaminat", "bakterie", "bacteria", "spoil", "bederv"):
            self.assertNotIn(banned, self.method_visible)

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



class TestFaultChunkGuardrails(unittest.TestCase):
    """Contract §§9-16, 24: recognise and describe carefully; descriptor is
    never diagnosis; no causes for acetaldehyde/sulphur; no health claim;
    light-struck deferred."""

    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)
        items = {i["id"]: i for i in self.data["chunks"] + self.data["questions"]}
        self.items = items

        def texts(item):
            if "text" in item:
                return list(item["text"].values())
            out = [t for f in ("prompt", "feedback_correct", "feedback_incorrect") for t in item[f].values()]
            return out + [t for o in item["options"] for t in o["text"].values()]

        fault_ids = list(_FACT_CLAIMS)
        self.fault_visible = " ".join(t for i in fault_ids for t in texts(items[i])).lower()
        self.fault_teaching = " ".join(
            [t for i in fault_ids if i.startswith("CHUNK") for t in items[i]["text"].values()]
            + [t for i in fault_ids if i.startswith("Q-") for t in items[i]["feedback_correct"].values()]
        ).lower()

    def test_no_en_symmetry(self):
        for item_id in _FACT_CLAIMS:
            item = self.items[item_id]
            bilinguals = [item["text"]] if "text" in item else (
                [item["prompt"], item["feedback_correct"], item["feedback_incorrect"]] + [o["text"] for o in item["options"]])
            for b in bilinguals:
                self.assertEqual(set(b), {"no", "en"}, item_id)
                self.assertTrue(b["no"].strip() and b["en"].strip(), item_id)

    def test_new_questions_are_beginner_fact_questions_with_existing_concepts(self):
        for qid in ("Q-SENS-007", "Q-SENS-008", "Q-SENS-009", "Q-SENS-010"):
            q = self.items[qid]
            self.assertEqual((q["type"], q["basis"], q["difficulty"]), ("scenario", "fact", "beginner"), qid)
            self.assertEqual(len(q["options"]), 3, qid)
            self.assertEqual(sum(1 for o in q["options"] if o["correct"]), 1, qid)
        concepts = {c for q in self.data["questions"] for c in q["concepts"]}
        for absent in ("sensory.lightstruck", "sensory.sulphur_observation", "sensory.acetaldehyde_recognition",
                       "sensory.diacetyl_recognition", "sensory.sourness", "sensory.spoilage"):
            self.assertNotIn(absent, concepts)
        self.assertEqual(set(METHODOLOGY_CONCEPTS), _APPROVED_METHODOLOGY_CONCEPTS)

    def test_descriptor_is_never_diagnosis(self):
        self.assertIn("«dette lukter smør» er en observasjon, ikke et bevis på diacetyl", self.fault_teaching)
        self.assertIn("en beskrivelse er ikke en diagnose", self.fault_teaching)
        self.assertIn("a descriptor is not a diagnosis", self.fault_teaching)
        self.assertIn("beviser ikke at kokingen var for kort", self.fault_teaching)
        self.assertIn("beviser ikke at du sprutet ved overføringen", self.fault_teaching)
        for banned in ("smør = diacetyl", "butter = diacetyl", "smør betyr diacetyl", "butter means diacetyl",
                       "betyr at kokingen var for kort", "means the boil was too short",
                       "gjæren sviktet helt sikkert", "the yeast definitely failed"):
            self.assertNotIn(banned, self.fault_teaching)

    def test_no_numbers_thresholds_or_fixed_rests(self):
        self.assertNotRegex(self.fault_visible, r"[0-9%°]")
        for banned in ("ppm", "ppb", "terskel", "threshold", "diacetylrast", "diacetyl rest", "minutt", "minute",
                       "dager", "days", "timer", "hours", "enzym", "enzyme"):
            self.assertNotIn(banned, self.fault_visible)

    def test_acetaldehyde_and_sulphur_carry_no_cause_or_maturation_claim(self):
        teaching = self.fault_teaching
        self.assertIn("beskrivelsen sier ingenting om årsaken", teaching)
        self.assertIn("uten å slutte noe om hva det skyldes", teaching)
        for banned in ("umodent", "immature", "green beer", "grønt øl", "trenger mer tid", "needs more time",
                       "forsvinner med tid", "fades with time", "går over", "goes away", "svovel betyr", "sulphur means",
                       "svovel er midlertidig", "sulphur is temporary", "stammeavhengig svovel"):
            self.assertNotIn(banned, self.fault_visible)

    def test_no_health_or_safety_claims_about_sourness_or_spoilage(self):
        for banned in ("farlig", "dangerous", "trygt", "safe", "usikkert", "unsafe", "helse", "health", "syk", "sick",
                       "ikke drikk", "do not drink", "don't drink", "udrikkelig", "undrinkable", "giftig", "toxic"):
            # Whole words: "healthy yeast" (FACT-SENSORY-0001) is not a health claim.
            self.assertIsNone(re.search(r"\b" + re.escape(banned) + r"\b", self.fault_visible), banned)
        self.assertIn("smaken alene viser bare at ølet er surere enn du ønsket", self.fault_teaching)
        self.assertIn("taste alone only shows that the beer is more sour than you intended", self.fault_teaching)

    def test_boil_and_oxygen_wording_traps(self):
        # FACT-BOIL-0002: the precursor is never the volatile material.
        self.assertIn("det er dms selv som er flyktig", self.fault_teaching)
        self.assertNotRegex(self.fault_visible, r"forstadi\w* (er|som er) flyktig|precursor (is|that is) volatile")
        # FACT-OXY-0002: a risk direction, never "instantly ruins".
        for banned in ("ødelegger alltid", "always ruins", "instantly", "med en gang ødelagt"):
            self.assertNotIn(banned, self.fault_visible)


if __name__ == "__main__":
    unittest.main()
