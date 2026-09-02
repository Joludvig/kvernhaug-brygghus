"""
PRI 2C3 -- automatisert Streamlit-smoke-test for den nye
.kbhrecipe-import-UI-en i ui/sidebar.py, via Streamlit sitt offisielle
`streamlit.testing.v1.AppTest`-rammeverk (samme prinsipp som en
manuell smoke-test issue #4 nevner som mulig alternativ -- denne kjører
i stedet AUTOMATISK, gjentakbart, som del av den vanlige testsuiten,
via ekte widget-interaksjon: fil-opplasting, knappeklikk og faktisk
gjenrendring -- IKKE en nettleser-DOM, men Streamlit sin egen,
offisielle scriptkjøringsmotor).

`tests/fixtures/streamlit_harness/sidebar_harness.py` er en minimal
harness som kun laster ui/sidebar.py::render_sidebar() isolert (ikke
hele app.py -- malt-/humle-/gjærpanelene, beregningsmotoren osv. er
IKKE del av dette, se harness-filens egen kommentar).

Hovedvekten av regresjonsdekningen for selve state-hydreringen ligger i
tests/test_kbh_import_apply.py (ren, rask, ingen Streamlit-scriptkjøring)
-- denne filen dekker i tillegg den FAKTISKE UI-flyten (opplasting ->
analyser -> forhåndsvisning -> bekreft) som den filen ikke rører ved.

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

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_HARNESS = os.path.join(_REPO_ROOT, "tests", "fixtures", "streamlit_harness", "sidebar_harness.py")

# Ekte, eksisterende kanoniske ID-er (data/master_*.json) -- samme
# "aldri anta, alltid verifiser mot ekte data"-disiplin som resten av
# denne testsuiten (se f.eks. tests/test_kbh_import.py).
_GYLDIG_MALT_ID = "bohemian_pilsner_floor"
_GYLDIG_HUMLE_ID = "amarillo"
_GYLDIG_GJAER_ID = "lalbrew_house_ale"


def _kbhrecipe_tekst(**overrides):
    payload = {
        "recipeSchemaVersion": 1,
        "navn": "AppTest Smoke Ale",
        "volum": 21.0,
        "effektivitet": 71,
        "malt": [{"id": _GYLDIG_MALT_ID, "mengde": 4.2}],
        "humle": [{"id": _GYLDIG_HUMLE_ID, "gram": 18, "tid": 60}],
        "gjaerId": _GYLDIG_GJAER_ID,
        "brygger": "Smoke Tester",
        "notater": "Fra AppTest-smoketest",
    }
    payload.update(overrides)
    return json.dumps({
        "format": "kbhrecipe", "version": 1, "exportedAt": "2026-09-02T00:00:00Z",
        "generator": "test", "recipe": payload,
    })


def _ss(at, key, default=None):
    """Trygg session_state-lesing -- AppTest sin session_state-proxy
    støtter ikke .get(), kun subscript (se streamlit.runtime.state.
    safe_session_state.SafeSessionState)."""
    try:
        return at.session_state[key]
    except KeyError:
        return default


class TestKbhrecipeImportUiAppTest(unittest.TestCase):
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

    def _ny_apptest(self, **forhaandssatt_state):
        at = AppTest.from_file(_HARNESS)
        for k, v in forhaandssatt_state.items():
            at.session_state[k] = v
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak ved initial render: {at.exception}")
        return at

    def _last_opp(self, at, filnavn, tekst):
        uploader = at.sidebar.file_uploader[0]
        uploader.upload(filnavn, tekst.encode("utf-8"), "application/octet-stream")
        at.run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter opplasting: {at.exception}")

    def _klikk(self, at, key):
        knapper = [b for b in at.sidebar.button if b.key == key]
        self.assertEqual(len(knapper), 1, f"Fant ikke akkurat én knapp med key={key!r}")
        knapper[0].click().run()
        self.assertEqual(len(at.exception), 0, f"Uventet unntak etter klikk på {key!r}: {at.exception}")

    # ─── 1: grunnleggende rendring ─────────────────────────────────────

    def test_1_sidebar_rendrer_uten_feil_med_begge_import_ekspandere(self):
        at = self._ny_apptest()
        labels = [e.label for e in at.sidebar.expander]
        self.assertIn("📥 Importer oppskrift fra tekst", labels)
        self.assertIn("📦 Importer .kbhrecipe-fil", labels)

    # ─── 2: full, ekte UI-flyt ──────────────────────────────────────────

    def test_2_full_opplasting_analyser_bekreft_hydrerer_riktig_state(self):
        at = self._ny_apptest()
        self._last_opp(at, "smoke.kbhrecipe", _kbhrecipe_tekst())
        self._klikk(at, "kbhrecipe_analyser_btn")

        self.assertIsNotNone(_ss(at, "kbhrecipe_import_preview"))
        self.assertIsNone(_ss(at, "kbhrecipe_import_feil"))
        # Ingen mutasjon av selve den aktive oppskriften ENNÅ (kun forhåndsvisning).
        self.assertEqual(_ss(at, "gjeldende_navn"), "Kvernhaug Spesial")

        forrige_versjon = _ss(at, "import_versjon", 0)
        self._klikk(at, "kbhrecipe_bekreft_btn")

        self.assertEqual(_ss(at, "gjeldende_navn"), "AppTest Smoke Ale")
        self.assertEqual(_ss(at, "batch_volum_input"), 21.0)
        self.assertAlmostEqual(_ss(at, "_aktiv_recipe_efficiency"), 0.71)
        self.assertEqual(_ss(at, "valgt_malt"), [{"id": _GYLDIG_MALT_ID, "mengde": 4.2}])
        self.assertEqual(_ss(at, "valgt_humle"), [{"id": _GYLDIG_HUMLE_ID, "gram": 18, "tid": 60}])
        self.assertEqual(_ss(at, "valgt_gjaer_id"), _GYLDIG_GJAER_ID)
        self.assertEqual(_ss(at, "_aktiv_kbh_passthrough"), {
            "brygger": "Smoke Tester", "notater": "Fra AppTest-smoketest",
        })
        self.assertGreater(_ss(at, "import_versjon"), forrige_versjon)
        # Forhåndsvisnings-/feilstate ryddet etter vellykket bekreftelse.
        self.assertIsNone(_ss(at, "kbhrecipe_import_preview"))
        self.assertIsNone(_ss(at, "kbhrecipe_import_feil"))

    # ─── 3: import as new -- gammel identitet ryddes ───────────────────

    def test_3_import_as_new_rydder_gammel_lagret_identitet(self):
        at = self._ny_apptest(
            _last_loaded_recipe="En Gammel Lagret Oppskrift",
            _last_loaded_recipe_file="en_gammel_lagret_oppskrift.json",
        )
        self.assertEqual(_ss(at, "_last_loaded_recipe"), "En Gammel Lagret Oppskrift")

        self._last_opp(at, "smoke.kbhrecipe", _kbhrecipe_tekst())
        self._klikk(at, "kbhrecipe_analyser_btn")
        self._klikk(at, "kbhrecipe_bekreft_btn")

        self.assertIsNone(_ss(at, "_last_loaded_recipe"))
        self.assertIsNone(_ss(at, "_last_loaded_recipe_file"))

    # ─── 4: avvist fil -- feil vises, INGEN mutasjon ───────────────────

    def test_4_avvist_fil_viser_feil_og_endrer_ikke_aktiv_oppskrift(self):
        at = self._ny_apptest()
        ugyldig_tekst = _kbhrecipe_tekst(malt=[{"id": "helt-ukjent-malt-id", "mengde": 1.0}])
        self._last_opp(at, "ugyldig.kbhrecipe", ugyldig_tekst)
        self._klikk(at, "kbhrecipe_analyser_btn")

        self.assertIsNone(_ss(at, "kbhrecipe_import_preview"))
        feil = _ss(at, "kbhrecipe_import_feil")
        self.assertIsNotNone(feil)
        self.assertIn("helt-ukjent-malt-id", feil)

        # Den aktive oppskriften/økten er HELT urørt.
        self.assertEqual(_ss(at, "gjeldende_navn"), "Kvernhaug Spesial")
        self.assertEqual(_ss(at, "batch_volum_input"), 20.0)
        self.assertEqual(_ss(at, "valgt_gjaer_id"), "safale_us_05")

        # Feilmeldingen vises faktisk i UI-et.
        feilmeldinger = [e.value for e in at.sidebar.error]
        self.assertTrue(any("helt-ukjent-malt-id" in m for m in feilmeldinger))

        # Ingen bekreft-knapp uten en gyldig forhåndsvisning.
        self.assertEqual([b for b in at.sidebar.button if b.key == "kbhrecipe_bekreft_btn"], [])

    def test_4b_ugyldig_json_gir_tydelig_feil(self):
        at = self._ny_apptest()
        self._last_opp(at, "ugyldig.kbhrecipe", "{ ikke gyldig json")
        self._klikk(at, "kbhrecipe_analyser_btn")
        self.assertIsNone(_ss(at, "kbhrecipe_import_preview"))
        self.assertIsNotNone(_ss(at, "kbhrecipe_import_feil"))
        self.assertEqual(_ss(at, "gjeldende_navn"), "Kvernhaug Spesial")

    def test_4c_ustottet_prosess_gir_tydelig_feil(self):
        at = self._ny_apptest()
        ugyldig_tekst = _kbhrecipe_tekst(prosess={
            "process_id": "enkel_infusjon",
            "mash_steps": [{"temperatur": 64.0, "varighet": 45, "stegtype": "infusjon", "kommentar": "x"}],
            "sparge_method": "batch_sparge", "boil_minutes": 60,
            "decoction_steps": None, "reiterated_mash": None,
        })
        self._last_opp(at, "ugyldig_prosess.kbhrecipe", ugyldig_tekst)
        self._klikk(at, "kbhrecipe_analyser_btn")
        self.assertIsNone(_ss(at, "kbhrecipe_import_preview"))
        self.assertIsNotNone(_ss(at, "kbhrecipe_import_feil"))
        self.assertEqual(_ss(at, "gjeldende_navn"), "Kvernhaug Spesial")

    def test_4d_ikke_utf8_gir_tydelig_feil(self):
        at = self._ny_apptest()
        uploader = at.sidebar.file_uploader[0]
        uploader.upload("ugyldig_encoding.kbhrecipe", b"\xff\xfe\x00ikke-utf8", "application/octet-stream")
        at.run()
        self._klikk(at, "kbhrecipe_analyser_btn")
        self.assertIsNone(_ss(at, "kbhrecipe_import_preview"))
        feil = _ss(at, "kbhrecipe_import_feil")
        self.assertIsNotNone(feil)
        self.assertIn("UTF-8", feil)

    # ─── 5: forhåndsvisning alene muterer aldri ─────────────────────────

    def test_5_forhandsvisning_uten_bekreftelse_gjor_ingen_mutasjon(self):
        at = self._ny_apptest()
        self._last_opp(at, "smoke.kbhrecipe", _kbhrecipe_tekst())
        self._klikk(at, "kbhrecipe_analyser_btn")

        # Bekreft-knappen FINNES (klar for brukeren), men er IKKE klikket.
        self.assertEqual(len([b for b in at.sidebar.button if b.key == "kbhrecipe_bekreft_btn"]), 1)
        self.assertEqual(_ss(at, "gjeldende_navn"), "Kvernhaug Spesial")
        self.assertEqual(_ss(at, "valgt_gjaer_id"), "safale_us_05")
        self.assertIsNone(_ss(at, "_aktiv_kbh_passthrough"))

    # ─── 6: eksisterende tekstimport uendret ────────────────────────────

    def test_6_eksisterende_tekstimport_ekspander_fortsatt_der(self):
        at = self._ny_apptest()
        tekst_ekspander = [e for e in at.sidebar.expander if e.label == "📥 Importer oppskrift fra tekst"]
        self.assertEqual(len(tekst_ekspander), 1)
        analyser_knapper = [b for b in at.sidebar.button if b.key == "import_analyser_btn"]
        self.assertEqual(len(analyser_knapper), 1)


if __name__ == "__main__":
    unittest.main()
