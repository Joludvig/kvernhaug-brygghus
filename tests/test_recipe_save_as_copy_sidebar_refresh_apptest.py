"""
issue #399 -- AppTest-basert regresjonstest for at "💾 Lagre som ny
kopi" faktisk oppdaterer sidebarens lagrede-oppskrifter-liste UTEN at
brukeren må gjøre en manuell nettleser-refresh.

Bekreftet root cause (se PR-beskrivelsen): app.py rendrer
render_sidebar() FØR render_recipe_card(...) i hver scriptkjøring.
ui/sidebar.py::render_sidebar() laster `lagrede_brygg` fra disk KUN ved
sitt eget kall -- FØR "Lagre som ny kopi"-knappen i det hele tatt kan
ha lagret noe denne kjøringen. Den forrige suksess-grenen kalte
`st.toast(...)` uten noen `st.rerun()`, så den nye kopien forble
usynlig i sidebaren helt til en helt urelatert, senere rerun (eller en
manuell refresh) tilfeldigvis kom.

Fiksen speiler NØYAKTIG samme "sett engangsflagg -> st.rerun() ->
konsumer/vis st.success() i render_sidebar() FØR alt annet"-mønster som
issue #391 sin Chief-korrigerte NESTE_VARIANT_SEED_PENDING_NOKKEL (se
ui/sidebar.py sin _LAGRE_SOM_KOPI_SUCCESS_PENDING_NOKKEL-kommentar) --
bevisst INGEN st.toast()/st.success() rendret i SAMME kjøring som selve
st.rerun()-kallet, siden et slikt element aldri rekker å bli synlig for
brukeren (en rerun tegner et helt nytt scripttre).

Disse testene kjører den EKTE brukerstien via full `app.py`-AppTest og
den EKTE `sidebar_recipe_selector`-widgeten (samme prinsipp som
tests/test_app_a4_selector_orientation_apptest.py og
tests/test_kbhbrew_next_variant_e2e_apptest.py) -- en syntetisk harness
som setter session_state direkte ville hoppet forbi akkurat den
sidebar-lastings-rekkefølgen denne regresjonen består av.

Run with:
    py -3 -m unittest tests.test_recipe_save_as_copy_sidebar_refresh_apptest -v
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.recipe_storage as recipe_storage
from modules.recipe import bygg_recipe_object
from modules.kbhbrew_storage import oppdater_brew_lag, opprett_og_lagre_ny_brew
from ui.sidebar import _INGEN_OPPSKRIFT_VALGT, _LAGRE_SOM_KOPI_SUCCESS_PENDING_NOKKEL

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")
_DATA_DIR = os.path.join(_REPO_ROOT, "data")

_BREW_ID = "brew-399-sidebar-refresh"


def _last_master(filnavn):
    with open(os.path.join(_DATA_DIR, filnavn), encoding="utf-8") as f:
        data = json.load(f)
    return {k: v for k, v in data.items() if not k.startswith("_")}


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (samme mønster som
    tests/test_app_a4_selector_orientation_apptest.py)."""
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


def _hovedside_success_tekster(at):
    """Samme prinsipp som tests/test_kbhbrew_next_variant_e2e_apptest.py
    sin _hovedside_success_tekster: `at.success` (uskopert) fanger opp
    suksesselementer uansett hvor i tre-et de rendres -- beviser
    bekreftelsen faktisk finnes, uansett sidebar-tilstand."""
    return [e.value for e in at.success]


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


class TestLagreSomNyKopiSidebarRefreshIssue399(_MedIsolerteOppskrifter):

    # ─── 1-4: kopien lagres ÉN gang, én rerun, synlig/velgbar i sidebar ────

    def test_ny_kopi_lagres_en_gang_og_blir_velgbar_i_sidebar_uten_manuell_refresh(self):
        _lagre_recipe("399 Original")

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("399 Original").run()
        self.assertFalse(at.exception)
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "399 Original")

        at.text_input(key="gjeldende_navn").set_value("399 Ny Kopi").run()
        self.assertFalse(at.exception)

        # Ett eneste .click().run() dekker BEGGE reruns (knappens egen
        # st.rerun(), pluss AppTest sin automatiske gjennomkjøring av
        # den) -- samme prinsipp som allerede bevist for #391 i
        # tests/test_kbhbrew_next_variant_e2e_apptest.py.
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

        # Lagret ÉN gang -- ingen duplikat/annen-navngitt fil.
        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("399 Ny Kopi", lagrede)
        self.assertIn("399 Original", lagrede)
        self.assertEqual(len(lagrede), 2, f"forventet nøyaktig 2 lagrede oppskrifter, fikk: {list(lagrede)}")

        # Den NYE kopien er faktisk velgbar i den EKTE sidebar-widgeten
        # på DENNE rerunen -- ingen ekstra .run() eller sidereload
        # trengs. .select() feiler selv hvis navnet ikke finnes i
        # options-lista, så dette er et direkte, ekte bevis på at
        # sidebaren lastet den nye filen fra disk uten manuell refresh.
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("399 Ny Kopi").run()
        self.assertFalse(at.exception)
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "399 Ny Kopi")

    # ─── 5-6: suksessbekreftelse synlig ETTER rerun, og ett-gangs ──────────

    def test_suksessbekreftelse_synlig_paa_rerunen_etter_lagring_og_er_ett_gangs(self):
        _lagre_recipe("399 Bekreftelse Original")

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("399 Bekreftelse Original").run()
        self.assertFalse(at.exception)

        at.text_input(key="gjeldende_navn").set_value("399 Bekreftelse Kopi").run()
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        meldinger = _hovedside_success_tekster(at)
        self.assertTrue(
            any("399 Bekreftelse Kopi" in m for m in meldinger),
            f"forventet en synlig 'Lagret: ...'-bekreftelse på hovedsiden, fikk: {meldinger}",
        )

        # Engangsflagget er konsumert -- lekker ikke videre.
        with self.assertRaises(KeyError):
            _ = at.session_state[_LAGRE_SOM_KOPI_SUCCESS_PENDING_NOKKEL]

        # En helt urelatert, påfølgende rerun skal IKKE fortsatt vise
        # den samme bekreftelsen -- den er ett-gangs, ikke persistent
        # session-state-visning.
        at.sidebar.selectbox(key="sidebar_recipe_selector").select(_INGEN_OPPSKRIFT_VALGT).run()
        self.assertFalse(at.exception)
        meldinger_etter = _hovedside_success_tekster(at)
        self.assertFalse(
            any("399 Bekreftelse Kopi" in m for m in meldinger_etter),
            f"bekreftelsen skal ikke overleve en senere, urelatert rerun: {meldinger_etter}",
        )

    # ─── 9: navnekollisjon rerunner ALDRI som en falsk suksess ─────────────

    def test_navnekollisjon_rerunner_ikke_og_viser_ingen_falsk_suksess(self):
        _lagre_recipe("399 Kollisjon")

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("399 Kollisjon").run()
        self.assertFalse(at.exception)

        # IKKE endre "Bryggnavn" -- "Lagre som ny kopi" kolliderer da
        # per definisjon med kildeoppskriften som allerede ligger på
        # disk (bloker_ved_navnekollisjon=True).
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception, f"app.py kastet exception: {at.exception}")

        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(
            any("399 Kollisjon" in m for m in feilmeldinger),
            f"forventet en kollisjonsfeilmelding, fikk: {feilmeldinger}",
        )
        # Ingen falsk "Lagret: ..."-suksessbekreftelse for kollisjonen
        # (appen kan ha andre, helt urelaterte st.success()-elementer fra
        # andre paneler på en fersk rendering -- sjekker derfor spesifikt
        # etter en "Lagret: 399 Kollisjon"-tekst, ikke fravær av ALLE
        # suksesselementer).
        self.assertFalse(
            any("Lagret: 399 Kollisjon" in m for m in _hovedside_success_tekster(at)),
            _hovedside_success_tekster(at),
        )
        # Ingen duplikatfil skrevet -- fortsatt kun den ene originalen.
        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertEqual(len(lagrede), 1)
        self.assertEqual(lagrede["399 Kollisjon"]["batch_size"], 20.0)
        # Engangsflagget skal aldri ha blitt satt ved en avvist lagring.
        with self.assertRaises(KeyError):
            _ = at.session_state[_LAGRE_SOM_KOPI_SUCCESS_PENDING_NOKKEL]

    # ─── 7: fersk originRecipeId for en ordinær ny kopi ────────────────────

    def test_ordinaer_ny_kopi_far_fersk_origin_recipe_id(self):
        _lagre_recipe("399 Origin Original")
        # Vanlige lagringer minter ALDRI selv en originRecipeId (App sin
        # "aldri implisitt"-regel, §3.2) -- kilden har derfor bevisst
        # INGEN verdi her, kun kopien skal få en fersk en.
        kilde_id = recipe_storage.hent_alle_oppskrifter()["399 Origin Original"].get("originRecipeId")
        self.assertFalse(kilde_id)

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("399 Origin Original").run()
        at.text_input(key="gjeldende_navn").set_value("399 Origin Kopi").run()
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        kopi_id = lagrede["399 Origin Kopi"]["originRecipeId"]
        self.assertTrue(kopi_id)
        self.assertNotEqual(kopi_id, kilde_id)
        # Kilden er byte-for-byte uendret (fortsatt uten egen id).
        self.assertEqual(lagrede["399 Origin Original"].get("originRecipeId"), kilde_id)

    # ─── 8: frossen neste-variant-origin overlever den nye flyten uendret ──

    def test_frossen_neste_variant_origin_overlever_lagre_som_ny_kopi(self):
        # Samme oppsett som den bevisste, allerede-grønne
        # tests/test_kbhbrew_next_variant_e2e_apptest.py::
        # _seed_kilde_og_brew() -- en ekte kildebrygg trenger en EKSPLISITT
        # mintet originRecipeId (via sikre_origin_recipe_id(), samme
        # eksport-mekanisme App selv bruker) FØR brygget fryses, siden
        # vanlige lagringer aldri minter en selv.
        malt_db = _last_master("master_malt.json")
        humle_db = _last_master("master_humle_v2.json")
        gjaer_db = _last_master("master_gjaer_v2.json")
        malt_id = next(iter(malt_db))
        gjaer_id = next(iter(gjaer_db))

        kilde = bygg_recipe_object(
            "399 NV Kildebrygg", 20.0, 0.75,
            [{"id": malt_id, "mengde": 5.0}], [],
            gjaer_id, 1.050, 1.012, 5.0, 20, 8, {},
        )
        filnavn = recipe_storage.lagre_oppskrift(kilde)
        kilde_origin_id = recipe_storage.sikre_origin_recipe_id(filnavn)
        self.assertTrue(kilde_origin_id)
        kilde["originRecipeId"] = kilde_origin_id

        equipment = {
            "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
            "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
            "default_boil_time_min": 60,
        }
        opprett_og_lagre_ny_brew(
            kilde, malt_db, humle_db, gjaer_db, equipment,
            {"og": 1.050, "fg": 1.012, "abv": 5.0},
            recipe_id=filnavn, brew_id=_BREW_ID,
        )
        oppdater_brew_lag(_BREW_ID, learning={"nextTime": "Litt mer humle neste gang."})

        at = AppTest.from_file(_APP_PY, default_timeout=30)
        at.run()
        self.assertFalse(at.exception)

        at.selectbox(key="kbhbrew_historikk_valgt_id").select(_BREW_ID).run()
        self.assertFalse(at.exception)
        at.button(key=f"kbhbrew_hist_neste_variant_btn::{_BREW_ID}").click().run()
        self.assertFalse(at.exception)

        fersk_id = _ss(at, "_aktiv_kbh_origin_recipe_id")
        self.assertTrue(fersk_id)
        self.assertNotEqual(fersk_id, kilde_origin_id)

        at.text_input(key="gjeldende_navn").set_value("399 NV Kildebrygg v2").run()
        at.button(key="lagre_ny_kopi_btn").click().run()
        self.assertFalse(at.exception)

        lagrede = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("399 NV Kildebrygg v2", lagrede)
        # Den frosne seed-IDen overlevde -- IKKE en ny, tredje UUID
        # mintet av den nye rerun/suksess-flyten.
        self.assertEqual(lagrede["399 NV Kildebrygg v2"]["originRecipeId"], fersk_id)
        self.assertNotEqual(lagrede["399 NV Kildebrygg v2"]["originRecipeId"], kilde_origin_id)

        # Og den nye kopien er selvsagt velgbar i sidebaren, samme bevis
        # som hovedtesten over.
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("399 NV Kildebrygg v2").run()
        self.assertFalse(at.exception)
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "399 NV Kildebrygg v2")


if __name__ == "__main__":
    unittest.main()
