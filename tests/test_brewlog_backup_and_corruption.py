"""
Tester for herdingen av bryggeloggen (modules/recipe_storage.py::
lagre_logg_entry()/hent_logg()): automatisk backup før overskriving,
og en KORRUPT eksisterende loggfil skal ALDRI stille overskrives med
bare den nye oppføringen (som ville slettet hele historikken).

Bruker UTELUKKENDE tempfile.TemporaryDirectory() via
KVERNHAUG_RECIPES_DIR -- aldri den ekte recipes/-mappen (se
tests/test_recipe_storage_isolation.py for bakgrunnen til dette mønsteret).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest
from unittest.mock import patch

import modules.recipe_storage as recipe_storage
from modules.recipe_storage import LoggKorruptError


class _IsolertRecipeMappeTestCase(unittest.TestCase):
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

    def _mappe(self):
        return self._tmpdir.name

    def _filer(self):
        return set(os.listdir(self._mappe()))

    def _logg_sti(self, filnavn="test_brygg_logg.json"):
        # Legacy-plassering (mappe-roten) -- brukt for å simulere en
        # logg som ble opprettet FØR recipes/_logs/ ble innført (se
        # tests/test_brewlog_logs_namespace.py for selve namespace-
        # fiksen). Brukes her fortsatt for korrupt-legacy-logg-testene.
        return os.path.join(self._mappe(), filnavn)

    def _ny_logg_sti(self, filnavn="test_brygg_logg.json"):
        # Den NYE plasseringen -- der lagre_logg_entry() faktisk skriver
        # en helt fersk logg (ingen legacy-fil finnes fra før).
        return os.path.join(self._mappe(), "_logs", filnavn)


class TestNormalAppend(_IsolertRecipeMappeTestCase):
    def test_normal_append_lagres_i_rekkefolge(self):
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-07-28", "actual_og": 1.050})
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-08-01", "actual_og": 1.012})
        logg = recipe_storage.hent_logg("Test Brygg")
        self.assertEqual(len(logg), 2)
        self.assertEqual(logg[0]["date"], "2026-07-28")
        self.assertEqual(logg[1]["date"], "2026-08-01")

    def test_hent_logg_uten_fil_gir_tom_liste(self):
        self.assertEqual(recipe_storage.hent_logg("Ingen Slik Oppskrift"), [])


class TestBackupFoerAppend(_IsolertRecipeMappeTestCase):
    def test_forste_lagring_lager_ingen_backup(self):
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-07-28"})
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))

    def test_andre_lagring_tar_tidsstemplet_backup_av_forrige_versjon(self):
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-07-28"})
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-08-01"})

        backup_mappe = os.path.join(self._mappe(), "_backup")
        self.assertTrue(os.path.isdir(backup_mappe))
        backupfiler = [f for f in os.listdir(backup_mappe) if f.startswith("test_brygg_logg.json.backup_")]
        self.assertEqual(len(backupfiler), 1)

        with open(os.path.join(backup_mappe, backupfiler[0]), encoding="utf-8") as f:
            backup_innhold = json.load(f)
        self.assertEqual(backup_innhold, [{"date": "2026-07-28"}], "Backupen skal inneholde DEN GAMLE loggen (1 oppføring)")

        gjeldende = recipe_storage.hent_logg("Test Brygg")
        self.assertEqual(len(gjeldende), 2, "Selve loggfilen skal ha BEGGE oppføringene")

    def test_backup_ryddes_til_samme_maks_antall_som_oppskrifter(self):
        for i in range(recipe_storage.RECIPE_BACKUP_MAKS_ANTALL + 5):
            recipe_storage.lagre_logg_entry("Test Brygg", {"date": f"2026-08-{i:02d}"})
        backup_mappe = os.path.join(self._mappe(), "_backup")
        backupfiler = [f for f in os.listdir(backup_mappe) if f.startswith("test_brygg_logg.json.backup_")]
        self.assertEqual(len(backupfiler), recipe_storage.RECIPE_BACKUP_MAKS_ANTALL)


class TestKorruptEksisterendeLogg(_IsolertRecipeMappeTestCase):
    def _skriv_korrupt_logg(self, innhold="{ikke gyldig json"):
        recipe_storage.sikre_mappe()
        with open(self._logg_sti(), "w", encoding="utf-8") as f:
            f.write(innhold)

    def test_hent_logg_kaster_loggkorruptexception_uten_aa_roere_filen(self):
        self._skriv_korrupt_logg()
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Test Brygg")
        with open(self._logg_sti(), encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ikke gyldig json")

    def test_lagre_logg_entry_overskriver_aldri_korrupt_logg_stille(self):
        self._skriv_korrupt_logg()
        with self.assertRaises(LoggKorruptError):
            recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-07-28"})

        # Filen skal stå fullstendig urørt -- den ene, nye oppføringen
        # skal ALDRI ha erstattet den (uleselige, men fortsatt
        # tilstedeværende) historikken.
        with open(self._logg_sti(), encoding="utf-8") as f:
            self.assertEqual(f.read(), "{ikke gyldig json")
        # Vi kom aldri til skrive-steget -- ingen backup skal opprettes
        # av et forsøk som feilet allerede ved LESING.
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))

    def test_tom_fil_regnes_ogsaa_som_korrupt_ikke_som_tom_logg(self):
        self._skriv_korrupt_logg(innhold="")
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Test Brygg")


class TestSkrivefeilUtenLekketTmpFil(_IsolertRecipeMappeTestCase):
    def test_os_replace_feil_rydder_tmp_og_beholder_original_byte_for_byte(self):
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-07-28"})
        with open(self._ny_logg_sti(), "rb") as f:
            original_bytes = f.read()

        with patch("modules.recipe_storage.os.replace", side_effect=OSError("simulert diskfeil")):
            with self.assertRaises(OSError):
                recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-08-01"})

        filer = os.listdir(os.path.join(self._mappe(), "_logs"))
        self.assertFalse(any(".tmp_" in f for f in filer), f"Lekket midlertidig fil funnet: {filer}")
        with open(self._ny_logg_sti(), "rb") as f:
            self.assertEqual(f.read(), original_bytes, "Originalfilen skal være helt uendret etter en mislykket skriving")

    def test_json_serialiseringsfeil_rydder_tmp_og_beholder_original(self):
        recipe_storage.lagre_logg_entry("Test Brygg", {"date": "2026-07-28"})
        with open(self._ny_logg_sti(), "rb") as f:
            original_bytes = f.read()

        # Et ikke-JSON-serialiserbart felt (et Python-sett) i en ny
        # oppføring skal feile INNE i json.dump -- fortsatt skal
        # ingenting lekke eller overskrives.
        with self.assertRaises(TypeError):
            recipe_storage.lagre_logg_entry(
                "Test Brygg", {"date": "2026-08-01", "userialiserbart_felt": {1, 2, 3}},
            )

        filer = os.listdir(os.path.join(self._mappe(), "_logs"))
        self.assertFalse(any(".tmp_" in f for f in filer), f"Lekket midlertidig fil funnet: {filer}")
        with open(self._ny_logg_sti(), "rb") as f:
            self.assertEqual(f.read(), original_bytes)


class TestKorruptLoggIEktApp(unittest.TestCase):
    """Ende-til-ende UI-regresjonstest (samme mønster som
    tests/test_real_app_process_flow.py): en korrupt loggfil skal vises
    som en tydelig feil i den EKTE appen -- ikke krasje siden, og ikke få
    "Legg til loggoppføring"-skjemaet til å stå klart til å overskrive
    historikken stille."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        os.environ["KVERNHAUG_RECIPES_DIR"] = self._tmpdir.name

        from modules.recipe import bygg_recipe_object
        # NB: navnet må IKKE selv ende på ordet "logg" -- generer_filnavn()
        # av f.eks. "E2E Korrupt Logg" ville gitt "e2e_korrupt_logg.json",
        # som i seg selv ender på "_logg.json" og dermed (feilaktig) ville
        # blitt filtrert bort som om DEN var en loggfil av
        # modules/recipe_storage.py::_skann_oppskriftsfiler().
        recipe = bygg_recipe_object(
            "E2E Test Korrupt Brygg", 20.0, 0.75,
            [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
        )
        recipe_storage.lagre_oppskrift(recipe)
        with open(os.path.join(self._tmpdir.name, "e2e_test_korrupt_brygg_logg.json"), "w", encoding="utf-8") as f:
            f.write("{dette er ikke gyldig json")

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        self._tmpdir.cleanup()

    def test_korrupt_logg_vises_som_feil_ikke_krasj(self):
        import logging
        logging.getLogger("streamlit").setLevel(logging.ERROR)
        from streamlit.testing.v1 import AppTest

        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        app_py = os.path.join(repo_root, "app.py")

        at = AppTest.from_file(app_py)
        at.run()
        at.sidebar.selectbox(key="sidebar_recipe_selector").select("E2E Test Korrupt Brygg").run()
        self.assertFalse(at.exception, f"app.py kastet exception ved lasting: {at.exception}")

        varsel_tekster = " ".join(e.value for e in at.error)
        self.assertIn("kunne ikke leses", varsel_tekster.lower())

        # Loggfilen skal fortsatt være helt urørt.
        with open(os.path.join(self._tmpdir.name, "e2e_test_korrupt_brygg_logg.json"), encoding="utf-8") as f:
            self.assertEqual(f.read(), "{dette er ikke gyldig json")


if __name__ == "__main__":
    unittest.main()
