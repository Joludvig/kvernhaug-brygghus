"""
App A4-3 (issue #246) -- AppTest-basert regresjonstest for
selector-orienteringsfiksen i den ratifiserte A4-workflow-polish-
preflighten (docs/development/app_a4_workflow_polish_preflight.md).

Bekreftet root cause (se reproduksjonsscriptet denne testen speiler):
A3-4 (issue #237, ui/recipe_card.py) setter allerede
_last_loaded_recipe/_last_loaded_recipe_file korrekt til den NYE
identiteten FØR sin egen st.rerun(). Men selve
`sidebar_recipe_selector`-widgetens BUNDNE verdi (ui/sidebar.py) er
fortsatt det GAMLE navnet på den kommende rerunen. Siden det gamle
navnet ikke lenger finnes i den ferske `lagrede_brygg`-listen (filen
er omdøpt/arkivert), faller Streamlit selv tilbake til plassholder-
indeksen for widgeten -- og sidebarens EGEN, allerede eksisterende
"elif valgt_lagret_navn == _INGEN_OPPSKRIFT_VALGT"-gren (der for et
BEVISST plassholder-valg) tolker dette som nettopp det, og SLETTER
_last_loaded_recipe/_last_loaded_recipe_file vi nettopp satte -- ikke
bare en kosmetisk visningsfeil, men et reelt identitetstap (bl.a.
forsvinner "💾 Lagre endringer"-knappen helt på neste rendering, siden
den kun vises når `_last_loaded_recipe` er satt).

Fiksen speiler EKSAKT samme engangs-UI-koordineringsmønster som issue
#242 (`_nullstill_oppskrift_selector_neste_render`, se
ui/sidebar.py), men i motsatt retning: `_recipe_card.py` setter
`_sett_oppskrift_selector_neste_render` til det NYE navnet rett før
sin egen A3-4-rerun; `render_sidebar()` konsumerer flagget FØR
selectboksen instansieres, validerer at navnet faktisk finnes i den
FERSKE `lagrede_brygg`-dicten, og setter selectboksens bundne
widget-state direkte -- ingen ny identitetsmodell, kun UI-koordinering
av en EKSISTERENDE widget.

Disse testene kjører den EKTE brukerstien via full `app.py`-AppTest og
den EKTE `sidebar_recipe_selector`-widgeten (aldri en syntetisk
harness som setter `_last_loaded_recipe` direkte -- det ville hoppet
forbi akkurat den widget-state-mismatchen denne regresjonen består av,
se advarselen i tests/test_app_a3_state_orientation_apptest.py sin
egen preflight-referanse). test_1 MÅ feile på uendret master (før
denne fiksen) og bestå etter fiksen.

Kjøres med:
    py -3 -m unittest tests.test_app_a4_selector_orientation_apptest -v
"""
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.recipe_storage as recipe_storage
from modules.recipe import bygg_recipe_object
from ui.sidebar import _INGEN_OPPSKRIFT_VALGT, _SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (samme mønster som
    tests/test_app_a3_state_orientation_apptest.py)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


def _lagre_recipe(navn, batch=20.0):
    recipe = bygg_recipe_object(
        navn, batch, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
    )
    recipe_storage.lagre_oppskrift(recipe)
    return recipe


class _MedIsolerteOppskrifter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        self._tmpdir.cleanup()


class TestA43OmdopingReorientererSelector(_MedIsolerteOppskrifter):

    # ─── 1: omdøping + lagring -> selector følger med til det nye navnet ──

    def test_1_omdoping_og_lagring_reorienterer_selector_til_nytt_navn(self):
        _lagre_recipe("A4-3 Original")

        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Original").run()
        self.assertFalse(at.exception)
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Original")
        gammelt_filnavn = _ss(at, "_last_loaded_recipe_file")

        at.text_input(key="gjeldende_navn").set_value("A4-3 Omdopt").run()
        self.assertFalse(at.exception)

        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lagring: {at.exception}")

        # Identiteten peker på det NYE navnet ...
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Omdopt")
        nytt_filnavn = _ss(at, "_last_loaded_recipe_file")
        self.assertIsNotNone(nytt_filnavn)
        self.assertNotEqual(nytt_filnavn, gammelt_filnavn)
        self.assertEqual(_ss(at, "gjeldende_navn"), "A4-3 Omdopt")

        # ... OG selectboksen (den EKTE widgeten) er reorientert til å
        # vise NØYAKTIG det samme -- ikke plassholderen, ikke det gamle
        # navnet, ikke en annen lagret oppskrift.
        selector_verdi = at.sidebar.selectbox(key="sidebar_recipe_selector").value
        self.assertEqual(selector_verdi, "A4-3 Omdopt")
        self.assertNotEqual(selector_verdi, "A4-3 Original")
        self.assertNotEqual(selector_verdi, _INGEN_OPPSKRIFT_VALGT)

        # Det gamle navnet finnes ikke lenger blant de lagrede oppskriftene.
        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertNotIn("A4-3 Original", lagrede)
        self.assertIn("A4-3 Omdopt", lagrede)

        # Engangsflagget er konsumert -- lekker ikke videre til neste rendering.
        with self.assertRaises(KeyError):
            _ = at.session_state[_SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER]

    # ─── 2: uendret navn -> ingen unødvendig orienteringschurn ─────────

    def test_2_uendret_navn_lagring_selector_uendret_ingen_churn(self):
        _lagre_recipe("A4-3 Uendret")

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Uendret").run()
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), "a4-3_uendret.json")

        # Lagre uten å endre "Bryggnavn" -- ingen A3-4-rerun forventes.
        at.button(key="lagre_endringer_btn").click().run()
        self.assertFalse(at.exception)

        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Uendret")
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), "a4-3_uendret.json")
        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").value, "A4-3 Uendret",
        )
        # Engangsflagget skal aldri ha blitt satt for et navneUENDRET lagre-klikk.
        with self.assertRaises(KeyError):
            _ = at.session_state[_SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER]

    # ─── 3: manuelt bytte til en annen lagret oppskrift fungerer uendret ──

    def test_3_manuelt_bytte_til_annen_lagret_oppskrift_fungerer(self):
        _lagre_recipe("A4-3 Bytte Kilde")
        _lagre_recipe("A4-3 Bytte Mål")

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Bytte Kilde").run()
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Bytte Kilde")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Bytte Mål").run()
        self.assertFalse(at.exception)
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Bytte Mål")
        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").value, "A4-3 Bytte Mål",
        )

    # ─── 4: eksplisitt plassholder-valg rydder identitet uendret ───────

    def test_4_plassholder_valg_rydder_identitet_uendret(self):
        _lagre_recipe("A4-3 Plassholder")

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Plassholder").run()
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Plassholder")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select_index(0).run()
        self.assertFalse(at.exception)
        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").value, _INGEN_OPPSKRIFT_VALGT,
        )
        with self.assertRaises(KeyError):
            _ = at.session_state["_last_loaded_recipe"]
        with self.assertRaises(KeyError):
            _ = at.session_state["_last_loaded_recipe_file"]

    # ─── 5: "Lagre som ny kopi" -- kopien blir ALDRI auto-valgt ────────

    def test_5_lagre_som_ny_kopi_ny_kopi_ikke_auto_valgt(self):
        _lagre_recipe("A4-3 Kopi Original")

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Kopi Original").run()
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Kopi Original")
        opprinnelig_filnavn = _ss(at, "_last_loaded_recipe_file")

        # Naviger navnefeltet til et NYTT navn, men trykk "Lagre som ny
        # kopi" (IKKE "Lagre endringer") -- A4-3-mekanismen skal ikke
        # være koblet til denne knappen i det hele tatt.
        at.text_input(key="gjeldende_navn").set_value("A4-3 Kopi Ny").run()
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

        # Brukeren fortsetter å redigere ORIGINALEN -- uendret identitet.
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Kopi Original")
        self.assertEqual(_ss(at, "_last_loaded_recipe_file"), opprinnelig_filnavn)
        # Selectboksen forblir på originalen -- den nye kopien er IKKE auto-valgt.
        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").value, "A4-3 Kopi Original",
        )
        # Kopien finnes likevel på disk, tilgjengelig i listen.
        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("A4-3 Kopi Ny", lagrede)

    # ─── 6: ren rendering / urelatert rerun skriver ingenting nytt ────

    def test_6_ren_rendering_skriver_ingen_nye_oppskrifter(self):
        _lagre_recipe("A4-3 Uberørt")
        antall_foer = len(recipe_storage.hent_alle_oppskrifter())

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.run()  # urelatert ekstra rendering -- ingen widget-interaksjon
        self.assertFalse(at.exception)

        self.assertEqual(len(recipe_storage.hent_alle_oppskrifter()), antall_foer)
        with self.assertRaises(KeyError):
            _ = at.session_state[_SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER]

    # ─── 8: begge engangsflagg satt samtidig -> deterministisk, dokumentert utfall ──

    def test_8_begge_engangsflagg_samtidig_nullstilling_vinner(self):
        _lagre_recipe("A4-3 Skulle Vunnet")
        _lagre_recipe("A4-3 Skal Ikke Vinne")

        at = AppTest.from_file(_APP_PY)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("A4-3 Skulle Vunnet").run()
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "A4-3 Skulle Vunnet")

        # Denne kombinasjonen kan ikke oppstå via ekte brukerflyter (se
        # modulens docstring/ui/sidebar.py sin kommentar), men testes
        # likevel direkte for å bevise den dokumenterte, deterministiske
        # oppløsningen: #242 sin plassholder-nullstilling vinner ALLTID
        # over A4-3 sin navngitte reorientering.
        at.session_state["_nullstill_oppskrift_selector_neste_render"] = True
        at.session_state[_SETT_OPPSKRIFT_SELECTOR_NESTE_RENDER] = "A4-3 Skal Ikke Vinne"
        at.run()
        self.assertFalse(at.exception)

        self.assertEqual(
            at.sidebar.selectbox(key="sidebar_recipe_selector").value, _INGEN_OPPSKRIFT_VALGT,
        )
        with self.assertRaises(KeyError):
            _ = at.session_state["_last_loaded_recipe"]


class TestA43DemoModeUberoert(unittest.TestCase):

    # ─── 7: DEMO_MODE -- "Lagre endringer" utilgjengelig, ingen A4-3-mekanisme kan nås ──

    def test_7_demo_mode_ingen_lagre_endringer_knapp(self):
        import subprocess
        import sys

        script = (
            "import logging\n"
            "logging.getLogger('streamlit').setLevel(logging.ERROR)\n"
            "from streamlit.testing.v1 import AppTest\n"
            "at = AppTest.from_file('app.py')\n"
            "at.run()\n"
            "assert not at.exception, at.exception\n"
            "knapper = [b.key for b in at.button]\n"
            "assert 'lagre_endringer_btn' not in knapper, knapper\n"
            "print('OK')\n"
        )
        env = dict(os.environ)
        env["DEMO_MODE"] = "1"
        env.pop("KVERNHAUG_RECIPES_DIR", None)
        resultat = subprocess.run(
            [sys.executable, "-c", script], cwd=_REPO_ROOT, env=env,
            capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(resultat.returncode, 0, resultat.stdout + resultat.stderr)
        self.assertIn("OK", resultat.stdout)


if __name__ == "__main__":
    unittest.main()
