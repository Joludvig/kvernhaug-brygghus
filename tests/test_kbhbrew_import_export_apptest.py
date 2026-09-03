"""
PRI 3B2 (issue #29) -- AppTest-basert regresjonstest for
ui/kbhbrew_panel.py sine import-/eksport-paneler (🔧 Verktøy-fanen), via
tests/fixtures/streamlit_harness/kbhbrew_verktoy_harness.py.

Dekker de UI-spesifikke sikkerhetskravene fra issue #29:
  - opplasting ALENE skriver ingenting;
  - forhåndsvisning (uten bekreftelse) skriver ingenting;
  - ETT eksplisitt "Importer brygg"-klikk skriver NØYAKTIG ett nytt,
    lokalt brygg med en FERSK, lokalt mintet brewId (aldri origin-en
    lest fra filen);
  - duplikat-originBrewId avvises eksplisitt, skriver ingenting;
  - ugyldig format/JSON viser en tydelig feil, skriver ingenting;
  - eksport kilder UTELUKKENDE fra den nye Core V1-butikken
    (hent_alle_brews()) og rører aldri recipes/_logs/ (legacy).

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_import_export_apptest -b
"""
import json
import logging
import os
import tempfile
import unittest

logging.getLogger("streamlit").setLevel(logging.ERROR)

from streamlit.testing.v1 import AppTest

import modules.kbhbrew_storage as kbhbrew_storage
from modules.kbhbrew import bygg_kbhbrew_konvolutt, bygg_ny_brew
from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_verktoy_harness.py")


def _recipe(navn="Verktøy Ale"):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}],
        [{"id": "cascade", "gram": 30.0, "tid": 60}],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8,
        {"Maltfylde": 5.0, "Sitrus": 2.0},
    )


def _dbs():
    return (
        {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}},
        {"cascade": {"display_name": "Cascade", "alfa": 6.0}},
        {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}},
    )


def _kbhbrew_tekst(origin_brew_id, navn="Verktøy Ale"):
    malt_db, humle_db, gjaer_db = _dbs()
    brew = bygg_ny_brew(
        _recipe(navn), malt_db, humle_db, gjaer_db, None,
        {"og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 8},
        created_at="2026-08-01T09:00:00+00:00", brew_id=origin_brew_id,
    )
    konvolutt = bygg_kbhbrew_konvolutt(brew, "2026-08-01T09:05:00+00:00")
    return json.dumps(konvolutt, ensure_ascii=False)


def _ss(at, key, default=None):
    try:
        return at.session_state[key]
    except KeyError:
        return default


class TestKbhbrewImportExportAppTest(unittest.TestCase):
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
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _last_opp(self, at, filnavn, tekst):
        uploader = at.file_uploader[0]
        uploader.upload(filnavn, tekst.encode("utf-8"), "application/octet-stream")
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter opplasting: {at.exception}")

    def _klikk(self, at, key):
        knapper = [b for b in at.button if b.key == key]
        self.assertEqual(len(knapper), 1, f"Fant ikke akkurat én knapp med key={key!r}")
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter klikk på {key!r}: {at.exception}")

    # ─── 1: grunnleggende rendring ─────────────────────────────────────

    def test_1_paneler_rendrer_uten_feil(self):
        at = self._ny_apptest()
        titler = [s.value for s in at.subheader]
        self.assertIn("📦 Importer .kbhbrew-fil", titler)
        self.assertIn("📥 Eksporter lagret .kbhbrew-brygg", titler)

    def test_1b_ingen_lagrede_brygg_viser_tom_tilstand_uten_selector(self):
        at = self._ny_apptest()
        self.assertEqual(list(at.selectbox), [])
        captions = [c.value for c in at.caption]
        self.assertTrue(any("Ingen Core V1-brygg lagret lokalt ennå" in c for c in captions))

    # ─── 2: opplasting alene skriver ingenting ─────────────────────────

    def test_2_opplasting_alene_skriver_ingenting(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-1"))
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "kbhbrew_import_preview"))

    # ─── 3: forhåndsvisning alene skriver ingenting ────────────────────

    def test_3_analyser_bygger_forhandsvisning_uten_a_skrive(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-2"))
        self._klikk(at, "kbhbrew_analyser_btn")

        preview = _ss(at, "kbhbrew_import_preview")
        self.assertIsNotNone(preview)
        self.assertEqual(preview["originBrewId"], "brew-origin-2")
        self.assertEqual(preview["snapshot"]["recipe"]["navn"], "Verktøy Ale")
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})

        # Bekreft-knappen finnes, men er IKKE trykket ennå.
        self.assertEqual(len([b for b in at.button if b.key == "kbhbrew_bekreft_btn"]), 1)

    # ─── 4: eksplisitt import skriver nøyaktig ett brygg, fersk brewId ─

    def test_4_eksplisitt_import_skriver_ett_brygg_med_fersk_lokal_id(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-3"))
        self._klikk(at, "kbhbrew_analyser_btn")
        self._klikk(at, "kbhbrew_bekreft_btn")

        brews = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(len(brews), 1)
        (brew_id, brew), = brews.items()
        self.assertEqual(brew["originBrewId"], "brew-origin-3")
        self.assertNotEqual(brew_id, "brew-origin-3")
        self.assertIsNone(brew["recipeId"])

        # Forhåndsvisnings-/feilstate ryddet etter vellykket import.
        self.assertIsNone(_ss(at, "kbhbrew_import_preview"))
        self.assertIsNone(_ss(at, "kbhbrew_import_feil"))

    # ─── 5: duplikat origin avvises, skriver ingenting ekstra ──────────

    def test_5_duplikat_origin_avvises_uten_a_skrive(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-4"))
        self._klikk(at, "kbhbrew_analyser_btn")
        self._klikk(at, "kbhbrew_bekreft_btn")
        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)

        at2 = self._ny_apptest()
        self._last_opp(at2, "batch_igjen.kbhbrew", _kbhbrew_tekst("brew-origin-4"))
        self._klikk(at2, "kbhbrew_analyser_btn")
        self._klikk(at2, "kbhbrew_bekreft_btn")

        self.assertEqual(len(kbhbrew_storage.hent_alle_brews()), 1)
        advarsler = [e.value for e in at2.warning]
        self.assertTrue(any("brew-origin-4" in m and "allerede importert" in m for m in advarsler))

    # ─── 6: ugyldig fil -- tydelig feil, ingenting skrevet ─────────────

    def test_6_ugyldig_json_viser_feil_og_skriver_ingenting(self):
        at = self._ny_apptest()
        self._last_opp(at, "ugyldig.kbhbrew", "{ ikke gyldig json")
        self._klikk(at, "kbhbrew_analyser_btn")

        self.assertIsNone(_ss(at, "kbhbrew_import_preview"))
        self.assertIsNotNone(_ss(at, "kbhbrew_import_feil"))
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertEqual([b for b in at.button if b.key == "kbhbrew_bekreft_btn"], [])

    def test_6b_feil_format_viser_feil_og_skriver_ingenting(self):
        at = self._ny_apptest()
        feil_tekst = json.dumps({"format": "kbhrecipe", "version": 1, "recipe": {}})
        self._last_opp(at, "feil_format.kbhbrew", feil_tekst)
        self._klikk(at, "kbhbrew_analyser_btn")

        self.assertIsNone(_ss(at, "kbhbrew_import_preview"))
        self.assertIsNotNone(_ss(at, "kbhbrew_import_feil"))
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})

    # ─── 7: eksport kilder utelukkende fra den nye V1-butikken ─────────

    def test_7_eksport_tilbyr_importert_brygg_og_bygger_gyldig_konvolutt(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-5", navn="Eksporttest Ale"))
        self._klikk(at, "kbhbrew_analyser_btn")
        self._klikk(at, "kbhbrew_bekreft_btn")

        (lokal_brew_id, _), = kbhbrew_storage.hent_alle_brews().items()

        selectorer = list(at.selectbox)
        self.assertEqual(len(selectorer), 1)
        # AppTest sin Selectbox eksponerer de FORMATERTE etikettene (via
        # format_func), ikke de rå options-verdiene (brewId) -- selve
        # brewId->label-mappingen er allerede dekket rent/raskt av
        # modules/kbhbrew_ui.py sin egen testsuite
        # (tests/test_kbhbrew_ui_helpers.py). Her bekreftes kun at
        # panelet faktisk tilbyr akkurat det NYLIG importerte brygget.
        self.assertEqual(
            selectorer[0].options,
            [f"Eksporttest Ale — 2026-08-01 — active · {lokal_brew_id[-8:]}"],
        )
        self.assertEqual(selectorer[0].value, lokal_brew_id)

        # Trykk den EKTE eksportknappen -- bekreft at selve eksportkoden
        # (eksporter_kbhbrew() + st.download_button-oppsettet) kjører uten
        # å krasje (st.download_button har ingen introspiserbar payload i
        # denne AppTest-versjonen, se tests/test_kbh_contract.py sin
        # tilsvarende kommentar). Selve envelope-formen er allerede
        # tungt dekket direkte i tests/test_kbhbrew_roundtrip.py /
        # tests/test_kbhbrew_schema_contract.py -- her bekreftes kun at
        # UI-en faktisk kobler riktig, lokalt importert brewId til den
        # EKTE produksjonsfunksjonen.
        self._klikk(at, "kbhbrew_eksport_btn")
        self.assertEqual(len([b for b in at.download_button if b.key == "kbhbrew_eksport_last_ned_btn"]), 1)

        konvolutt = kbhbrew_storage.eksporter_kbhbrew(lokal_brew_id)
        self.assertEqual(konvolutt["format"], "kbhbrew")
        self.assertEqual(konvolutt["version"], 1)
        self.assertEqual(konvolutt["brew"]["originBrewId"], "brew-origin-5")
        # Eksportert konvolutt bærer ALDRI lokal identitet (brewId/recipeId).
        self.assertNotIn("brewId", konvolutt["brew"])
        self.assertNotIn("recipeId", konvolutt["brew"])

    def test_8_ingen_recipes_logs_mappe_beroert_av_hele_flyten(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-6"))
        self._klikk(at, "kbhbrew_analyser_btn")
        self._klikk(at, "kbhbrew_bekreft_btn")

        logs_mappe = os.path.join(self._tmpdir.name, "_logs")
        self.assertFalse(os.path.exists(logs_mappe))


if __name__ == "__main__":
    unittest.main()
