"""
Ende-til-ende UI-regresjonstest (samme mønster som
tests/test_real_app_process_flow.py -- kjører den EKTE app.py via
streamlit.testing.v1.AppTest, ikke en proxy/testvert): bekrefter at en
oppskrift med en humle hvis egen koketid overstiger total koketid faktisk
vises som et varsel i BÅDE Bryggemåte-panelet og Bryggedag-panelet, og at
"🖨️ Generer Bryggedagsark"-knappen er låst til brukeren har bekreftet
avviket eksplisitt.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")


def _finn_avvik_bekreftelse_checkbox(at):
    """Bekreftelses-checkboxens nøkkel er BEVISST avledet av en signatur
    på oppskrift + koketid + avvikende humler (se ui/brewday_panel.py),
    ikke en fast nøkkel -- så testene finner den ved nøkkel-PREFIKS i
    stedet for en eksakt nøkkel. Returnerer None hvis ingen slik
    checkbox er rendret akkurat nå."""
    for cb in at.checkbox:
        if cb.key and cb.key.startswith("bd_bekreft_humletid_avvik::"):
            return cb
    return None


class TestHumletidOverKoketidIEktApp(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        # 90 min humle, ingen prosessprofil valgt ennå (=> standard 60 min
        # koketid siden ingen pilsnermalt er brukt) -- akkurat scenarioet
        # fra feilrapporten: UI viste tilsetning ved kokestart samtidig
        # som en umulig 90-minutters IBU ble beregnet.
        recipe = bygg_recipe_object(
            "E2E Humletid Over Koketid", 20.0, 0.75,
            [{"id": "vienna", "mengde": 5.0}],
            [{"id": "magnum", "gram": 20, "tid": 90}],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_varsel_vises_og_eksport_er_last_til_bekreftet(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Humletid Over Koketid").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        # Bekreft utgangstilstanden: 90 min humle, standard 60 min koketid.
        self.assertEqual(st_boil := at.session_state["prosess_boil_minutes"], 60)
        self.assertEqual(at.session_state["valgt_humle"][0]["tid"], 90)

        # === Bryggemåte-panelet: varsel om umulig humletid ===
        varsel_tekster = " ".join(w.value for w in at.warning)
        self.assertIn("koketid", varsel_tekster.lower())
        self.assertIn("Magnum", varsel_tekster)

        # === Bryggedag-panelet: eksportknappen er låst ===
        eksport_knapp = at.button(key="brewday_print_btn")
        self.assertTrue(eksport_knapp.disabled, "Eksportknappen skal være låst før avviket er bekreftet")

        bekreft_checkbox = _finn_avvik_bekreftelse_checkbox(at)
        self.assertIsNotNone(bekreft_checkbox, "Fant ingen bekreftelses-checkbox for avviket")
        self.assertFalse(bekreft_checkbox.value)

        bekreft_checkbox.check().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved bekreftelse: {at.exception}")

        eksport_knapp = at.button(key="brewday_print_btn")
        self.assertFalse(eksport_knapp.disabled, "Eksportknappen skal låses opp etter eksplisitt bekreftelse")

    def test_ingen_varsel_eller_lasing_naar_humletid_er_innenfor_koketiden(self):
        import modules.recipe_storage as recipe_storage
        ok_recipe = bygg_recipe_object(
            "E2E Humletid OK", 20.0, 0.75,
            [{"id": "vienna", "mengde": 5.0}],
            [{"id": "magnum", "gram": 20, "tid": 60}],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(ok_recipe)

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Humletid OK").run()
        self.assertFalse(at.exception)

        varsel_tekster = " ".join(w.value for w in at.warning)
        self.assertNotIn("koketid", varsel_tekster.lower())

        eksport_knapp = at.button(key="brewday_print_btn")
        self.assertFalse(eksport_knapp.disabled)
        # Bekreftelses-checkboxen skal ikke engang rendres når det ikke
        # finnes noe avvik å bekrefte.
        self.assertIsNone(_finn_avvik_bekreftelse_checkbox(at))


class TestBekreftelseFolgerIkkeMedVedByttMellomUgyldigePlaner(unittest.TestCase):
    """Regresjonstest for at bekreftelses-checkboxens nøkkel er avledet av
    oppskrift+koketid+avvikende humler, ikke fast: en bekreftelse gitt for
    ÉN oppskrift skal ALDRI "følge med" til en ANNEN oppskrift ved et
    direkte bytte, selv om begge har et (forskjellig) humletidsavvik."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        recipe_storage.lagre_oppskrift(bygg_recipe_object(
            "E2E Avvik A", 20.0, 0.75,
            [{"id": "vienna", "mengde": 5.0}],
            [{"id": "magnum", "gram": 20, "tid": 90}],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        ))
        recipe_storage.lagre_oppskrift(bygg_recipe_object(
            "E2E Avvik B", 20.0, 0.75,
            [{"id": "vienna", "mengde": 5.0}],
            [{"id": "tettnang", "gram": 20, "tid": 75}],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        ))

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_direkte_bytte_mellom_to_ugyldige_planer_krever_ny_bekreftelse(self):
        at = AppTest.from_file(_APP_PY)
        at.run()

        # === Last A, bekreft avviket, lås opp eksport ===
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Avvik A").run()
        self.assertFalse(at.exception)
        cb_a = _finn_avvik_bekreftelse_checkbox(at)
        self.assertIsNotNone(cb_a)
        self.assertFalse(cb_a.value)
        cb_a.check().run()
        self.assertFalse(at.button(key="brewday_print_btn").disabled, "Eksport skal være låst opp for A etter bekreftelse")

        # === Direkte bytte til B (også et avvik, men et ANNET) ===
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Avvik B").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved bytte: {at.exception}")

        # B sitt avvik skal vises (annen humle, annen tid).
        varsel_tekster = " ".join(w.value for w in at.warning)
        self.assertIn("Tettnang", varsel_tekster)

        # Eksport skal IKKE lenger være låst opp -- A sin bekreftelse må
        # ALDRI gjelde for B sitt (forskjellige) avvik.
        self.assertTrue(
            at.button(key="brewday_print_btn").disabled,
            "A sin bekreftelse fulgte feilaktig med til B",
        )
        cb_b = _finn_avvik_bekreftelse_checkbox(at)
        self.assertIsNotNone(cb_b)
        self.assertFalse(cb_b.value, "B sin bekreftelses-checkbox skal starte ubekreftet")
        self.assertNotEqual(cb_a.key, cb_b.key, "A og B skal ha ULIKE bekreftelsesnøkler")


if __name__ == "__main__":
    unittest.main()
