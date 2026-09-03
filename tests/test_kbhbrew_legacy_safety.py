"""
PRI 3B1 (issue #24) -- legacy-safety-tester. Beviser at INGENTING i den
nye `.kbhbrew`-motoren (modules/kbhbrew.py, modules/kbhbrew_storage.py)
leser, konverterer, migrerer eller på annen måte rører eksisterende App
legacy-bryggelogger (recipes/_logs/, modules/recipe_storage.py) -- se
issue #24 "Critical legacy rule -- legacy conversion/export is OUT" og
Section 7 "Legacy safety".

Denne modulen bygger ALDRI et Core V1-snapshot fra en legacy-
loggoppføring, og eksponerer ingen konverterings-/eksportfunksjon for
dem i det hele tatt -- disse testene beviser at negativet stemmer:
ingen slik funksjon finnes, og de frosne legacy-fixturene endres aldri
bare fordi den nye motoren importeres/kjøres.

Kjøres med:
    python3 -m unittest tests.test_kbhbrew_legacy_safety -b
"""
import inspect
import os
import tempfile
import unittest

import modules.kbhbrew as kbhbrew
import modules.kbhbrew_storage as kbhbrew_storage
import modules.recipe_storage as recipe_storage
from modules.recipe import bygg_recipe_object

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LEGACY_APP_FIXTURE = os.path.join(_ROOT, "tests", "fixtures", "legacy", "app", "brew_log.json")


def _recipe(navn="Legacy Trygghet"):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
    )


def _dbs():
    return (
        {"weyermann_pilsner": {"display_name": "Weyermann Pilsner", "ebc": 3.5, "potensiale": 1.037}},
        {},
        {"safale_us_05": {"display_name": "SafAle US-05", "attenuation": 0.75}},
    )


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


class TestNoConversionExportFunctionExistsAtAll(unittest.TestCase):
    """Section 7 "Legacy safety" + explicit non-goals: PRI 3B1 must not
    expose a legacy -> `.kbhbrew` conversion/export action. Proven here
    by asserting no such name exists on either module's public surface
    -- not just "unused", genuinely absent."""

    def test_no_legacy_conversion_symbol_on_kbhbrew_module(self):
        navn = {n for n, _ in inspect.getmembers(kbhbrew) if not n.startswith("_")}
        for mistenkelig in ("konverter_legacy", "convert_legacy", "legacy_to_kbhbrew", "eksporter_legacy_logg"):
            self.assertNotIn(mistenkelig, navn)

    def test_no_legacy_conversion_symbol_on_kbhbrew_storage_module(self):
        navn = {n for n, _ in inspect.getmembers(kbhbrew_storage) if not n.startswith("_")}
        for mistenkelig in ("konverter_legacy", "convert_legacy", "legacy_to_kbhbrew", "eksporter_legacy_logg", "migrer_legacy_logg"):
            self.assertNotIn(mistenkelig, navn)

    def test_kbhbrew_module_never_imports_recipe_storage(self):
        # The pure engine module must have zero coupling to the legacy
        # log storage layer -- it doesn't even know recipes/_logs/ exists.
        # Checked against actual import statements only (not prose in
        # docstrings/comments, which legitimately reference the legacy
        # module by name for context).
        import_linjer = [
            linje.strip() for linje in inspect.getsource(kbhbrew).splitlines()
            if linje.strip().startswith("import ") or linje.strip().startswith("from ")
        ]
        for linje in import_linjer:
            self.assertNotIn("recipe_storage", linje)


class TestExistingLegacyFixtureUnreadByNewEngine(unittest.TestCase):
    def test_legacy_app_fixture_is_a_flat_list_the_new_reader_would_reject(self):
        import json
        with open(_LEGACY_APP_FIXTURE, "r", encoding="utf-8") as f:
            tekst = f.read()
        # The legacy fixture is a bare JSON list (no {format,version,brew}
        # envelope) -- parse_kbhbrew_json() must reject it outright, never
        # silently reinterpret a legacy entry as a Core V1 brew.
        with self.assertRaises(kbhbrew.UgyldigKbhbrewForImport) as ctx:
            kbhbrew.parse_kbhbrew_json(tekst)
        self.assertEqual(ctx.exception.kategori, kbhbrew.KATEGORI_INVALID_ENVELOPE)
        # Sanity: the fixture itself is untouched/still a plain list.
        self.assertIsInstance(json.loads(tekst), list)


class TestLegacyLogsUntouchedByNewEngineRuntime(_IsolertRecipeMappeTestCase):
    def test_creating_new_brews_never_reads_or_writes_legacy_logs(self):
        recipe_storage.lagre_oppskrift(_recipe())
        recipe_storage.lagre_logg_entry(
            "Legacy Trygghet",
            {"date": "2026-01-15", "actual_volume_l": 20.0, "actual_og": 1.049, "actual_fg": 1.013,
             "actual_abv": 4.7, "note": ""},
        )
        legacy_logg_foer = recipe_storage.hent_logg("Legacy Trygghet")
        logg_filsti = os.path.join(self._mappe(), "_logs", "legacy_trygghet_logg.json")
        with open(logg_filsti, "rb") as f:
            bytes_foer = f.read()

        malt_db, humle_db, gjaer_db = _dbs()
        kbhbrew_storage.opprett_og_lagre_ny_brew(_recipe(), malt_db, humle_db, gjaer_db, None, {})
        kbhbrew_storage.hent_alle_brews()

        with open(logg_filsti, "rb") as f:
            bytes_etter = f.read()
        self.assertEqual(bytes_foer, bytes_etter)
        self.assertEqual(recipe_storage.hent_logg("Legacy Trygghet"), legacy_logg_foer)

    def test_no_synthetic_snapshot_created_for_an_old_legacy_entry(self):
        recipe_storage.lagre_oppskrift(_recipe("Gammelt Brygg"))
        recipe_storage.lagre_logg_entry(
            "Gammelt Brygg",
            {"date": "2020-01-01", "actual_volume_l": 20.0, "actual_og": 1.045, "actual_fg": 1.010,
             "actual_abv": 4.6, "note": "Gammel loggoppføring"},
        )
        # The new kbhbrew namespace must not spontaneously contain
        # anything derived from this legacy entry -- it did not exist
        # before, and merely having a legacy log must not create one.
        self.assertEqual(kbhbrew_storage.hent_alle_brews(), {})
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_kbhbrew")))

    def test_legacy_note_field_is_never_read_or_classified_by_the_new_engine(self):
        # Section 3/#4 (ratified Option C, deferred): legacy `note` must
        # never be auto-split into actuals.notes/sensing.notes. Proven by
        # showing the new engine's normalizers have no code path that
        # reads a field literally named "note" (singular -- the legacy
        # App field) at all; the V1 wire shape only ever uses the plural,
        # distinct `notes` fields on `actuals`/`sensing`.
        kilde = inspect.getsource(kbhbrew)
        self.assertNotIn('"note"', kilde)
        self.assertNotIn("get('note')", kilde)


if __name__ == "__main__":
    unittest.main()
