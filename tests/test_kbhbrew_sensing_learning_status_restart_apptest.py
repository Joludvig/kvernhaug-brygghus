"""
Issue #289 -- Phase 3B acceptance-gap audit (#269 / PR #273): the one
narrow automated gap the merged audit identified was fresh-session
persistence for `.kbhbrew` SENSING, LEARNING and STATUS specifically --
tests/test_kbhbrew_history_panel_restart_apptest.py already proves this
for actuals (OG -> FG) using a genuinely independent second `AppTest`
instance (a real restart/reopen, never a `.run()` rerun on the same
instance). This file closes the same gap for the remaining three layers,
using the identical pattern and the same isolated-tmpdir/harness
contract (never the real recipes/ directory).

Covers (issue #289 "Required coverage"):
  1. `sensing.judgment`/`sensing.notes` saved in one session are read
     back from disk in a brand-new, independent session.
  2. `learning.nextTime` saved in one session is read back from disk in
     a brand-new, independent session.
  3. A persisted `status` transition (active -> done / discarded)
     survives a fresh session/reopen.
  4. Reopening/reading never creates a duplicate brew.
  5. Updating one layer (sensing/learning) never overwrites unrelated
     actuals/snapshot/status across a fresh-session boundary, and vice
     versa.
  6. A second, untouched brew remains completely unchanged.

Item 7 of the issue ("existing active/non-active history behavior
remains green") is a regression-evidence requirement, not new coverage
-- proven by running the existing suites this task's report lists
(tests/test_kbhbrew_history_panel_apptest.py in particular, whose
test_22-test_25 already cover the "current active brew" vs. "just
selected, not-yet-active historical brew" distinction), unchanged by
this file.

Uses only existing, supported UI/storage write paths
(ui/kbhbrew_history_panel.py's two separate save buttons via
modules/kbhbrew_storage.py::oppdater_brew_lag()) -- no new UX, no
storage-layer change, no assertion on implementation internals beyond
what modules/kbhbrew_storage.py already publicly returns.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_sensing_learning_status_restart_apptest -b
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_history_harness.py")


class _IsolertRecipeMappeTestCase(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_seed_count = os.environ.pop("KVERNHAUG_TEST_KBHBREW_SEED_COUNT", None)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        if self._gammel_seed_count is None:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_SEED_COUNT", None)
        else:
            os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = self._gammel_seed_count
        self._tmpdir.cleanup()

    def _fersk_apptest(self, seed_count=1):
        """Bygger en HELT NY, uavhengig AppTest-instans -- aldri en
        `.run()` på en eksisterende instans -- for å modellere en ekte
        fersk app-økt/gjenåpning mot det samme on-disk-lageret."""
        os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = str(seed_count)
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _lagre_actuals(self, at, brew_id):
        knapper = [b for b in at.button if b.key == f"kbhbrew_hist_lagre_btn::{brew_id}"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring av actuals: {at.exception}")

    def _lagre_sensing_learning(self, at, brew_id):
        knapper = [b for b in at.button if b.key == f"kbhbrew_hist_sensing_learning_lagre_btn::{brew_id}"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring av sensing/learning: {at.exception}")

    def _velg_brew(self, at, brew_id):
        """Historikk-utvalget sorterer nyeste `createdAt` først
        (modules/kbhbrew_ui.py::sorter_brews_for_eksport), så med flere
        seedede brygg er IKKE `brew_id` nødvendigvis forhåndsvalgt --
        velg det eksplisitt før feltene under det brygget kan nås."""
        at.selectbox(key="kbhbrew_historikk_valgt_id").select(brew_id).run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved brygg-valg: {at.exception}")


class TestFreshSessionSensingPersistence(_IsolertRecipeMappeTestCase):
    def test_sensing_judgment_and_notes_saved_in_one_session_are_read_from_disk_in_a_fresh_session(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.selectbox(key=f"kbhbrew_hist_sensing_judgment::{brew_id}").select("yes").run()
        okt1.text_area(key=f"kbhbrew_hist_sensing_notes::{brew_id}").set_value("Fruktig aroma, god humlebalanse").run()
        self._lagre_sensing_learning(okt1, brew_id)
        self.assertTrue(list(okt1.success), "Forventet en synlig lagre-bekreftelse i første økt")

        # Genuinely fresh session: a brand-new AppTest instance, with no
        # reference to okt1 at all -- only the on-disk store is shared.
        okt2 = self._fersk_apptest(seed_count=1)
        self.assertEqual(
            okt2.selectbox(key=f"kbhbrew_hist_sensing_judgment::{brew_id}").value, "yes",
            "Lagret sensing.judgment må gjenskapes i en helt fersk økt, lest fra disk",
        )
        self.assertEqual(
            okt2.text_area(key=f"kbhbrew_hist_sensing_notes::{brew_id}").value, "Fruktig aroma, god humlebalanse",
            "Lagret sensing.notes må gjenskapes i en helt fersk økt, lest fra disk",
        )

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["sensing"], {"judgment": "yes", "notes": "Fruktig aroma, god humlebalanse"})

    def test_reopen_after_sensing_save_does_not_silently_create_a_second_brew(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.selectbox(key=f"kbhbrew_hist_sensing_judgment::{brew_id}").select("yes").run()
        self._lagre_sensing_learning(okt1, brew_id)

        self._fersk_apptest(seed_count=1)
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)


class TestFreshSessionLearningPersistence(_IsolertRecipeMappeTestCase):
    def test_learning_next_time_saved_in_one_session_is_read_from_disk_in_a_fresh_session(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.text_area(key=f"kbhbrew_hist_learning_next::{brew_id}").set_value("Senk mesketemperatur 2C neste gang").run()
        self._lagre_sensing_learning(okt1, brew_id)
        self.assertTrue(list(okt1.success), "Forventet en synlig lagre-bekreftelse i første økt")

        okt2 = self._fersk_apptest(seed_count=1)
        self.assertEqual(
            okt2.text_area(key=f"kbhbrew_hist_learning_next::{brew_id}").value,
            "Senk mesketemperatur 2C neste gang",
            "Lagret learning.nextTime må gjenskapes i en helt fersk økt, lest fra disk",
        )

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["learning"]["nextTime"], "Senk mesketemperatur 2C neste gang")
        self.assertNotIn("whatWorked", brew["learning"])
        self.assertNotIn("whatChanged", brew["learning"])

    def test_reopen_after_learning_save_does_not_silently_create_a_second_brew(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.text_area(key=f"kbhbrew_hist_learning_next::{brew_id}").set_value("Kortere koking").run()
        self._lagre_sensing_learning(okt1, brew_id)

        self._fersk_apptest(seed_count=1)
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)

    def test_learning_hypothesis_saved_in_one_session_is_read_from_disk_in_a_fresh_session(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.text_area(key=f"kbhbrew_hist_learning_hypothesis::{brew_id}").set_value("Kanskje for varm mesk").run()
        self._lagre_sensing_learning(okt1, brew_id)
        self.assertTrue(list(okt1.success), "Forventet en synlig lagre-bekreftelse i første økt")

        okt2 = self._fersk_apptest(seed_count=1)
        self.assertEqual(
            okt2.text_area(key=f"kbhbrew_hist_learning_hypothesis::{brew_id}").value,
            "Kanskje for varm mesk",
            "Lagret learning.hypothesis må gjenskapes i en helt fersk økt, lest fra disk",
        )

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["learning"]["hypothesis"], "Kanskje for varm mesk")


class TestFreshSessionStatusPersistence(_IsolertRecipeMappeTestCase):
    def test_status_transition_to_done_survives_fresh_session_reopen(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.selectbox(key=f"kbhbrew_hist_status::{brew_id}").select("done").run()
        self._lagre_actuals(okt1, brew_id)
        self.assertTrue(list(okt1.success), "Forventet en synlig lagre-bekreftelse i første økt")

        okt2 = self._fersk_apptest(seed_count=1)
        self.assertEqual(
            okt2.selectbox(key=f"kbhbrew_hist_status::{brew_id}").value, "done",
            "Lagret status må gjenskapes i en helt fersk økt, lest fra disk",
        )

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["status"], "done")

    def test_reopen_after_status_save_does_not_silently_create_a_second_brew(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.selectbox(key=f"kbhbrew_hist_status::{brew_id}").select("discarded").run()
        self._lagre_actuals(okt1, brew_id)

        self._fersk_apptest(seed_count=1)
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)


class TestFreshSessionCrossLayerAndCrossBrewIsolation(_IsolertRecipeMappeTestCase):
    def test_sensing_learning_save_across_fresh_sessions_never_overwrites_actuals_snapshot_status_or_other_brew(self):
        brew_id = "brew-seed-0001"
        annet_brew_id = "brew-seed-0002"

        okt1 = self._fersk_apptest(seed_count=2)
        annen_brew_foer = kbhbrew_storage.hent_brew(annet_brew_id)

        self._velg_brew(okt1, brew_id)
        okt1.text_input(key=f"kbhbrew_hist_og::{brew_id}").set_value("1.055").run()
        okt1.selectbox(key=f"kbhbrew_hist_status::{brew_id}").select("done").run()
        self._lagre_actuals(okt1, brew_id)

        brew_etter_okt1 = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew_etter_okt1["actuals"]["og"], 1.055)
        self.assertEqual(brew_etter_okt1["status"], "done")
        self.assertEqual(brew_etter_okt1.get("sensing"), {})
        self.assertEqual(brew_etter_okt1.get("learning"), {})
        snapshot_foer = brew_etter_okt1["snapshot"]

        # Second, independent fresh session: only the SEPARATE
        # sensing/learning save button is clicked here, without ever
        # re-supplying OG/status -- their own disk-backed pre-fill (see
        # ui/kbhbrew_history_panel.py::_render_actuals_skjema) is what
        # proves they were never re-typed and thus never re-written by
        # this session's own actuals-save path (which is never clicked
        # here at all).
        okt2 = self._fersk_apptest(seed_count=2)
        self._velg_brew(okt2, brew_id)
        self.assertEqual(okt2.text_input(key=f"kbhbrew_hist_og::{brew_id}").value, "1.055")
        self.assertEqual(okt2.selectbox(key=f"kbhbrew_hist_status::{brew_id}").value, "done")
        okt2.selectbox(key=f"kbhbrew_hist_sensing_judgment::{brew_id}").select("maybe").run()
        okt2.text_area(key=f"kbhbrew_hist_learning_next::{brew_id}").set_value("Kortere koking").run()
        self._lagre_sensing_learning(okt2, brew_id)
        self.assertTrue(list(okt2.success), "Forventet en synlig lagre-bekreftelse i andre økt")

        # Third, independent fresh session reads everything back from disk.
        self._fersk_apptest(seed_count=2)
        brew_etter = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew_etter["actuals"]["og"], 1.055, "Actuals fra første økt må overleve uendret")
        self.assertEqual(brew_etter["status"], "done", "Status fra første økt må overleve uendret")
        self.assertEqual(brew_etter["sensing"]["judgment"], "maybe")
        self.assertEqual(brew_etter["learning"]["nextTime"], "Kortere koking")
        self.assertEqual(brew_etter["snapshot"], snapshot_foer, "Det frosne snapshotet må aldri endres")
        self.assertEqual(brew_etter["brewId"], brew_etter_okt1["brewId"])
        self.assertEqual(brew_etter["originBrewId"], brew_etter_okt1["originBrewId"])
        self.assertEqual(brew_etter["recipeId"], brew_etter_okt1["recipeId"])

        self.assertEqual(
            kbhbrew_storage.hent_brew(annet_brew_id), annen_brew_foer,
            "Det andre, urørte bryggets data må forbli fullstendig uendret over alle tre øktene",
        )
        self.assertEqual(
            len(kbhbrew_storage.hent_alle_brews()), 2,
            "Ingen av de tre øktenes lagringer/gjenåpninger skal opprette et nytt/duplisert brygg",
        )


if __name__ == "__main__":
    unittest.main()
