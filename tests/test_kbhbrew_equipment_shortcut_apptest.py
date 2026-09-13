"""
App A4-2 (issue #244) -- fjerner Bryggdag sin første-gangs-dødvekt uten å
svekke den eksisterende utstyrs-sikkerhetssperren
(modules.equipment.equipment_kilde_er_lagret()).

Uendret sperre: et klikk på "▶️ Start nytt brygg" uten en bekreftet
utstyrsprofil viser fortsatt den EKSISTERENDE feilmeldingen og oppretter
fortsatt INGEN .kbhbrew. Nytt i denne PR-en: SAMME feilmelding følges nå
også av en eksplisitt "✅ Bruk og bekreft standardutstyr"-knapp
(ui/kbhbrew_panel.py::_VIS_UTSTYR_SNARVEI_NOKKEL) som lagrer nøyaktig
last_equipment() via den eksisterende lagre_equipment() -- samme
skrivevei som "💾 Lagre utstyrsprofil" i ui/equipment_panel.py -- uten å
opprette noe brygg. Selve flagget lever i session_state (ikke bare
nestet inne i "if st.button('Start nytt brygg')") fordi et klikk på
bekreftelsesknappen trigger en NY rendering der Start-knappens EGEN
st.button() på nytt returnerer False (samme fallgruve/løsning som
_nullstill_oppskrift_selector_neste_render i ui/sidebar.py, issue #242).

Kjøres med:
    py -3 -m unittest tests.test_kbhbrew_equipment_shortcut_apptest -v
"""
import json
import logging
import os
import subprocess
import sys
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.equipment as equipment
import modules.kbhbrew_storage as kbhbrew_storage
import modules.recipe_storage as recipe_storage
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_APP_PY = os.path.join(_REPO_ROOT, "app.py")
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_create_harness.py")

_TILPASSET_EQUIPMENT = {
    "efficiency": 0.68, "boil_off_l_per_hour": 3.0, "grain_absorption_l_per_kg": 0.9,
    "dead_space_l": 1.5, "mash_ratio_l_per_kg": 3.0, "kettle_capacity_l": 50.0,
    "default_boil_time_min": 90,
}


class _MedIsolertUtstyrOgOppskrifter(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_recipes_dir = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name
        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        self._equipment_file = os.path.join(self._tmpdir.name, "equipment.json")
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._equipment_file
        # Filen finnes bevisst IKKE ennå -- happy-path-testen (8) oppretter
        # den selv med en TILPASSET profil før rendring.

    def tearDown(self):
        if self._gammel_recipes_dir is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_recipes_dir
        if self._gammel_equipment_file is None:
            os.environ.pop("KVERNHAUG_EQUIPMENT_FILE", None)
        else:
            os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._gammel_equipment_file
        self._tmpdir.cleanup()


class TestUtstyrssnarveiHarness(_MedIsolertUtstyrOgOppskrifter):
    """Isolert test av selve render_kbhbrew_create_panel() via den
    eksisterende minimale harnessen (samme som
    tests/test_kbhbrew_create_panel_apptest.py)."""

    def _ny_apptest(self):
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _knapp(self, at, key):
        knapper = [b for b in at.button if b.key == key]
        self.assertEqual(
            len(knapper), 1,
            f"Fant ikke akkurat én knapp med key={key!r}: {[b.key for b in at.button]}",
        )
        return knapper[0]

    # ─── 1+2: ren rendring skriver ingenting ────────────────────────────

    def test_1_ren_rendring_oppretter_ingen_equipment_fil_og_ingen_brew(self):
        at = self._ny_apptest()
        self.assertFalse(os.path.exists(self._equipment_file))
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        snarvei = [b for b in at.button if b.key == "kbhbrew_bekreft_standardutstyr_btn"]
        self.assertEqual(snarvei, [], "Snarveien skal IKKE vises før 'Start nytt brygg' er klikket.")

    # ─── 3: første Start-klikk uten profil -- sperre + snarvei, ingen brew

    def test_3_start_uten_profil_viser_sperre_og_snarvei_ingen_brew(self):
        at = self._ny_apptest()
        self._knapp(at, "kbhbrew_start_ny_brew_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("bekreftet utstyrsprofil" in m for m in feilmeldinger))
        self._knapp(at, "kbhbrew_bekreft_standardutstyr_btn")  # kaster hvis ikke akkurat én
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertFalse(os.path.exists(self._equipment_file))

    # ─── 4+5: bekreftelsesklikk skriver default-profilen, ingen brew ───

    def test_4_5_bekreftelsesklikk_skriver_default_profil_ingen_brew_sperre_faller(self):
        at = self._ny_apptest()
        self._knapp(at, "kbhbrew_start_ny_brew_btn").click().run()
        self._knapp(at, "kbhbrew_bekreft_standardutstyr_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved bekreftelse: {at.exception}")

        self.assertTrue(os.path.exists(self._equipment_file))
        with open(self._equipment_file, "r", encoding="utf-8") as f:
            lagret = json.load(f)
        self.assertEqual(lagret, equipment.DEFAULTS)
        self.assertEqual(equipment.last_equipment(), equipment.DEFAULTS)
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {}, "Bekreftelse skal ALDRI opprette et brygg.")
        self.assertTrue(equipment.equipment_kilde_er_lagret())

        # AppTest sin .click().run() prosesserer selve klikket (skriving +
        # flagg-popping skjedde allerede -- bekreftet over), men den
        # returnerte treet reflekterer FORTSATT det AVBRUTTE scriptet fra
        # akkurat det passet (der bekreftelsesknappen alt var rendret FØR
        # selve st.rerun()-kallet). Et EKSTRA eksplisitt at.run() -- uten
        # noen ny widget-interaksjon -- gjenspeiler den ferske rendringen
        # (samme sekvens en ekte bruker uansett ville sett i nettleseren
        # etter Streamlit sin egen, umiddelbare rerun).
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved påfølgende rerun: {at.exception}")
        gjenvaerende_snarvei = [b for b in at.button if b.key == "kbhbrew_bekreft_standardutstyr_btn"]
        self.assertEqual(gjenvaerende_snarvei, [], "Snarveien skal forsvinne så snart profilen er bekreftet.")

    # ─── 6+7: bruker må selv klikke Start på nytt -- normal opprettelse ─

    def test_6_7_eksplisitt_start_etter_bekreftelse_oppretter_brygg_normalt(self):
        at = self._ny_apptest()
        self._knapp(at, "kbhbrew_start_ny_brew_btn").click().run()
        self._knapp(at, "kbhbrew_bekreft_standardutstyr_btn").click().run()
        self.assertEqual(
            kbhbrew_storage.hent_alle_brews(), {},
            "Ingen brew skal finnes før det andre, eksplisitte Start-klikket.",
        )

        self._knapp(at, "kbhbrew_start_ny_brew_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved opprettelse: {at.exception}")

        brews = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(len(brews), 1)
        brew = next(iter(brews.values()))
        self.assertEqual(brew["snapshot"]["recipe"]["navn"], "Harness Pilsner")
        self.assertEqual(brew["snapshot"]["equipment"], equipment.DEFAULTS)

    # ─── 8: eksisterende, TILPASSET profil -- normal flyt, ingen overskriving

    def test_8_eksisterende_tilpasset_profil_uendret_av_normal_flyt(self):
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            json.dump(_TILPASSET_EQUIPMENT, f)

        at = self._ny_apptest()
        snarvei = [b for b in at.button if b.key == "kbhbrew_bekreft_standardutstyr_btn"]
        self.assertEqual(snarvei, [], "Snarveien skal ikke vises når en gyldig profil allerede er lagret.")

        self._knapp(at, "kbhbrew_start_ny_brew_btn").click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak: {at.exception}")

        brews = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(len(brews), 1)
        brew = next(iter(brews.values()))
        self.assertEqual(brew["snapshot"]["equipment"], _TILPASSET_EQUIPMENT)

        with open(self._equipment_file, "r", encoding="utf-8") as f:
            fortsatt_lagret = json.load(f)
        self.assertEqual(
            fortsatt_lagret, _TILPASSET_EQUIPMENT,
            "Normal flyt/snarvei skal ALDRI overskrive en eksisterende, tilpasset profil.",
        )


class TestUtstyrssnarveiIFullApp(_MedIsolertUtstyrOgOppskrifter):
    """9+10 krever en full app.py-rendring: Verktøy- og Bryggdag-fanens
    innhold kjøres begge i SAMME script-kjøring under st.tabs() (uendret
    Streamlit-oppførsel), så en widget-key-kollisjon her ville rammet
    Verktøy sitt ⚙️-panel akkurat i det snarveien vises."""

    def setUp(self):
        super().setUp()
        recipe = bygg_recipe_object(
            "Full App Snarvei Test", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)

    def _apptest_med_snarvei_synlig(self):
        at = AppTest.from_file(_APP_PY)
        at.run()
        self.assertEqual(len(at.exception), 0, f"app.py kastet exception ved oppstart: {at.exception}")

        at.sidebar.selectbox(key="sidebar_recipe_selector").select("Full App Snarvei Test").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved lasting: {at.exception}")

        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        self.assertEqual(len(knapper), 1)
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved Start-klikk: {at.exception}")
        return at

    def test_9_verktoy_panel_sameksisterer_uten_duplikat_nokkel(self):
        at = self._apptest_med_snarvei_synlig()

        snarvei = [b for b in at.button if b.key == "kbhbrew_bekreft_standardutstyr_btn"]
        self.assertEqual(len(snarvei), 1)

        eq_lagre = [b for b in at.button if b.key == "eq_save_btn"]
        self.assertEqual(len(eq_lagre), 1, "Verktøy sin egen lagre-knapp mangler eller er duplisert.")
        eq_eff = [w for w in at.number_input if w.key == "eq_efficiency"]
        self.assertEqual(len(eq_eff), 1, "Verktøy sitt eq_efficiency-felt mangler eller er duplisert.")

        snarvei[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved bekreftelse: {at.exception}")
        self.assertTrue(equipment.equipment_kilde_er_lagret())

        eq_eff_etter = [w for w in at.number_input if w.key == "eq_efficiency"]
        self.assertEqual(len(eq_eff_etter), 1, "Verktøy-panelet feilet/duplikerte etter bekreftelse.")

    def test_10_no_og_en_ordlyd_pa_snarveiknappen(self):
        at = self._apptest_med_snarvei_synlig()

        knapp_no = [b for b in at.button if b.key == "kbhbrew_bekreft_standardutstyr_btn"]
        self.assertEqual(len(knapp_no), 1)
        self.assertIn("Bruk og bekreft standardutstyr", knapp_no[0].label)

        at.sidebar.radio(key="sprak").set_value("en").run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved språkbytte: {at.exception}")

        knapp_en = [b for b in at.button if b.key == "kbhbrew_bekreft_standardutstyr_btn"]
        self.assertEqual(len(knapp_en), 1, "Snarveien forsvant ved språkbytte -- flagget skal overleve rerunet.")
        self.assertIn("Use and confirm default equipment", knapp_en[0].label)


class TestUtstyrssnarveiDemoMode(unittest.TestCase):
    """11: DEMO_MODE er lest FRISKT som en modulnivå-konstant av
    config.py -- må derfor testes i en EGEN prosess (samme mønster som
    tests/test_brewday_a1_measurement_apptest.py sin
    test_9_lagreseksjonen_skjules_i_demo_mode) for at env-variabelen
    faktisk skal reflekteres."""

    def test_11_demo_mode_ingen_knapper_og_ingen_skriving(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env["DEMO_MODE"] = "1"
            fiktiv_equipment_fil = os.path.join(tmp, "demo-skal-ikke-skrives.json")
            env["KVERNHAUG_EQUIPMENT_FILE"] = fiktiv_equipment_fil
            script = (
                "import logging; logging.getLogger('streamlit').setLevel(logging.ERROR); "
                "from streamlit.testing.v1 import AppTest; "
                f"at = AppTest.from_file(r{_HARNESS!r}); "
                "at.run(); "
                "assert not at.exception, at.exception; "
                "knapper = list(at.button); "
                "assert knapper == [], knapper; "
                "print('OK')"
            )
            resultat = subprocess.run(
                [sys.executable, "-c", script],
                cwd=_REPO_ROOT, env=env, capture_output=True, text=True, timeout=60,
            )
            self.assertEqual(resultat.returncode, 0, f"stdout={resultat.stdout}\nstderr={resultat.stderr}")
            self.assertIn("OK", resultat.stdout)
            self.assertFalse(os.path.exists(fiktiv_equipment_fil))


if __name__ == "__main__":
    unittest.main()
