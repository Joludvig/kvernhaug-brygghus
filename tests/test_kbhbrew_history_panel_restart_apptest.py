"""
Issue #257 -- Phase 3B readiness audit: regression coverage for two
realistic multi-week real-brew sequences the existing `.kbhbrew`
AppTest suite (tests/test_kbhbrew_history_panel_apptest.py) does not
cover directly, because every test there reuses `.run()` on the SAME
`AppTest` instance (a rerun within one session) -- never a genuinely
fresh, second `AppTest.from_file(...)` instance pointed at the same
on-disk store.

Covers (issue #257 Scope 1 + 2):
  1. Fresh-session reopen persistence: save an actual OG in one
     `AppTest` session, then construct a brand-new, independent
     `AppTest` instance (never touching the first instance's Python
     object or its Streamlit session state) against the SAME
     KVERNHAUG_RECIPES_DIR, and prove the saved actual is read back
     from disk -- not inherited widget/session state, since a second
     `AppTest.from_file(...)` call has none of the first's state to
     inherit from.
  2. Temporally separated OG -> FG updates across that same
     fresh-session boundary: OG is saved in the first session; FG is
     saved in the second, independent session, without the test ever
     re-supplying OG to that second session's save click (the OG
     text_input's own pre-fill-from-disk, exercised via the real
     supported UI path, is what carries OG forward) -- proves OG
     survives and FG is added to the same brew, and that unrelated
     layers (sensing/learning) and the frozen snapshot are untouched.

Uses the same isolated-tmpdir/harness pattern as
tests/test_kbhbrew_history_panel_apptest.py (same harness file, same
KVERNHAUG_RECIPES_DIR/KVERNHAUG_TEST_KBHBREW_SEED_COUNT env contract) --
never the real recipes/ directory.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_history_panel_restart_apptest -b
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
        `.run()` på en eksisterende instans -- for å modellere en
        ekte fersk app-økt/gjenåpning mot det samme on-disk-lageret."""
        os.environ["KVERNHAUG_TEST_KBHBREW_SEED_COUNT"] = str(seed_count)
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _lagre_actuals(self, at, brew_id):
        knapper = [b for b in at.button if b.key == f"kbhbrew_hist_lagre_btn::{brew_id}"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lagring: {at.exception}")


class TestFreshSessionReopenPersistence(_IsolertRecipeMappeTestCase):
    def test_actual_og_saved_in_one_session_is_read_from_disk_in_a_brand_new_session(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.text_input(key=f"kbhbrew_hist_og::{brew_id}").set_value("1.055").run()
        self._lagre_actuals(okt1, brew_id)
        self.assertTrue(list(okt1.success), "Forventet en synlig lagre-bekreftelse i første økt")

        # Genuinely fresh session: a brand-new AppTest instance, with no
        # reference to okt1 at all -- only the on-disk store is shared.
        okt2 = self._fersk_apptest(seed_count=1)
        self.assertEqual(
            okt2.text_input(key=f"kbhbrew_hist_og::{brew_id}").value, "1.055",
            "Den lagrede OG-verdien må vises i en helt fersk økt, lest fra disk",
        )

        brew = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew["actuals"]["og"], 1.055)

    def test_reopen_does_not_silently_create_a_second_brew(self):
        brew_id = "brew-seed-0001"
        okt1 = self._fersk_apptest(seed_count=1)
        okt1.text_input(key=f"kbhbrew_hist_og::{brew_id}").set_value("1.055").run()
        self._lagre_actuals(okt1, brew_id)

        self._fersk_apptest(seed_count=1)
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)


class TestTemporallySeparatedOgThenFgUpdatesAcrossFreshSessions(_IsolertRecipeMappeTestCase):
    def test_og_saved_in_one_session_and_fg_saved_later_in_a_fresh_session_both_persist(self):
        brew_id = "brew-seed-0001"

        okt1 = self._fersk_apptest(seed_count=1)
        okt1.text_input(key=f"kbhbrew_hist_og::{brew_id}").set_value("1.055").run()
        self._lagre_actuals(okt1, brew_id)

        brew_etter_okt1 = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew_etter_okt1["actuals"]["og"], 1.055)
        self.assertNotIn("fg", brew_etter_okt1["actuals"])
        snapshot_foer = brew_etter_okt1["snapshot"]

        # Second, independent session -- FG is set WITHOUT the test ever
        # re-typing OG here; the OG field's own disk-backed pre-fill (see
        # ui/kbhbrew_history_panel.py::_render_actuals_skjema) is what
        # carries the earlier value forward on save.
        okt2 = self._fersk_apptest(seed_count=1)
        self.assertEqual(okt2.text_input(key=f"kbhbrew_hist_og::{brew_id}").value, "1.055")
        okt2.text_input(key=f"kbhbrew_hist_fg::{brew_id}").set_value("1.011").run()
        self._lagre_actuals(okt2, brew_id)
        self.assertTrue(list(okt2.success), "Forventet en synlig lagre-bekreftelse i andre økt")

        brew_etter_okt2 = kbhbrew_storage.hent_brew(brew_id)
        self.assertEqual(brew_etter_okt2["actuals"]["og"], 1.055, "OG må overleve uendret fra første økt")
        self.assertEqual(brew_etter_okt2["actuals"]["fg"], 1.011, "FG må legges til fra andre økt")

        # Unrelated layers/snapshot are untouched by either save.
        self.assertEqual(brew_etter_okt2.get("sensing"), {})
        self.assertEqual(brew_etter_okt2.get("learning"), {})
        self.assertEqual(brew_etter_okt2["snapshot"], snapshot_foer)


if __name__ == "__main__":
    unittest.main()
