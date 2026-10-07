"""
Stage UI S4 -- learner progress per (module, stage) and per stage
(docs/development/v22_course_stage_ui_contract.md §7.2, §7.3, §7.4, §8;
offline, no GitHub issue yet).

What is checked:
- the canonical status from course_stage.module_stage_status() (pure,
  read-only over answered_questions): fresh, partial, worked through,
  earlier correct but latest wrong, stages independent, a concept shared
  across stages never merges question progress, existing history counts;
- stage_progress(): module counts with the denominator from the stage map
  (never a hard-coded 9), and stage_worked_through() defined through it;
- the cards: one status line for modules with content at the selected
  stage, no status on single-stage special cards, and the old session
  badges replaced (only the session-local button text stays);
- the stage count line, guidance, recommendation and default lens all
  driven by the same helpers;
- no percentage, score or completion wording; no mastery writes; the
  invalid-map fallback is still today's overview.

All AppTests use an isolated KVERNHAUG_BRYGGESKOLE_STATE_DIR; history is
seeded only through apply_answer + write_mastery_state.

Run with:
    python -m unittest tests.test_ui_bryggeskole_stage_progress
"""
import copy
import inspect
import os
import re
import unittest
from unittest import mock

from bryggeskole import course_stage
from bryggeskole.mastery import apply_answer
from bryggeskole.mastery_store import default_state_path, neutral_state_document, read_mastery_state
from modules.i18n import t as t_ren
from tests.test_ui_bryggeskole_panel import _alle_synlige_tekster, _korrekt_svar_ider
from tests.test_ui_bryggeskole_stage_selector import (
    _EKSPLISITT,
    _FORBUDTE_ORD,
    _KANONISK,
    _KUN_FOUNDATION,
    _KUN_KOMPETENT,
    _NOW,
    _S3Test,
    _alle_foundation,
    _pilot,
    _seed,
    _stage_map,
    _visning,
)
from ui import bryggeskole_panel as panel

_STATUS_NOKKEL = {
    course_stage.STATUS_NOT_STARTED: "bryggeskole.trinn.status.ikke_startet",
    course_stage.STATUS_IN_PROGRESS: "bryggeskole.trinn.status.pabegynt",
    course_stage.STATUS_WORKED_THROUGH: "bryggeskole.trinn.status.gjennomgatt",
}
_GAMLE_MERKER = ("bryggeskole.status.ovd_tidligere", "bryggeskole.status.pabegynt", "bryggeskole.status.fullfort_okt")


def _t(key, sprak="no", **kw):
    return t_ren(key, sprak, **kw)


def _sporsmal(modul_id, trinn):
    return list(course_stage._module_entry(_stage_map(), modul_id)[trinn]["questions"])


def _svar(dokument, qid, korrekt):
    modul_id = next(m for m in _KANONISK
                    if any(qid in course_stage._module_entry(_stage_map(), m)[s]["questions"]
                           for s in course_stage.STAGES))
    sporsmal = next(q for q in _pilot(modul_id)["questions"] if q["id"] == qid)
    return apply_answer(dokument, sporsmal, korrekt, now=_NOW)


def _moduler_med_sporsmal(trinn):
    return [m for m in _KANONISK if _sporsmal(m, trinn)]


class TestCanonicalStatus(unittest.TestCase):
    """Pure helpers over answered_questions -- the one definition."""

    def setUp(self):
        self.kart = _stage_map()

    def _status(self, aq, modul_id, trinn):
        return course_stage.module_stage_status(self.kart, modul_id, trinn, aq)

    def test_fresh_learner(self):
        for trinn in course_stage.STAGES:
            for modul_id in _moduler_med_sporsmal(trinn):
                self.assertEqual(self._status({}, modul_id, trinn), course_stage.STATUS_NOT_STARTED)
            self.assertEqual(course_stage.stage_progress(self.kart, trinn, {}), (0, len(_moduler_med_sporsmal(trinn))))

    def test_partial_worked_through_and_latest_wrong(self):
        dok = neutral_state_document()
        ids = _sporsmal("gjaring", "kompetent")
        dok = _svar(dok, ids[0], True)
        aq = dok["answered_questions"]
        self.assertEqual(self._status(aq, "gjaring", "kompetent"), course_stage.STATUS_IN_PROGRESS)
        for qid in ids[1:]:
            dok = _svar(dok, qid, True)
        self.assertEqual(self._status(dok["answered_questions"], "gjaring", "kompetent"),
                         course_stage.STATUS_WORKED_THROUGH)
        # Earlier correct, latest wrong: the latest answer is authoritative.
        dok = _svar(dok, ids[2], False)
        self.assertEqual(dok["answered_questions"][ids[2]]["attempts"], 2)
        self.assertEqual(self._status(dok["answered_questions"], "gjaring", "kompetent"),
                         course_stage.STATUS_IN_PROGRESS)
        # ...and a later correct answer restores it.
        dok = _svar(dok, ids[2], True)
        self.assertEqual(self._status(dok["answered_questions"], "gjaring", "kompetent"),
                         course_stage.STATUS_WORKED_THROUGH)

    def test_stages_are_independent(self):
        dok = neutral_state_document()
        for qid in _sporsmal("mesking", "foundation"):
            dok = _svar(dok, qid, True)
        aq = dok["answered_questions"]
        self.assertEqual(self._status(aq, "mesking", "foundation"), course_stage.STATUS_WORKED_THROUGH)
        self.assertEqual(self._status(aq, "mesking", "kompetent"), course_stage.STATUS_NOT_STARTED)
        self.assertEqual(course_stage.stage_progress(self.kart, "foundation", aq)[0], 1)
        self.assertEqual(course_stage.stage_progress(self.kart, "kompetent", aq)[0], 0)

    def test_shared_concept_never_merges_question_progress(self):
        dok = neutral_state_document()
        for qid in _sporsmal("pakking", "foundation"):
            dok = _svar(dok, qid, True)
        self.assertGreater(dok["concepts"]["package.priming"]["attempts"], 0)
        kompetent_konsepter = {k for q in _visning("pakking", "kompetent")["questions"] for k in q["concepts"]}
        self.assertIn("package.priming", kompetent_konsepter)
        self.assertEqual(self._status(dok["answered_questions"], "pakking", "kompetent"),
                         course_stage.STATUS_NOT_STARTED)

    def test_single_stage_modules_have_no_status_at_the_other_stage(self):
        for modul_id in _KUN_FOUNDATION:
            self.assertIsNone(self._status({}, modul_id, "kompetent"))
        for modul_id in _KUN_KOMPETENT:
            self.assertIsNone(self._status({}, modul_id, "foundation"))

    def test_denominator_comes_from_the_map(self):
        for trinn in course_stage.STAGES:
            self.assertEqual(course_stage.stage_progress(self.kart, trinn, {})[1],
                             len(_moduler_med_sporsmal(trinn)))
        endret = copy.deepcopy(self.kart)
        mesking = course_stage._module_entry(endret, "mesking")
        mesking["foundation"] = {"chunks": [], "questions": []}
        self.assertEqual(course_stage.stage_progress(endret, "foundation", {})[1],
                         course_stage.stage_progress(self.kart, "foundation", {})[1] - 1)

    def test_stage_worked_through_is_defined_by_stage_progress(self):
        dok = neutral_state_document()
        moduler = _moduler_med_sporsmal("foundation")
        for modul_id in moduler:
            for qid in _sporsmal(modul_id, "foundation"):
                dok = _svar(dok, qid, True)
            n, totalt = course_stage.stage_progress(self.kart, "foundation", dok["answered_questions"])
            self.assertEqual(course_stage.stage_worked_through(self.kart, "foundation", dok["answered_questions"]),
                             n == totalt)
        self.assertEqual(n, totalt)
        self.assertFalse(course_stage.stage_worked_through(self.kart, "kompetent", dok["answered_questions"]))

    def test_helpers_are_pure(self):
        aq = {"Q-MASH-001": {"attempts": 1, "last_correct": True, "last_tested": _NOW}}
        foer = copy.deepcopy(aq)
        course_stage.stage_progress(self.kart, "foundation", aq)
        course_stage.module_stage_status(self.kart, "mesking", "foundation", aq)
        self.assertEqual(aq, foer)


class _S4Test(_S3Test):
    def _status_linjer(self, at, sprak="no"):
        statuser = {_t(n, sprak): s for s, n in _STATUS_NOKKEL.items()}
        return [statuser[c.value] for c in at.caption if c.value in statuser]

    def _telling(self, at, sprak="no"):
        monster = re.compile(r"^\d+ (av|of) \d+ ")
        return [c.value for c in at.caption if monster.match(c.value)]

    def _forventet(self, trinn, aq):
        kart = _stage_map()
        return [course_stage.module_stage_status(kart, m, trinn, aq) for m in _KANONISK
                if course_stage.module_has_stage(kart, m, trinn)
                and course_stage.module_stage_status(kart, m, trinn, aq) is not None]


class TestCardStatusAndCount(_S4Test):
    def test_fresh_learner_no_and_en_both_environments(self):
        for sprak in ("no", "en"):
            for knapp in ("bs_velg_hjemmebrygger_btn", "bs_velg_bryggeri_btn"):
                for trinn in course_stage.STAGES:
                    with self.subTest(sprak=sprak, miljo=knapp, trinn=trinn):
                        at = self._oversikt(knapp, sprak if sprak != "no" else None)
                        if trinn == "kompetent":
                            self._velg_trinn(at, trinn)
                        totalt = len(_moduler_med_sporsmal(trinn))
                        self.assertEqual(self._status_linjer(at, sprak), [course_stage.STATUS_NOT_STARTED] * totalt)
                        self.assertEqual(self._telling(at, sprak),
                                         [_t("bryggeskole.trinn.fremdrift", sprak, n=0, totalt=totalt)])
                        self.assertEqual(len(self._kort(at)), 11)

    def test_partial_and_worked_through_history(self):
        _seed([("raavarer", "foundation")])
        gjaring = _sporsmal("gjaring", "foundation")
        _seed([("gjaring", "foundation")], unntak=set(gjaring[1:]))
        _seed([("mesking", "kompetent")])
        aq = read_mastery_state()["answered_questions"]
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt("bs_velg_bryggeri_btn", sprak if sprak != "no" else None)
                statuser = self._status_linjer(at, sprak)
                self.assertEqual(statuser, self._forventet("foundation", aq))
                self.assertEqual(statuser[0], course_stage.STATUS_WORKED_THROUGH)  # Råvarer
                self.assertEqual(statuser[6], course_stage.STATUS_IN_PROGRESS)     # Gjæring
                self.assertEqual(statuser[3], course_stage.STATUS_NOT_STARTED)     # Mesking F
                self.assertEqual(self._telling(at, sprak), [_t("bryggeskole.trinn.fremdrift", sprak, n=1, totalt=9)])
                self._velg_trinn(at, "kompetent")
                statuser = self._status_linjer(at, sprak)
                self.assertEqual(statuser, self._forventet("kompetent", aq))
                self.assertEqual(statuser[1], course_stage.STATUS_WORKED_THROUGH)  # Mesking K
                self.assertEqual(self._telling(at, sprak), [_t("bryggeskole.trinn.fremdrift", sprak, n=1, totalt=9)])

    def test_latest_wrong_answer_downgrades_the_card(self):
        _seed([("pakking", "foundation")])
        _seed([("pakking", "foundation")], korrekt=False, unntak=set(_sporsmal("pakking", "foundation")[1:]))
        at = self._oversikt()
        self.assertEqual(self._status_linjer(at)[7], course_stage.STATUS_IN_PROGRESS)
        self.assertEqual(self._telling(at), [_t("bryggeskole.trinn.fremdrift", n=0, totalt=9)])

    def test_status_updates_from_answers_in_this_session(self):
        at = self._oversikt()
        self._klikk(at, "bs_apne_modul_mesking_btn")
        self._start_sporsmalsrunde(at, "mesking")
        self._fullfor_alle_sporsmal(at, 1, _korrekt_svar_ider(_visning("mesking", "foundation")), "mesking")
        self._klikk(at, "bs_oppsummering_tilbake_mesking_btn")
        self.assertEqual(self._status_linjer(at)[3], course_stage.STATUS_WORKED_THROUGH)
        self.assertEqual(self._telling(at), [_t("bryggeskole.trinn.fremdrift", n=1, totalt=9)])
        # Session-local button text stays.
        self.assertEqual(self._kort(at)[3].label, _t("bryggeskole.modul.se_resultat"))

    def test_special_cards_get_no_fake_status(self):
        at = self._oversikt()
        captions = [c.value for c in at.caption]
        self.assertEqual(len(self._status_linjer(at)), 9)
        self.assertEqual(captions.count(_t("bryggeskole.trinn.kort.horer_til_trinn2")), 2)
        self._velg_trinn(at, "kompetent")
        self.assertEqual(len(self._status_linjer(at)), 9)
        self.assertEqual([c.value for c in at.caption].count(_t("bryggeskole.trinn.kort.bygger_pa_foundation")), 2)
        # Each special line is followed directly by the button, never a status.
        for modul_id in _KUN_FOUNDATION:
            idx = _KANONISK.index(modul_id)
            self.assertEqual(self._kort(at)[idx].label, _t("bryggeskole.trinn.kort.repeter"))
        # Status lines map to the 9 Kompetent modules only.
        kart = _stage_map()
        self.assertEqual(len([m for m in _KANONISK if course_stage.module_has_stage(kart, m, "kompetent")]), 9)

    def test_old_session_badges_are_replaced(self):
        _seed([("mesking", "foundation")])  # «Øvd på tidligere» history for Mesking
        at = self._oversikt()
        self._klikk(at, "bs_apne_modul_gjaring_btn")
        self._tilbake(at, "gjaring")
        for sprak_at in (at,):
            tekst = [c.value for c in sprak_at.caption]
            for nokkel in _GAMLE_MERKER:
                self.assertNotIn(_t(nokkel), tekst)
        self.assertEqual(self._kort(at)[6].label, _t("bryggeskole.modul.fortsett"))
        self.assertEqual(self._status_linjer(at)[3], course_stage.STATUS_WORKED_THROUGH)
        self.assertEqual(self._status_linjer(at)[6], course_stage.STATUS_NOT_STARTED)


class TestGuidanceAndRecommendationUseTheHelpers(_S4Test):
    def test_recommendation_follows_module_stage_status(self):
        _seed([("raavarer", "foundation")])
        with mock.patch.object(panel._course_stage, "module_stage_status",
                               wraps=course_stage.module_stage_status) as spy:
            at = self._oversikt()
            self.assertTrue(any(c.args[2] == "foundation" for c in spy.call_args_list))
        anbefalt = [i.value for i in at.info if _t(panel._MODULER["rengjoring"]["tittel_nokkel"]) in i.value]
        self.assertEqual(len(anbefalt), 1)
        # The S3/S4 overview helpers carry no second status rule of their own.
        for funksjon in (panel._anbefalt_modul_i_trinn, panel._render_trinnkort,
                         panel._render_trinnfremdrift, panel._render_trinnveiledning, panel._standard_trinn):
            kilde = inspect.getsource(funksjon)
            for ord_ in ("last_correct", "attempts", "answered_questions["):
                self.assertNotIn(ord_, kilde, funksjon.__name__)

    def test_count_and_default_use_stage_progress(self):
        with mock.patch.object(panel._course_stage, "stage_progress",
                               wraps=course_stage.stage_progress) as spy:
            self._oversikt()
            self.assertTrue(spy.called)
        kilde = inspect.getsource(panel._render_trinnfremdrift)
        kode = kilde.split('"""')[-1]  # the body after the docstring
        self.assertNotRegex(kode, r"\b9\b")
        self.assertIn("stage_progress", kode)

    def test_auto_default_and_explicit_choice(self):
        _seed(_alle_foundation())
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                self.assertEqual(self._lens(at).value, "kompetent")
                self.assertIs(at.session_state[_EKSPLISITT], False)
                self.assertEqual([s.value for s in at.success], [_t("bryggeskole.trinn.trinn2_anbefalt", sprak)])
                self.assertEqual(self._telling(at, sprak), [_t("bryggeskole.trinn.fremdrift", sprak, n=0, totalt=9)])
                self._velg_trinn(at, "foundation")
                self.assertEqual([s.value for s in at.success], [_t("bryggeskole.trinn.klar_for_trinn2", sprak)])
                self.assertEqual(self._telling(at, sprak), [_t("bryggeskole.trinn.fremdrift", sprak, n=9, totalt=9)])
                self.assertEqual(self._status_linjer(at, sprak), [course_stage.STATUS_WORKED_THROUGH] * 9)
                self._bytt_miljo(at, "bs_velg_bryggeri_btn")
                self.assertEqual(self._lens(at).value, "foundation")

    def test_no_percentage_score_or_completion_wording(self):
        _seed([("raavarer", "foundation"), ("mesking", "kompetent")])
        for sprak in ("no", "en"):
            for trinn in course_stage.STAGES:
                with self.subTest(sprak=sprak, trinn=trinn):
                    at = self._oversikt(sprak=sprak if sprak != "no" else None)
                    if trinn == "kompetent":
                        self._velg_trinn(at, trinn)
                    tekst = " ".join(_alle_synlige_tekster(at)).lower()
                    for ord_ in _FORBUDTE_ORD + ("score", "poeng", "grade", "karakter"):
                        self.assertNotIn(ord_, tekst)
                    self.assertFalse(any(b.disabled for b in at.button))

    def test_exact_strings(self):
        for nokkel, no, en in (
            ("bryggeskole.trinn.status.ikke_startet", "Ikke startet", "Not started"),
            ("bryggeskole.trinn.status.pabegynt", "Påbegynt", "In progress"),
            ("bryggeskole.trinn.status.gjennomgatt", "Gjennomgått", "Worked through"),
        ):
            self.assertEqual((_t(nokkel, "no"), _t(nokkel, "en")), (no, en))
        self.assertEqual(_t("bryggeskole.trinn.fremdrift", "no", n=4, totalt=9), "4 av 9 moduler gjennomgått")
        self.assertEqual(_t("bryggeskole.trinn.fremdrift", "en", n=4, totalt=9), "4 of 9 modules worked through")


class TestStorageAndFallback(_S4Test):
    def test_overview_never_writes_mastery(self):
        _seed([("mesking", "foundation"), ("gjaring", "kompetent")])
        foer = os.stat(default_state_path()).st_mtime_ns
        dokument = read_mastery_state()
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(os.stat(default_state_path()).st_mtime_ns, foer)
        self.assertEqual(read_mastery_state(), dokument)

    def test_invalid_map_keeps_todays_overview(self):
        _seed([("mesking", "foundation")])
        with mock.patch.object(panel._course_stage, "load_stage_map",
                               side_effect=course_stage.StageMapError(["broken"])), \
                self.assertLogs(panel._LOGGER, "WARNING"):
            at = self._oversikt()
            self.assertEqual(self._status_linjer(at), [])
            self.assertEqual(self._telling(at), [])
            captions = [c.value for c in at.caption]
            self.assertIn(_t("bryggeskole.status.ovd_tidligere"), captions)  # legacy badge in the fallback
            self.assertEqual(captions.count(_t("bryggeskole.prosess.aktiv_badge")), 11)


if __name__ == "__main__":
    unittest.main()
