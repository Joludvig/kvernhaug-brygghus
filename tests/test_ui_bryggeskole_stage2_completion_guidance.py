"""
Issue #506 -- Stage 2 end-of-coursework guidance
(docs/development/v22_course_stage_ui_contract.md §7.3, §14).

In the Kompetent lens, once BOTH Foundation and Kompetent are worked through
(course_stage.stage_worked_through, read-only over answered_questions), the
overview shows one guidance line: the coursework is worked through, the next
step is a real brew, and deeper tracks are optional. It takes precedence over
the Stage-2 lines in the Kompetent lens; everything else is unchanged.

What is checked:
- the trigger needs both stages; Kompetent alone, Foundation alone or a
  fresh learner never shows it;
- precedence: the Foundation lens keeps «Klar for Trinn 2?», the Kompetent
  lens shows only the new line (no «Trinn 2 vises som anbefalt…»), the
  Foundation-gap tip is unchanged;
- exact NO/EN copy, through environment and language switches;
- no locks, no completion/certification/score wording, no Bryggemester,
  no mastery write, the 11-card grid, and the key-only panel source.

All AppTests use an isolated KVERNHAUG_BRYGGESKOLE_STATE_DIR; history is
seeded only through apply_answer + write_mastery_state.

Run with:
    python -m unittest tests.test_ui_bryggeskole_stage2_completion_guidance
"""
import io
import os
import unittest

from bryggeskole import course_stage
from bryggeskole.mastery_store import default_state_path, read_mastery_state
from modules.i18n import t as t_ren
from tests.test_ui_bryggeskole_panel import _alle_synlige_tekster
from tests.test_ui_bryggeskole_stage_selector import (
    _EKSPLISITT,
    _FORBUDTE_ORD,
    _KANONISK,
    _KORT_KEYS,
    _PANEL_SOURCE,
    _S3Test,
    _alle_foundation,
    _seed,
    _stage_map,
)

_NOKKEL = "bryggeskole.trinn.trinn2_gjennomgatt"
_NO = ("Du har gått gjennom Trinn 2 · Kompetent hjemmebrygger. Neste steg er å bruke det du har lært på et ekte "
       "brygg og lære av resultatet. Når du har gjort det, kan Hjemmebrygger-løpet avsluttes her – dypere spor er "
       "valgfritt.")
_EN = ("You've worked through Stage 2 · Competent homebrewer. Next, use what you've learned on a real brew and learn "
       "from the result. Once you've done that, the Homebrewer journey can end here — deeper tracks are optional.")
# Beyond the stage UI's own list: no score, certificate, qualification or
# Bryggemester stage in the learner-facing text.
_OGSA_FORBUDT = ("score", "poeng", "grade", "karakter", "sertifikat", "certificate", "qualif", "kvalifis",
                 "fullført", "bryggemester", "bryggmester")


def _t(key, sprak="no", **kw):
    return t_ren(key, sprak, **kw)


def _alle_kompetent():
    return [(m, "kompetent") for m in _KANONISK
            if course_stage.module_has_stage(_stage_map(), m, "kompetent")]


class _GuidanceTest(_S3Test):
    def _suksess(self, at):
        return [s.value for s in at.success]

    def _ny(self, at, sprak="no"):
        return _t(_NOKKEL, sprak) in self._suksess(at)


class TestExactCopy(unittest.TestCase):
    def test_no_and_en_text(self):
        self.assertEqual(_t(_NOKKEL, "no"), _NO)
        self.assertEqual(_t(_NOKKEL, "en"), _EN)

    def test_points_to_the_real_brew_and_optional_depth(self):
        self.assertIn("ekte brygg", _NO)
        self.assertIn("dypere spor er valgfritt", _NO)
        self.assertIn("real brew", _EN)
        self.assertIn("deeper tracks are optional", _EN)

    def test_no_forbidden_wording(self):
        for tekst in (_NO, _EN):
            for ord_ in _FORBUDTE_ORD + _OGSA_FORBUDT:
                self.assertNotIn(ord_, tekst.lower())

    def test_panel_uses_the_key_not_raw_text(self):
        with io.open(_PANEL_SOURCE, encoding="utf-8") as fh:
            kilde = fh.read()
        self.assertEqual(kilde.count(f'"{_NOKKEL}"'), 1)
        for rest in ("Neste steg er å bruke", "Next, use what you've learned", "Hjemmebrygger-løpet",
                     "Homebrewer journey"):
            self.assertNotIn(rest, kilde)


class TestTrigger(_GuidanceTest):
    def test_fresh_learner(self):
        for trinn in course_stage.STAGES:
            at = self._oversikt()
            self._velg_trinn(at, trinn)
            self.assertFalse(self._ny(at), trinn)

    def test_foundation_only_keeps_todays_guidance(self):
        _seed(_alle_foundation())
        at = self._oversikt()
        # Auto-default Kompetent: today's recommended-next-step line, unchanged.
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertEqual(self._suksess(at), [_t("bryggeskole.trinn.trinn2_anbefalt")])
        self._velg_trinn(at, "foundation")
        self.assertEqual(self._suksess(at), [_t("bryggeskole.trinn.klar_for_trinn2")])
        self._velg_trinn(at, "kompetent")
        self.assertEqual(self._suksess(at), [])  # explicit Kompetent: nothing, as today

    def test_kompetent_only_never_shows_it(self):
        _seed(_alle_kompetent())
        at = self._oversikt()
        self.assertEqual(self._lens(at).value, "foundation")
        self.assertEqual(self._suksess(at), [])
        self._velg_trinn(at, "kompetent")
        self.assertEqual(self._suksess(at), [])
        self.assertIn(_t("bryggeskole.trinn.tips_foundation"), [c.value for c in at.caption])

    def test_one_foundation_gap_is_enough_to_withhold_it(self):
        sporsmal = course_stage._module_entry(_stage_map(), "mesking")["foundation"]["questions"]
        _seed(_alle_foundation(), unntak={sporsmal[0]})
        _seed(_alle_kompetent())
        at = self._oversikt()
        self._velg_trinn(at, "kompetent")
        self.assertEqual(self._suksess(at), [])
        self.assertIn(_t("bryggeskole.trinn.tips_foundation"), [c.value for c in at.caption])

    def test_one_kompetent_gap_is_enough_to_withhold_it(self):
        sporsmal = course_stage._module_entry(_stage_map(), "smak")["kompetent"]["questions"]
        _seed(_alle_foundation())
        _seed(_alle_kompetent(), unntak={sporsmal[-1]})
        at = self._oversikt()
        self.assertEqual(self._suksess(at), [_t("bryggeskole.trinn.trinn2_anbefalt")])

    def test_latest_wrong_answer_withholds_it(self):
        _seed(_alle_foundation())
        _seed(_alle_kompetent())
        _seed([("gjaring", "kompetent")], korrekt=False)  # latest answers wrong: Gjæring back to in progress
        at = self._oversikt()
        self.assertEqual(self._suksess(at), [_t("bryggeskole.trinn.trinn2_anbefalt")])


class TestBothStagesWorkedThrough(_GuidanceTest):
    def setUp(self):
        super().setUp()
        _seed(_alle_foundation())
        _seed(_alle_kompetent())

    def test_kompetent_lens_shows_only_the_new_line(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                # Default lens unchanged: Foundation is worked through, so Kompetent.
                self.assertEqual(self._lens(at).value, "kompetent")
                self.assertIs(at.session_state[_EKSPLISITT], False)
                self.assertEqual(self._suksess(at), [_t(_NOKKEL, sprak)])
                # An explicit Kompetent choice keeps it.
                self._velg_trinn(at, "foundation")
                self._velg_trinn(at, "kompetent")
                self.assertEqual(self._suksess(at), [_t(_NOKKEL, sprak)])

    def test_foundation_lens_keeps_ready_for_stage_2(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                self._velg_trinn(at, "foundation")
                self.assertEqual(self._suksess(at), [_t("bryggeskole.trinn.klar_for_trinn2", sprak)])
                at.run()
                self.assertEqual(self._lens(at).value, "foundation")  # the lens is never moved

    def test_environment_switch_keeps_it(self):
        at = self._oversikt("bs_velg_bryggeri_btn")
        self.assertEqual(self._suksess(at), [_NO])
        self._bytt_miljo(at, "bs_velg_hjemmebrygger_btn")
        self.assertEqual(self._lens(at).value, "kompetent")
        self.assertEqual(self._suksess(at), [_NO])

    def test_language_switch_follows_the_language(self):
        at = self._oversikt()
        self.assertEqual(self._suksess(at), [_NO])
        at.session_state["sprak"] = "en"
        at.run()
        self.assertEqual(len(at.exception), 0, at.exception)
        self.assertEqual(self._suksess(at), [_EN])
        at.session_state["sprak"] = "no"
        at.run()
        self.assertEqual(self._suksess(at), [_NO])

    def test_no_locks_eleven_cards_counts_only(self):
        for sprak in ("no", "en"):
            with self.subTest(sprak=sprak):
                at = self._oversikt(sprak=sprak if sprak != "no" else None)
                kort = [b for b in at.button if b.key in _KORT_KEYS]
                self.assertEqual([b.key for b in kort], _KORT_KEYS)
                self.assertFalse(any(b.disabled for b in at.button))
                self.assertIn(_t("bryggeskole.trinn.fremdrift", sprak, n=9, totalt=9),
                              [c.value for c in at.caption])
                tekst = " ".join(_alle_synlige_tekster(at)).lower()
                for ord_ in _FORBUDTE_ORD + _OGSA_FORBUDT:
                    self.assertNotIn(ord_, tekst)
                # Two stages only: no third option in the selector.
                self.assertEqual(list(self._lens(at).options), [_t(f"bryggeskole.trinn.{s}", sprak)
                                                                 for s in course_stage.STAGES])

    def test_overview_never_writes_mastery(self):
        foer = os.stat(default_state_path()).st_mtime_ns
        dokument = read_mastery_state()
        at = self._oversikt()
        self._velg_trinn(at, "foundation")
        self._velg_trinn(at, "kompetent")
        self._bytt_miljo(at, "bs_velg_bryggeri_btn")
        self.assertTrue(self._ny(at))
        self.assertEqual(os.stat(default_state_path()).st_mtime_ns, foer)
        self.assertEqual(read_mastery_state(), dokument)


if __name__ == "__main__":
    unittest.main()
