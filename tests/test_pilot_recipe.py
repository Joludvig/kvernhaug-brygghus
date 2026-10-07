"""
Tests for bryggeskole/pilot_recipe.py -- the Oppskriftsforståelse module
(V2.2, contract docs/development/v22_recipe_understanding_module_contract.md
§27 and the §28 implementation draft; offline implementation, no GitHub
issue yet). The whole module is Kompetent.

Covers:
1. the locked shape: exactly CHUNK-REC-A..G and Q-REC-001..007, one
   question per chunk, all beginner, with the exact basis / concepts /
   source_claims per §28 and the per-chunk claim subsets;
2. the module's own scoped basis rule and closed methodology allow-list
   (recipe.style_context, recipe.formulation_workflow; no recipe.one_change,
   no log.hypothesis_next_change);
3. the binding wording traps (§18, §19, §27, §28 content rules) as
   guardrails, plus the exact nine-step workflow (§13).

Run with:
    python3 -m unittest tests.test_pilot_recipe
"""
import copy
import json
import os
import re
import tempfile
import unittest

from bryggeskole.course_fact_registry import get_verified_record
from bryggeskole.pilot_recipe import (
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

# Contract §28 chunk table: (id, basis, allowed source_claims). Fact chunks
# may cite any non-empty subset of their list; CHUNK-REC-D must cite
# FACT-RECIPE-0001 and CHUNK-REC-E exactly FACT-RECIPE-0003.
_CHUNK_ALLOWED = [
    ("CHUNK-REC-A", "fact", {"FACT-MALT-0002", "FACT-MALT-0004", "FACT-HOP-0003", "FACT-YEAST-0005"}),
    ("CHUNK-REC-B", "fact", {"FACT-YEAST-0001", "FACT-YEAST-0002", "FACT-MASH-0001", "FACT-MASH-0004",
                             "FACT-RECIPE-0002"}),
    ("CHUNK-REC-C", "fact", {"FACT-MALT-0002", "FACT-MALT-0003", "FACT-MALT-0004"}),
    ("CHUNK-REC-D", "fact", {"FACT-RECIPE-0001", "FACT-HOP-0001", "FACT-HOP-0002", "FACT-HOP-0005"}),
    ("CHUNK-REC-E", "fact", {"FACT-RECIPE-0003"}),
    ("CHUNK-REC-F", "methodology", set()),
    ("CHUNK-REC-G", "methodology", set()),
]
# Contract §28 question table, verbatim.
_QUESTIONS = [
    ("Q-REC-001", "scenario", "fact", ["malt.base_vs_specialty"], ["FACT-MALT-0002"]),
    ("Q-REC-002", "scenario", "fact", ["yeast.attenuation"], ["FACT-YEAST-0002"]),
    ("Q-REC-003", "concept_check", "fact", ["malt.colour_flavour"], ["FACT-MALT-0003"]),
    ("Q-REC-004", "scenario", "fact", ["recipe.ibu_vs_perceived_bitterness"], ["FACT-RECIPE-0001"]),
    ("Q-REC-005", "scenario", "fact", ["recipe.balance"], ["FACT-RECIPE-0003"]),
    ("Q-REC-006", "scenario", "methodology", ["recipe.style_context"], []),
    ("Q-REC-007", "scenario", "methodology", ["recipe.formulation_workflow"], []),
]
_NOT_CREATED_CONCEPTS = (
    "recipe.one_change", "log.hypothesis_next_change", "recipe.gravity_vs_fermentability",
    "recipe.attenuation_chain", "recipe.alcohol_concept", "recipe.colour_origin",
)
# Contract §13, in order.
_WORKFLOW_NO = (
    "bestem hva du vil at ølet skal være", "velg retning for styrke", "velg maltstruktur",
    "velg bitterhet og humleuttrykk", "velg gjær og retning for utgjæring", "velg prosessvalg som støtter målet",
    "sjekk de forventede konsekvensene i appen", "brygg, mål og evaluer", "endre én bevisst ting neste gang",
)
_WORKFLOW_EN = (
    "decide what you want the beer to be", "choose the strength direction", "choose the malt structure",
    "choose bitterness and hop expression", "choose the yeast and attenuation direction",
    "choose process choices that support the goal", "check the predicted consequences in the app",
    "brew, measure and evaluate", "change one deliberate thing next time",
)


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
            "concepts": ["recipe.style_context"], "difficulty": "beginner", "source_claims": [],
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


def _texts(item):
    if "text" in item:
        return list(item["text"].values())
    out = []
    for field in ("prompt", "feedback_correct", "feedback_incorrect"):
        out.extend(item[field].values())
    for o in item["options"]:
        out.extend(o["text"].values())
    return out


class TestScopedBasisRules(unittest.TestCase):
    def test_minimal_document_is_valid(self):
        self.assertEqual(_validate(_doc()), [])

    def test_bases_and_allow_list_are_exactly_the_locked_sets(self):
        self.assertEqual(BASES, ("fact", "methodology"))
        self.assertEqual(set(METHODOLOGY_CONCEPTS), {"recipe.style_context", "recipe.formulation_workflow"})

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
        for concept in _NOT_CREATED_CONCEPTS + ("sensory.evaluate_against_intent", "log.planned_vs_actual"):
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
        self.assertEqual(self.data["topic_id"], "PILOT-RECIPE-FUNDAMENTALS")

    def test_exact_chunks_in_order_with_per_chunk_claim_subsets(self):
        self.assertEqual([c["id"] for c in self.data["chunks"]], [row[0] for row in _CHUNK_ALLOWED])
        for chunk, (_, basis, allowed) in zip(self.data["chunks"], _CHUNK_ALLOWED):
            with self.subTest(chunk=chunk["id"]):
                self.assertEqual(chunk["basis"], basis)
                claims = set(chunk["source_claims"])
                self.assertEqual(len(claims), len(chunk["source_claims"]))
                if basis == "methodology":
                    self.assertEqual(chunk["source_claims"], [])
                else:
                    self.assertTrue(claims)
                    self.assertLessEqual(claims, allowed)
        self.assertIn("FACT-RECIPE-0001", self.data["chunks"][3]["source_claims"])
        self.assertEqual(self.data["chunks"][4]["source_claims"], ["FACT-RECIPE-0003"])

    def test_exact_questions_in_order_one_per_chunk(self):
        self.assertEqual(
            [(q["id"], q["type"], q["basis"], q["concepts"], q["source_claims"]) for q in self.data["questions"]],
            [tuple(row) for row in _QUESTIONS],
        )
        self.assertEqual(len(self.data["questions"]), len(self.data["chunks"]))

    def test_all_questions_beginner_with_three_options_one_correct(self):
        # "beginner" is item difficulty under the schema convention, not the
        # course stage (contract §27.2); the module is Kompetent regardless.
        for q in self.data["questions"]:
            self.assertEqual(q["difficulty"], "beginner", q["id"])
            self.assertEqual(len(q["options"]), 3, q["id"])
            self.assertEqual(sum(1 for o in q["options"] if o["correct"]), 1, q["id"])

    def test_every_fact_claim_is_verified_and_meas_is_never_cited(self):
        for item in self.data["chunks"] + self.data["questions"]:
            for claim in item["source_claims"]:
                self.assertIsNotNone(get_verified_record(DEFAULT_REGISTRY_PATH, claim), claim)
            self.assertFalse(any(c.startswith("FACT-MEAS-") for c in item["source_claims"]), item["id"])

    def test_no_concepts_outside_the_contract(self):
        dumped = json.dumps(self.data)
        for concept in _NOT_CREATED_CONCEPTS:
            self.assertNotIn(concept, dumped)

    def test_no_en_symmetry_no_empty_text(self):
        for item in self.data["chunks"] + self.data["questions"]:
            bilinguals = [item["text"]] if "text" in item else (
                [item["prompt"], item["feedback_correct"], item["feedback_incorrect"]]
                + [o["text"] for o in item["options"]]
            )
            for bilingual in bilinguals:
                self.assertEqual(set(bilingual), {"no", "en"})
                self.assertTrue(bilingual["no"].strip())
                self.assertTrue(bilingual["en"].strip())

    def test_workflow_has_the_nine_locked_steps_in_order(self):
        for lang, steps in (("no", _WORKFLOW_NO), ("en", _WORKFLOW_EN)):
            text = self.data["chunks"][6]["text"][lang].lower()
            positions = [text.find(step) for step in steps]
            self.assertNotIn(-1, positions, (lang, positions))
            self.assertEqual(positions, sorted(positions), lang)

    def test_no_raw_score_field(self):
        self.assertNotIn('"score"', json.dumps(self.data))


class TestWordingGuardrails(unittest.TestCase):
    """Binding wording traps: contract §18, §19, §27 and §28."""

    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)
        self.items = {item["id"]: item for item in self.data["chunks"] + self.data["questions"]}
        self.visible = " ".join(t for item in self.items.values() for t in _texts(item)).lower()
        self.teaching = " ".join(
            [t for c in self.data["chunks"] for t in c["text"].values()]
            + [t for q in self.data["questions"] for t in q["feedback_correct"].values()]
        ).lower()

    def _of(self, *ids):
        return " ".join(t for i in ids for t in _texts(self.items[i])).lower()

    def test_no_numbers_formulas_or_maths(self):
        self.assertNotRegex(self.visible, r"[0-9%]")
        for banned in ("formel", "formula", "tinseth", "utnyttelse", "utilisation", "utilization", "srm",
                       "lovibond", "abv", "plato", "brix", "effektivitet", "efficiency", "utbytte", "yield",
                       "tilsynelatende", "apparent", "glykolyse", "glycolysis", "minutt", "minute",
                       "statistikk", "statistic"):
            self.assertNotIn(banned, self.visible)

    def test_no_bu_gu_in_any_form(self):
        self.assertNotRegex(self.visible, r"bu\s*[:/]\s*gu|bugu|bu-gu")

    def test_no_bjcp_or_style_scores(self):
        for banned in ("bjcp", "kvalitetsscore", "quality score", "fasit"):
            self.assertNotIn(banned, self.visible)
        self.assertIn("gjør ikke oppskriften feil", self.teaching)
        self.assertIn("does not make the recipe wrong", self.teaching)

    def test_app_values_are_predicted_never_measured(self):
        for lang_re, ok in ((r"[^.!?]*\bappen\b[^.!?]*", ("beregn", "forvent")),
                            (r"[^.!?]*\bthe app\b[^.!?]*", ("calculat", "predict"))):
            for sentence in re.findall(lang_re, self.visible):
                with self.subTest(sentence=sentence):
                    if "stiltreff" in sentence or "style match" in sentence:
                        continue
                    self.assertTrue(any(word in sentence for word in ok), sentence)
                    self.assertNotRegex(sentence, r"\b(målt|måler|measured|measures)\b")
        self.assertIn("forventede eller beregnede verdier", self.teaching)
        self.assertIn("predicted or calculated values", self.teaching)

    def test_og_fg_are_not_redefined(self):
        self.assertIn("og og fg er definert i måling og bryggelogg", self.teaching)
        for banned in ("og er tettheten", "og is the gravity", "fg er tettheten", "fg is the gravity"):
            self.assertNotIn(banned, self.visible)

    def test_high_og_is_not_automatically_sweet_or_strong(self):
        self.assertIn("betyr ikke en høy og automatisk et søtt øl, og heller ikke automatisk et sterkt øl", self.teaching)
        self.assertIn("does not automatically mean a sweet beer, nor automatically a strong one", self.teaching)
        self.assertIn("ikke av gjæren alene", self.teaching)
        self.assertIn("not decided by the yeast alone", self.teaching)

    def test_no_crystal_sweetness_or_body_claims(self):
        # FACT-RECIPE-0002 deliberately claims neither sweetness nor body.
        # Body tendency is a FACT GAP (Chief 2026-10-04): not taught anywhere.
        for banned in ("søtere", "sweeter", "fylde", "body", "mouthfeel", "munnfølelse", "all spesialmalt",
                       "all specialty malt", "uforgjærbar", "unfermentable"):
            self.assertNotIn(banned, self.teaching)
        for banned in ("fylde", "fyldig", "body", "full-bodied", "munnfølelse", "mouthfeel"):
            self.assertNotIn(banned, self.visible)
        # "Søt"/"sweet" only in the contract's negation ("not automatically sweet").
        self.assertEqual(len(re.findall(r"\bsøtt?\b", self.teaching)), 1)
        self.assertEqual(len(re.findall(r"\bsweet\b", self.teaching)), 1)

    def test_colour_is_not_flavour(self):
        self.assertIn("forutsier ikke smaken én til én", self.teaching)
        self.assertIn("does not predict flavour one to one", self.teaching)

    def test_ebc_only_as_an_app_colour_estimate(self):
        # Chief 2026-10-04: no verified record teaches the EBC scale
        # direction, so EBC appears only as the App's calculated estimate.
        self.assertIn("appen viser en beregnet farge i ebc – det er et estimat", self.teaching)
        self.assertIn("the app shows a calculated colour in ebc – it is an estimate", self.teaching)
        for sentence in re.findall(r"[^.!?]*\bebc\b[^.!?]*", self.visible):
            with self.subTest(sentence=sentence):
                self.assertNotRegex(sentence, r"mørk|lys|darker|lighter|higher|lower|høyere|lavere|skala|scale")
        for banned in ("høyere tall betyr mørkere", "higher number means darker", "ebc-skala", "ebc scale"):
            self.assertNotIn(banned, self.visible)
        for banned in ("farge = smak", "colour = flavour", "fargen avgjør smaken"):
            self.assertNotIn(banned, self.visible)

    def test_ibu_is_one_axis_with_no_directional_matrix_claims(self):
        self.assertIn("én akse", self.teaching)
        self.assertIn("et estimat, ikke en garanti", self.teaching)
        for banned in ("ibu = opplevd", "ibu = perceived", "høyere ibu betyr alltid", "higher ibu always"):
            self.assertNotIn(banned, self.visible)
        bitterness = self._of("CHUNK-REC-D", "CHUNK-REC-E", "Q-REC-004", "Q-REC-005")
        for banned in ("alkohol", "alcohol", "restsukker", "residual", "rist", "roast", "mineral", "vann ",
                       "water", "karbon", "carbonat", "ph"):
            self.assertNotRegex(bitterness, r"\b" + re.escape(banned.strip()))

    def test_balance_is_judged_against_intent_and_never_a_quality_word(self):
        self.assertIn("vurderes opp mot ølet", self.teaching)
        # Word-bounded: "ideally one" (contract §13 one-change wording) is fine.
        for banned in ("harmonisk", "harmonious", "ideell", "ideal", "perfekt", "perfect", "riktig balanse",
                       "right balance", "correct balance", "veldig balansert", "er bedre", "is better"):
            self.assertIsNone(re.search(r"\b" + banned + r"\b", self.visible), banned)
        self.assertNotIn("riktig", self._of("CHUNK-REC-E"))

    def test_one_change_is_a_hypothesis_not_proof(self):
        self.assertIn("hypotese", self.teaching)
        self.assertIn("beviser ikke årsaken", self.teaching)
        self.assertIn("ikke et kontrollert forsøk", self.teaching)
        self.assertIn("not a controlled experiment", self.teaching)

    def test_smak_and_maaling_boundaries(self):
        for banned in ("smakerekkefølge", "tasting sequence", "feilsmak", "off-flavour", "off-flavor", "diacetyl",
                       "observasjon og tolkning", "observation and interpretation", "hydrometer", "bryggelogg-punkt"):
            self.assertNotIn(banned, self.visible)

    def test_no_engine_model_claims(self):
        for banned in ("motoren", "the engine", "appen modellerer", "the app models", "appen beregner fylde"):
            self.assertNotIn(banned, self.visible)

    def test_no_questions_use_negation_trap_stems(self):
        for question in self.data["questions"]:
            for lang in ("no", "en"):
                prompt = question["prompt"][lang].lower()
                self.assertNotRegex(prompt, r"\b(except|not true|which is not|unntatt|hvilket er ikke|hva er ikke)\b")


class TestRenderAndEvaluate(unittest.TestCase):
    def setUp(self):
        self.data = read_pilot_file(DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH)

    def test_render_exposes_basis_for_the_ui_label(self):
        self.assertEqual(render_chunk(self.data["chunks"][0], "no")["basis"], "fact")
        self.assertEqual(render_chunk(self.data["chunks"][5], "en")["basis"], "methodology")
        self.assertEqual(render_question(self.data["questions"][6], "en")["basis"], "methodology")

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
        import bryggeskole.pilot_recipe as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertIsNone(re.search(r"^\s*(import|from)\s+streamlit", source, re.MULTILINE))


if __name__ == "__main__":
    unittest.main()
