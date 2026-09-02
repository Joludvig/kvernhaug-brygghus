"""
PRI 2C3 -- Chief review-fiks (PR #5), blokkerende punkt 1: en bekreftet
.kbhrecipe-import må tvinge ui/process_panel.py og ui/water_panel.py
til å resynke sin EGEN, panel-lokale widget-state fra den nettopp
importerte prosessen/vannet -- selv når "forrige aktive oppskrift"
allerede var ny/ulagret (`_last_loaded_recipe` allerede `None` FØR OG
ETTER importen, altså en None -> None-"endring" begge panelenes egne
`_prosess_synced_for`/`_vann_synced_for`-markører ellers ikke ville
oppdaget).

Bruker tests/fixtures/streamlit_harness/sidebar_process_water_harness.py
(sidebar + process_panel + water_panel sammen) -- den ORIGINALE
sidebar-only AppTest-suiten (tests/test_kbh_import_ui_apptest.py)
rendrer ALDRI disse to panelene, og kunne derfor aldri ha oppdaget
denne regresjonen (nøyaktig reviewets poeng).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

from modules.process_profiles import hent_standardprofil

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(
    _REPO_ROOT, "tests", "fixtures", "streamlit_harness", "sidebar_process_water_harness.py",
)

_GYLDIG_MALT_ID = "bohemian_pilsner_floor"
_GYLDIG_HUMLE_ID = "amarillo"
_GYLDIG_GJAER_ID = "lalbrew_house_ale"


def _kbhrecipe_tekst_med_hochkurz_og_ny_vannkilde():
    hochkurz = hent_standardprofil("hochkurz")
    payload = {
        "recipeSchemaVersion": 1,
        "navn": "Resync Test Ale",
        "volum": 20.0,
        "effektivitet": 70,
        "malt": [{"id": _GYLDIG_MALT_ID, "mengde": 4.0}],
        "humle": [{"id": _GYLDIG_HUMLE_ID, "gram": 20, "tid": 60}],
        "gjaerId": _GYLDIG_GJAER_ID,
        "prosess": {
            "process_id": hochkurz["process_id"],
            "mash_steps": hochkurz["mash_steps"],
            "sparge_method": hochkurz["sparge_method"],
            "boil_minutes": hochkurz["boil_minutes"],
            "decoction_steps": hochkurz["decoction_steps"],
            "reiterated_mash": hochkurz["reiterated_mash"],
        },
        "vann": {
            "kilde": {"water_id": "regresjonstest_ny_kilde", "name": "Regresjonstest-kilde", "ca": 55.0},
        },
    }
    return json.dumps({
        "format": "kbhrecipe", "version": 1, "exportedAt": "2026-09-02T00:00:00Z",
        "generator": "test", "recipe": payload,
    })


def _ss(at, key, default=None):
    try:
        return at.session_state[key]
    except KeyError:
        return default


class TestProsessOgVannResyncEtterImport(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def _ny_apptest(self):
        at = AppTest.from_file(_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved initial render: {at.exception}")
        return at

    def test_prosess_og_vann_resynker_etter_bekreftet_import_over_allerede_ulagret_oppskrift(self):
        at = self._ny_apptest()

        # Etter FØRSTE render: _last_loaded_recipe er fraværende/None (en
        # helt vanlig, ny/ulagret økt), og BEGGE panelene har derfor
        # allerede synket seg selv MOT None én gang -- akkurat
        # forutsetningen reviewet beskriver.
        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_prosess_synced_for"))
        self.assertIsNone(_ss(at, "_vann_synced_for"))

        # Vannkilden starter naturlig på "ukjent" (ingen vannprofil på den
        # ferske, ulagrede oppskriften -- se _UKJENT_KILDE_ID i
        # ui/water_panel.py). Bekreft det FØR importen, slik at en
        # etterfølgende endring faktisk beviser noe.
        self.assertEqual(_ss(at, "vann_kilde_valgt_id"), "__ukjent__")

        # Simuler at brukeren manuelt hadde justert PROSESSEN for DEN
        # ALLEREDE AKTIVE, ulagrede oppskriften -- tydelig, gjenkjennelig
        # "gammel" verdi som ALDRI skal overleve importen under. (Kun
        # prosess_mash_steps -- en ren dataliste, ikke selv en widget-
        # nøkkel, ulikt vann_kilde_valgt_id som er bundet til en
        # selectbox og derfor ikke trygt kan settes til en vilkårlig,
        # ugyldig streng mellom to AppTest .run()-kall.)
        at.session_state["prosess_mash_steps"] = [
            {"temperatur": 40.0, "varighet": 5, "stegtype": "infusjon", "kommentar": "GAMMEL STALE VERDI"},
        ]

        # Importer en NY .kbhrecipe med en ANNEN, kjent prosess (hochkurz,
        # strukturelt helt forskjellig fra det manuelt justerte over) og
        # en ANNEN vannkilde.
        uploader = at.sidebar.file_uploader[0]
        uploader.upload("resync.kbhrecipe", _kbhrecipe_tekst_med_hochkurz_og_ny_vannkilde().encode("utf-8"), "application/octet-stream")
        at.run()

        analyser_btn = [b for b in at.sidebar.button if b.key == "kbhrecipe_analyser_btn"][0]
        analyser_btn.click().run()
        self.assertIsNotNone(_ss(at, "kbhrecipe_import_preview"))

        bekreft_btn = [b for b in at.sidebar.button if b.key == "kbhrecipe_bekreft_btn"][0]
        bekreft_btn.click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter bekreftet import: {at.exception}")

        # "Import as new" fortsatt intakt -- IKKE gjeninnført/adoptert.
        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))

        # Selve poenget: BEGGE panelene har resynket seg -- de gamle,
        # manuelt justerte verdiene har IKKE overlevd, og de nye,
        # importerte verdiene er faktisk der.
        hochkurz = hent_standardprofil("hochkurz")
        self.assertEqual(_ss(at, "prosess_mash_steps"), hochkurz["mash_steps"])
        self.assertNotEqual(
            _ss(at, "prosess_mash_steps"),
            [{"temperatur": 40.0, "varighet": 5, "stegtype": "infusjon", "kommentar": "GAMMEL STALE VERDI"}],
        )
        self.assertEqual(_ss(at, "vann_kilde_valgt_id"), "regresjonstest_ny_kilde")
        self.assertNotEqual(_ss(at, "vann_kilde_valgt_id"), "__ukjent__")

        # Og selve markørene er blitt konsistente igjen (samme verdi,
        # None, men nå faktisk et resultat av en FERSK resync -- ikke
        # bare urørt fra før importen).
        self.assertIsNone(_ss(at, "_prosess_synced_for"))
        self.assertIsNone(_ss(at, "_vann_synced_for"))


if __name__ == "__main__":
    unittest.main()
