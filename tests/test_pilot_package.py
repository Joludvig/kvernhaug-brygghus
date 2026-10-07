"""
Tests for bryggeskole/pilot_package.py -- the package-fundamentals pilot
content/questions slice (issue #374, V2.2 Goal 3G).

Synthetic invalid-shape fixtures are reused from
tests/fixtures/pilot_fermentation/ (this module's validator is a
byte-for-byte copy of pilot_fermentation.py's/pilot_mashing.py's/
pilot_boil_hop.py's/pilot_cool_transfer.py's) together with the same
registry fixture used by those suites
(tests/fixtures/course_fact_registry/verified_consumer_mixed.json),
which conveniently carries both a verified id (FACT-TEST-0020) and a
draft (unverified) id (FACT-TEST-0023) -- exactly the two cases this
module's source_claims validation must reject identically.

Run with:
    python3 -m unittest tests.test_pilot_package
"""
import io
import json
import os
import unittest

from bryggeskole.course_fact_registry import CourseFactRegistryError
from bryggeskole.pilot_package import (
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

# Foundation (#374) uses six facts; the Kompetent slice (package Kompetent
# contract §6–§7) reuses FACT-PACK-0001 and FACT-OXY-0002 and adds only the
# already verified FACT-BREW-0005.
_ALL_FACTS = {
    "FACT-COOL-0003", "FACT-OXY-0002",
    "FACT-PACK-0001", "FACT-PACK-0002", "FACT-PACK-0003", "FACT-PACK-0004",
    "FACT-BREW-0005",
}

_FOUNDATION_CHUNK_IDS = [
    "CHUNK-PACK-A", "CHUNK-PACK-B", "CHUNK-PACK-C", "CHUNK-PACK-D", "CHUNK-PACK-E",
]
_KOMPETENT_CHUNKS = [
    ("CHUNK-PACK-F", "fact", ["FACT-PACK-0001"]),
    ("CHUNK-PACK-G", "methodology", []),
    ("CHUNK-PACK-H", "fact", ["FACT-BREW-0005"]),
    ("CHUNK-PACK-I", "fact", ["FACT-OXY-0002"]),
]
_KOMPETENT_QUESTIONS = [
    ("Q-PACK-006", "scenario", "fact", ["package.priming"], ["FACT-PACK-0001"]),
    ("Q-PACK-007", "scenario", "methodology", ["package.priming_tool"], []),
    ("Q-PACK-008", "scenario", "fact", ["fermentation.conditioning"], ["FACT-BREW-0005"]),
    ("Q-PACK-009", "scenario", "fact", ["oxygen.post_pitch"], ["FACT-OXY-0002"]),
]
_KOMPETENT_IDS = {r[0] for r in _KOMPETENT_CHUNKS + _KOMPETENT_QUESTIONS}
_EXPECTED_CHUNK_IDS = _FOUNDATION_CHUNK_IDS + [r[0] for r in _KOMPETENT_CHUNKS]

_EXPECTED_CONCEPTS = {
    "cool.sanitation_boundary", "package.priming", "package.force_carbonation",
    "oxygen.post_pitch", "package.pressure_safety", "package.path_choice",
    # Kompetent: one new methodology concept plus the reused Gjæring concept.
    "package.priming_tool", "fermentation.conditioning",
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
    """The shipped package-fundamentals pilot content against the real
    production registry (FACT-COOL-0003 + FACT-OXY-0002 reused,
    FACT-PACK-0001..0004 new, issue #374)."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_schema_version(self):
        self.assertEqual(self.data["schema_version"], PILOT_SCHEMA_VERSION)

    def test_topic_id(self):
        self.assertEqual(self.data["topic_id"], "PILOT-PACKAGE-FUNDAMENTALS")

    def test_foundation_then_kompetent_chunks_in_order(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]], _EXPECTED_CHUNK_IDS)

    def test_at_least_one_question_per_chunk_count_is_compact(self):
        self.assertGreaterEqual(len(self.data["questions"]), 5)
        self.assertLessEqual(len(self.data["questions"]), 10)

    def test_chunk_source_claims_cover_exactly_the_six_package_facts(self):
        referenced = set()
        for chunk in self.data["chunks"]:
            referenced.update(chunk["source_claims"])
        self.assertEqual(referenced, _ALL_FACTS)

    def test_at_least_one_concept_check_and_one_scenario_question(self):
        types = [q["type"] for q in self.data["questions"]]
        self.assertIn("concept_check", types)
        self.assertIn("scenario", types)

    def test_question_source_claims_are_subset_of_the_six_package_facts(self):
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

    def test_exactly_the_expected_concepts(self):
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
            if question.get("basis", "fact") == "fact":
                self.assertTrue(question["source_claims"])
            else:
                self.assertEqual(question["source_claims"], [])

    def test_no_raw_score_field_anywhere_in_content(self):
        raw = json.dumps(self.data)
        self.assertNotIn('"score"', raw)

    def test_reuses_shared_concept_ids_from_cool_transfer_module(self):
        # §3.5 of the module contract: cool.sanitation_boundary and
        # oxygen.post_pitch are REUSED ids from pilot_cool_transfer.py,
        # not new ones -- this is the concrete mechanism behind shared
        # mastery across modules.
        concepts = set()
        for question in self.data["questions"]:
            concepts.update(question["concepts"])
        self.assertIn("cool.sanitation_boundary", concepts)
        self.assertIn("oxygen.post_pitch", concepts)

    def test_wording_never_asserts_a_single_universal_priming_amount(self):
        # Issue #374 §3 critical guardrail: never teach one universal
        # priming-sugar amount. Only authoritative text (chunk text,
        # correct feedback) is checked -- prompts/wrong-answer options may
        # voice the misconception as the thing to reject.
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("universell mengde primesukker", joined)
        self.assertNotIn("one universal priming", joined)

    def test_wording_never_asserts_force_carbonation_is_better(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("tvangskarbonering er bedre", joined)
        self.assertNotIn("force carbonation is better", joined)

    def test_wording_never_frames_bottling_as_beginner_and_kegging_as_serious(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("flasking er kun for nybegynnere", joined)
        self.assertNotIn("bottling is only for beginners", joined)
        self.assertNotIn("tapping på fat er alltid det seriøse", joined)
        self.assertNotIn("kegging is always the serious", joined)

    def test_wording_never_asserts_oxygen_instantly_ruins_beer(self):
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        self.assertNotIn("ødelegger ølet umiddelbart", joined)
        self.assertNotIn("instantly ruins the beer", joined)

    def test_wording_never_states_a_pressure_rating_or_burst_pressure_number(self):
        # Word-boundary regex, not a bare substring check -- "bar" (the
        # pressure unit) would otherwise false-positive against ordinary
        # Norwegian words like "bare" (only) and "gjærbart" (fermentable).
        authoritative = []
        for chunk in self.data["chunks"]:
            authoritative.extend(chunk["text"].values())
        for question in self.data["questions"]:
            authoritative.extend(question["feedback_correct"].values())
        joined = " ".join(authoritative).lower()
        for banned in (r"\d+\s*bar\b", r"\bpsi\b", r"\bkpa\b"):
            self.assertNotRegex(joined, banned)

    def test_no_specific_bottle_or_keg_brand_named(self):
        raw = json.dumps(self.data).lower()
        for banned in ("cornelius", "corny keg", "ss brewtech", "grainfather"):
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



class TestFermentationCompletionPointer(unittest.TestCase):
    """Stage allocation contract §D.9: Pakking links to the Måling
    completion check as a process dependency only -- no new claim and no
    unsupported safety consequence of packaging too early."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_pointer_present_in_no_and_en(self):
        chunk = self.data["chunks"][0]
        self.assertEqual(chunk["id"], "CHUNK-PACK-A")
        self.assertTrue(chunk["text"]["no"].endswith(
            "Og før du pakker: bruk sjekken for ferdig gjæring som du lærer i Måling og bryggelogg."))
        self.assertTrue(chunk["text"]["en"].endswith(
            "And before you package: use the completion check taught in Measurement and brew log."))
        self.assertEqual(chunk["source_claims"], ["FACT-COOL-0003"])

    def test_no_unsupported_early_packaging_consequence(self):
        raw = json.dumps(self.data, ensure_ascii=False).lower()
        for banned in ("flaskebombe", "bottle bomb", "eksploder", "explode", "for tidlig", "too early",
                       "FACT-MEAS".lower()):
            self.assertNotIn(banned, raw)


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
    """Package Kompetent contract §7: optional basis. Absent means "fact"
    (Foundation unchanged); "methodology" needs empty source_claims and, on
    a question, the approved methodology concept; unknown fails closed."""

    def test_value_sets(self):
        self.assertEqual(BASES, ("fact", "methodology"))
        self.assertEqual(METHODOLOGY_CONCEPTS, frozenset({"package.priming_tool"}))

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
        ok = {"basis": "methodology", "source_claims": [], "concepts": ["package.priming_tool"]}
        self.assertEqual(validate_pilot_content(_minimal_with(question_extra=ok), registry_path=_REGISTRY_FIXTURE), [])
        bad = dict(ok, concepts=["package.priming"])
        errors = validate_pilot_content(_minimal_with(question_extra=bad), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("not an approved methodology concept" in e for e in errors), errors)

    def test_unknown_basis_fails_closed(self):
        chunk = {"id": "CHUNK-TEST-B", "basis": "opinion", "source_claims": ["FACT-TEST-0020"],
                 "text": {"no": "x", "en": "x"}}
        errors = validate_pilot_content(_minimal_with(chunk_extra=chunk), registry_path=_REGISTRY_FIXTURE)
        self.assertTrue(any("invalid basis" in e for e in errors), errors)


def _kompetent_text(data, teaching_only=False):
    parts = []
    for chunk in data["chunks"]:
        if chunk["id"] in _KOMPETENT_IDS:
            parts.extend(chunk["text"].values())
    for q in data["questions"]:
        if q["id"] not in _KOMPETENT_IDS:
            continue
        parts.extend(q["feedback_correct"].values())
        for o in q["options"]:
            if o["correct"] or not teaching_only:
                parts.extend(o["text"].values())
        if not teaching_only:
            parts.extend(q["prompt"].values())
            parts.extend(q["feedback_incorrect"].values())
    return " ".join(parts).lower()


class TestPakkingKompetentShape(unittest.TestCase):
    """Package Kompetent contract §6–§7: CHUNK-PACK-F..I and Q-PACK-006..009
    appended in the same module after an unchanged Foundation."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)

    def test_foundation_items_unchanged_and_carry_no_basis(self):
        self.assertEqual([c["id"] for c in self.data["chunks"][:5]], _FOUNDATION_CHUNK_IDS)
        self.assertEqual([q["id"] for q in self.data["questions"][:5]], [f"Q-PACK-00{n}" for n in range(1, 6)])
        for item in self.data["chunks"][:5] + self.data["questions"][:5]:
            self.assertNotIn("basis", item, item["id"])

    def test_kompetent_chunks_match_the_locked_shape(self):
        got = [(c["id"], c["basis"], c["source_claims"]) for c in self.data["chunks"][5:]]
        self.assertEqual(got, [tuple(r) for r in _KOMPETENT_CHUNKS])

    def test_kompetent_questions_match_the_locked_shape(self):
        got = [(q["id"], q["type"], q["basis"], q["concepts"], q["source_claims"]) for q in self.data["questions"][5:]]
        self.assertEqual(got, [tuple(r) for r in _KOMPETENT_QUESTIONS])
        for q in self.data["questions"][5:]:
            self.assertEqual(q["difficulty"], "intermediate", q["id"])
            self.assertEqual(len(q["options"]), 3, q["id"])
            self.assertEqual(sum(o["correct"] for o in q["options"]), 1, q["id"])


class TestPakkingKompetentGuardrails(unittest.TestCase):
    """Binding wording traps (package Kompetent contract §7)."""

    def setUp(self):
        self.data = read_pilot_file(_PRODUCTION_PILOT, registry_path=_PRODUCTION_REGISTRY)
        self.visible = _kompetent_text(self.data)
        self.teaching = _kompetent_text(self.data, teaching_only=True)
        self.chunks = {c["id"]: c["text"] for c in self.data["chunks"]}

    def test_no_numbers_units_or_formulas(self):
        self.assertNotRegex(self.visible, r"[0-9]")
        for banned in (" gram", "g/l", "volum co", "volumes of co", "°", "%", "psi", "kpa", " bar ",
                       "regn ut slik", "residual", "restkullsyre", "tabellverdi", "table value"):
            self.assertNotIn(banned, self.visible)
        # "formula" may appear only in the rejected distractor of Q-PACK-007.
        for banned in ("formel", "formula"):
            self.assertNotIn(banned, self.teaching)

    def test_priming_tool_is_methodology_without_manual_maths(self):
        g = self.chunks["CHUNK-PACK-G"]
        for needle in ("trenger ikke regne ut primemengden selv", "oppskriften", "primekalkulator",
                       "karboneringstabell du stoler på", "skriv ned"):
            self.assertIn(needle, g["no"].lower())
        for needle in ("do not need to work out the priming amount yourself", "calculator", "table you trust",
                       "write down"):
            self.assertIn(needle, g["en"].lower())
        self.assertEqual(METHODOLOGY_CONCEPTS, frozenset({"package.priming_tool"}))

    def test_priming_fact_stays_within_pack_0001(self):
        f = self.chunks["CHUNK-PACK-F"]
        self.assertIn("ikke én mengde som passer alle brygg", f["no"])
        self.assertIn("no single amount that fits every batch", f["en"])
        for banned in ("sukkertype", "sugar type", "dextrose", "druesukker", "honning", "honey"):
            self.assertNotIn(banned, self.visible)

    def test_clarity_stays_within_brew_0005(self):
        h = self.chunks["CHUNK-PACK-H"]
        for needle in ("gjerne til bunns", "ofte klarere", "avhenger av gjærstammen", "noen øl skal være uklare"):
            self.assertIn(needle, h["no"])
        for banned in ("finings", "klaringsmiddel", "gelatin", "isinglass", "kaldkrasj", "cold crash",
                       "cold condition", "kaldmodning", "kjøl ned", "må være blank", "must be bright",
                       "must be clear", "skal være helt klar"):
            self.assertNotIn(banned, self.teaching)

    def test_oxygen_stays_within_oxy_0002(self):
        i = self.chunks["CHUNK-PACK-I"]
        for needle in ("pappaktig", "svakere humlearoma", "dårligere holdbarhet", "unødvendig skvulping",
                       "ikke en regel om at én eksponering ødelegger"):
            self.assertIn(needle, i["no"])
        for banned in ("oksidasjonskjemi", "oxidation chemistry", "aldehyd", "aldehyde", "radikal", "radical",
                       "måneder", "months", "uker", "weeks", "best før", "best before",
                       "ødelegger ølet umiddelbart", "instantly ruins the beer"):
            self.assertNotIn(banned, self.teaching)

    def test_no_universal_claims_in_teaching(self):
        for banned in ("alltid", "always", "aldri", "never", "garantert", "guarantee"):
            self.assertNotIn(banned, self.teaching)


if __name__ == "__main__":
    unittest.main()
