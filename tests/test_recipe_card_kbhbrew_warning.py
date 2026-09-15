"""
Issue #256 -- regresjonstest: dual-truth-vakt for den gamle,
per-oppskrift Bryggeloggen (ui/recipe_card.py::
_render_brewday_result_panel()) når den lastede oppskriften allerede har
>=1 lagret .kbhbrew-brygg.

Bakgrunn (Phase 3B readiness-audit, durable decision #253): App eier det
gjeldende strukturerte bryggrecordet; Web er ikke en parallell live-logg.
For en oppskrift med et eksisterende `.kbhbrew` skal den gamle
per-oppskrift-Bryggeloggen ALDRI fremstå som den kanoniske live-
batch-loggen. Owner/Chief-beslutning: "advar, ikke skjul" -- Bryggeloggen
skal forbli tilgjengelig for historisk kompatibilitet, men med en tydelig
advarsel når et .kbhbrew-brygg finnes for akkurat DENNE oppskriften.

Bruker AppTest-harnesset tests/fixtures/streamlit_harness/
recipe_card_kbhbrew_warning_harness.py -- ekte rendring via Streamlit
AppTest (samme prinsipp som tests/test_kbhbrew_create_panel_apptest.py),
IKKE en ren kildekode-/streng-sjekk.

Dekker:
  - oppskrift UTEN noen .kbhbrew: eksisterende legacy-flyt uendret, ingen
    advarsel, Bryggeloggen fortsatt fullt tilgjengelig.
  - oppskrift MED >=1 .kbhbrew: advarsel vises (før/rundt Bryggeloggen),
    Bryggeloggen forblir likevel tilgjengelig (historisk kompatibilitet,
    ikke skjult).

Kjøres med:
    python3 -m unittest tests.test_recipe_card_kbhbrew_warning -b
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(
    _REPO_ROOT, "tests", "fixtures", "streamlit_harness", "recipe_card_kbhbrew_warning_harness.py",
)


class TestRecipeCardKbhbrewWarning(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_has_kbhbrew = os.environ.pop("KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW", None)

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        if self._gammel_has_kbhbrew is not None:
            os.environ["KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW"] = self._gammel_has_kbhbrew
        else:
            os.environ.pop("KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW", None)
        self._tmpdir.cleanup()

    def _kjor(self, har_kbhbrew):
        if har_kbhbrew:
            os.environ["KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW"] = "1"
        else:
            os.environ.pop("KVERNHAUG_TEST_RECIPE_CARD_HAS_KBHBREW", None)
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertFalse(at.exception, f"Harness kastet exception: {at.exception}")
        return at

    def test_1_ingen_kbhbrew_gir_ingen_advarsel_og_uendret_bryggelogg(self):
        at = self._kjor(har_kbhbrew=False)
        self.assertEqual([w.value for w in at.warning], [])
        self.assertTrue(
            any("Bryggelogg" in (e.label or "") for e in at.expander),
            "Bryggelogg-ekspanderen skal fortsatt finnes uendret uten noen .kbhbrew",
        )

    def test_2_med_kbhbrew_vises_advarsel_men_bryggeloggen_forblir_tilgjengelig(self):
        at = self._kjor(har_kbhbrew=True)
        advarsler = [w.value for w in at.warning]
        self.assertEqual(len(advarsler), 1, f"Forventet nøyaktig én advarsel, fikk: {advarsler}")
        self.assertIn("Bryggdag", advarsler[0])
        self.assertIn(".kbhbrew", advarsler[0])
        # Historisk kompatibilitet -- "advar, ikke skjul": ekspanderen
        # skal fortsatt finnes, ikke fjernes.
        self.assertTrue(
            any("Bryggelogg" in (e.label or "") for e in at.expander),
            "Bryggelogg-ekspanderen skal forbli tilgjengelig selv når et .kbhbrew finnes",
        )


if __name__ == "__main__":
    unittest.main()
