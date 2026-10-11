"""
Contract tests for the Bryggeskole learning-page map
(bryggeskole/learning_pages.py, bryggeskole/data/course_learning_pages.json;
owner acceptance #508, stage UI contract §5.1).

The authored chunk stays the content/provenance unit; a learning page only
groups adjacent chunks of one (module, stage) for presentation. These tests
pin the shipped map against the live stage map and pilots -- so a content
change that moves, adds or removes a chunk fails here instead of silently
mis-paging -- and prove the validator fails closed on every broken shape.

Pure: no Streamlit, no learner state.

Run with:
    python -m unittest tests.test_learning_pages
"""
import copy
import io
import json
import os
import tempfile
import unittest

from bryggeskole import course_stage
from bryggeskole import learning_pages as lp

# Approved page plan (KBH_LEARNING_PAGE_CLEANUP_PLAN.md §3): pages per
# (module, stage).
_PLAN = {
    ("raavarer", "foundation"): 4,
    ("rengjoring", "foundation"): 3,
    ("metodevalg", "foundation"): 3,
    ("mesking", "foundation"): 1,
    ("mesking", "kompetent"): 4,
    ("koking", "foundation"): 2,
    ("koking", "kompetent"): 1,
    ("kjoling", "foundation"): 4,
    ("gjaring", "foundation"): 2,
    ("gjaring", "kompetent"): 4,
    ("pakking", "foundation"): 4,
    ("pakking", "kompetent"): 2,
    ("maaling", "foundation"): 4,
    ("maaling", "kompetent"): 3,
    ("oppskrift", "kompetent"): 5,
    ("smak", "kompetent"): 4,
}

# The only explicit map subheadings the plan calls for (chunks that have no
# authored heading of their own).
_MAP_SUBHEADINGS = {
    "CHUNK-METHOD-B": {"no": "Meskepose (BIAB)", "en": "Mash bag (BIAB)"},
    "CHUNK-METHOD-C": {"no": "Tradisjonelt oppsett", "en": "Traditional setup"},
    "CHUNK-METHOD-D": {"no": "Alt-i-ett-maskin", "en": "All-in-one machine"},
    "CHUNK-PACK-B": {"no": "Flaskekondisjonering", "en": "Bottle conditioning"},
    "CHUNK-PACK-C": {"no": "Tvangskarbonering", "en": "Force carbonation"},
}


class _Production(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pilots = course_stage.load_production_pilots()
        cls.stage_map = course_stage.load_stage_map(pilots=cls.pilots)
        with io.open(lp.DEFAULT_LEARNING_PAGES_PATH, encoding="utf-8") as fh:
            cls.data = json.load(fh)
        cls.pages = cls.data["pages"]
        cls.chunks = {c["id"]: c for p in cls.pilots.values() for c in p["chunks"]}

    def _stage_chunk_ids(self, module_id, stage):
        return [c["id"] for c in course_stage.items_for_stage(
            self.stage_map, module_id, self.pilots[module_id], stage)["chunks"]]


class TestProductionMap(_Production):
    def test_validates_against_the_live_stage_map_and_pilots(self):
        self.assertEqual(lp.validate_learning_pages(self.data, self.stage_map, self.pilots), [])
        self.assertEqual(lp.load_learning_pages(), self.data)

    def test_schema_and_required_fields(self):
        self.assertEqual(set(self.data), {"schema_version", "notes", "pages"})
        self.assertEqual(self.data["schema_version"], 1)
        for page in self.pages:
            self.assertTrue({"id", "module", "stage", "title", "chunks"} <= set(page) <= {
                "id", "module", "stage", "title", "chunks", "subheadings"}, page.get("id"))

    def test_bilingual_titles(self):
        for page in self.pages:
            self.assertEqual(set(page["title"]), {"no", "en"}, page["id"])
            for lang in ("no", "en"):
                self.assertTrue(page["title"][lang].strip(), (page["id"], lang))
                self.assertEqual(page["title"][lang], page["title"][lang].strip())

    def test_baseline_page_totals(self):
        self.assertEqual(len(self.pages), 50)
        self.assertEqual(sum(p["stage"] == "foundation" for p in self.pages), 27)
        self.assertEqual(sum(p["stage"] == "kompetent" for p in self.pages), 23)
        counts = {}
        for page in self.pages:
            counts[(page["module"], page["stage"])] = counts.get((page["module"], page["stage"]), 0) + 1
        self.assertEqual(counts, _PLAN)

    def test_all_eleven_modules_are_represented(self):
        self.assertEqual(sorted({p["module"] for p in self.pages}), sorted(course_stage.MODULE_ORDER))

    def test_every_stage_with_chunks_has_pages_and_no_other(self):
        for module_id in course_stage.MODULE_ORDER:
            for stage in course_stage.STAGES:
                with self.subTest(module=module_id, stage=stage):
                    has_chunks = bool(self._stage_chunk_ids(module_id, stage))
                    self.assertEqual(bool(lp.pages_for_stage(self.data, module_id, stage)), has_chunks)

    def test_pages_concatenate_to_the_canonical_stage_chunks(self):
        total = 0
        for module_id in course_stage.MODULE_ORDER:
            for stage in course_stage.STAGES:
                mapped = [c for p in lp.pages_for_stage(self.data, module_id, stage) for c in p["chunks"]]
                self.assertEqual(mapped, self._stage_chunk_ids(module_id, stage), (module_id, stage))
                total += len(mapped)
        self.assertEqual(total, 84)

    def test_every_chunk_exactly_once_and_no_unknown_or_question_ids(self):
        mapped = [c for p in self.pages for c in p["chunks"]]
        self.assertEqual(len(mapped), len(set(mapped)))
        self.assertEqual(set(mapped), set(self.chunks))
        question_ids = {q["id"] for p in self.pilots.values() for q in p["questions"]}
        self.assertEqual(set(mapped) & question_ids, set())
        self.assertNotIn("Q-", json.dumps(self.data))

    def test_page_chunks_are_one_stage_of_one_module(self):
        for page in self.pages:
            for chunk_id in page["chunks"]:
                self.assertIn(chunk_id, self._stage_chunk_ids(page["module"], page["stage"]), page["id"])

    def test_deterministic_page_order_and_ids(self):
        expected = [(m, s) for m in course_stage.MODULE_ORDER for s in course_stage.STAGES if (m, s) in _PLAN]
        runs = []
        for page in self.pages:
            if not runs or runs[-1] != (page["module"], page["stage"]):
                runs.append((page["module"], page["stage"]))
        self.assertEqual(runs, expected)
        for module_id, stage in expected:
            ids = [p["id"] for p in lp.pages_for_stage(self.data, module_id, stage)]
            self.assertEqual(ids, [f"{module_id}.{stage}.{n}" for n in range(1, len(ids) + 1)])

    def test_title_and_subheading_rules(self):
        for page in self.pages:
            for lang in ("no", "en"):
                texts = {c: self.chunks[c]["text"][lang] for c in page["chunks"]}
                sections = lp.page_sections(page, texts, lang)
                self.assertEqual([s[0] for s in sections], page["chunks"])
                for chunk_id, subheading, body in sections:
                    self.assertFalse(body.startswith("**"), (page["id"], chunk_id, lang))
                    if subheading is not None:
                        self.assertFalse(lp.same_heading(subheading, page["title"][lang]), (page["id"], lang))
                # A suppressed authored heading is the page title itself.
                for chunk_id in page["chunks"]:
                    heading = lp.split_heading(texts[chunk_id])[0]
                    if heading is not None and lp.same_heading(heading, page["title"][lang]):
                        self.assertEqual(chunk_id, page["chunks"][0], page["id"])
        explicit = {c: v for p in self.pages for c, v in (p.get("subheadings") or {}).items()}
        self.assertEqual(explicit, _MAP_SUBHEADINGS)
        for chunk_id in explicit:
            self.assertIsNone(lp.split_heading(self.chunks[chunk_id]["text"]["no"])[0], chunk_id)

    def test_derived_titles_equal_the_first_chunks_heading(self):
        # Spot-check the plan's derived titles: the page title shows the
        # authored heading once, and the body no longer repeats it.
        malt = lp.pages_for_stage(self.data, "raavarer", "foundation")[0]
        self.assertEqual(malt["title"], {"no": "Malt", "en": "Malt"})
        self.assertEqual(malt["chunks"], ["CHUNK-RAW-A", "CHUNK-RAW-B", "CHUNK-RAW-C"])
        when = lp.pages_for_stage(self.data, "maaling", "foundation")[1]
        self.assertEqual(when["title"], {"no": "Når er gjæringen ferdig?", "en": "When is fermentation finished?"})


class TestHeadingHelper(unittest.TestCase):
    def test_bold_prefix_is_lifted_from_the_body(self):
        self.assertEqual(lp.split_heading("**Malt.** Malt er bygg som er maltet."), ("Malt", "Malt er bygg som er maltet."))

    def test_question_mark_is_kept_full_stop_dropped(self):
        self.assertEqual(lp.split_heading("**Feil eller karakter?** Tekst."), ("Feil eller karakter?", "Tekst."))
        self.assertEqual(lp.split_heading("**Volum – og når du målte det.** X"), ("Volum – og når du målte det", "X"))

    def test_text_without_a_leading_prefix_is_unchanged(self):
        for text in ("Malt er bygg.", "Du kan **se** og **lukte**.", " **Ikke i starten.** x", "*Kursiv.* x"):
            self.assertEqual(lp.split_heading(text), (None, text))

    def test_only_the_first_bold_run_is_lifted(self):
        self.assertEqual(lp.split_heading("**OG.** Mål **OG** før gjæring."), ("OG", "Mål **OG** før gjæring."))

    def test_same_heading(self):
        self.assertTrue(lp.same_heading("Malt.", "Malt"))
        self.assertTrue(lp.same_heading(" malt ", "Malt"))
        self.assertFalse(lp.same_heading("Feil eller karakter?", "Feil eller karakter"))
        self.assertFalse(lp.same_heading("Humle", "Malt"))

    def _page(self, **extra):
        page = {"id": "x.foundation.1", "module": "x", "stage": "foundation",
                "title": {"no": "Malt", "en": "Malt"}, "chunks": ["A", "B", "C"]}
        page.update(extra)
        return page

    def test_title_equal_prefix_is_suppressed_others_become_subheadings(self):
        texts = {"A": "**Malt.** Malt er korn.", "B": "**Spesialmalt.** Gir farge.", "C": "Andelen betyr noe."}
        self.assertEqual(lp.page_sections(self._page(), texts, "no"), [
            ("A", None, "Malt er korn."),
            ("B", "Spesialmalt", "Gir farge."),
            ("C", None, "Andelen betyr noe."),
        ])

    def test_explicit_subheading_only_for_a_chunk_without_a_heading(self):
        page = self._page(subheadings={"C": {"no": "Andel", "en": "Share"}})
        texts = {"A": "**Malt.** a", "B": "b", "C": "c"}
        self.assertEqual(lp.page_sections(page, texts, "en"), [("A", None, "a"), ("B", None, "b"), ("C", "Share", "c")])


class TestValidatorFailsClosed(_Production):
    def _errors(self, mutate):
        data = copy.deepcopy(self.data)
        mutate(data)
        return lp.validate_learning_pages(data, self.stage_map, self.pilots)

    def _page(self, data, page_id):
        return next(p for p in data["pages"] if p["id"] == page_id)

    def assertInvalid(self, mutate, needle):
        errors = self._errors(mutate)
        self.assertTrue(errors, "the map must be invalid")
        self.assertTrue(any(needle in e for e in errors), errors)

    def test_not_an_object_or_no_page_list(self):
        self.assertTrue(lp.validate_learning_pages([], self.stage_map, self.pilots))
        self.assertInvalid(lambda d: d.update(pages={}), "'pages' must be a list")

    def test_schema_version_and_unknown_fields(self):
        self.assertInvalid(lambda d: d.update(schema_version=2), "schema_version")
        self.assertInvalid(lambda d: d.update(extra=1), "Unknown top-level field")
        self.assertInvalid(lambda d: d["pages"][0].update(visual="malt"), "unknown field")
        self.assertInvalid(lambda d: d["pages"][0].pop("title"), "missing field")

    def test_unknown_module_or_stage(self):
        self.assertInvalid(lambda d: d["pages"][0].update(module="brygging"), "unknown module")
        self.assertInvalid(lambda d: d["pages"][0].update(stage="bryggemester"), "unknown stage")

    def test_title_must_be_bilingual_and_non_empty(self):
        self.assertInvalid(lambda d: d["pages"][0]["title"].pop("en"), "exactly ['no', 'en']")
        self.assertInvalid(lambda d: d["pages"][0]["title"].update(no="  "), "title.no")
        self.assertInvalid(lambda d: d["pages"][0].update(title="Malt"), "title")

    def test_unknown_chunk(self):
        self.assertInvalid(lambda d: d["pages"][0]["chunks"].append("CHUNK-RAW-Z"), "unknown chunk id")

    def test_question_id(self):
        self.assertInvalid(lambda d: d["pages"][0]["chunks"].append("Q-RAW-001"), "is a question id")

    def test_empty_page(self):
        self.assertInvalid(lambda d: d["pages"][0].update(chunks=[]), "non-empty list")

    def test_duplicate_chunk(self):
        self.assertInvalid(lambda d: self._page(d, "raavarer.foundation.2")["chunks"].insert(0, "CHUNK-RAW-C"),
                           "duplicate ['CHUNK-RAW-C']")

    def test_missing_chunk(self):
        self.assertInvalid(lambda d: self._page(d, "raavarer.foundation.1")["chunks"].remove("CHUNK-RAW-B"),
                           "missing ['CHUNK-RAW-B']")

    def test_reordered_chunks(self):
        def swap(d):
            page = self._page(d, "raavarer.foundation.1")
            page["chunks"] = ["CHUNK-RAW-B", "CHUNK-RAW-A", "CHUNK-RAW-C"]
        self.assertInvalid(swap, "concatenate to the stage chunks exactly")

    def test_non_adjacent_grouping(self):
        def split(d):
            self._page(d, "raavarer.foundation.1")["chunks"] = ["CHUNK-RAW-A", "CHUNK-RAW-C"]
            self._page(d, "raavarer.foundation.2")["chunks"].insert(0, "CHUNK-RAW-B")
        self.assertInvalid(split, "concatenate to the stage chunks exactly")

    def test_cross_stage_grouping(self):
        def move(d):
            self._page(d, "mesking.kompetent.1")["chunks"].insert(0, "CHUNK-MASH-A")
        self.assertInvalid(move, "no cross-stage grouping")

    def test_chunk_of_another_module(self):
        self.assertInvalid(lambda d: self._page(d, "raavarer.foundation.4")["chunks"].append("CHUNK-SAFE-A"),
                           "belongs to module 'rengjoring'")

    def test_page_for_a_stage_without_chunks(self):
        def invent(d):
            d["pages"].insert(4, {"id": "raavarer.kompetent.1", "module": "raavarer", "stage": "kompetent",
                                  "title": {"no": "X", "en": "X"}, "chunks": ["CHUNK-RAW-K"]})
        self.assertInvalid(invent, "has no chunks in stage 'kompetent'")

    def test_missing_stage(self):
        def drop(d):
            d["pages"] = [p for p in d["pages"] if (p["module"], p["stage"]) != ("smak", "kompetent")]
        self.assertInvalid(drop, "No pages for 'smak' / 'kompetent'")

    def test_page_ids_number_each_stage(self):
        self.assertInvalid(lambda d: d["pages"][1].update(id="raavarer.foundation.7"), "expected id raavarer.foundation.2")
        self.assertInvalid(lambda d: d["pages"][1].update(id="raavarer.foundation.1"), "duplicate page id")

    def test_page_order_is_canonical(self):
        def swap_runs(d):
            rav = [p for p in d["pages"] if p["module"] == "raavarer"]
            d["pages"] = [p for p in d["pages"] if p["module"] != "raavarer"] + rav
        self.assertInvalid(swap_runs, "canonical module and stage order")

    def test_stage_run_must_be_contiguous(self):
        def interleave(d):
            pages = d["pages"]
            pages[1], pages[4] = pages[4], pages[1]
        self.assertInvalid(interleave, "one contiguous run")

    def test_subheading_rules(self):
        self.assertInvalid(
            lambda d: self._page(d, "rengjoring.foundation.1").update(subheadings={"CHUNK-SAFE-B": {"no": "B", "en": "B"}}),
            "no double heading")
        self.assertInvalid(
            lambda d: self._page(d, "metodevalg.foundation.2")["subheadings"].update({"CHUNK-METHOD-A": {"no": "A", "en": "A"}}),
            "not a chunk on this page")
        self.assertInvalid(
            lambda d: self._page(d, "metodevalg.foundation.2")["subheadings"]["CHUNK-METHOD-B"].pop("en"),
            "subheadings.CHUNK-METHOD-B")
        self.assertInvalid(lambda d: self._page(d, "metodevalg.foundation.2").update(subheadings={}), "non-empty object")

    def test_title_heading_match_must_agree_across_languages(self):
        self.assertInvalid(lambda d: self._page(d, "raavarer.foundation.2")["title"].update(en="Hop basics"),
                           "equals the page title in only one language")

    def test_a_repeated_title_must_be_the_first_chunk(self):
        def retitle(d):
            self._page(d, "rengjoring.foundation.1")["title"] = {"no": "Rengjør først, saniter etterpå",
                                                                  "en": "Clean first, sanitize second"}
        self.assertInvalid(retitle, "is not the page's first chunk")

    def test_heading_parity_between_languages(self):
        pilots = copy.deepcopy(self.pilots)
        chunk = next(c for c in pilots["raavarer"]["chunks"] if c["id"] == "CHUNK-RAW-A")
        chunk["text"]["en"] = lp.split_heading(chunk["text"]["en"])[1]
        errors = lp.validate_learning_pages(self.data, self.stage_map, pilots)
        self.assertTrue(any("authored heading in only one language" in e for e in errors), errors)


class TestLoadFailsClosed(_Production):
    def _write(self, tmp, text):
        path = os.path.join(tmp, "pages.json")
        with io.open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def test_invalid_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(lp.LearningPagesError) as ctx:
                lp.load_learning_pages(self._write(tmp, "{"), self.stage_map, self.pilots)
        self.assertIn("Invalid JSON", ctx.exception.errors[0])

    def test_invalid_map_carries_every_error(self):
        data = copy.deepcopy(self.data)
        data["pages"][0]["chunks"] = []
        data["schema_version"] = 3
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(lp.LearningPagesError) as ctx:
                lp.load_learning_pages(self._write(tmp, json.dumps(data)), self.stage_map, self.pilots)
        self.assertGreaterEqual(len(ctx.exception.errors), 2)
        self.assertIsInstance(ctx.exception, ValueError)

    def test_missing_file(self):
        with self.assertRaises(OSError):
            lp.load_learning_pages(os.path.join(tempfile.gettempdir(), "kbh-no-such-pages.json"),
                                   self.stage_map, self.pilots)

    def test_pages_for_stage_rejects_an_unknown_stage(self):
        with self.assertRaises(ValueError):
            lp.pages_for_stage(self.data, "raavarer", "bryggemester")


if __name__ == "__main__":
    unittest.main()
