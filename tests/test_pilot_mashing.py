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
    BASES,
    DEFAULT_PILOT_PATH,
    DEFAULT_REGISTRY_PATH,
    DIFFICULTIES,
    METHODOLOGY_CONCEPTS,
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

# Foundation (#337) uses FACT-MASH-0001/0002/0004. The Kompetent slice
# (mashing Kompetent contract §6.1/§7.1) adds the verified M1/M2 records
# FACT-MASH-0005/0006 and reuses the verified FACT-METHOD-0001…0005.
_FOUNDATION_FACTS = {"FACT-MASH-0001", "FACT-MASH-0002", "FACT-MASH-0004"}
_KOMPETENT_FACTS = {
    "FACT-MASH-0005", "FACT-MASH-0006",
    "FACT-METHOD-0001", "FACT-METHOD-0002", "FACT-METHOD-0003", "FACT-METHOD-0004", "FACT-METHOD-0005",
}
_ALL_FACTS = _FOUNDATION_FACTS | _KOMPETENT_FACTS

_FOUNDATION_CHUNK_IDS = ["CHUNK-MASH-A", "CHUNK-MASH-B", "CHUNK-MASH-C"]
_KOMPETENT_CHUNKS = [
    ("CHUNK-MASH-D", "fact",
     ["FACT-METHOD-0001", "FACT-METHOD-0002", "FACT-METHOD-0003", "FACT-METHOD-0005", "FACT-MASH-0005"]),
    ("CHUNK-MASH-E", "fact", ["FACT-MASH-0006", "FACT-METHOD-0004"]),
    ("CHUNK-MASH-F", "methodology", []),
]
_KOMPETENT_QUESTIONS = [
    ("Q-MASH-004", "concept_check", "fact", ["mashing.grain_separation"],
     ["FACT-METHOD-0001", "FACT-METHOD-0002", "FACT-METHOD-0003"]),
    ("Q-MASH-005", "scenario", "fact", ["mashing.grain_separation"], ["FACT-MASH-0005"]),
    ("Q-MASH-006", "scenario", "fact", ["mashing.wort_collection"], ["FACT-MASH-0006"]),
    ("Q-MASH-007", "scenario", "fact", ["method.planning_variables"], ["FACT-METHOD-0004"]),
    ("Q-MASH-008", "scenario", "methodology", ["mashing.preboil_check"], []),
]
_KOMPETENT_IDS = {r[0] for r in _KOMPETENT_CHUNKS + _KOMPETENT_QUESTIONS}
_EXPECTED_CHUNK_IDS = _FOUNDATION_CHUNK_IDS + [r[0] for r in _KOMPETENT_CHUNKS]


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

    def test_foundation_then_kompetent_chunks_in_order(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]], _EXPECTED_CHUNK_IDS)

    def test_three_foundation_plus_five_kompetent_questions(self):
        self.assertEqual([q["id"] for q in self.data["questions"]], [f"Q-MASH-00{n}" for n in range(1, 9)])

    def test_foundation_chunk_source_claims_cover_exactly_fact_mash_0001_0002_0004(self):
        referenced = set()
        for chunk in self.data["chunks"][:3]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, _FOUNDATION_FACTS)

    def test_chunk_source_claims_cover_all_facts(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, _ALL_FACTS)

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_question_source_claims_are_subset_of_the_allowed_facts(self):
        for question in self.data["questions"][:3]:
            self.assertTrue(set(question["source_claims"]) <= _FOUNDATION_FACTS)
        for question in self.data["questions"]:
            self.assertTrue(set(question["source_claims"]) <= _ALL_FACTS)

    def test_no_new_factual_claims_are_introduced(self):
        all_claims = set()
        for chunk in self.data["chunks"]:
            all_claims.update(chunk["source_claims"])
        for question in self.data["questions"]:
            all_claims.update(question["source_claims"])
        self.assertEqual(all_claims, _ALL_FACTS)

    def test_fact_mash_0003_is_never_referenced(self):
        # FACT-MASH-0003 (iodine test) is still `draft`, not `verified` --
        # a source_claims reference to it would fail validation, so its
        # absence here is a structural guarantee, not just a convention.
        raw = json.dumps(self.data)
        self.assertNotIn("FACT-MASH-0003", raw)

    def test_exactly_the_expected_concepts(self):
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
                # Kompetent: two new fact concepts, one methodology concept
                # and the reused Forberedelse/metode planning concept.
                "mashing.grain_separation",
                "mashing.wort_collection",
                "mashing.preboil_check",
                "method.planning_variables",
            },
        )
        self.assertEqual(len(concepts), 9)

    def test_every_question_declares_stable_id_concepts_difficulty_and_source_claims(self):
        for question in self.data["questions"]:
            self.assertRegex(question["id"], r"^Q-[A-Z0-9]+-\d{3}$")
            self.assertTrue(question["concepts"])
            self.assertIn(question["difficulty"], DIFFICULTIES)
            if question.get("basis", "fact") == "fact":
                self.assertTrue(question["source_claims"])
            else:
                self.assertEqual(question["source_claims"], [])

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


def _minimal_with(chunk_extra=None, question_extra=None):
    data = _load_fixture("valid_minimal.json")
    if chunk_extra is not None:
        data["chunks"].append(chunk_extra)
    if question_extra is not None:
        q = json.loads(json.dumps(data["questions"][0]))
        q["id"] = "Q-TEST-099"
        q.update(question_extra)
        data["questions"].append(q)
    return data


class TestScopedBasisRule(unittest.TestCase):
    """Mashing Kompetent contract §7: optional basis. Absent means "fact"
    (Foundation unchanged); "methodology" needs empty source_claims and, on
    a question, the approved methodology concept; unknown fails closed."""

    def test_value_sets(self):
        self.assertEqual(BASES, ("fact", "methodology"))
        self.assertEqual(METHODOLOGY_CONCEPTS, frozenset({"mashing.preboil_check"}))

    def test_absent_basis_is_fact_and_needs_claims(self):
        chunk = {"id": "CHUNK-TEST-B", "source_claims": [], "text": {"no": "x", "en": "x"}}
        errors = validate_pilot_content(_minimal_with(chunk_extra=chunk), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("non-empty list" in e for e in errors), errors)

    def test_fact_basis_needs_a_verified_claim(self):
        chunk = {"id": "CHUNK-TEST-B", "basis": "fact", "source_claims": ["FACT-TEST-0023"],
                 "text": {"no": "x", "en": "x"}}
        errors = validate_pilot_content(_minimal_with(chunk_extra=chunk), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("not a verified Course Fact" in e for e in errors), errors)

    def test_methodology_chunk_needs_empty_claims(self):
        ok = {"id": "CHUNK-TEST-B", "basis": "methodology", "source_claims": [], "text": {"no": "x", "en": "x"}}
        self.assertEqual(validate_pilot_content(_minimal_with(chunk_extra=ok), registry_path=_REGISTRY_FIXTURE), [])
        bad = dict(ok, source_claims=["FACT-TEST-0020"])
        errors = validate_pilot_content(_minimal_with(chunk_extra=bad), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("requires 'source_claims' to be an empty list" in e for e in errors), errors)

    def test_methodology_question_only_with_the_approved_concept(self):
        ok = {"basis": "methodology", "source_claims": [], "concepts": ["mashing.preboil_check"]}
        self.assertEqual(validate_pilot_content(_minimal_with(question_extra=ok), registry_path=_REGISTRY_FIXTURE), [])
        for concept in ("mashing.wort_collection", "method.planning_variables"):
            bad = dict(ok, concepts=[concept])
            errors = validate_pilot_content(_minimal_with(question_extra=bad), registry_path=_REGISTRY_FIXTURE)
            self.assertTrue(any("not an approved methodology concept" in e for e in errors), errors)

    def test_unknown_basis_fails_closed(self):
        for item in ({"id": "CHUNK-TEST-B", "basis": "opinion", "source_claims": ["FACT-TEST-0020"],
                      "text": {"no": "x", "en": "x"}},):
            errors = validate_pilot_content(_minimal_with(chunk_extra=item), registry_path=_REGISTRY_FIXTURE)
            self.assertTrue(any("invalid basis" in e for e in errors), errors)
        errors = validate_pilot_content(_minimal_with(question_extra={"basis": "Methodology"}),
                                        registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("invalid basis" in e for e in errors), errors)


def _kompetent_text(data, teaching_only=False, ids=None):
    ids = _KOMPETENT_IDS if ids is None else ids
    parts = []
    for chunk in data["chunks"]:
        if chunk["id"] in ids:
            parts.extend(chunk["text"].values())
    for q in data["questions"]:
        if q["id"] not in ids:
            continue
        parts.extend(q["feedback_correct"].values())
        for o in q["options"]:
            if o["correct"] or not teaching_only:
                parts.extend(o["text"].values())
        if not teaching_only:
            parts.extend(q["prompt"].values())
            parts.extend(q["feedback_incorrect"].values())
    return " ".join(parts).lower()


class TestMeskingKompetentShape(unittest.TestCase):
    """Mashing Kompetent contract §6.1/§7.1: CHUNK-MASH-D..F and
    Q-MASH-004..008 appended in the same module after an unchanged
    Foundation."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_foundation_items_unchanged_and_carry_no_basis(self):
        self.assertEqual([c["id"] for c in self.data["chunks"][:3]], _FOUNDATION_CHUNK_IDS)
        self.assertEqual([q["id"] for q in self.data["questions"][:3]], ["Q-MASH-001", "Q-MASH-002", "Q-MASH-003"])
        for item in self.data["chunks"][:3] + self.data["questions"][:3]:
            self.assertNotIn("basis", item, item["id"])

    def test_kompetent_chunks_match_the_locked_shape(self):
        got = [(c["id"], c["basis"], c["source_claims"]) for c in self.data["chunks"][3:]]
        self.assertEqual(got, [tuple(r) for r in _KOMPETENT_CHUNKS])

    def test_kompetent_questions_match_the_locked_shape(self):
        got = [(q["id"], q["type"], q["basis"], q["concepts"], q["source_claims"]) for q in self.data["questions"][3:]]
        self.assertEqual(got, [tuple(r) for r in _KOMPETENT_QUESTIONS])
        for q in self.data["questions"][3:]:
            self.assertEqual(q["difficulty"], "intermediate", q["id"])
            self.assertEqual(len(q["options"]), 3, q["id"])
            self.assertEqual(sum(o["correct"] for o in q["options"]), 1, q["id"])


class TestMeskingKompetentGuardrails(unittest.TestCase):
    """Binding wording traps (mashing Kompetent contract §7, Chief M1/M2
    boundaries in §9.1)."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)
        self.visible = _kompetent_text(self.data)
        self.teaching = _kompetent_text(self.data, teaching_only=True)
        self.chunks = {c["id"]: c["text"] for c in self.data["chunks"]}

    def test_no_numbers_units_or_excluded_topics(self):
        self.assertNotRegex(self.visible, r"[0-9]")
        self.assertNotIn("ph", __import__("re").findall(r"[a-zæøå]+", self.visible))
        for banned in ("°", "%", "liter", "litre", "quart", "minutt", "minute", "ppg", "utbytte", "yield",
                       "jod", "iodine", "omdanningstest", "conversion check", "knus", "crush", "mill", "kvern",
                       "tannin", "garvestoff", "parti-gyle", "rikere", "richer", "fastkjør", "stuck", "risskall",
                       "rice hull", "krystallklar", "crystal", "squeez", "klemme", "maillard", "fly sparg",
                       "batch sparg", "flytehastighet", "run-off rate", "flow rate"):
            self.assertNotIn(banned, self.visible)

    def test_efficiency_only_as_a_rejected_calculation(self):
        for chunk_id in ("CHUNK-MASH-D", "CHUNK-MASH-E"):
            for text in self.chunks[chunk_id].values():
                self.assertNotIn("effektiv", text.lower())
                self.assertNotIn("efficien", text.lower())
        self.assertIn("ingen effektivitetsberegning", self.chunks["CHUNK-MASH-F"]["no"])
        self.assertIn("do not need an efficiency calculation", self.chunks["CHUNK-MASH-F"]["en"])
        # Efficiency maths appears only in the rejected distractor of Q-MASH-008.
        correct = _kompetent_text(self.data, teaching_only=True,
                                  ids={r[0] for r in _KOMPETENT_QUESTIONS})
        self.assertNotIn("regn ut", correct)
        self.assertNotIn("calculate", correct)

    def test_no_method_hierarchy_in_teaching(self):
        for banned in ("ordentlig", "riktige måten", "ekte", "avansert", "proper", "real brewing", "advanced",
                       "alltid", "always", "aldri", "never"):
            self.assertNotIn(banned, self.teaching)
        self.assertIn("ingen av metodene er universelt best", self.chunks["CHUNK-MASH-D"]["no"])
        self.assertIn("no method is universally best", self.chunks["CHUNK-MASH-D"]["en"])

    def test_m1_boundary(self):
        d = self.chunks["CHUNK-MASH-D"]
        for needle in ("avhenger av utstyret ditt", "falsk bunn", "selve kornsengen fungerer som filter",
                       "kurv eller et maltrør som løftes opp og får renne av", "posen med kornet ut",
                       "første vørteren ofte grumsete", "stort sett fri for kornpartikler",
                       "trenger ikke å være helt klar", "ikke til alle metoder"):
            self.assertIn(needle, d["no"])
        for needle in ("depends on your equipment", "false bottom", "grain bed itself acts as the filter",
                       "basket or malt pipe that is lifted and left to drain", "bag with the grain is lifted out",
                       "first runnings are often cloudy", "largely free of grain particles",
                       "does not need to be perfectly clear", "not to every method"):
            self.assertIn(needle, d["en"])
        # All-in-one recirculation is not taught as a clarity step.
        for text in d.values():
            self.assertNotIn("resirkul", text.lower())
            self.assertNotIn("recircul", text.lower())

    def test_m2_boundary(self):
        e = self.chunks["CHUNK-MASH-E"]
        for needle in ("våte kornet fortsatt på sukkerrik vørter", "Skylling (sparging)",
                       "hele vannmengden i meskingen", "mer sukker blir igjen",
                       "senere avrenningene svakere enn den første", "ditt eget anlegg", "dødvolum"):
            self.assertIn(needle, e["no"])
        for needle in ("wet grain still holds sugar-rich wort", "Sparging", "full water volume into the mash",
                       "more sugar stays behind", "later runnings are weaker than the first", "your own system",
                       "dead space"):
            self.assertIn(needle, e["en"])

    def test_preboil_methodology_is_simple_and_honest(self):
        f = self.chunks["CHUNK-MASH-F"]
        for needle in ("hva planen din forventet", "varm eller avkjølt", "før kokingen", "Sammenlign så planen",
                       "én hypotese", "ikke et bevis", "én bevisst endring", "ingen fasit forteller deg automatisk",
                       "uten mer presisjon enn målingen har"):
            self.assertIn(needle, f["no"])
        for needle in ("what your plan expected", "hot or cooled", "before the boil", "compare the plan",
                       "one hypothesis", "not proof", "one deliberate change", "no answer key will tell you",
                       "no more precision than the measurement has"):
            self.assertIn(needle, f["en"])
        self.assertEqual(METHODOLOGY_CONCEPTS, frozenset({"mashing.preboil_check"}))


if __name__ == "__main__":
    unittest.main()
