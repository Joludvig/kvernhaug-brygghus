"""
App A4-4 (issue #248) -- AppTest-basert regresjonstest for de ÅTTE
brukervendte terminologi-/visningsfiksene i ui/kbhbrew_panel.py (se
docs/development/app_a4_workflow_polish_preflight.md Section 6):

  1. Create-panel-tittel: "snapshot" fjernet.
  2. Create-panel-beskrivelse: "Core V1"/"snapshot" fjernet.
  3. Manglende-ingrediens-feil: "snapshot" fjernet, sperren uendret.
  4. Suksess-toast ved opprettelse: oppskriftsnavn i stedet for rå brewId.
  5. Aktivt skrivemål (kbhbrew.skriver_til): oppskriftsnavn i stedet for
     rå brewId, lagret status fortsatt synlig separat (A3-2).
  6. Import-beskrivelse: "Core V1" fjernet, ".kbhbrew"/"historisk brygg,
     IKKE en oppskrift"-distinksjonen beholdt.
  7. Import-bekreftelse: oppskriftsnavn i stedet for rå brewId.
  8. Eksport tom-tilstand: "Core V1" fjernet.

Alle åtte er RENE ordlyd-/visningsendringer via modules/i18n.py sin
t()-nøkler -- ingen opprettelses-/import-/eksportlogikk, ingen
.kbhbrew-skjemaendring. Bruker de allerede eksisterende harnessene
(kbhbrew_create_harness.py, kbhbrew_verktoy_harness.py) -- samme
mønster som tests/test_kbhbrew_create_panel_apptest.py og
tests/test_kbhbrew_import_export_apptest.py.

Kjøres med:
    py -3 -m unittest tests.test_kbhbrew_terminology_apptest -v
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
_CREATE_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_create_harness.py")
_VERKTOY_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "kbhbrew_verktoy_harness.py")

_GYLDIG_EQUIPMENT = {
    "efficiency": 0.75, "boil_off_l_per_hour": 4.0, "grain_absorption_l_per_kg": 1.0,
    "dead_space_l": 2.0, "mash_ratio_l_per_kg": 3.2, "kettle_capacity_l": 35.0,
    "default_boil_time_min": 60,
}


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (se tests/test_kbh_import_ui_apptest.py)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


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


class _MedIsolerteOppskrifter(unittest.TestCase):
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


# ─── 1/2/3/4/5 -- create-panel (kbhbrew_create_harness.py) ─────────────

class TestA44CreatePanelTerminologi(_MedIsolerteOppskrifter):
    def setUp(self):
        super().setUp()
        self._gammel_invalid = os.environ.pop("KVERNHAUG_TEST_KBHBREW_INVALID", None)
        self._gammel_missing_malt = os.environ.pop("KVERNHAUG_TEST_KBHBREW_MISSING_MALT", None)
        self._gammel_equipment_file = os.environ.get("KVERNHAUG_EQUIPMENT_FILE")
        self._equipment_file = os.path.join(self._tmpdir.name, "equipment.json")
        with open(self._equipment_file, "w", encoding="utf-8") as f:
            json.dump(_GYLDIG_EQUIPMENT, f)
        os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._equipment_file

    def tearDown(self):
        if self._gammel_invalid is not None:
            os.environ["KVERNHAUG_TEST_KBHBREW_INVALID"] = self._gammel_invalid
        else:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_INVALID", None)
        if self._gammel_missing_malt is not None:
            os.environ["KVERNHAUG_TEST_KBHBREW_MISSING_MALT"] = self._gammel_missing_malt
        else:
            os.environ.pop("KVERNHAUG_TEST_KBHBREW_MISSING_MALT", None)
        if self._gammel_equipment_file is None:
            os.environ.pop("KVERNHAUG_EQUIPMENT_FILE", None)
        else:
            os.environ["KVERNHAUG_EQUIPMENT_FILE"] = self._gammel_equipment_file
        super().tearDown()

    def _ny_apptest(self):
        at = AppTest.from_file(_CREATE_HARNESS)
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved render: {at.exception}")
        return at

    def _klikk_start(self, at):
        knapper = [b for b in at.button if b.key == "kbhbrew_start_ny_brew_btn"]
        self.assertEqual(len(knapper), 1, "Fant ikke akkurat én 'Start nytt brygg'-knapp")
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter klikk: {at.exception}")
        return at

    # ─── 1/2: tittel + beskrivelse ─────────────────────────────────────

    def test_1_tittel_er_brygger_vendt_uten_snapshot(self):
        at = self._ny_apptest()
        markdowns = [m.value for m in at.markdown]
        self.assertTrue(any("Start nytt brygg" in m for m in markdowns))
        self.assertFalse(any("snapshot" in m.lower() for m in markdowns))

    def test_2_beskrivelse_uten_core_v1_eller_snapshot(self):
        at = self._ny_apptest()
        captions = [c.value for c in at.caption]
        self.assertFalse(any("Core V1" in c for c in captions))
        self.assertFalse(any("snapshot" in c.lower() for c in captions))
        # Semantikken (fryst/historisk brygg, senere endringer påvirker
        # ikke, flere klikk = flere batcher) skal fortsatt være forklart.
        self.assertTrue(any("historisk" in c.lower() for c in captions))
        self.assertTrue(any("NYTT batch" in c for c in captions))

    # ─── 3: manglende ingrediens -- sperre uendret, ordlyd fikset ──────

    def test_3_manglende_ingrediens_sperre_uendret_ordlyd_fikset(self):
        os.environ["KVERNHAUG_TEST_KBHBREW_MISSING_MALT"] = "1"
        at = self._ny_apptest()
        self._klikk_start(at)

        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertIsNone(_ss(at, "_aktiv_kbhbrew_brew_id"))
        feilmeldinger = [e.value for e in at.error]
        self.assertTrue(any("weyermann_pilsner" in m for m in feilmeldinger))
        self.assertFalse(any("snapshot" in m.lower() for m in feilmeldinger))

    # ─── 4: suksess-toast viser oppskriftsnavn, ikke rå brewId ─────────

    def test_4_suksess_toast_viser_oppskriftsnavn_ikke_rå_brewid(self):
        at = self._ny_apptest()
        self._klikk_start(at)

        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")
        self.assertIsNotNone(brew_id)
        brews = kbhbrew_storage.hent_alle_brews()
        self.assertEqual(brews[brew_id]["brewId"], brew_id)  # rå id fortsatt intern identitet

        toasts = [tst.value for tst in at.toast]
        self.assertTrue(any("Harness Pilsner" in m for m in toasts))
        self.assertFalse(any(brew_id in m for m in toasts))

    # ─── 5: aktivt skrivemål -- oppskriftsnavn, status separat, ikke id ─

    def test_5_aktivt_skrivemal_viser_oppskriftsnavn_og_status_separat(self):
        at = self._ny_apptest()
        self._klikk_start(at)
        brew_id = _ss(at, "_aktiv_kbhbrew_brew_id")

        at.run()  # rerun uten nytt klikk -- skrivemål-meldingen skal fortsatt vises
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved rerun: {at.exception}")

        suksessmeldinger = [e.value for e in at.success]
        self.assertTrue(any("Harness Pilsner" in m for m in suksessmeldinger))
        self.assertFalse(any(brew_id in m for m in suksessmeldinger))
        # A3-2: lagret status vises fortsatt, atskilt fra selve skrivemålet.
        self.assertTrue(any("Aktiv" in m for m in suksessmeldinger))


# ─── 6/7/8 -- import/eksport-paneler (kbhbrew_verktoy_harness.py) ──────

class TestA44ImportEksportTerminologi(_MedIsolerteOppskrifter):
    def _ny_apptest(self):
        at = AppTest.from_file(_VERKTOY_HARNESS)
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

    # ─── 6: import-beskrivelse ──────────────────────────────────────────

    def test_6_import_beskrivelse_uten_core_v1_med_kbhbrew_distinksjon(self):
        at = self._ny_apptest()
        captions = [c.value for c in at.caption]
        self.assertFalse(any("Core V1" in c for c in captions))
        self.assertTrue(any(".kbhbrew" in c and "historisk brygg" in c and "IKKE en oppskrift" in c for c in captions))

    # ─── 7: import-bekreftelse viser oppskriftsnavn, ikke rå brewId ────

    def test_7_import_bekreftelse_viser_oppskriftsnavn_ikke_rå_brewid(self):
        at = self._ny_apptest()
        self._last_opp(at, "batch.kbhbrew", _kbhbrew_tekst("brew-origin-a44-1", navn="A4-4 Importert Ale"))
        self._klikk(at, "kbhbrew_analyser_btn")
        self._klikk(at, "kbhbrew_bekreft_btn")

        (brew_id, brew), = kbhbrew_storage.hent_alle_brews().items()
        self.assertEqual(brew["snapshot"]["recipe"]["navn"], "A4-4 Importert Ale")

        suksessmeldinger = [e.value for e in at.success]
        self.assertTrue(any("A4-4 Importert Ale" in m for m in suksessmeldinger))
        self.assertFalse(any(brew_id in m for m in suksessmeldinger))
        # Selve import-/lagringsoppførselen (fersk lokal id, korrekt lagret brew) uendret.
        self.assertEqual(brew["originBrewId"], "brew-origin-a44-1")
        self.assertNotEqual(brew_id, "brew-origin-a44-1")

    # ─── 8: eksport tom-tilstand ────────────────────────────────────────

    def test_8_eksport_tom_tilstand_uten_core_v1(self):
        at = self._ny_apptest()
        captions = [c.value for c in at.caption]
        self.assertTrue(any("Ingen brygg lagret lokalt ennå" in c for c in captions))
        self.assertFalse(any("Core V1" in c for c in captions))


# ─── i18n: begge språk løser alle åtte nye/endrede nøkler ──────────────

class TestA44NoEnNoklerLoserBeggeSprak(unittest.TestCase):
    def test_alle_a44_nokler_finnes_pa_begge_sprak_uten_markor(self):
        from modules.i18n import t as ren_t

        nokler_og_interpolasjon = {
            "kbhbrew.start_ny_brew_tittel": {},
            "kbhbrew.start_ny_brew_beskrivelse": {},
            "kbhbrew.manglende_ingrediens_feil": {"ider": "weyermann_pilsner"},
            "kbhbrew.nytt_brygg_toast": {"oppskriftsnavn": "Testoppskrift"},
            "kbhbrew.skriver_til": {"oppskriftsnavn": "Testoppskrift", "opprettet": "2026-01-01"},
            "kbhbrew.import_beskrivelse": {},
            "kbhbrew.import_bekreftet": {"oppskriftsnavn": "Testoppskrift"},
            "kbhbrew.export_tomt": {},
            "kbhbrew.oppskrift_ukjent_fallback": {},
        }
        for nokkel, params in nokler_og_interpolasjon.items():
            for sprak in ("no", "en"):
                tekst = ren_t(nokkel, sprak, **params)
                self.assertTrue(tekst, f"{nokkel}/{sprak} ga en tom/falsy tekst")
                self.assertFalse(
                    tekst.startswith("??") and tekst.endswith("??"),
                    f"{nokkel}/{sprak} ga en manglende-nøkkel-markør: {tekst!r}",
                )


if __name__ == "__main__":
    unittest.main()
