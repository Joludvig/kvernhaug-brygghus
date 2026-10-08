"""
AppTest coverage for stage UI S5 -- the final local/offline QA of the
Foundation -> Kompetent stage UI (docs/development/v22_course_stage_ui_contract.md
§3-§12, §15; offline, no GitHub issue yet).

S2-S4 each test their own slice. This suite checks the finished experience
end to end, across both languages and both legacy environments:
- every one of the 18 valid (module, stage) pairs, opened from its card:
  stage, breadcrumb, chunks/questions, widget-key family, no preselected
  answer, disabled «Sjekk svar», wrong and correct feedback, retry, summary,
  both ways back to the overview, and the card status / stage count moving
  Ikke startet -> Påbegynt (latest answer wrong) -> Gjennomgått (corrected);
- the state/switching rules in one session (default, explicit choices,
  environment and language switches, lesson-only Foundation review);
- the i18n pass: no raw keys, no missing-key markers, no raw stage ids, no
  legacy «Leksjon tilgjengelig» in the staged overview, no Norwegian in EN;
- the invalid-map fallback: malformed or missing map -> today's single flow
  with its legacy badges, warned once per session.

Learner history lives only in an isolated KVERNHAUG_BRYGGESKOLE_STATE_DIR
(via _MedIsolertTilstand).

Run with:
    python -m unittest tests.test_ui_bryggeskole_stage_final_qa
"""
import io
import json
import logging
import os
import re
import tempfile
from unittest import mock

from bryggeskole import course_stage
from bryggeskole.mastery_store import default_state_path, read_mastery_state
from modules.i18n import t as t_ren
from tests.test_ui_bryggeskole_panel import (
    _MedIsolertTilstand,
    _alle_synlige_tekster,
    _feil_svar_ider,
    _knapp,
    _korrekt_svar_ider,
)
from tests.test_ui_bryggeskole_stage_selector import _alle_foundation, _seed, _visning
from ui import bryggeskole_panel as panel

_LENS = "bs_trinn"
_EKSPLISITT = "bs_trinn_valgt_eksplisitt"
_KANONISK = list(panel._MODUL_REKKEFOLGE)
_KORT_KEYS = [f"bs_apne_modul_{m}_btn" for m in _KANONISK]
_MILJO_KNAPP = {"hjemmebrygger": "bs_velg_hjemmebrygger_btn", "bryggeri": "bs_velg_bryggeri_btn"}
# Every pair gets one (language, environment) combination; across the 18
# pairs each combination is used several times and each stage meets each one.
_KOMBINASJONER = (("no", "hjemmebrygger"), ("en", "bryggeri"), ("en", "hjemmebrygger"), ("no", "bryggeri"))
_STATUS = ("ikke_startet", "pabegynt", "gjennomgatt")


def _t(key, sprak, **kw):
    return t_ren(key, sprak, **kw)


def _par():
    kart = course_stage.load_stage_map()
    return [(m, tr) for tr in course_stage.STAGES for m in _KANONISK if course_stage.module_has_stage(kart, m, tr)]


def _raa_tekstfeil(tekster, sprak):
    """Text a learner must never see: raw i18n keys, missing-key markers,
    raw stage ids, and (in EN) Norwegian UI words."""
    feil = []
    for tekst in tekster:
        if re.search(r"\bbryggeskole\.[a-z_]+\.", tekst) or "??" in tekst:
            feil.append(tekst)
        if re.search(r"\b(foundation|kompetent)\b", tekst):  # lowercase = a raw stage id
            feil.append(tekst)
        if sprak == "en" and re.search(r"\b(Trinn|Påbegynt|Gjennomgått|Ikke startet|Repeter|Bryggeskole)\b", tekst):
            feil.append(tekst)
    return feil


class _S5Test(_MedIsolertTilstand):
    _ENKELTFLYT = False

    def _oversikt(self, sprak="no", miljo="hjemmebrygger"):
        at = self._ny_apptest()
        if sprak != "no":
            at.session_state["sprak"] = sprak
            at.run()
        self._velg_miljo(at, _MILJO_KNAPP[miljo])
        return at

    def _klikk(self, at, key):
        _knapp(at, key).click().run()
        self.assertEqual(len(at.exception), 0, at.exception)

    def _lens(self, at):
        radios = [r for r in at.radio if r.key == _LENS]
        self.assertEqual(len(radios), 1, [r.key for r in at.radio])
        return radios[0]

    def _velg_trinn(self, at, trinn):
        self._lens(at).set_value(trinn).run()
        self.assertEqual(len(at.exception), 0, at.exception)

    def _sprak(self, at, sprak):
        at.session_state["sprak"] = sprak
        at.run()
        self.assertEqual(len(at.exception), 0, at.exception)

    def _sti(self, at):
        return [c.value for c in at.caption if " ▸ " in c.value]

    def _status_telling(self, at, sprak):
        captions = [c.value for c in at.caption]
        return {s: captions.count(_t(f"bryggeskole.trinn.status.{s}", sprak)) for s in _STATUS}

    def _fremdrift(self, at, sprak, trinn):
        totalt = course_stage.stage_progress(course_stage.load_stage_map(), trinn, {})[1]
        mal = re.escape(_t("bryggeskole.trinn.fremdrift", sprak, n="@", totalt=totalt)).replace("@", r"(\d+)")
        treff = [re.fullmatch(mal, c.value) for c in at.caption]
        tall = [int(m.group(1)) for m in treff if m]
        self.assertEqual(len(tall), 1, [c.value for c in at.caption])
        return tall[0]


class TestEveryPairEndToEnd(_S5Test):
    """The 18 valid (module, stage) pairs, each a fresh learner, each walked
    twice from its card: round 1 with the first answer wrong, round 2 (retry)
    all correct."""

    def _sjekk_tekst(self, at, sprak, hvor):
        self.assertEqual(_raa_tekstfeil(_alle_synlige_tekster(at), sprak), [], hvor)

    def test_all_eighteen_pairs(self):
        par = _par()
        self.assertEqual(len(par), 18)
        kart = course_stage.load_stage_map()
        for nr, (modul_id, trinn) in enumerate(par):
            sprak, miljo = _KOMBINASJONER[nr % len(_KOMBINASJONER)]
            with self.subTest(modul=modul_id, trinn=trinn, sprak=sprak, miljo=miljo):
                if os.path.exists(default_state_path()):
                    os.remove(default_state_path())
                self._ett_par(modul_id, trinn, sprak, miljo, kart)

    def _ett_par(self, modul_id, trinn, sprak, miljo, kart):
        at = self._oversikt(sprak, miljo)
        if trinn == "kompetent":
            self._velg_trinn(at, "kompetent")
        self.assertEqual(self._lens(at).value, trinn)
        antall_med_innhold = sum(course_stage.module_has_stage(kart, m, trinn) for m in _KANONISK)
        self.assertEqual(self._status_telling(at, sprak),
                         {"ikke_startet": antall_med_innhold, "pabegynt": 0, "gjennomgatt": 0})
        self.assertEqual(self._fremdrift(at, sprak, trinn), 0)
        self.assertEqual(_knapp(at, f"bs_apne_modul_{modul_id}_btn").label, _t("bryggeskole.modul.start", sprak))
        self._sjekk_tekst(at, sprak, "overview")

        # Card -> the right stage, with both axes in the breadcrumb.
        self._klikk(at, f"bs_apne_modul_{modul_id}_btn")
        base = modul_id + panel._TRINN_NOKKEL_INFIKS[trinn]
        self._aktiv_modul = base
        self.assertEqual(at.session_state["bs_aktiv_trinn"], trinn)
        sti = " ▸ ".join([_t("tabs.bryggeskole", sprak), _t(f"bryggeskole.miljo.{miljo}", sprak),
                          _t(f"bryggeskole.trinn.sti.{trinn}", sprak),
                          _t(panel._MODULER[modul_id]["tittel_nokkel"], sprak)])
        self.assertEqual(self._sti(at), [sti])
        visning = _visning(modul_id, trinn)
        teller = _t("bryggeskole.leksjon.bolk_teller", sprak, n=1, totalt=len(visning["chunks"]))
        if visning["chunks"]:
            self.assertIn(teller, [c.value for c in at.caption])
        else:
            # Questions-only stage: no invented chunk, the neutral intro and a
            # way back to the Foundation lesson.
            self.assertNotIn(teller, [c.value for c in at.caption])
            self.assertIn(_t("bryggeskole.trinn.kun_sporsmal", sprak), [i.value for i in at.info])
            _knapp(at, f"bs_trinn_repeter_{base}_btn")
        if trinn == "kompetent" and course_stage.module_has_stage(kart, modul_id, "foundation"):
            self.assertEqual(_knapp(at, f"bs_trinn_repeter_{base}_btn").label,
                             _t("bryggeskole.trinn.repeter_foundation", sprak))
        self._sjekk_tekst(at, sprak, "lesson")

        # Round 1: the first answer wrong, the rest correct.
        self._start_sporsmalsrunde(at)
        korrekt, feil = _korrekt_svar_ider(visning), _feil_svar_ider(visning)
        stage_radios = [r.key for r in at.radio if r.key.startswith("bs_valg_")]
        self.assertEqual(stage_radios, [f"bs_valg_{base}_r1_q0"])
        for idx in range(len(visning["questions"])):
            self.assertIsNone(at.radio(key=f"bs_valg_{base}_r1_q{idx}").value)
            self.assertTrue(_knapp(at, f"bs_svar_btn_{base}_r1_q{idx}").disabled)
            self._besvar_sporsmal(at, idx, 1, feil[idx] if idx == 0 else korrekt[idx])
            if idx == 0:
                self.assertEqual(len(at.error), 1)
                self.assertEqual(len(at.success), 0)
                riktig = _t("bryggeskole.svar.riktig_svar", sprak)
                self.assertTrue(any(c.value.startswith(riktig + ": ") for c in at.caption))
                self._sjekk_tekst(at, sprak, "wrong feedback")
            else:
                self.assertEqual(len(at.success), 1)
                self.assertEqual(len(at.error), 0)
            self._fortsett(at, idx, 1)
        self._sjekk_oppsummering(at, sprak, visning, runde_ok=False)
        self._klikk(at, f"bs_oppsummering_tilbake_{base}_btn")

        # Back on the overview: same lens, latest answer wrong -> Påbegynt.
        self.assertEqual(self._lens(at).value, trinn)
        self.assertEqual(self._status_telling(at, sprak),
                         {"ikke_startet": antall_med_innhold - 1, "pabegynt": 1, "gjennomgatt": 0})
        self.assertEqual(self._fremdrift(at, sprak, trinn), 0)
        self.assertEqual(_knapp(at, f"bs_apne_modul_{modul_id}_btn").label,
                         _t("bryggeskole.modul.se_resultat", sprak))

        # Round 2 (retry from the summary): fresh, unanswered, all correct.
        self._klikk(at, f"bs_apne_modul_{modul_id}_btn")
        self._klikk(at, f"bs_prov_igjen_{base}_btn")
        self.assertIsNone(at.radio(key=f"bs_valg_{base}_r2_q0").value)
        self.assertTrue(_knapp(at, f"bs_svar_btn_{base}_r2_q0").disabled)
        self._fullfor_alle_sporsmal(at, 2, korrekt)
        self._sjekk_oppsummering(at, sprak, visning, runde_ok=True)
        self._klikk(at, f"bs_tilbake_{base}_btn")

        # Corrected later -> Gjennomgått, and the stage count moves.
        self.assertEqual(self._lens(at).value, trinn)
        self.assertEqual(self._status_telling(at, sprak),
                         {"ikke_startet": antall_med_innhold - 1, "pabegynt": 0, "gjennomgatt": 1})
        self.assertEqual(self._fremdrift(at, sprak, trinn), 1)
        self.assertEqual(set(read_mastery_state()["answered_questions"]), {q["id"] for q in visning["questions"]})
        self._sjekk_tekst(at, sprak, "overview after the walk")

    def _sjekk_oppsummering(self, at, sprak, visning, runde_ok):
        self.assertIn(_t("bryggeskole.oppsummering.heading", sprak), [s.value for s in at.subheader])
        linjer = [m.value for m in at.markdown if m.value.startswith(_t("bryggeskole.oppsummering.denne_runden_label", sprak))]
        self.assertEqual(len(linjer), len({k for q in visning["questions"] for k in q["concepts"]}))
        reprise = _t("bryggeskole.oppsummering.runde_reprise", sprak)
        if runde_ok:
            self.assertFalse(any(reprise in linje for linje in linjer))
        else:
            self.assertTrue(any(reprise in linje for linje in linjer))
        self._sjekk_tekst(at, sprak, "summary")


class TestStateAndSwitching(_S5Test):
    def test_one_session_through_every_switch(self):
        at = self._oversikt()
        # 1. Fresh session: Foundation, not explicit.
        self.assertEqual(self._lens(at).value, "foundation")
        self.assertFalse(at.session_state[_EKSPLISITT])
        # 6. Opening and closing a module keeps the lens.
        self._klikk(at, "bs_apne_modul_mesking_btn")
        self._klikk(at, "bs_tilbake_mesking_btn")
        self.assertEqual(self._lens(at).value, "foundation")
        # 3. Explicit Kompetent.
        self._velg_trinn(at, "kompetent")
        self.assertTrue(at.session_state[_EKSPLISITT])
        # 4. Environment switch keeps it.
        self._klikk(at, "bs_bytt_miljo_btn")
        self._klikk(at, "bs_velg_bryggeri_btn")
        self.assertEqual(self._lens(at).value, "kompetent")
        # 5. NO -> EN -> NO keeps it.
        self._sprak(at, "en")
        self.assertEqual(self._lens(at).value, "kompetent")
        self._sprak(at, "no")
        self.assertEqual(self._lens(at).value, "kompetent")
        # 7. Lesson-only Foundation review (card «Repeter» and the in-lesson
        # «Repeter Foundation-delen») never moves the lens.
        self._klikk(at, "bs_apne_modul_rengjoring_btn")
        self.assertEqual(at.session_state["bs_aktiv_trinn"], "foundation")
        self.assertIn(_t("bryggeskole.trinn.sti.foundation", "no"), self._sti(at)[0])
        self._klikk(at, "bs_tilbake_rengjoring_btn")
        self.assertEqual(self._lens(at).value, "kompetent")
        self._klikk(at, "bs_apne_modul_gjaring_btn")
        self._klikk(at, "bs_trinn_repeter_gjaring_k_btn")
        self.assertIn(_t("bryggeskole.trinn.sti.foundation", "no"), self._sti(at)[0])
        self._klikk(at, "bs_tilbake_gjaring_btn")
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertIsNone(at.session_state["bs_aktiv_trinn"])
        # 2. Explicit Foundation stays Foundation, through the same switches.
        self._velg_trinn(at, "foundation")
        self._klikk(at, "bs_bytt_miljo_btn")
        self._klikk(at, "bs_velg_hjemmebrygger_btn")
        self._sprak(at, "en")
        self.assertEqual(self._lens(at).value, "foundation")
        # 8. A Kompetent-only card under Foundation switches the lens explicitly.
        self._klikk(at, "bs_apne_modul_smak_btn")
        self.assertIn(_t("bryggeskole.trinn.sti.kompetent", "en"), self._sti(at)[0])
        self._klikk(at, "bs_tilbake_smak_k_btn")
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertTrue(at.session_state[_EKSPLISITT])

    def test_auto_default_only_without_an_explicit_choice(self):
        _seed(_alle_foundation())
        # 9. Foundation worked through, no explicit choice -> Kompetent, with the
        # recommended-next line; through switches it stays that way.
        at = self._oversikt("en", "bryggeri")
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertFalse(at.session_state[_EKSPLISITT])
        self.assertIn(_t("bryggeskole.trinn.trinn2_anbefalt", "en"), [s.value for s in at.success])
        # 10. An explicit Foundation choice is never overridden afterwards.
        self._velg_trinn(at, "foundation")
        for steg in ("miljo", "sprak", "modul"):
            if steg == "miljo":
                self._klikk(at, "bs_bytt_miljo_btn")
                self._klikk(at, "bs_velg_hjemmebrygger_btn")
            elif steg == "sprak":
                self._sprak(at, "no")
            else:
                self._klikk(at, "bs_apne_modul_mesking_btn")
                self._klikk(at, "bs_tilbake_mesking_btn")
            self.assertEqual(self._lens(at).value, "foundation", steg)
        self.assertIn(_t("bryggeskole.trinn.klar_for_trinn2", "no"), [s.value for s in at.success])
        self.assertEqual(self._fremdrift(at, "no", "foundation"), 9)


class TestProgressAcrossStages(_S5Test):
    def test_history_and_independent_stages(self):
        # Historical answers from an earlier session count; the stages never
        # share progress, even for a module with both.
        _seed([("gjaring", "foundation")])
        _seed([("gjaring", "kompetent")], korrekt=False)
        at = self._oversikt("en", "hjemmebrygger")
        self.assertEqual(self._fremdrift(at, "en", "foundation"), 1)
        self.assertEqual(self._status_telling(at, "en"), {"ikke_startet": 8, "pabegynt": 0, "gjennomgatt": 1})
        self._velg_trinn(at, "kompetent")
        self.assertEqual(self._fremdrift(at, "en", "kompetent"), 0)
        self.assertEqual(self._status_telling(at, "en"), {"ikke_startet": 8, "pabegynt": 1, "gjennomgatt": 0})
        tekst = " ".join(_alle_synlige_tekster(at)).lower()
        for ord_ in ("%", "score", "grade", "certif", "passed", "mastered", "complete"):
            self.assertNotIn(ord_, tekst)


class TestI18nPass(_S5Test):
    def test_overviews_have_no_raw_or_mixed_text(self):
        for sprak in ("no", "en"):
            for miljo in ("hjemmebrygger", "bryggeri"):
                for trinn in course_stage.STAGES:
                    with self.subTest(sprak=sprak, miljo=miljo, trinn=trinn):
                        at = self._oversikt(sprak, miljo)
                        self._velg_trinn(at, trinn)
                        tekster = _alle_synlige_tekster(at) + [self._lens(at).label]
                        tekster += list(self._lens(at).options)  # the rendered option labels
                        self.assertEqual(_raa_tekstfeil(tekster, sprak), [])
                        # The staged overview never shows the legacy badge.
                        self.assertNotIn(_t("bryggeskole.prosess.aktiv_badge", sprak), tekster)
                        self.assertEqual([b.key for b in at.button if b.key in _KORT_KEYS], _KORT_KEYS)

    def test_every_stage_key_is_translated(self):
        from modules.i18n import TEKSTER
        nokler = {k for k in TEKSTER["no"] if k.startswith("bryggeskole.trinn.")}
        self.assertEqual(nokler, {k for k in TEKSTER["en"] if k.startswith("bryggeskole.trinn.")})
        for nokkel in sorted(nokler):
            with self.subTest(nokkel=nokkel):
                self.assertNotEqual(TEKSTER["no"][nokkel], TEKSTER["en"][nokkel])
                self.assertIsNone(re.search(r"[æøåÆØÅ]", TEKSTER["en"][nokkel]))
                # A stage is never named by the bare environment word.
                self.assertNotIn(TEKSTER["no"][nokkel].strip(), ("Hjemmebrygger", "🏠 Hjemmebrygger"))


class TestInvalidMapFallback(_S5Test):
    def _malformert(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        sti = os.path.join(tmp.name, "course_stage_map.json")
        with io.open(sti, "w", encoding="utf-8") as fh:
            fh.write('{"schema_version": 1, "modules": [')  # not JSON
        ekte = course_stage.load_stage_map
        return mock.patch.object(panel._course_stage, "load_stage_map", lambda: ekte(sti))

    def _manglende(self):
        ekte = course_stage.load_stage_map
        return mock.patch.object(panel._course_stage, "load_stage_map",
                                 lambda: ekte(os.path.join(tempfile.gettempdir(), "kbh-ingen-slik-fil.json")))

    def test_malformed_and_missing_map(self):
        for navn, patch in (("malformed", self._malformert), ("missing", self._manglende)):
            with self.subTest(kart=navn), patch(), \
                    self.assertLogs("ui.bryggeskole_panel", level=logging.WARNING) as logg:
                at = self._oversikt()
                self.assertEqual([r for r in at.radio if r.key == _LENS], [])
                captions = [c.value for c in at.caption]
                self.assertEqual(captions.count(_t("bryggeskole.prosess.aktiv_badge", "no")), 11)
                for s in _STATUS:
                    self.assertNotIn(_t(f"bryggeskole.trinn.status.{s}", "no"), captions)
                self.assertFalse(any(re.search(r"moduler gjennomgått", c) for c in captions))
                # The old single flow stays usable end to end, with its badges.
                self._klikk(at, "bs_apne_modul_rengjoring_btn")
                self._aktiv_modul = "rengjoring"
                self.assertEqual(self._sti(at)[0].count(" ▸ "), 2)
                self._start_sporsmalsrunde(at)
                pilot = panel._MODULER["rengjoring"]["pilot"].read_pilot_file()
                self._fullfor_alle_sporsmal(at, 1, _korrekt_svar_ider(pilot))
                self._klikk(at, "bs_oppsummering_tilbake_rengjoring_btn")
                self.assertIn(_t("bryggeskole.status.fullfort_okt", "no"), [c.value for c in at.caption])
                # More reruns, a language and an environment switch: still one warning.
                self._sprak(at, "en")
                self._klikk(at, "bs_bytt_miljo_btn")
                self._klikk(at, "bs_velg_bryggeri_btn")
                self.assertEqual([r for r in at.radio if r.key == _LENS], [])
            self.assertEqual(len(logg.records), 1, logg.output)
            if os.path.exists(default_state_path()):
                os.remove(default_state_path())


if __name__ == "__main__":
    import unittest

    unittest.main()
