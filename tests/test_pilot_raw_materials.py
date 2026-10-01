"""
Tests for bryggeskole/pilot_raw_materials.py -- the Raavarer Foundation
module content/questions slice (issue #458, V2.2 Goal 3P, contract
slice 5).

Synthetic invalid-shape fixtures are reused from
tests/fixtures/pilot_fermentation/ (this module's validator is a
byte-for-byte copy of pilot_package.py's) together with the same registry
fixture used by the other pilot suites.

Run with:
    python3 -m unittest tests.test_pilot_raw_materials
"""
import io
import json
import os
import re
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError, read_registry_file
from bryggeskole.pilot_raw_materials import (
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

_SECTION_FACTS = {
    "malt": {"FACT-MALT-0001", "FACT-MALT-0002", "FACT-MALT-0003", "FACT-MALT-0004"},
    "hops": {"FACT-HOP-0001", "FACT-HOP-0002", "FACT-HOP-0003", "FACT-HOP-0004", "FACT-HOP-0005"},
    "yeast": {
        "FACT-YEAST-0001", "FACT-YEAST-0002", "FACT-YEAST-0003",
        "FACT-YEAST-0004", "FACT-YEAST-0005",
    },
    "water": {"FACT-WATER-0001", "FACT-WATER-0002", "FACT-WATER-0003"},
}
_REUSED_FACTS = {"FACT-MASH-0001", "FACT-MASH-0004", "FACT-BREW-0001", "FACT-BREW-0003"}
_ALLOWED_FACTS = set().union(*_SECTION_FACTS.values()) | _REUSED_FACTS


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
        self.assertEqual(self.data["topic_id"], "PILOT-RAW-MATERIALS-FUNDAMENTALS")

    def test_chunk_count_is_foundation_depth(self):
        self.assertGreaterEqual(len(self.data["chunks"]), 10)
        self.assertLessEqual(len(self.data["chunks"]), 12)

    def test_question_count_is_foundation_depth(self):
        self.assertGreaterEqual(len(self.data["questions"]), 10)
        self.assertLessEqual(len(self.data["questions"]), 14)

    def test_chunk_ids_are_unique_and_ordered(self):
        ids = [c["id"] for c in self.data["chunks"]]
        self.assertEqual(ids, sorted(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_four_sections_have_chunks_and_questions(self):
        for name, facts in _SECTION_FACTS.items():
            chunk_claims = set().union(*(set(c["source_claims"]) for c in self.data["chunks"]))
            question_claims = set().union(*(set(q["source_claims"]) for q in self.data["questions"]))
            self.assertTrue(chunk_claims & facts, f"no chunk covers section {name}")
            self.assertTrue(question_claims & facts, f"no question covers section {name}")

    def test_section_chunk_distribution_is_roughly_3_3_3_2(self):
        counts = {name: 0 for name in _SECTION_FACTS}
        for chunk in self.data["chunks"]:
            for name, facts in _SECTION_FACTS.items():
                if set(chunk["source_claims"]) & facts:
                    counts[name] += 1
                    break
        self.assertEqual(counts, {"malt": 3, "hops": 3, "yeast": 3, "water": 2})

    def test_only_already_verified_registry_facts_are_used(self):
        used = set()
        for chunk in self.data["chunks"]:
            used.update(chunk["source_claims"])
        for question in self.data["questions"]:
            used.update(question["source_claims"])
        self.assertTrue(used <= _ALLOWED_FACTS, f"unexpected facts: {used - _ALLOWED_FACTS}")
        registry = read_registry_file(DEFAULT_REGISTRY_PATH)
        records = registry["records"] if isinstance(registry, dict) and "records" in registry else registry
        status = {r["id"]: r["status"] for r in records}
        for fact_id in used:
            self.assertEqual(status.get(fact_id), "verified", fact_id)

    def test_every_question_source_claim_appears_in_a_chunk(self):
        chunk_claims = set()
        for chunk in self.data["chunks"]:
            chunk_claims.update(chunk["source_claims"])
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= chunk_claims, question["id"])

    def test_mix_of_concept_check_and_scenario(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_every_question_declares_id_concepts_difficulty_and_claims(self):
        for question in self.data["questions"]:
            self.assertRegex(question["id"], r"^Q-RAW-\d{3}$")
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
    """Guardrails taken from the registry records' own wording traps and
    the issue #458 content boundary."""

    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)
        self.text = _authoritative_text(self.data)
        self.everything = json.dumps(self.data, ensure_ascii=False).lower()

    def test_no_numeric_colour_dp_ph_or_shelf_life_values(self):
        for banned in (r"\b\d+\s*ebc\b", r"\b\d+\s*srm\b", r"lintner", r"congress mash", r"\bph\s*\d", r"\b\d+\s*months?\b", r"\b\d+\s*måneder"):
            self.assertNotRegex(self.everything, banned)

    def test_never_teaches_specialty_malt_cannot_convert(self):
        for banned in ("never converts", "aldri omdanner", "no enzymes", "ingen enzymer", "can never self-convert"):
            self.assertNotIn(banned, self.text)

    def test_never_equates_alpha_percent_with_ibu(self):
        for banned in ("alpha acid is the ibu", "alfasyreprosenten er ølets ibu", "= 12 ibu", "12 ibu"):
            self.assertNotIn(banned, self.text)

    def test_never_claims_late_hops_have_zero_or_negligible_bitterness(self):
        for banned in ("no bitterness at all", "negligible bitterness", "ubetydelig bitterhet", "ingen bitterhet i det hele tatt"):
            self.assertNotIn(banned, self.text)

    def test_never_teaches_boiling_as_universal_chlorine_fix(self):
        for banned in ("boil the water to remove", "koke vannet for å fjerne", "leave it overnight", "la det stå over natten"):
            self.assertNotIn(banned, self.text)

    def test_no_campden_or_water_dosing_content(self):
        for banned in ("campden", "ppm", "residual alkalinity", "restalkalitet", "mg/l"):
            self.assertNotIn(banned, self.everything)

    def test_never_teaches_always_aerate_or_cell_count_arithmetic(self):
        for banned in ("always aerate", "alltid lufte", "million cells", "millioner celler", "cells/ml", "celler/ml"):
            self.assertNotIn(banned, self.text)

    def test_never_claims_norwegian_chloramine_is_common(self):
        for banned in ("most norwegian", "many norwegian", "mange norske vannverk", "de fleste norske"):
            self.assertNotIn(banned, self.everything)

    def test_no_brand_or_strain_or_variety_catalogue(self):
        for banned in ("safale", "wlp", "wyeast", "fermentis us-05", "citra", "cascade", "pilsner malt", "maris otter"):
            self.assertNotIn(banned, self.everything)

    def test_no_questions_use_negation_trap_stems(self):
        # Anti-trick rule: prompts test brewing knowledge, not reading
        # vigilance -- no "which is NOT / all EXCEPT" stems.
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
        import bryggeskole.pilot_raw_materials as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+streamlit", source, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
