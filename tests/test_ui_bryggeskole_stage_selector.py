"""
AppTest coverage for stage UI S3 -- the stage selector and stage-aware cards
over the single 11-card grid (docs/development/v22_course_stage_ui_contract.md
§3, §4, §7.3, §8, §9, §12, §15; offline, no GitHub issue yet).

What is checked:
- the compact `bs_trinn` selector (Foundation default, NO/EN, both legacy
  environments) and the Chief refinement: an explicit learner choice -- the
  selector's own change, or a card action that switches the lens -- is never
  overridden in the session, while a widget value Streamlit merely
  materialised never counts as explicit;
- the 11 canonical cards in both lenses, with stage lines and actions for
  both-stage, Foundation-only and Kompetent-only modules (never disabled);
- the S2 bridge: a card opens the S2 stage lesson (Foundation keys, `_k`
  keys, two-axis breadcrumb, stage-local retry);
- stage-aware «Anbefalt neste», the Foundation-gap tip and «Klar for Trinn
  2?», driven read-only by the stored answered_questions -- no locks, no S4
  counts, no completion wording;
- the invalid-map fallback to today's single-flow overview.

Learner history is seeded only through the existing mastery API
(apply_answer + write_mastery_state) into an isolated
KVERNHAUG_BRYGGESKOLE_STATE_DIR (via _MedIsolertTilstand).

Run with:
    python -m unittest tests.test_ui_bryggeskole_stage_selector
"""
import io
import os
import re
import unittest
from unittest import mock

from bryggeskole import course_stage
from bryggeskole.mastery import apply_answer
from bryggeskole.mastery_store import default_state_path, read_mastery_state, write_mastery_state
from modules.i18n import t as t_ren
from tests.test_ui_bryggeskole_panel import (
    _MedIsolertTilstand,
    _alle_synlige_tekster,
    _feil_svar_ider,
    _knapp,
    _korrekt_svar_ider,
)
from ui import bryggeskole_panel as panel

_LENS = "bs_trinn"
_EKSPLISITT = "bs_trinn_valgt_eksplisitt"
_KANONISK = list(panel._MODUL_REKKEFOLGE)
_KORT_KEYS = [f"bs_apne_modul_{m}_btn" for m in _KANONISK]
_KUN_FOUNDATION = ("rengjoring", "metodevalg")
_KUN_KOMPETENT = ("oppskrift", "smak")
_BEGGE = tuple(m for m in _KANONISK if m not in _KUN_FOUNDATION + _KUN_KOMPETENT)
_PANEL_SOURCE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "bryggeskole_panel.py")
_NOW = "2026-01-01T00:00:00+00:00"
# Learner-facing wording the stage UI must never use (contract §7.3, §7.4).
_FORBUDTE_ORD = ("complete", "certified", "passed", "mastered", "sertifisert", "bestått", "mestret",
                 "ferdig med trinn", "trinn 1 fullført", "%")


def _t(key, sprak, **kw):
    return t_ren(key, sprak, **kw)


def _stage_map():
    return course_stage.load_stage_map()


def _pilot(modul_id):
    return panel._MODULER[modul_id]["pilot"].read_pilot_file()


def _visning(modul_id, trinn):
    pilot = _pilot(modul_id)
    return dict(pilot, **course_stage.items_for_stage(_stage_map(), modul_id, pilot, trinn))


def _seed(trinn_moduler, korrekt=True, unntak=()):
    """Writes real history through apply_answer: every question of the
    given (module, stage) pairs answered once, except question ids in
    `unntak`. Returns the stored document."""
    kart = _stage_map()
    dokument = read_mastery_state()
    for modul_id, trinn in trinn_moduler:
        pilot = _pilot(modul_id)
        ids = set(course_stage._module_entry(kart, modul_id)[trinn]["questions"])
        for sporsmal in pilot["questions"]:
            if sporsmal["id"] in ids and sporsmal["id"] not in unntak:
                dokument = apply_answer(dokument, sporsmal, korrekt, now=_NOW)
    write_mastery_state(dokument)
    return dokument


def _alle_foundation():
    return [(m, "foundation") for m in _KANONISK
            if course_stage.module_has_stage(_stage_map(), m, "foundation")]


class _S3Test(_MedIsolertTilstand):
    _ENKELTFLYT = False

    def _oversikt(self, miljo_knapp="bs_velg_hjemmebrygger_btn", sprak=None):
        at = self._ny_apptest()
        if sprak:
            at.session_state["sprak"] = sprak
            at.run()
        self._velg_miljo(at, miljo_knapp)
        return at

    def _lens(self, at):
        radios = [r for r in at.radio if r.key == _LENS]
        self.assertEqual(len(radios), 1, [r.key for r in at.radio])
        return radios[0]

    def _velg_trinn(self, at, trinn):
        self._lens(at).set_value(trinn).run()
        self.assertEqual(len(at.exception), 0, at.exception)

    def _kort(self, at):
        return [b for b in at.button if b.key in _KORT_KEYS]

    def _klikk(self, at, key):
        _knapp(at, key).click().run()
        self.assertEqual(len(at.exception), 0, at.exception)

    def _sti(self, at):
        return [c.value for c in at.caption if " ▸ " in c.value]

    def _tilbake(self, at, base):
        self._klikk(at, f"bs_tilbake_{base}_btn")

    def _bytt_miljo(self, at, ny_miljo_knapp):
        self._klikk(at, "bs_bytt_miljo_btn")
        self._klikk(at, ny_miljo_knapp)


class TestSelector(_S3Test):
    def test_default_is_foundation_and_not_explicit(self):
        for knapp in ("bs_velg_hjemmebrygger_btn", "bs_velg_bryggeri_btn"):
            with self.subTest(miljo=knapp):
                at = self._oversikt(knapp)
                self.assertEqual(self._lens(at).value, "foundation")
                self.assertIs(at.session_state[_EKSPLISITT], False)

    def test_labels_no_and_en(self):
        for sprak, foundation, kompetent, label in (
            ("no", "Trinn 1 · Foundation", "Trinn 2 · Kompetent hjemmebrygger", "Trinn"),
            ("en", "Stage 1 · Foundation", "Stage 2 · Competent homebrewer", "Stage"),
        ):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                radio = self._lens(at)
                self.assertEqual(radio.options, [foundation, kompetent])
                self.assertEqual(radio.label, label)
                self.assertIn(_t("bryggeskole.trinn.foundation_forklaring", sprak), [c.value for c in at.caption])
                for verdi in course_stage.STAGES:
                    self.assertNotIn(verdi, radio.options)

    def test_selector_values_are_stage_values_never_environment_values(self):
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        self.assertEqual(at.session_state[_LENS], "kompetent")
        self.assertNotIn(at.session_state[_LENS], (panel._ENV_HJEMMEBRYGGER, panel._ENV_BRYGGERI))
        self.assertEqual(at.session_state["bs_miljo"], panel._ENV_HJEMMEBRYGGER)

    def test_choosing_kompetent_is_explicit(self):
        for knapp in ("bs_velg_hjemmebrygger_btn", "bs_velg_bryggeri_btn"):
            with self.subTest(miljo=knapp):
                at = self._oversikt(knapp)
                self._velg_trinn(at, "kompetent")
                self.assertEqual(self._lens(at).value, "kompetent")
                self.assertIs(at.session_state[_EKSPLISITT], True)
                self.assertIn(_t("bryggeskole.trinn.kompetent_forklaring", "no"), [c.value for c in at.caption])

    def test_materialised_default_never_counts_as_explicit(self):
        at = self._oversikt()
        for _ in range(3):
            at.run()
        self._klikk(at, "bs_apne_modul_mesking_btn")
        self._tilbake(at, "mesking")
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        at.session_state["sprak"] = "en"
        at.run()
        self.assertEqual(self._lens(at).value, "foundation")
        self.assertIs(at.session_state[_EKSPLISITT], False)

    def test_environment_switch_keeps_the_stage(self):
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(self._lens(at).value, "kompetent")
        self._bytt_miljo(at, "bs_velg_hjemmebrygger_btn")
        self.assertEqual(self._lens(at).value, "kompetent")

    def test_language_switch_keeps_the_stage(self):
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        at.session_state["sprak"] = "en"
        at.run()
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertEqual(self._lens(at).options[1], "Stage 2 · Competent homebrewer")

    def test_stage_survives_an_open_module(self):
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        self._klikk(at, "bs_apne_modul_mesking_btn")
        self.assertEqual([r for r in at.radio if r.key == _LENS], [])
        self._tilbake(at, "mesking_k")
        self.assertEqual(self._lens(at).value, "kompetent")


class TestExplicitChoiceAgainstTheDefault(_S3Test):
    def test_foundation_worked_through_makes_kompetent_the_default(self):
        _seed(_alle_foundation())
        at = self._oversikt()
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertIs(at.session_state[_EKSPLISITT], False)
        # Already looking at Trinn 2: no «Klar for Trinn 2?» question.
        self.assertEqual([s.value for s in at.success], [_t("bryggeskole.trinn.trinn2_anbefalt", "no")])

    def test_explicit_foundation_is_never_overridden(self):
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        self._velg_trinn(at, "foundation")
        self.assertIs(at.session_state[_EKSPLISITT], True)
        _seed(_alle_foundation())  # Foundation becomes worked through mid-session.
        at.run()
        self._klikk(at, "bs_apne_modul_mesking_btn")
        self._tilbake(at, "mesking")
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(self._lens(at).value, "foundation")
        # The guidance still invites; it never moves the lens.
        self.assertIn(_t("bryggeskole.trinn.klar_for_trinn2", "no"), [s.value for s in at.success])

    def test_explicit_foundation_after_the_kompetent_default(self):
        _seed(_alle_foundation())
        at = self._oversikt()
        self.assertEqual(self._lens(at).value, "kompetent")
        self._velg_trinn(at, "foundation")
        for _ in range(2):
            at.run()
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(self._lens(at).value, "foundation")

    def test_explicit_kompetent_is_kept_when_history_changes(self):
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        _seed([("mesking", "foundation")], korrekt=False)
        at.session_state["sprak"] = "en"
        at.run()
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(self._lens(at).value, "kompetent")

    def test_kompetent_only_card_action_is_explicit_and_kept(self):
        at = self._oversikt()
        self.assertIs(at.session_state[_EKSPLISITT], False)
        self._klikk(at, "bs_apne_modul_oppskrift_btn")
        self.assertEqual(at.session_state[_LENS], "kompetent")
        self.assertIs(at.session_state[_EKSPLISITT], True)
        self._tilbake(at, "oppskrift_k")
        # Foundation is not worked through, so the default would be
        # Foundation -- the card's explicit switch wins for the session.
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(self._lens(at).value, "kompetent")


class TestCards(_S3Test):
    def test_eleven_cards_in_canonical_order_everywhere(self):
        for sprak in ("no", "en"):
            for knapp in ("bs_velg_hjemmebrygger_btn", "bs_velg_bryggeri_btn"):
                for trinn in course_stage.STAGES:
                    with self.subTest(sprak=sprak, miljo=knapp, trinn=trinn):
                        at = self._oversikt(knapp, sprak if sprak != "no" else None)
                        if trinn == "kompetent":
                            self._velg_trinn(at, trinn)
                        kort = self._kort(at)
                        self.assertEqual([b.key for b in kort], _KORT_KEYS)
                        self.assertEqual(_KORT_KEYS.index("bs_apne_modul_mesking_btn"), 3)
                        self.assertEqual(_KORT_KEYS.index("bs_apne_modul_pakking_btn"), 7)
                        self.assertFalse(any(b.disabled for b in kort))
                        tekster = " ".join(_alle_synlige_tekster(at))
                        self.assertNotIn(_t("bryggeskole.prosess.kommer_badge", sprak), tekster)

    def test_stage_lines_per_module_kind_no_and_en(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                captions = [c.value for c in at.caption]
                self.assertEqual(captions.count(_t("bryggeskole.trinn.kort.innhold", sprak)), 9)
                self.assertEqual(captions.count(_t("bryggeskole.trinn.kort.horer_til_trinn2", sprak)), 2)
                self.assertNotIn(_t("bryggeskole.prosess.aktiv_badge", sprak), captions)
                self.assertEqual(
                    [b.label for b in self._kort(at)][-2:], [_t("bryggeskole.trinn.kort.se_trinn2", sprak)] * 2)
                self._velg_trinn(at, "kompetent")
                captions = [c.value for c in at.caption]
                self.assertEqual(captions.count(_t("bryggeskole.trinn.kort.innhold", sprak)), 9)
                self.assertEqual(captions.count(_t("bryggeskole.trinn.kort.bygger_pa_foundation", sprak)), 2)
                labels = [b.label for b in self._kort(at)]
                self.assertEqual(labels[1:3], [_t("bryggeskole.trinn.kort.repeter", sprak)] * 2)

    def test_exact_card_strings(self):
        self.assertEqual(_t("bryggeskole.trinn.kort.bygger_pa_foundation", "no"),
                         "Bygger på Foundation – ingen egen Trinn 2-del")
        self.assertEqual(_t("bryggeskole.trinn.kort.bygger_pa_foundation", "en"),
                         "Builds on Foundation – no separate Stage 2 section")
        self.assertEqual(_t("bryggeskole.trinn.kort.repeter", "no"), "Repeter")
        self.assertEqual(_t("bryggeskole.trinn.kort.repeter", "en"), "Review")
        self.assertEqual(_t("bryggeskole.trinn.kort.horer_til_trinn2", "no"), "Hører til Trinn 2")
        self.assertEqual(_t("bryggeskole.trinn.kort.horer_til_trinn2", "en"), "Belongs to Stage 2")
        self.assertEqual(_t("bryggeskole.trinn.kort.se_trinn2", "no"), "Se Trinn 2-innholdet")
        self.assertEqual(_t("bryggeskole.trinn.kort.se_trinn2", "en"), "View Stage 2 content")

    def test_card_titles_stay_tied_to_the_environment(self):
        at = self._oversikt("bs_velg_bryggeri_btn")
        self._velg_trinn(at, "kompetent")
        titler = [m.value for m in at.markdown if m.value.startswith("**")]
        self.assertEqual(titler, [f"**{s['no']}**" for s in panel._PROSESS_STADIER[panel._ENV_BRYGGERI]])

    def test_both_stage_modules_open_at_the_selected_stage(self):
        for trinn in course_stage.STAGES:
            for modul_id in _BEGGE:
                with self.subTest(trinn=trinn, modul=modul_id):
                    at = self._oversikt()
                    if trinn == "kompetent":
                        self._velg_trinn(at, trinn)
                    self._klikk(at, f"bs_apne_modul_{modul_id}_btn")
                    self.assertEqual(at.session_state["bs_aktiv_trinn"], trinn)
                    self.assertIn(f"{modul_id}@{trinn}", at.session_state["bs_modul_sesjon"])
                    self.assertEqual(len(at.session_state["bs_modul_sesjon"]), 1)

    def test_foundation_only_card_under_kompetent_reviews_foundation(self):
        for sprak in ("no", "en"):
            for modul_id in _KUN_FOUNDATION:
                with self.subTest(sprak=sprak, modul=modul_id):
                    at = self._oversikt(sprak=sprak if sprak != "no" else None)
                    self._velg_trinn(at, "kompetent")
                    self._klikk(at, f"bs_apne_modul_{modul_id}_btn")
                    self.assertEqual(at.session_state["bs_aktiv_trinn"], "foundation")
                    self.assertEqual(at.session_state[_LENS], "kompetent")
                    sti = self._sti(at)[0]
                    self.assertIn(_t("bryggeskole.trinn.sti.foundation", sprak), sti)
                    # Foundation content with today's keys.
                    self.assertTrue(any(b.key == f"bs_tilbake_{modul_id}_btn" for b in at.button))
                    self.assertEqual(
                        len(_visning(modul_id, "foundation")["chunks"]),
                        int(re.search(r"(\d+)\D*$", [c.value for c in at.caption
                                                      if c.value.startswith(("Læringsbolk", "Learning block"))][0]).group(1)))
                    self._tilbake(at, modul_id)
                    # The global lens is still Kompetent; other cards untouched.
                    self.assertEqual(self._lens(at).value, "kompetent")
                    self.assertEqual(_knapp(at, "bs_apne_modul_mesking_btn").label,
                                     _t("bryggeskole.modul.start", sprak))

    def test_kompetent_only_card_under_foundation_switches_the_lens(self):
        for sprak in ("no", "en"):
            for knapp in ("bs_velg_hjemmebrygger_btn", "bs_velg_bryggeri_btn"):
                for modul_id in _KUN_KOMPETENT:
                    with self.subTest(sprak=sprak, miljo=knapp, modul=modul_id):
                        at = self._oversikt(knapp, sprak if sprak != "no" else None)
                        self._klikk(at, f"bs_apne_modul_{modul_id}_btn")
                        self.assertEqual(at.session_state[_LENS], "kompetent")
                        self.assertIs(at.session_state[_EKSPLISITT], True)
                        self.assertEqual(at.session_state["bs_aktiv_trinn"], "kompetent")
                        self.assertIn(_t("bryggeskole.trinn.sti.kompetent", sprak), self._sti(at)[0])
                        self.assertTrue(any(b.key == f"bs_bolk_neste_{modul_id}_k_btn" for b in at.button))
                        self._tilbake(at, f"{modul_id}_k")
                        self.assertEqual(self._lens(at).value, "kompetent")

    def test_card_badges_follow_the_selected_stage_session(self):
        at = self._oversikt()
        self._klikk(at, "bs_apne_modul_mesking_btn")
        self._tilbake(at, "mesking")
        fortsett = _t("bryggeskole.modul.fortsett", "no")
        self.assertEqual(_knapp(at, "bs_apne_modul_mesking_btn").label, fortsett)
        self._velg_trinn(at, "kompetent")
        self.assertEqual(_knapp(at, "bs_apne_modul_mesking_btn").label, _t("bryggeskole.modul.start", "no"))
        self.assertNotIn(_t("bryggeskole.status.pabegynt", "no"), [c.value for c in at.caption])


class TestS2Bridge(_S3Test):
    def _bolk_teller(self, at):
        return [c.value for c in at.caption if c.value.startswith(("Læringsbolk", "Learning block"))]

    def test_foundation_default_opens_mesking_foundation_with_todays_keys(self):
        for knapp in ("bs_velg_hjemmebrygger_btn", "bs_velg_bryggeri_btn"):
            with self.subTest(miljo=knapp):
                at = self._oversikt(knapp)
                self._klikk(at, "bs_apne_modul_mesking_btn")
                self.assertEqual(self._bolk_teller(at), ["Læringsbolk 1 av 1"])
                self._klikk(at, "bs_start_sporsmal_mesking_btn")
                self.assertIsNone(at.radio(key="bs_valg_mesking_r1_q0").value)
                self.assertTrue(_knapp(at, "bs_svar_btn_mesking_r1_q0").disabled)
                self.assertEqual(len([r for r in at.radio if r.key.startswith("bs_valg_mesking_k")]), 0)

    def test_selector_kompetent_opens_mesking_kompetent_with_k_keys(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                self._velg_trinn(at, "kompetent")
                self._klikk(at, "bs_apne_modul_mesking_btn")
                self.assertEqual(self._bolk_teller(at),
                                 ["Læringsbolk 1 av 5" if sprak == "no" else "Learning block 1 of 5"])
                self._aktiv_modul = "mesking_k"
                self._start_sporsmalsrunde(at)
                self.assertIsNone(at.radio(key="bs_valg_mesking_k_r1_q0").value)
                self.assertTrue(_knapp(at, "bs_svar_btn_mesking_k_r1_q0").disabled)

    def test_breadcrumb_has_both_axes(self):
        tilfeller = (
            ("no", "bs_velg_hjemmebrygger_btn", "kompetent",
             "🎓 Bryggeskole ▸ 🏠 Hjemmebrygger ▸ Trinn 2 · Kompetent ▸ Mesking"),
            ("no", "bs_velg_bryggeri_btn", "foundation",
             "🎓 Bryggeskole ▸ 🏭 Bryggeri ▸ Trinn 1 · Foundation ▸ Mesking"),
            ("en", "bs_velg_hjemmebrygger_btn", "kompetent",
             "🎓 Brew School ▸ 🏠 Homebrewer ▸ Stage 2 · Competent homebrewer ▸ Mashing"),
            ("en", "bs_velg_bryggeri_btn", "foundation",
             "🎓 Brew School ▸ 🏭 Brewery ▸ Stage 1 · Foundation ▸ Mashing"),
        )
        for sprak, knapp, trinn, forventet in tilfeller:
            with self.subTest(sprak=sprak, miljo=knapp, trinn=trinn):
                at = self._oversikt(knapp, sprak if sprak != "no" else None)
                if trinn == "kompetent":
                    self._velg_trinn(at, trinn)
                self._klikk(at, "bs_apne_modul_mesking_btn")
                self.assertEqual(self._sti(at), [forventet])

    def test_questions_only_kompetent_module(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                self._velg_trinn(at, "kompetent")
                self._klikk(at, "bs_apne_modul_kjoling_btn")
                self.assertIn(_t("bryggeskole.trinn.kun_sporsmal", sprak), [i.value for i in at.info])
                self.assertEqual(self._bolk_teller(at), [])
                _knapp(at, "bs_trinn_repeter_kjoling_k_btn")
                self._klikk(at, "bs_start_sporsmal_kjoling_k_btn")
                self.assertIsNone(at.radio(key="bs_valg_kjoling_k_r1_q0").value)
                self.assertTrue(_knapp(at, "bs_svar_btn_kjoling_k_r1_q0").disabled)

    def test_retry_is_stage_local(self):
        at = self._oversikt()
        self._klikk(at, "bs_apne_modul_pakking_btn")
        self._tilbake(at, "pakking")
        self._velg_trinn(at, "kompetent")
        self._klikk(at, "bs_apne_modul_pakking_btn")
        self._aktiv_modul = "pakking_k"
        self._start_sporsmalsrunde(at)
        visning = _visning("pakking", "kompetent")
        self._fullfor_alle_sporsmal(at, 1, _feil_svar_ider(visning))
        self._klikk(at, "bs_prov_igjen_pakking_k_btn")
        self.assertIsNone(at.radio(key="bs_valg_pakking_k_r2_q0").value)
        self.assertTrue(_knapp(at, "bs_svar_btn_pakking_k_r2_q0").disabled)
        sesjoner = at.session_state["bs_modul_sesjon"]
        self.assertEqual(sesjoner["pakking@kompetent"]["runde"], 2)
        self.assertEqual(sesjoner["pakking@foundation"]["runde"], 0)
        self.assertEqual(sesjoner["pakking@foundation"]["fase"], "leksjon")


class TestEveryModuleAndStageFromTheCards(_S3Test):
    """The stage-aware counterpart of the single-flow panel suite's full
    flows: every (module, stage) pair with content, opened from its card
    under that lens, walked lesson block by block, every question answered
    correctly (no preselection, disabled «Sjekk svar»), ending in the
    summary with only that stage's concepts."""

    def test_full_walk(self):
        kart = _stage_map()
        par = [(m, tr) for tr in course_stage.STAGES for m in _KANONISK if course_stage.module_has_stage(kart, m, tr)]
        self.assertEqual(len(par), 18)
        for modul_id, trinn in par:
            with self.subTest(modul=modul_id, trinn=trinn):
                if os.path.exists(default_state_path()):
                    os.remove(default_state_path())  # each pair starts as a fresh learner
                at = self._oversikt()
                if trinn == "kompetent":
                    self._velg_trinn(at, trinn)
                self._klikk(at, f"bs_apne_modul_{modul_id}_btn")
                base = modul_id + ("_k" if trinn == "kompetent" else "")
                self._aktiv_modul = base
                visning = _visning(modul_id, trinn)
                teller = [c.value for c in at.caption if c.value.startswith("Læringsbolk")]
                self.assertEqual(teller, [f"Læringsbolk 1 av {len(visning['chunks'])}"] if visning["chunks"] else [])
                self._start_sporsmalsrunde(at)
                for idx in range(len(visning["questions"])):
                    self.assertIsNone(at.radio(key=f"bs_valg_{base}_r1_q{idx}").value)
                    self.assertTrue(_knapp(at, f"bs_svar_btn_{base}_r1_q{idx}").disabled)
                    self._besvar_sporsmal(at, idx, 1, _korrekt_svar_ider(visning)[idx])
                    self._fortsett(at, idx, 1)
                _knapp(at, f"bs_prov_igjen_{base}_btn")
                tekst = " ".join(_alle_synlige_tekster(at))
                stage_konsepter = {k for q in visning["questions"] for k in q["concepts"]}
                for k in {k for q in _pilot(modul_id)["questions"] for k in q["concepts"]} - stage_konsepter:
                    self.assertNotIn(panel._konsept_label(k, "no"), tekst, k)
                self.assertEqual(set(read_mastery_state()["answered_questions"]),
                                 {q["id"] for q in visning["questions"]})


class TestGuidance(_S3Test):
    def _anbefalt(self, at, sprak="no"):
        """The recommended module names (AppTest reports the 💡 as the icon)."""
        prefiks = _t("bryggeskole.anbefalt_neste", sprak, modul="").replace("💡", "").strip()
        return [i.value.split(prefiks, 1)[1].strip() for i in at.info if prefiks in i.value]

    def _modul(self, modul_id, sprak="no"):
        return _t(panel._MODULER[modul_id]["tittel_nokkel"], sprak)

    def test_fresh_learner(self):
        at = self._oversikt()
        self.assertEqual(self._anbefalt(at), [self._modul("raavarer")])
        self.assertEqual(len(at.success), 0)
        self.assertNotIn(_t("bryggeskole.trinn.tips_foundation", "no"), [c.value for c in at.caption])
        self._velg_trinn(at, "kompetent")
        self.assertIn(_t("bryggeskole.trinn.tips_foundation", "no"), [c.value for c in at.caption])
        self.assertEqual(len(at.success), 0)

    def test_recommendation_is_stage_aware(self):
        _seed([("raavarer", "kompetent")])
        at = self._oversikt()
        self.assertEqual(self._anbefalt(at), [self._modul("raavarer")])
        self._velg_trinn(at, "kompetent")
        # Rengjøring/Forberedelse have no Kompetent part, so the next is Mesking.
        self.assertEqual(self._anbefalt(at), [self._modul("mesking")])

    def test_foundation_lens_never_recommends_kompetent_only_modules(self):
        siste_foundation = [m for m, _ in _alle_foundation()][-1]
        unntak = set(course_stage._module_entry(_stage_map(), siste_foundation)["foundation"]["questions"])
        _seed(_alle_foundation(), unntak=unntak)
        at = self._oversikt()
        self.assertEqual(self._anbefalt(at),
                         [self._modul(siste_foundation)])
        self.assertEqual(len(at.success), 0)

    def test_wrong_latest_answer_is_not_worked_through(self):
        _seed(_alle_foundation(), korrekt=False)
        at = self._oversikt()
        self.assertEqual(self._lens(at).value, "foundation")
        self.assertEqual(len(at.success), 0)

    def test_ready_for_stage_2_only_when_foundation_is_worked_through(self):
        _seed(_alle_foundation())
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                # Auto-default Kompetent: the "recommended next step" line.
                self.assertEqual(self._lens(at).value, "kompetent")
                self.assertEqual([s.value for s in at.success], [_t("bryggeskole.trinn.trinn2_anbefalt", sprak)])
                self.assertNotIn(_t("bryggeskole.trinn.tips_foundation", sprak), [c.value for c in at.caption])
                # Explicit Foundation: «Klar for Trinn 2?» -- and the lens stays.
                self._velg_trinn(at, "foundation")
                self.assertEqual([s.value for s in at.success], [_t("bryggeskole.trinn.klar_for_trinn2", sprak)])
                at.run()
                self.assertEqual(self._lens(at).value, "foundation")
                # Explicit Kompetent: already there, no prompt.
                self._velg_trinn(at, "kompetent")
                self.assertEqual(len(at.success), 0)

    def test_exact_guidance_strings(self):
        self.assertEqual(_t("bryggeskole.trinn.klar_for_trinn2", "no"), "Du har gått gjennom Trinn 1. Klar for Trinn 2?")
        self.assertEqual(_t("bryggeskole.trinn.klar_for_trinn2", "en"), "You've worked through Stage 1. Ready for Stage 2?")
        self.assertEqual(_t("bryggeskole.trinn.trinn2_anbefalt", "no"),
                         "Du har gått gjennom Trinn 1. Trinn 2 vises som anbefalt neste steg.")
        self.assertEqual(_t("bryggeskole.trinn.trinn2_anbefalt", "en"),
                         "You've worked through Stage 1. Stage 2 is now shown as the recommended next step.")
        self.assertEqual(_t("bryggeskole.trinn.tips_foundation", "no"),
                         "Tips: Du har fortsatt noen Foundation-deler du kan gå tilbake til.")
        self.assertEqual(_t("bryggeskole.trinn.tips_foundation", "en"),
                         "Tip: You still have some Foundation sections you can revisit.")

    def test_no_locks_no_completion_wording(self):
        _seed(_alle_foundation(), unntak={"Q-MASH-001"})
        for sprak in ("no", "en"):
            for trinn in course_stage.STAGES:
                with self.subTest(sprak=sprak, trinn=trinn):
                    at = self._oversikt(sprak=sprak if sprak != "no" else None)
                    if trinn == "kompetent":
                        self._velg_trinn(at, trinn)
                    self.assertFalse(any(b.disabled for b in at.button))
                    tekst = " ".join(_alle_synlige_tekster(at)).lower()
                    for ord_ in _FORBUDTE_ORD:
                        self.assertNotIn(ord_, tekst)
                    # Since S4 the one count on the page is the stage's module
                    # count line (tests/test_ui_bryggeskole_stage_progress.py).
                    tellinger = re.findall(r"\d+\s+(?:av|of)\s+\d+", tekst)
                    self.assertEqual(len(tellinger), 1, tekst)


class TestMasteryIsReadOnly(_S3Test):
    def test_status_helper_follows_answered_questions(self):
        kart = _stage_map()
        mesk_k = course_stage._module_entry(kart, "mesking")["kompetent"]["questions"]
        self.assertEqual(course_stage.module_stage_status(kart, "mesking", "kompetent", {}),
                         course_stage.STATUS_NOT_STARTED)
        delvis = {mesk_k[0]: {"attempts": 1, "last_correct": True}}
        self.assertEqual(course_stage.module_stage_status(kart, "mesking", "kompetent", delvis),
                         course_stage.STATUS_IN_PROGRESS)
        alle = {q: {"attempts": 2, "last_correct": True} for q in mesk_k}
        self.assertEqual(course_stage.module_stage_status(kart, "mesking", "kompetent", alle),
                         course_stage.STATUS_WORKED_THROUGH)
        alle[mesk_k[-1]] = {"attempts": 3, "last_correct": False}
        self.assertEqual(course_stage.module_stage_status(kart, "mesking", "kompetent", alle),
                         course_stage.STATUS_IN_PROGRESS)
        self.assertIsNone(course_stage.module_stage_status(kart, "oppskrift", "foundation", alle))
        self.assertFalse(course_stage.stage_worked_through(kart, "foundation", {}))

    def test_overview_never_writes_mastery(self):
        dokument = _seed(_alle_foundation())
        sti = default_state_path()
        for_ = os.stat(sti).st_mtime_ns
        at = self._oversikt()
        self._velg_trinn(at, "foundation")
        self._velg_trinn(at, "kompetent")
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertEqual(os.stat(sti).st_mtime_ns, for_)
        self.assertEqual(read_mastery_state(), dokument)

    def test_shared_concepts_no_stage_ids(self):
        at = self._oversikt()
        self._klikk(at, "bs_apne_modul_pakking_btn")
        self._start_sporsmalsrunde(at, "pakking")
        self._fullfor_alle_sporsmal(at, 1, _korrekt_svar_ider(_visning("pakking", "foundation")), "pakking")
        self._klikk(at, "bs_oppsummering_tilbake_pakking_btn")
        self._velg_trinn(at, "kompetent")
        self._klikk(at, "bs_apne_modul_pakking_btn")
        self._aktiv_modul = "pakking_k"
        self._start_sporsmalsrunde(at)
        self._fullfor_alle_sporsmal(at, 1, _korrekt_svar_ider(_visning("pakking", "kompetent")))
        tilstand = read_mastery_state()
        self.assertEqual(tilstand["concepts"]["package.priming"]["attempts"], 2)
        for nokkel in list(tilstand["concepts"]) + list(tilstand["answered_questions"]):
            self.assertNotIn("@", nokkel)
            self.assertNotIn("kompetent", nokkel)
            self.assertNotIn("foundation", nokkel)


class TestInvalidMapFallback(_S3Test):
    def _ugyldig(self):
        return mock.patch.object(panel._course_stage, "load_stage_map",
                                 side_effect=course_stage.StageMapError(["broken"]))

    def test_overview_falls_back_to_the_single_flow(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak), self._ugyldig(), self.assertLogs(panel._LOGGER, "WARNING") as logg:
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                self.assertEqual([r for r in at.radio if r.key == _LENS], [])
                self.assertEqual([b.key for b in self._kort(at)], _KORT_KEYS)
                captions = [c.value for c in at.caption]
                self.assertEqual(captions.count(_t("bryggeskole.prosess.aktiv_badge", sprak)), 11)
                for nokkel in ("bryggeskole.trinn.kort.innhold", "bryggeskole.trinn.kort.horer_til_trinn2",
                               "bryggeskole.trinn.tips_foundation"):
                    self.assertNotIn(_t(nokkel, sprak), captions)
                self._klikk(at, "bs_apne_modul_mesking_btn")
                self.assertEqual(self._sti(at)[0].count(" ▸ "), 2)
                self.assertIn("mesking", at.session_state["bs_modul_sesjon"])
                self.assertEqual(len(logg.records), 1)

    def test_missing_map_file_does_not_crash(self):
        with mock.patch.object(panel._course_stage, "load_stage_map", side_effect=FileNotFoundError("x")), \
                self.assertLogs(panel._LOGGER, "WARNING"):
            at = self._oversikt()
            self.assertEqual([r for r in at.radio if r.key == _LENS], [])
            self._klikk(at, "bs_apne_modul_oppskrift_btn")
            self.assertTrue(any(b.key == "bs_bolk_neste_oppskrift_btn" for b in at.button))


class TestStageLabelsAndSource(unittest.TestCase):
    def test_stage_label_never_uses_bare_hjemmebrygger(self):
        self.assertIn("Kompetent hjemmebrygger", t_ren("bryggeskole.trinn.kompetent", "no"))
        self.assertNotEqual(t_ren("bryggeskole.trinn.kompetent", "en"), t_ren("bryggeskole.miljo.hjemmebrygger", "en"))
        for sprak in ("no", "en"):
            miljo = t_ren("bryggeskole.miljo.hjemmebrygger", sprak)
            for verdi in course_stage.STAGES:
                self.assertNotEqual(t_ren(f"bryggeskole.trinn.{verdi}", sprak), miljo)

    def test_new_keys_exist_in_both_languages(self):
        for nokkel in ("velg", "velg_hjelp", "foundation", "kompetent", "foundation_forklaring",
                       "kompetent_forklaring", "kort.innhold", "kort.bygger_pa_foundation", "kort.repeter",
                       "kort.horer_til_trinn2", "kort.se_trinn2", "tips_foundation", "klar_for_trinn2", "trinn2_anbefalt"):
            full = f"bryggeskole.trinn.{nokkel}"
            self.assertNotEqual(t_ren(full, "no"), full)
            self.assertNotEqual(t_ren(full, "en"), full)
            self.assertNotEqual(t_ren(full, "no"), t_ren(full, "en"), full)
            self.assertLessEqual(len(t_ren(full, "no")), 140)

    def test_selector_labels_fit_the_contract_width(self):
        for sprak in ("no", "en"):
            for verdi in course_stage.STAGES:
                self.assertLessEqual(len(t_ren(f"bryggeskole.trinn.{verdi}", sprak)), 34)

    def test_one_authoritative_stage(self):
        with io.open(_PANEL_SOURCE, encoding="utf-8") as fh:
            kilde = fh.read()
        # The lens is written only by the selector default, its own widget, and
        # the two explicit Kompetent actions; never from the environment.
        self.assertEqual(len(re.findall(r"st\.session_state\[_TRINN_VALG_KEY\] = ", kilde)), 5)
        self.assertNotIn("_ENV_", "".join(re.findall(r"_TRINN_VALG_KEY\][^\n]*", kilde)))
        self.assertIn('_TRINN_VALG_KEY = "bs_trinn"', kilde)
        self.assertIn("horizontal=True", kilde)


if __name__ == "__main__":
    unittest.main()
