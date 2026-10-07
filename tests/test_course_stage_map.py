"""
Tests for bryggeskole/course_stage.py and bryggeskole/data/course_stage_map.json
-- S1 of the course stage UI contract
(docs/development/v22_course_stage_ui_contract.md §6, §15, §16; offline, no
GitHub issue yet). Metadata and validation only: S1 changes no runtime
behaviour.

The real chunk and question ids are read straight from the production pilot
modules (not from course_stage's own loader), so the map is checked against
the content itself rather than against a second handwritten id list.

Run with:
    python -m unittest tests.test_course_stage_map
"""
import copy
import io
import json
import os
import re
import tempfile
import unittest

from bryggeskole import (
    pilot_boil_hop,
    pilot_cleaning_safety,
    pilot_cool_transfer,
    pilot_fermentation,
    pilot_mashing,
    pilot_measurement,
    pilot_method_context,
    pilot_package,
    pilot_raw_materials,
    pilot_recipe,
    pilot_sensory,
)
from bryggeskole import course_stage
from bryggeskole.course_stage import (
    DEFAULT_STAGE_MAP_PATH,
    MODULE_ORDER,
    STAGES,
    StageMapError,
    items_for_stage,
    load_stage_map,
    module_has_stage,
    stage_for_chunk,
    stage_for_question,
    validate_stage_map,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Independent of course_stage.MODULE_PILOTS: imported directly here.
_PILOT_MODULES = {
    "raavarer": pilot_raw_materials,
    "rengjoring": pilot_cleaning_safety,
    "metodevalg": pilot_method_context,
    "mesking": pilot_mashing,
    "koking": pilot_boil_hop,
    "kjoling": pilot_cool_transfer,
    "gjaring": pilot_fermentation,
    "pakking": pilot_package,
    "maaling": pilot_measurement,
    "oppskrift": pilot_recipe,
    "smak": pilot_sensory,
}


def _read_raw_map():
    with io.open(DEFAULT_STAGE_MAP_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class _WithProduction(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilots = {m: mod.read_pilot_file() for m, mod in _PILOT_MODULES.items()}
        cls.stage_map = load_stage_map(pilots=cls.pilots)
        cls.entries = {e["module"]: e for e in cls.stage_map["modules"]}

    def stage_ids(self, module_id, stage, kind):
        return list(self.entries[module_id][stage][kind])


class TestCanonicalModules(_WithProduction):
    def test_eleven_canonical_modules_in_order(self):
        self.assertEqual(
            MODULE_ORDER,
            ("raavarer", "rengjoring", "metodevalg", "mesking", "koking", "kjoling",
             "gjaring", "pakking", "maaling", "oppskrift", "smak"),
        )
        self.assertEqual([e["module"] for e in self.stage_map["modules"]], list(MODULE_ORDER))

    def test_module_identities_match_the_panel(self):
        from ui import bryggeskole_panel as panel

        self.assertEqual(list(panel._MODUL_REKKEFOLGE), list(MODULE_ORDER))
        for module_id, pilot_module in course_stage.MODULE_PILOTS:
            self.assertEqual(panel._MODULER[module_id]["pilot"].__name__, pilot_module)
            self.assertIs(_PILOT_MODULES[module_id], panel._MODULER[module_id]["pilot"])

    def test_topic_ids_match_the_pilots(self):
        for module_id, pilot in self.pilots.items():
            self.assertEqual(self.entries[module_id]["topic_id"], pilot["topic_id"])


class TestEveryItemExactlyOnce(_WithProduction):
    def _check(self, kind):
        for module_id, pilot in self.pilots.items():
            with self.subTest(module=module_id):
                real = [i["id"] for i in pilot[kind]]
                mapped = self.stage_ids(module_id, "foundation", kind) + self.stage_ids(module_id, "kompetent", kind)
                self.assertEqual(sorted(mapped), sorted(real))
                self.assertEqual(len(mapped), len(set(mapped)))

    def test_every_chunk_exactly_once(self):
        self._check("chunks")

    def test_every_question_exactly_once(self):
        self._check("questions")

    def test_lookup_agrees_with_the_map_for_every_item(self):
        for module_id, pilot in self.pilots.items():
            for chunk in pilot["chunks"]:
                stage = stage_for_chunk(self.stage_map, module_id, chunk["id"])
                self.assertIn(chunk["id"], self.entries[module_id][stage]["chunks"])
            for question in pilot["questions"]:
                stage = stage_for_question(self.stage_map, module_id, question["id"])
                self.assertIn(question["id"], self.entries[module_id][stage]["questions"])


class TestTotals(_WithProduction):
    def _count(self, stage, kind):
        return sum(len(e[stage][kind]) for e in self.stage_map["modules"])

    def test_stage_totals(self):
        self.assertEqual((self._count("foundation", "chunks"), self._count("foundation", "questions")), (48, 45))
        self.assertEqual((self._count("kompetent", "chunks"), self._count("kompetent", "questions")), (36, 54))

    def test_totals_equal_the_real_content(self):
        real_chunks = sum(len(p["chunks"]) for p in self.pilots.values())
        real_questions = sum(len(p["questions"]) for p in self.pilots.values())
        self.assertEqual((real_chunks, real_questions), (84, 99))
        self.assertEqual(self._count("foundation", "chunks") + self._count("kompetent", "chunks"), real_chunks)
        self.assertEqual(self._count("foundation", "questions") + self._count("kompetent", "questions"), real_questions)

    def test_nine_modules_per_stage(self):
        for stage in STAGES:
            with self.subTest(stage=stage):
                self.assertEqual(sum(module_has_stage(self.stage_map, m, stage) for m in MODULE_ORDER), 9)


class TestAllocationFollowsTheContracts(_WithProduction):
    """Stage allocation contract §C/§D, stage UI contract §6.2/§6.3."""

    def test_interim_locks(self):
        self.assertEqual(stage_for_chunk(self.stage_map, "koking", "CHUNK-BOILHOP-B"), "foundation")
        self.assertEqual(stage_for_chunk(self.stage_map, "kjoling", "CHUNK-COOLXFER-D"), "foundation")
        self.assertEqual(stage_for_question(self.stage_map, "koking", "Q-BOILHOP-008"), "kompetent")
        self.assertEqual(stage_for_question(self.stage_map, "koking", "Q-BOILHOP-004"), "foundation")
        self.assertEqual(stage_for_question(self.stage_map, "koking", "Q-BOILHOP-005"), "foundation")
        self.assertIn("CHUNK-BOILHOP-B", self.entries["koking"]["notes"])
        self.assertIn("CHUNK-COOLXFER-D", self.entries["kjoling"]["notes"])

    def test_single_stage_modules(self):
        for module_id in ("rengjoring", "metodevalg"):
            self.assertTrue(module_has_stage(self.stage_map, module_id, "foundation"))
            self.assertFalse(module_has_stage(self.stage_map, module_id, "kompetent"))
        for module_id in ("oppskrift", "smak"):
            self.assertFalse(module_has_stage(self.stage_map, module_id, "foundation"))
            self.assertTrue(module_has_stage(self.stage_map, module_id, "kompetent"))

    def test_appended_kompetent_slices_follow_their_foundation(self):
        # (Foundation chunk count, Foundation question count): everything after
        # the Foundation prefix is Kompetent (Mesking §D.1 + Kompetent slice;
        # Gjæring, Pakking and Måling Kompetent slices).
        for module_id, (n_chunks, n_questions) in {
            "mesking": (1, 1), "gjaring": (4, 3), "pakking": (5, 5), "maaling": (5, 6),
        }.items():
            with self.subTest(module=module_id):
                pilot = self.pilots[module_id]
                for kind, n in (("chunks", n_chunks), ("questions", n_questions)):
                    ids = [i["id"] for i in pilot[kind]]
                    self.assertEqual(self.stage_ids(module_id, "foundation", kind), ids[:n])
                    self.assertEqual(self.stage_ids(module_id, "kompetent", kind), ids[n:])

    def test_question_level_moves(self):
        self.assertEqual(self.stage_ids("raavarer", "kompetent", "chunks"), [])
        self.assertEqual(
            self.stage_ids("raavarer", "kompetent", "questions"),
            ["Q-RAW-004", "Q-RAW-006", "Q-RAW-009", "Q-RAW-010", "Q-RAW-011", "Q-RAW-012"],
        )
        self.assertEqual(self.stage_ids("koking", "kompetent", "chunks"), ["CHUNK-BOILHOP-F"])
        self.assertEqual(self.stage_ids("koking", "kompetent", "questions"),
                         ["Q-BOILHOP-002", "Q-BOILHOP-007", "Q-BOILHOP-008"])
        self.assertEqual(self.stage_ids("kjoling", "kompetent", "chunks"), [])
        self.assertEqual(self.stage_ids("kjoling", "kompetent", "questions"), ["Q-COOLXFER-004", "Q-COOLXFER-005"])

    def test_recipe_is_kompetent_despite_beginner_difficulty(self):
        recipe = self.pilots["oppskrift"]
        self.assertTrue(all(q["difficulty"] == "beginner" for q in recipe["questions"]))
        for question in recipe["questions"]:
            self.assertEqual(stage_for_question(self.stage_map, "oppskrift", question["id"]), "kompetent")

    def test_difficulty_does_not_determine_stage(self):
        pairs = {(q["difficulty"], stage_for_question(self.stage_map, m, q["id"]))
                 for m, p in self.pilots.items() for q in p["questions"]}
        self.assertIn(("beginner", "kompetent"), pairs)
        self.assertIn(("intermediate", "foundation"), pairs)

    def test_sensory_taster_is_not_exposed_as_foundation(self):
        self.assertEqual(stage_for_chunk(self.stage_map, "smak", "CHUNK-SENS-A"), "kompetent")


class TestNoOtherAxesInTheMap(_WithProduction):
    def test_only_the_two_active_stages(self):
        self.assertEqual(STAGES, ("foundation", "kompetent"))
        raw = json.dumps(_read_raw_map()).lower()
        for banned in ('"bryggemester"', '"bryggeri"', '"hjemmebrygger"', '"difficulty"'):
            self.assertNotIn(banned, raw)

    def test_no_development_declarations_or_learner_progress(self):
        def keys(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    yield k
                    yield from keys(v)
            elif isinstance(node, list):
                for v in node:
                    yield from keys(v)

        raw_map = _read_raw_map()
        self.assertTrue(set(keys(raw_map)) <= {"schema_version", "notes", "modules", "module", "topic_id",
                                               "foundation", "kompetent", "chunks", "questions"})
        text = json.dumps(raw_map, ensure_ascii=False).lower()
        for banned in ("complete", "fullført", "gjennomgått", "mastery", "attempts", "verified", "score"):
            self.assertNotIn(banned, text)


class TestLookupApi(_WithProduction):
    def test_items_for_stage_keeps_pilot_order_and_objects(self):
        pilot = self.pilots["mesking"]
        komp = items_for_stage(self.stage_map, "mesking", pilot, "kompetent")
        self.assertEqual([c["id"] for c in komp["chunks"]], [f"CHUNK-MASH-{c}" for c in "BCDEF"])
        self.assertEqual([q["id"] for q in komp["questions"]], [f"Q-MASH-00{n}" for n in range(2, 9)])
        self.assertIs(komp["chunks"][0], pilot["chunks"][1])
        found = items_for_stage(self.stage_map, "mesking", pilot, "foundation")
        self.assertEqual([c["id"] for c in found["chunks"]], ["CHUNK-MASH-A"])

    def test_questions_only_stage_has_no_chunks(self):
        items = items_for_stage(self.stage_map, "kjoling", self.pilots["kjoling"], "kompetent")
        self.assertEqual(items["chunks"], [])
        self.assertEqual(len(items["questions"]), 2)

    def test_unknowns_raise(self):
        with self.assertRaises(ValueError):
            module_has_stage(self.stage_map, "mesking", "bryggemester")
        with self.assertRaises(ValueError):
            items_for_stage(self.stage_map, "mesking", self.pilots["mesking"], "Foundation")
        with self.assertRaises(KeyError):
            stage_for_chunk(self.stage_map, "mesking", "CHUNK-MASH-Z")
        with self.assertRaises(KeyError):
            stage_for_question(self.stage_map, "mesking", "Q-PACK-001")
        with self.assertRaises(KeyError):
            module_has_stage(self.stage_map, "bryggeri", "foundation")


class TestFailClosed(_WithProduction):
    """Every broken map is reported, never repaired (stage UI contract §6.1)."""

    def errors_for(self, mutate):
        data = copy.deepcopy(_read_raw_map())
        mutate(data)
        return validate_stage_map(data, self.pilots)

    def entry(self, data, module_id):
        return next(e for e in data["modules"] if e["module"] == module_id)

    def assertError(self, mutate, needle):
        errors = self.errors_for(mutate)
        self.assertTrue(any(needle in e for e in errors), errors)

    def test_current_map_passes(self):
        self.assertEqual(validate_stage_map(_read_raw_map(), self.pilots), [])

    def test_missing_chunk(self):
        self.assertError(lambda d: self.entry(d, "mesking")["kompetent"]["chunks"].remove("CHUNK-MASH-D"),
                         "chunk 'CHUNK-MASH-D' is not mapped to any stage")

    def test_missing_question(self):
        self.assertError(lambda d: self.entry(d, "smak")["kompetent"]["questions"].remove("Q-SENS-005"),
                         "question 'Q-SENS-005' is not mapped to any stage")

    def test_duplicate_mapping(self):
        self.assertError(lambda d: self.entry(d, "pakking")["foundation"]["questions"].append("Q-PACK-001"),
                         "duplicate mapping of 'Q-PACK-001'")

    def test_same_id_in_two_stages(self):
        self.assertError(lambda d: self.entry(d, "koking")["kompetent"]["chunks"].append("CHUNK-BOILHOP-B"),
                         "'CHUNK-BOILHOP-B' is mapped to both 'foundation' and 'kompetent'")

    def test_unknown_chunk_id(self):
        self.assertError(lambda d: self.entry(d, "gjaring")["kompetent"]["chunks"].append("CHUNK-FERM-Z"),
                         "unknown chunk id 'CHUNK-FERM-Z'")

    def test_item_from_another_module_is_unknown(self):
        self.assertError(lambda d: self.entry(d, "gjaring")["kompetent"]["questions"].append("Q-PACK-006"),
                         "unknown question id 'Q-PACK-006'")

    def test_unknown_question_id(self):
        self.assertError(lambda d: self.entry(d, "maaling")["foundation"]["questions"].append("Q-MEAS-099"),
                         "unknown question id 'Q-MEAS-099'")

    def test_unknown_module(self):
        def mutate(d):
            d["modules"].append({"module": "bryggemester", "topic_id": "X",
                                 "foundation": {"chunks": [], "questions": []},
                                 "kompetent": {"chunks": [], "questions": []}})
        self.assertError(mutate, "unknown module 'bryggemester'")

    def test_missing_module(self):
        self.assertError(lambda d: d["modules"].pop(), "Module 'smak' is missing")

    def test_duplicate_module(self):
        self.assertError(lambda d: d["modules"].append(copy.deepcopy(d["modules"][0])), "duplicate module 'raavarer'")

    def test_wrong_module_order(self):
        def mutate(d):
            d["modules"][0], d["modules"][1] = d["modules"][1], d["modules"][0]
        self.assertError(mutate, "canonical order")

    def test_topic_id_mismatch(self):
        self.assertError(lambda d: self.entry(d, "mesking").update(topic_id="PILOT-PACKAGE-FUNDAMENTALS"),
                         "does not match the pilot")

    def test_unknown_stage(self):
        def mutate(d):
            e = self.entry(d, "mesking")
            e["bryggemester"] = e.pop("kompetent")
        errors = self.errors_for(mutate)
        self.assertTrue(any("unknown field(s) ['bryggemester']" in e for e in errors), errors)
        self.assertTrue(any("missing field(s) ['kompetent']" in e for e in errors), errors)

    def test_malformed_structures(self):
        cases = [
            (lambda d: d.update(schema_version=2), "'schema_version' must be 1"),
            (lambda d: d.update(modules={}), "'modules' must be a list"),
            (lambda d: d.update(extra=True), "Unknown top-level field(s) ['extra']"),
            (lambda d: d["modules"].__setitem__(0, "raavarer"), "modules[0]: must be an object"),
            (lambda d: self.entry(d, "koking").update(foundation=["CHUNK-BOILHOP-A"]), "must be an object with 'chunks'"),
            (lambda d: self.entry(d, "koking")["foundation"].update(chunks="CHUNK-BOILHOP-A"), "must be a list of id strings"),
            (lambda d: self.entry(d, "koking")["foundation"].pop("questions"), "must have exactly the fields"),
        ]
        for mutate, needle in cases:
            with self.subTest(needle=needle):
                self.assertError(mutate, needle)
        self.assertEqual(validate_stage_map([], self.pilots), ["Stage map must be a JSON object, got list."])

    def test_load_raises_with_all_errors_and_never_repairs(self):
        data = copy.deepcopy(_read_raw_map())
        self.entry(data, "mesking")["kompetent"]["chunks"].remove("CHUNK-MASH-D")
        self.entry(data, "smak")["kompetent"]["questions"].append("Q-SENS-099")
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "map.json")
            with io.open(path, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            with self.assertRaises(StageMapError) as ctx:
                load_stage_map(path, pilots=self.pilots)
            self.assertEqual(len(ctx.exception.errors), 2)
            with io.open(path, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh), data)
            with io.open(path, "w", encoding="utf-8") as fh:
                fh.write("{not json")
            with self.assertRaises(StageMapError) as ctx:
                load_stage_map(path, pilots=self.pilots)
            self.assertIn("Invalid JSON", ctx.exception.errors[0])


class TestS1HasNoRuntimeEffect(unittest.TestCase):
    """S1 is metadata only: nothing in the app reads it yet, and the module
    is pure (stage UI contract §15)."""

    def _source(self, *parts):
        with io.open(os.path.join(_ROOT, *parts), encoding="utf-8") as fh:
            return fh.read()

    def test_no_runtime_consumer_yet(self):
        for parts in (("app.py",), ("ui", "bryggeskole_panel.py"), ("ui", "process_panel.py"),
                      ("ui", "hop_panel.py"), ("ui", "yeast_panel.py")):
            self.assertNotIn("course_stage", self._source(*parts), parts)

    def test_module_is_pure(self):
        source = self._source("bryggeskole", "course_stage.py")
        imports = set(re.findall(r"^(?:from|import)\s+([\w.]+)", source, re.M))
        self.assertEqual(imports, {"importlib", "json", "os"})
        for banned in ("session_state", "DEMO_MODE"):
            self.assertNotIn(banned, source)
        self.assertIsNone(re.search(r"\bst\.", source))
        self.assertIsNone(re.search(r"open\([^)]*['\"][wa]", source))
        self.assertNotIn(".write(", source)


if __name__ == "__main__":
    unittest.main()
