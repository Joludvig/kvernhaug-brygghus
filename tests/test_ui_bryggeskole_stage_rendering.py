"""
AppTest coverage for stage UI S2 -- lesson rendering by (module, stage)
(docs/development/v22_course_stage_ui_contract.md §5, §6, §11, §15; offline,
no GitHub issue yet).

Since S3 a stage is requested the way a learner does it: the `bs_trinn`
selector, then the module card. A lesson context S3 cards never open (a
single-stage module at the stage it lacks, an unknown stage) is reached
by setting the panel's internal lesson-context key (`bs_aktiv_trinn`)
directly, so S2's own handling of it stays covered. The selector and
cards themselves are covered by tests/test_ui_bryggeskole_stage_selector.py.

Expected stage content comes from the canonical stage map
(bryggeskole.course_stage) -- the same single source the panel uses -- and,
for the modules the Chief named, also from explicit ids.

All tests use an isolated KVERNHAUG_BRYGGESKOLE_STATE_DIR (via
_MedIsolertTilstand).

Run with:
    python -m unittest tests.test_ui_bryggeskole_stage_rendering
"""
import functools
import io
import json
import logging
import os
import re
import tempfile
import unittest
from unittest import mock

from bryggeskole import course_stage
from bryggeskole import learning_pages
from bryggeskole.mastery_store import read_mastery_state
from modules.i18n import t as t_ren
from tests.test_ui_bryggeskole_panel import (
    _MedIsolertTilstand,
    _alle_synlige_tekster,
    _feil_svar_ider,
    _knapp,
    _korrekt_svar_ider,
)
from ui import bryggeskole_panel as panel

_TRINN_KEY = "bs_aktiv_trinn"
_PANEL_SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "bryggeskole_panel.py")


def _stage_map():
    return course_stage.load_stage_map()


def _pilot(modul_id):
    return panel._MODULER[modul_id]["pilot"].read_pilot_file()


def _visning(modul_id, trinn):
    pilot = _pilot(modul_id)
    return dict(pilot, **course_stage.items_for_stage(_stage_map(), modul_id, pilot, trinn))


@functools.lru_cache(maxsize=None)
def _sidekart():
    return learning_pages.load_learning_pages()


def _sider(modul_id, trinn):
    """The learning pages of one (module, stage), from the same validated
    page map the panel uses."""
    return learning_pages.pages_for_stage(_sidekart(), modul_id, trinn)


def _base(modul_id, trinn):
    return modul_id + ("_k" if trinn == "kompetent" else "")


class _TrinnTest(_MedIsolertTilstand):
    _ENKELTFLYT = False

    def _apne_i_trinn(self, at, modul_id, trinn, miljo_knapp="bs_velg_hjemmebrygger_btn", sprak=None):
        if sprak:
            at.session_state["sprak"] = sprak
            at.run()
        self._velg_miljo(at, miljo_knapp)
        lens = [r for r in at.radio if r.key == "bs_trinn"]  # absent without a valid map
        if lens and trinn in course_stage.STAGES and lens[0].value != trinn:
            lens[0].set_value(trinn).run()
        _knapp(at, f"bs_apne_modul_{modul_id}_btn").click().run()
        self.assertEqual(len(at.exception), 0, at.exception)
        if lens and at.session_state[_TRINN_KEY] != trinn:
            # S3 cards never open this lesson context; S2's handling of it
            # is reached through the internal key.
            at.session_state[_TRINN_KEY] = trinn
            at.run()
        self._aktiv_modul = _base(modul_id, trinn)
        return at

    def _bolk_teller(self, at):
        return [c.value for c in at.caption if c.value.startswith(("Læringsside", "Learning page"))]

    def _leksjonstekst(self, at):
        return [m.value for m in at.markdown if m.value.strip()]

    def _gjennomga_leksjon(self, at, modul_id, trinn, chunks, sprak="no"):
        """Walks the stage lesson page by page and checks each page's
        counter, title and chunk bodies against the page map, and that the
        pages together hold exactly `chunks` (the expected stage chunks)."""
        base = self._aktiv_modul
        render = panel._MODULER[modul_id]["pilot"].render_chunk
        sider = _sider(modul_id, trinn)
        self.assertEqual([c for side in sider for c in side["chunks"]], [c["id"] for c in chunks])
        etter_id = {c["id"]: c for c in chunks}
        for i, side in enumerate(sider):
            self.assertEqual(self._bolk_teller(at), [
                f"Læringsside {i + 1} av {len(sider)}" if sprak == "no" else f"Learning page {i + 1} of {len(sider)}"
            ])
            self.assertEqual([s.value for s in at.subheader][-1], side["title"][sprak])
            tekster = {cid: render(etter_id[cid], sprak)["text"] for cid in side["chunks"]}
            for chunk_id, _sub, body in learning_pages.page_sections(side, tekster, sprak):
                self.assertIn(body, self._leksjonstekst(at), chunk_id)
            if i + 1 < len(sider):
                self.assertEqual([b.key for b in at.button if b.key.startswith("bs_start_sporsmal_")], [])
                _knapp(at, f"bs_bolk_neste_{base}_btn").click().run()
                self.assertEqual(len(at.exception), 0)
        _knapp(at, f"bs_start_sporsmal_{base}_btn")

    def _svar_alle(self, at, visning, runde=1, svar=None, sprak="no"):
        """Answers every stage question (correct unless `svar` overrides),
        checking no preselection and a disabled «Sjekk svar» before each
        choice, and the question order against the stage view."""
        base = self._aktiv_modul
        svar = svar or _korrekt_svar_ider(visning)
        for idx, sporsmal in enumerate(visning["questions"]):
            self.assertIsNone(at.radio(key=f"bs_valg_{base}_r{runde}_q{idx}").value)
            self.assertTrue(_knapp(at, f"bs_svar_btn_{base}_r{runde}_q{idx}").disabled)
            self.assertIn(
                f"{idx + 1} av {len(visning['questions'])}" if sprak == "no"
                else f"{idx + 1} of {len(visning['questions'])}",
                " ".join(c.value for c in at.caption),
            )
            self._besvar_sporsmal(at, idx, runde, svar[idx])
            self._fortsett(at, idx, runde)

    def _gjennomfor_trinn(self, modul_id, trinn, miljo_knapp="bs_velg_hjemmebrygger_btn", sprak="no"):
        at = self._ny_apptest()
        self._apne_i_trinn(at, modul_id, trinn, miljo_knapp, sprak if sprak != "no" else None)
        visning = _visning(modul_id, trinn)
        if visning["chunks"]:
            self._gjennomga_leksjon(at, modul_id, trinn, visning["chunks"], sprak)
        self._start_sporsmalsrunde(at)
        self._svar_alle(at, visning, sprak=sprak)
        _knapp(at, f"bs_prov_igjen_{self._aktiv_modul}_btn")
        return at, visning


class TestNormalEntryIsTheFoundationStage(_TrinnTest):
    """Since S3 the normal entry is stage-aware: with no choice made, a card
    opens the module's Foundation part with today's keys (S2 kept the
    single flow here only because S3 did not exist yet)."""

    def test_default_card_opens_foundation(self):
        at = self._ny_apptest()
        self._apne_modul(at, "mesking")
        self.assertEqual(at.session_state[_TRINN_KEY], "foundation")
        # #508: Mesking Foundation has two learning pages.
        self.assertEqual(self._bolk_teller(at), ["Læringsside 1 av 2"])
        _knapp(at, "bs_bolk_neste_mesking_btn").click().run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 2 av 2"])
        _knapp(at, "bs_start_sporsmal_mesking_btn")
        self.assertIn("mesking@foundation", at.session_state["bs_modul_sesjon"])
        self.assertNotIn("mesking", at.session_state["bs_modul_sesjon"])


class TestMixedModulesByStage(_TrinnTest):
    def test_mesking_foundation(self):
        at, visning = self._gjennomfor_trinn("mesking", "foundation")
        self.assertEqual([c["id"] for c in visning["chunks"]], ["CHUNK-MASH-A", "CHUNK-MASH-G"])
        self.assertEqual([q["id"] for q in visning["questions"]], ["Q-MASH-001", "Q-MASH-009", "Q-MASH-010"])
        # Foundation keeps today's widget keys.
        self.assertEqual(self._aktiv_modul, "mesking")
        tekst = " ".join(_alle_synlige_tekster(at))
        # #508: the basic mash procedure credits temperature and time in
        # Foundation; the Kompetent-only concepts stay out.
        for k in ("mashing.starch_conversion", "mashing.temperature", "mashing.duration"):
            self.assertIn(panel._konsept_label(k, "no"), tekst)
        for k in ("mashing.fermentability", "mashing.grain_separation", "mashing.preboil_check"):
            self.assertNotIn(panel._konsept_label(k, "no"), tekst)

    def test_mesking_kompetent(self):
        at, visning = self._gjennomfor_trinn("mesking", "kompetent")
        self.assertEqual([c["id"] for c in visning["chunks"]], [f"CHUNK-MASH-{c}" for c in "BCDEF"])
        self.assertEqual([q["id"] for q in visning["questions"]], [f"Q-MASH-00{n}" for n in range(2, 9)])
        self.assertEqual(self._aktiv_modul, "mesking_k")
        tekst = " ".join(_alle_synlige_tekster(at))
        for k in ("mashing.temperature", "mashing.grain_separation", "mashing.wort_collection",
                  "method.planning_variables", "mashing.preboil_check"):
            self.assertIn(panel._konsept_label(k, "no"), tekst)
        for k in ("mashing.starch_conversion", "mashing.dextrins"):
            self.assertNotIn(panel._konsept_label(k, "no"), tekst)
        self.assertIsNone(re.search(r"\b(mashing|method)\.[a-z_]+", tekst))

    def test_gjaring_both_stages(self):
        _, f = self._gjennomfor_trinn("gjaring", "foundation")
        self.assertEqual([c["id"][-1] for c in f["chunks"]], list("ABCD"))
        self.assertEqual(len(f["questions"]), 3)
        _, k = self._gjennomfor_trinn("gjaring", "kompetent")
        self.assertEqual([c["id"][-1] for c in k["chunks"]], list("EFGHIJK"))
        self.assertEqual(len(k["questions"]), 8)

    def test_pakking_both_stages(self):
        _, f = self._gjennomfor_trinn("pakking", "foundation")
        self.assertEqual([c["id"][-1] for c in f["chunks"]], list("ABCDE"))
        _, k = self._gjennomfor_trinn("pakking", "kompetent")
        self.assertEqual([c["id"][-1] for c in k["chunks"]], list("FGHI"))
        self.assertEqual([q["id"] for q in k["questions"]], [f"Q-PACK-00{n}" for n in range(6, 10)])

    def test_maaling_both_stages(self):
        _, f = self._gjennomfor_trinn("maaling", "foundation")
        self.assertEqual([c["id"][-1] for c in f["chunks"]], list("ABCDE"))
        self.assertEqual(len(f["questions"]), 6)
        _, k = self._gjennomfor_trinn("maaling", "kompetent")
        self.assertEqual([c["id"][-1] for c in k["chunks"]], list("FGHIJ"))
        self.assertEqual(len(k["questions"]), 7)

    def test_koking_interim_locks(self):
        _, f = self._gjennomfor_trinn("koking", "foundation")
        self.assertIn("CHUNK-BOILHOP-B", [c["id"] for c in f["chunks"]])
        self.assertEqual([q["id"] for q in f["questions"]],
                         ["Q-BOILHOP-001", "Q-BOILHOP-003", "Q-BOILHOP-004", "Q-BOILHOP-005", "Q-BOILHOP-006"])
        _, k = self._gjennomfor_trinn("koking", "kompetent")
        self.assertEqual([c["id"] for c in k["chunks"]], ["CHUNK-BOILHOP-F"])
        self.assertEqual([q["id"] for q in k["questions"]], ["Q-BOILHOP-002", "Q-BOILHOP-007", "Q-BOILHOP-008"])

    def test_kjoling_foundation_keeps_the_oxygen_rule_chunk(self):
        _, f = self._gjennomfor_trinn("kjoling", "foundation")
        self.assertIn("CHUNK-COOLXFER-D", [c["id"] for c in f["chunks"]])
        self.assertNotIn("Q-COOLXFER-004", [q["id"] for q in f["questions"]])


class TestQuestionsOnlyStage(_TrinnTest):
    def _sjekk(self, modul_id, forventet, sprak="no"):
        at = self._ny_apptest()
        self._apne_i_trinn(at, modul_id, "kompetent", sprak=sprak if sprak != "no" else None)
        self.assertEqual(self._bolk_teller(at), [], "No chunk may be invented.")
        self.assertEqual([i.value for i in at.info][-1], t_ren("bryggeskole.trinn.kun_sporsmal", sprak))
        _knapp(at, f"bs_trinn_repeter_{modul_id}_k_btn")
        _knapp(at, f"bs_start_sporsmal_{modul_id}_k_btn").click().run()
        visning = _visning(modul_id, "kompetent")
        self.assertEqual([q["id"] for q in visning["questions"]], forventet)
        self._svar_alle(at, visning, sprak=sprak)
        _knapp(at, f"bs_prov_igjen_{modul_id}_k_btn")

    def test_kjoling_kompetent_is_questions_only(self):
        self._sjekk("kjoling", ["Q-COOLXFER-004", "Q-COOLXFER-005"])

    def test_raavarer_kompetent_is_questions_only_in_english(self):
        self._sjekk("raavarer", ["Q-RAW-004", "Q-RAW-006", "Q-RAW-009", "Q-RAW-010", "Q-RAW-011", "Q-RAW-012"], "en")

    def test_review_foundation_switches_only_the_lesson_stage(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "kjoling", "kompetent")
        _knapp(at, "bs_trinn_repeter_kjoling_k_btn").click().run()
        self.assertEqual(at.session_state[_TRINN_KEY], "foundation")
        self.assertEqual(at.session_state["bs_aktiv_modul"], "kjoling")
        self.assertEqual(self._bolk_teller(at), ["Læringsside 1 av 4"])
        _knapp(at, "bs_bolk_neste_kjoling_btn")


class TestSingleStageModules(_TrinnTest):
    def test_foundation_only_modules_requested_as_kompetent(self):
        for modul_id, antall in (("rengjoring", 3), ("metodevalg", 3)):
            with self.subTest(modul=modul_id):
                at = self._ny_apptest()
                self._apne_i_trinn(at, modul_id, "kompetent")
                self.assertEqual(self._bolk_teller(at), [])
                self.assertIn(t_ren("bryggeskole.trinn.ingen_kompetent_del", "no"), [i.value for i in at.info])
                self.assertEqual([b.key for b in at.button if b.key.startswith(f"bs_start_sporsmal_{modul_id}")], [])
                self.assertNotIn(f"{modul_id}@kompetent", at.session_state["bs_modul_sesjon"])
                _knapp(at, f"bs_trinn_repeter_{modul_id}_k_btn").click().run()
                self.assertEqual(self._bolk_teller(at), [f"Læringsside 1 av {antall}"])

    def test_kompetent_only_modules_requested_as_foundation(self):
        for modul_id, antall in (("oppskrift", 5), ("smak", 4)):
            with self.subTest(modul=modul_id):
                at = self._ny_apptest()
                self._apne_i_trinn(at, modul_id, "foundation", sprak="en")
                self.assertEqual(self._bolk_teller(at), [])
                self.assertIn(t_ren("bryggeskole.trinn.horer_til_kompetent", "en"), [i.value for i in at.info])
                self.assertNotIn(f"{modul_id}@foundation", at.session_state["bs_modul_sesjon"])
                _knapp(at, f"bs_trinn_til_kompetent_{modul_id}_btn").click().run()
                self.assertEqual(self._bolk_teller(at), [f"Learning page 1 of {antall}"])
                _knapp(at, f"bs_bolk_neste_{modul_id}_k_btn")


class TestKeyIsolationAndSessions(_TrinnTest):
    def test_kompetent_and_foundation_never_share_widget_or_session_state(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "mesking", "kompetent")
        self._start_sporsmalsrunde(at)
        visning_k = _visning("mesking", "kompetent")
        fasit_k = _korrekt_svar_ider(visning_k)
        self._besvar_sporsmal(at, 0, 1, fasit_k[0])
        self._fortsett(at, 0, 1)
        # Choose (but do not submit) an answer on Kompetent question 2.
        at.radio(key="bs_valg_mesking_k_r1_q1").set_value(fasit_k[1]).run()
        sesjoner = at.session_state["bs_modul_sesjon"]
        self.assertEqual(sesjoner["mesking@kompetent"]["sporsmal_idx"], 1)
        self.assertNotIn("mesking", sesjoner)

        # Switch the lesson context to Foundation: fresh Foundation session,
        # today's keys, no value carried over.
        at.session_state[_TRINN_KEY] = "foundation"
        at.run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 1 av 2"])
        _knapp(at, "bs_bolk_neste_mesking_btn").click().run()
        _knapp(at, "bs_start_sporsmal_mesking_btn").click().run()
        self.assertIsNone(at.radio(key="bs_valg_mesking_r1_q0").value)
        self.assertTrue(_knapp(at, "bs_svar_btn_mesking_r1_q0").disabled)
        self.assertNotIn("bs_valg_mesking_r1_q1", [r.key for r in at.radio])

        # Back to Kompetent: it resumes at the same question of the same
        # round. (An unsubmitted radio choice is dropped by Streamlit when its
        # widget is not rendered -- the same as today's overview round-trip.)
        at.session_state[_TRINN_KEY] = "kompetent"
        at.run()
        self.assertEqual(at.session_state["bs_modul_sesjon"]["mesking@kompetent"]["sporsmal_idx"], 1)
        self.assertIsNone(at.radio(key="bs_valg_mesking_k_r1_q1").value)
        self.assertEqual(read_mastery_state()["answered_questions"].keys(), {"Q-MASH-002"})

    def test_retry_in_a_stage_starts_empty_with_submit_disabled(self):
        at, _ = self._gjennomfor_trinn("pakking", "kompetent", miljo_knapp="bs_velg_bryggeri_btn", sprak="en")
        _knapp(at, "bs_prov_igjen_pakking_k_btn").click().run()
        self.assertIsNone(at.radio(key="bs_valg_pakking_k_r2_q0").value)
        self.assertTrue(_knapp(at, "bs_svar_btn_pakking_k_r2_q0").disabled)

    def test_wrong_answer_gives_explanatory_feedback_in_kompetent(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "mesking", "kompetent")
        self._start_sporsmalsrunde(at)
        visning = _visning("mesking", "kompetent")
        self._besvar_sporsmal(at, 0, 1, _feil_svar_ider(visning)[0])
        self.assertIn(visning["questions"][0]["feedback_incorrect"]["no"], [e.value for e in at.error])


class TestMasteryStaysShared(_TrinnTest):
    def test_shared_concept_across_stages_is_one_concept(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "pakking", "foundation")
        self._bla_til_siste_bolk(at)
        self._start_sporsmalsrunde(at)
        self._svar_alle(at, _visning("pakking", "foundation"))
        self.assertEqual(read_mastery_state()["concepts"]["package.priming"]["attempts"], 1)

        at.session_state[_TRINN_KEY] = "kompetent"
        at.run()
        self._aktiv_modul = "pakking_k"
        self._start_sporsmalsrunde(at)
        self._svar_alle(at, _visning("pakking", "kompetent"))
        tilstand = read_mastery_state()
        self.assertEqual(tilstand["concepts"]["package.priming"]["attempts"], 2)
        pilot_konsepter = {k for q in _pilot("pakking")["questions"] for k in q["concepts"]}
        self.assertTrue(set(tilstand["concepts"]) <= pilot_konsepter)
        self.assertEqual(set(tilstand["answered_questions"]), {q["id"] for q in _pilot("pakking")["questions"]})
        self.assertFalse(any("kompetent" in k or "foundation" in k or "@" in k
                             for k in list(tilstand["concepts"]) + list(tilstand["answered_questions"])))


class TestBreadcrumb(_TrinnTest):
    def _sti(self, at):
        return next(c.value for c in at.caption if "▸" in c.value)

    def test_environment_and_stage_are_separate_axes(self):
        cases = [
            ("bs_velg_hjemmebrygger_btn", "kompetent", None,
             "🎓 Bryggeskole ▸ 🏠 Hjemmebrygger ▸ Trinn 2 · Kompetent ▸ Mesking"),
            ("bs_velg_bryggeri_btn", "foundation", None,
             "🎓 Bryggeskole ▸ 🏭 Bryggeri ▸ Trinn 1 · Foundation ▸ Mesking"),
            ("bs_velg_hjemmebrygger_btn", "kompetent", "en",
             "🎓 Brew School ▸ 🏠 Homebrewer ▸ Stage 2 · Competent homebrewer ▸ Mashing"),
            ("bs_velg_bryggeri_btn", "foundation", "en",
             "🎓 Brew School ▸ 🏭 Brewery ▸ Stage 1 · Foundation ▸ Mashing"),
        ]
        for miljo_knapp, trinn, sprak, forventet in cases:
            with self.subTest(miljo=miljo_knapp, trinn=trinn, sprak=sprak):
                at = self._ny_apptest()
                self._apne_i_trinn(at, "mesking", trinn, miljo_knapp, sprak)
                self.assertEqual(self._sti(at), forventet)

    def test_single_flow_breadcrumb_is_unchanged(self):
        with mock.patch.object(panel._course_stage, "load_stage_map", side_effect=FileNotFoundError("x")),                 self.assertLogs("ui.bryggeskole_panel", level=logging.WARNING):
            at = self._ny_apptest()
            self._apne_modul(at, "mesking")
            self.assertEqual(self._sti(at), "🎓 Bryggeskole ▸ 🏠 Hjemmebrygger ▸ Mesking")


class TestInvalidMapFallsBackToTheSingleFlow(_TrinnTest):
    def _sjekk_fallback(self, at):
        pilot = _pilot("mesking")
        self.assertEqual(self._bolk_teller(at), [f"Læringsside 1 av {len(pilot['chunks'])}"])
        _knapp(at, "bs_bolk_neste_mesking_btn")
        self.assertEqual([b.key for b in at.button if "_k_" in (b.key or "")], [])
        self.assertNotIn("Trinn", " ".join(c.value for c in at.caption))
        self.assertIsNone(at.session_state["_bs_trinnkart"])
        self.assertIn("mesking", at.session_state["bs_modul_sesjon"])

    def test_real_invalid_map_file(self):
        with io.open(course_stage.DEFAULT_STAGE_MAP_PATH, encoding="utf-8") as fh:
            data = json.load(fh)
        data["modules"][3]["kompetent"]["chunks"].remove("CHUNK-MASH-D")  # mesking: unmapped chunk
        ekte_last = course_stage.load_stage_map
        with tempfile.TemporaryDirectory() as tmp:
            sti = os.path.join(tmp, "map.json")
            with io.open(sti, "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            with mock.patch.object(panel._course_stage, "load_stage_map", lambda: ekte_last(sti)), \
                    self.assertLogs("ui.bryggeskole_panel", level=logging.WARNING) as logg:
                at = self._ny_apptest()
                self._apne_i_trinn(at, "mesking", "kompetent")
                self._sjekk_fallback(at)
                _knapp(at, "bs_bolk_neste_mesking_btn").click().run()
                self.assertEqual(len(at.exception), 0)
        self.assertEqual(len(logg.records), 1, "The fallback is logged once per session, not on every rerun.")
        self.assertIn("StageMapError", logg.output[0])

    def test_missing_map_file(self):
        def mangler():
            raise FileNotFoundError("course_stage_map.json")

        with mock.patch.object(panel._course_stage, "load_stage_map", mangler), \
                self.assertLogs("ui.bryggeskole_panel", level=logging.WARNING):
            at = self._ny_apptest()
            self._apne_i_trinn(at, "mesking", "foundation")
            self._sjekk_fallback(at)

    def test_unknown_lesson_stage_is_never_guessed(self):
        # Not a fallback to the whole module any more: an unknown lesson
        # context uses the learner's lens (Foundation here), never a guess.
        at = self._ny_apptest()
        self._apne_i_trinn(at, "mesking", "bryggemester")
        self.assertEqual(self._bolk_teller(at), ["Læringsside 1 av 2"])
        self.assertIn("Trinn 1 · Foundation", self._sti_tekst(at))

    def _sti_tekst(self, at):
        return next(c.value for c in at.caption if "▸" in c.value)


def _elementer(node):
    """The rendered elements under `node`, in display order, as (type,
    value) pairs; containers and columns are walked through."""
    ut = []
    for barn in node.children.values():
        if getattr(barn, "children", None):
            ut.extend(_elementer(barn))
        else:
            verdi = getattr(barn, "value", None) if barn.type in ("markdown", "caption", "subheader") else None
            ut.append((barn.type, verdi))
    return ut


_MALT_SVG = '<svg viewBox="0 0 560 270"'


class TestLearningPages(_TrinnTest):
    """Owner acceptance #508: a stage lesson shows learning pages -- adjacent
    chunks under one real title -- instead of one chunk per screen."""

    def _side_elementer(self, at):
        """The lesson page's own elements: after the page counter, before the
        nav row."""
        alle = _elementer(at.main)
        start = next(i for i, (typ, v) in enumerate(alle)
                     if typ == "caption" and v.startswith(("Læringsside", "Learning page")))
        slutt = next(i for i, (typ, _v) in enumerate(alle) if typ == "button" and i > start)
        return alle[start + 1:slutt]

    def _bodies(self, modul_id, chunk_ids, sprak="no"):
        render = panel._MODULER[modul_id]["pilot"].render_chunk
        etter_id = {c["id"]: c for c in _pilot(modul_id)["chunks"]}
        return [learning_pages.split_heading(render(etter_id[c], sprak)["text"])[1] for c in chunk_ids]

    def test_malt_page_title_once_three_chunks_and_visual_beside(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._ny_apptest()
                self._apne_i_trinn(at, "raavarer", "foundation", sprak=sprak if sprak != "no" else None)
                self.assertEqual(self._bolk_teller(at),
                                 ["Læringsside 1 av 4" if sprak == "no" else "Learning page 1 of 4"])
                elementer = self._side_elementer(at)
                self.assertEqual([v for typ, v in elementer if typ == "subheader"], ["Malt"])
                markdown = [v for typ, v in elementer if typ == "markdown"]
                bodies = self._bodies("raavarer", ["CHUNK-RAW-A", "CHUNK-RAW-B", "CHUNK-RAW-C"], sprak)
                for body in bodies:
                    self.assertIn(body, markdown)
                self.assertEqual([markdown.index(b) for b in bodies], sorted(markdown.index(b) for b in bodies),
                                 "chunks render in page order")
                self.assertFalse(any("**Malt.**" in v for v in markdown), "the embedded title is lifted, not repeated")
                self.assertFalse(any(v.startswith("####") for v in markdown))
                self.assertEqual(sum(v.startswith(_MALT_SVG) for v in markdown), 1)
                self.assertEqual(len(at.columns), 2 + 3, "text | visual columns plus the nav row")
                _knapp(at, "bs_bolk_neste_raavarer_btn").click().run()
                markdown = [v for typ, v in self._side_elementer(at) if typ == "markdown"]
                self.assertEqual(sum(v.startswith(_MALT_SVG) for v in markdown), 0)
                self.assertEqual(len(at.columns), 3, "no columns on a page without the Malt visual")

    def test_authored_headings_become_subheadings_on_grouped_pages(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "rengjoring", "foundation")
        for _ in range(2):
            _knapp(at, "bs_bolk_neste_rengjoring_btn").click().run()
        elementer = self._side_elementer(at)
        self.assertEqual([v for typ, v in elementer if typ == "subheader"], ["Varme, CO₂ og trykk"])
        self.assertEqual([v for typ, v in elementer if typ == "markdown" and v.startswith("####")],
                         ["#### Varm vørter og overkoking", "#### CO₂ fra gjæringen", "#### Trykk i flasker og fat"])
        self.assertFalse(any(typ == "markdown" and v.startswith("**") for typ, v in elementer))

    def test_map_subheadings_only_where_the_chunk_has_none(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "metodevalg", "foundation", sprak="en")
        _knapp(at, "bs_bolk_neste_metodevalg_btn").click().run()
        elementer = self._side_elementer(at)
        self.assertEqual([v for typ, v in elementer if typ == "subheader"], ["Three ways to set up the brew"])
        self.assertEqual([v for typ, v in elementer if typ == "markdown" and v.startswith("####")],
                         ["#### Mash bag (BIAB)", "#### Traditional setup", "#### All-in-one machine"])
        # The method flow is a wide diagram: once, full width below the text.
        markdown = [v for typ, v in elementer if typ == "markdown"]
        self.assertEqual(sum(v.startswith("<svg") for v in markdown), 1)
        self.assertTrue(markdown[-1].startswith("<svg"))
        self.assertEqual(len(at.columns), 3)

    def test_methodology_label_stays_under_its_own_chunk(self):
        pilot = _pilot("pakking")
        basis = {c["id"]: c.get("basis") for c in pilot["chunks"]}
        side = _sider("pakking", "kompetent")[0]
        self.assertEqual([basis[c] for c in side["chunks"]], ["fact", "methodology"])
        at = self._ny_apptest()
        self._apne_i_trinn(at, "pakking", "kompetent")
        etikett = t_ren("bryggeskole.metode_etikett", "no")
        bodies = self._bodies("pakking", side["chunks"])
        rekkefolge = [v for typ, v in self._side_elementer(at) if typ in ("markdown", "caption")]
        self.assertEqual(rekkefolge.count(etikett), 1, "never a page-wide methodology label")
        self.assertLess(rekkefolge.index(bodies[0]), rekkefolge.index(bodies[1]))
        self.assertEqual(rekkefolge.index(etikett), rekkefolge.index(bodies[1]) + 1)

    def test_every_wide_visual_renders_once_per_page(self):
        for modul_id, trinn in (("koking", "foundation"), ("koking", "kompetent"), ("kjoling", "foundation"),
                                ("pakking", "foundation"), ("pakking", "kompetent")):
            with self.subTest(modul=modul_id, trinn=trinn):
                at = self._ny_apptest()
                self._apne_i_trinn(at, modul_id, trinn)
                antall = len(_sider(modul_id, trinn))
                for n in range(antall):
                    markdown = [v for typ, v in self._side_elementer(at) if typ == "markdown"]
                    self.assertEqual(sum(v.startswith("<svg") for v in markdown), 1, n)
                    if n + 1 < antall:
                        _knapp(at, f"bs_bolk_neste_{self._aktiv_modul}_btn").click().run()

    def test_previous_next_resume_and_start_only_after_the_last_page(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "gjaring", "kompetent")
        self.assertTrue(_knapp(at, "bs_bolk_forrige_gjaring_k_btn").disabled)
        _knapp(at, "bs_bolk_neste_gjaring_k_btn").click().run()
        _knapp(at, "bs_bolk_neste_gjaring_k_btn").click().run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 3 av 4"])
        _knapp(at, "bs_bolk_forrige_gjaring_k_btn").click().run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 2 av 4"])
        self.assertEqual(at.session_state["bs_modul_sesjon"]["gjaring@kompetent"]["side_idx"], 1)
        # Leave and reopen: the same page.
        _knapp(at, "bs_tilbake_gjaring_k_btn").click().run()
        _knapp(at, "bs_apne_modul_gjaring_btn").click().run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 2 av 4"])
        # The other stage of the module keeps its own position.
        at.session_state[_TRINN_KEY] = "foundation"
        at.run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 1 av 2"])
        at.session_state[_TRINN_KEY] = "kompetent"
        at.run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 2 av 4"])
        _knapp(at, "bs_bolk_neste_gjaring_k_btn").click().run()
        self.assertEqual([b.key for b in at.button if b.key.startswith("bs_start_sporsmal_")], [])
        _knapp(at, "bs_bolk_neste_gjaring_k_btn").click().run()
        self.assertEqual(self._bolk_teller(at), ["Læringsside 4 av 4"])
        self.assertEqual([b.key for b in at.button if b.key.startswith("bs_bolk_neste_")], [])
        _knapp(at, "bs_start_sporsmal_gjaring_k_btn").click().run()
        self.assertIsNone(at.radio(key="bs_valg_gjaring_k_r1_q0").value)

    def test_a_session_from_before_pages_resumes_on_the_page_holding_its_chunk(self):
        at = self._ny_apptest()
        self._apne_i_trinn(at, "raavarer", "foundation")
        sesjoner = at.session_state["bs_modul_sesjon"]
        gammel = dict(sesjoner["raavarer@foundation"])
        del gammel["side_idx"]
        gammel["bolk_idx"] = 5  # CHUNK-RAW-F, the last chunk of the Humle page
        sesjoner["raavarer@foundation"] = gammel
        at.session_state["bs_modul_sesjon"] = sesjoner
        at.run()
        self.assertEqual(len(at.exception), 0, at.exception)
        self.assertEqual(self._bolk_teller(at), ["Læringsside 2 av 4"])
        self.assertEqual([s.value for s in at.subheader][-1], "Humle")

    def test_an_invalid_page_map_falls_back_to_one_chunk_per_screen(self):
        feil = learning_pages.LearningPagesError(["pages[0]: broken"])
        with mock.patch.object(panel._learning_pages, "load_learning_pages", side_effect=feil), \
                self.assertLogs("ui.bryggeskole_panel", level=logging.WARNING) as logg:
            at = self._ny_apptest()
            self._apne_i_trinn(at, "raavarer", "foundation")
            visning = _visning("raavarer", "foundation")
            self.assertEqual(self._bolk_teller(at), [f"Læringsside 1 av {len(visning['chunks'])}"])
            render = panel._MODULER["raavarer"]["pilot"].render_chunk
            self.assertIn(render(visning["chunks"][0], "no")["text"], self._leksjonstekst(at))
            self.assertEqual([s.value for s in at.subheader], ["🌿 Råvarer"])
            _knapp(at, "bs_bolk_neste_raavarer_btn").click().run()
            self.assertEqual(len(at.exception), 0)
            self.assertEqual(self._bolk_teller(at), [f"Læringsside 2 av {len(visning['chunks'])}"])
        self.assertEqual(len(logg.records), 1, "The fallback is logged once per session, not on every rerun.")
        self.assertIn("LearningPagesError", logg.output[0])


class TestStageRenderingSource(unittest.TestCase):
    def test_stage_tables_cover_exactly_the_canonical_stages(self):
        self.assertEqual(set(panel._TRINN_NOKKEL_INFIKS), set(course_stage.STAGES))
        self.assertEqual(set(panel._TRINN_STI_NOKKEL), set(course_stage.STAGES))
        self.assertEqual(panel._TRINN_NOKKEL_INFIKS["foundation"], "")
        self.assertEqual(panel._TRINN_NOKKEL_INFIKS["kompetent"], "_k")

    def test_no_stage_logic_from_difficulty_letters_or_id_lists(self):
        with io.open(_PANEL_SOURCE, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn('["difficulty"]', source)
        self.assertNotIn('get("difficulty"', source)
        self.assertIsNone(re.search(r"[\"'](CHUNK|Q)-[A-Z]+-", source))
        self.assertIn("_course_stage.items_for_stage", source)

    def test_s2_strings_exist_in_both_languages(self):
        for key in ("bryggeskole.trinn.sti.foundation", "bryggeskole.trinn.sti.kompetent",
                    "bryggeskole.trinn.kun_sporsmal", "bryggeskole.trinn.repeter_foundation",
                    "bryggeskole.trinn.ingen_kompetent_del", "bryggeskole.trinn.horer_til_kompetent",
                    "bryggeskole.trinn.til_kompetent"):
            no, en = t_ren(key, "no"), t_ren(key, "en")
            self.assertNotEqual(no, key)
            self.assertNotEqual(en, key)
            self.assertNotEqual(no, en)
        self.assertEqual(t_ren("bryggeskole.trinn.sti.kompetent", "en"), "Stage 2 · Competent homebrewer")
        for sprak in ("no", "en"):
            for trinn_key in ("bryggeskole.trinn.sti.foundation", "bryggeskole.trinn.sti.kompetent"):
                self.assertNotEqual(t_ren(trinn_key, sprak), t_ren("bryggeskole.miljo.hjemmebrygger", sprak))


if __name__ == "__main__":
    unittest.main()
