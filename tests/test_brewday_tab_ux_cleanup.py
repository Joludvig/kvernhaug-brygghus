"""
Regresjonstester for Brewday Tab UX Cleanup V1 (MUST 1-5, Steg F13).

Dette var en ren layout-/struktur-opprydding av "🧪 Bryggdag"-fanen:
utstyrsprofilen flyttet til "🔧 Verktøy", vannplanleggingen
(kildevann/målprofil/vannmengder/salter/fordeling/sluttprofil/varsler/
syrer) lagt bak én lukket expander ("💧 Vannbehandling (forberedelse)"),
meske-pH holdt synlig UTENFOR den expanderen, de tre expanderne i
ui/process_panel.py lukket som standard, den dupliserte vannmengde-
metric-raden erstattet med en kompakt caption, og de konkurrerende
seksjonsnummereringene ("1. Kildevann" osv.) fjernet.

INGEN beregningslogikk, session_state-kontrakt eller kjørerekkefølge er
endret -- disse testene bekrefter nettopp DET, ikke ny funksjonalitet.

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
_WATER_RETURN_APP_PY = os.path.join(_REPO_ROOT, "tests", "_water_panel_return_app.py")


class TestVannSnapshotOgKjorerekkefolge(unittest.TestCase):
    """A: render_water_panel() setter fortsatt samme vann-snapshots etter
    at forberedelsesinnholdet ligger i en lukket expander.
    C: Bryggedag/eksport mottar oppdaterte vanndata i SAMME rerun --
    den harde water->brewday-kjørerekkefølgen i app.py er bevart."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        import modules.recipe_storage as recipe_storage
        self._malt = [{"id": "weyermann_pilsner", "mengde": 5.0}]
        self._hops = [{"id": "magnum_de", "gram": 20, "tid": 60}]
        recipe = bygg_recipe_object(
            "E2E Brewday UX Cleanup", 20.0, 0.75, self._malt, self._hops,
            "safale_us_05", 1.048, 1.010, 5.0, 20, 6, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_kildevalg_og_saltforslag_naar_frem_til_snapshot_selv_om_lukket(self):
        """Widgetene ("Velg kildevann", "Beregn saltforslag") ligger nå
        inne i en expander med expanded=False -- AppTest må fortsatt
        kunne nå dem via key (Streamlit kjører expander-innholdet
        uavhengig av om det er visuelt åpent), og resultatet må fortsatt
        havne i aktiv_vannbehandling/aktiv_vannmaal_snapshot slik det
        gjorde før oppryddingen."""
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Brewday UX Cleanup").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        at.selectbox(key="vann_kilde_valgt_id").select("jordalsvatnet_2025").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved kildevalg: {at.exception}")
        self.assertEqual(at.session_state["vann_kilde_valgt_id"], "jordalsvatnet_2025")
        self.assertEqual(at.session_state["aktiv_vannkilde_snapshot"]["water_id"], "jordalsvatnet_2025")

        at.button(key="vann_beregn_forslag_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved saltforslag: {at.exception}")
        forslag = at.session_state["vann_salter"]
        self.assertTrue(forslag, "Solveren foreslo ingen salter -- uendret oppførsel forventet.")

        behandling = at.session_state["aktiv_vannbehandling"]
        self.assertEqual(behandling["vannkilde_id"], "jordalsvatnet_2025")
        self.assertTrue(behandling["salter"], "aktiv_vannbehandling fikk ikke med saltforslaget.")
        self.assertEqual(
            {s["salt_id"] for s in behandling["salter"]},
            {s["salt_id"] for s in forslag},
        )

    def test_eksport_mottar_oppdaterte_vanndata_i_samme_rerun(self):
        """water->brewday-rekkefølgen (app.py: render_water_panel() FØR
        render_brewday_panel()) er en hard invariant -- eksporten leser
        aktiv_vannkilde_snapshot/aktiv_vannbehandling som render_water_panel
        satte i AKKURAT DENNE kjøringen, ikke ett rerun forsinket."""
        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Brewday UX Cleanup").run()
        self.assertFalse(at.exception)

        at.selectbox(key="vann_kilde_valgt_id").select("jordalsvatnet_2025").run()
        at.button(key="vann_beregn_forslag_btn").click().run()
        self.assertFalse(at.exception)

        # Samme rerun-prinsipp som test_water_recipe_integration.py: klikk
        # den ekte eksportknappen og bekreft at HELE kjøringen (inkl.
        # render_brewday_html() med vann-snapshotene fra DENNE kjøringen)
        # går uten exception.
        at.button(key="brewday_print_btn").click().run()
        self.assertFalse(at.exception, f"Eksport feilet: {at.exception}")

        # Vann-snapshotene brukt i eksporten skal fortsatt vise valget --
        # de ble ikke "hengende igjen" fra et tidligere rerun.
        self.assertEqual(at.session_state["aktiv_vannkilde_snapshot"]["water_id"], "jordalsvatnet_2025")
        self.assertTrue(at.session_state["aktiv_vannbehandling"]["salter"])


class TestVannPanelReturkontrakt(unittest.TestCase):
    """B: render_water_panel() returnerer fortsatt nøyaktig de fire
    forventede nøklene -- uendret på tvers av flere reruns, selv om
    forberedelsesinnholdet nå ligger i en lukket expander."""

    def test_returnerer_samme_fire_nokler_over_flere_reruns(self):
        at = AppTest.from_file(_WATER_RETURN_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"_water_panel_return_app.py kastet exception: {at.exception}")
        at.run()  # simulerer en ekte rerun (f.eks. en widget-interaksjon)
        self.assertFalse(at.exception)

        forventede_nokler = {
            "water_source_profile", "water_target_profile",
            "water_treatment", "water_measurements",
        }
        for i in (1, 2):
            resultat = at.session_state[f"_test_water_return_{i}"]
            self.assertEqual(set(resultat.keys()), forventede_nokler,
                             f"Uventet returkontrakt ved rerun {i}: {sorted(resultat.keys())}")


class TestUtstyrsprofilFortsattTilgjengeligIVerktoy(unittest.TestCase):
    """D: Utstyrsprofilen er fortsatt tilgjengelig/fungerer etter at
    render_equipment_panel() ble flyttet fra Bryggdag- til Verktøy-fanen
    i app.py (MUST 1). Klikker ALDRI "💾 Lagre utstyrsprofil" -- denne
    testen skal ikke skrive til den ekte data/equipment.json."""

    def test_utstyrswidget_finnes_og_kan_redigeres_uten_feil(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        eff_widgets = [w for w in at.number_input if w.key == "eq_efficiency"]
        self.assertEqual(len(eff_widgets), 1, "Fant ikke (eller fant duplikat av) eq_efficiency-widgeten.")

        ny_verdi = eff_widgets[0].value + 1 if eff_widgets[0].value < 99 else eff_widgets[0].value - 1
        at.number_input(key="eq_efficiency").set_value(ny_verdi).run()
        self.assertFalse(at.exception, f"Redigering av utstyrsprofilen feilet: {at.exception}")
        self.assertEqual(at.number_input(key="eq_efficiency").value, ny_verdi)


if __name__ == "__main__":
    unittest.main()
