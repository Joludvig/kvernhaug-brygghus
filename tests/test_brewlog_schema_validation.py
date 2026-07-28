"""
Tester for at hent_logg() validerer SCHEMAET til gyldig JSON, ikke bare
at innholdet parser som JSON i det hele tatt.

Bakgrunn: hent_logg() avviste tidligere ugyldig JSON (LoggKorruptError),
men godtok deretter EN HVILKEN SOM HELST gyldig JSON-verdi -- et objekt
({}), en streng, et tall, null, eller en liste med elementer som selv
ikke er objekter. lagre_logg_entry() gjør umiddelbart `logg.append(entry)`
på returverdien -- for alt annet enn en liste krasjer det med
AttributeError (f.eks. 'dict' object has no attribute 'append'), og for
en liste med ugyldige elementer ville UI-et (ui/recipe_card.py sin
_render_brewday_result_panel(), som bruker entry.get(...) på hver
oppføring) krasjet på visning.

hent_logg() krever nå at ROTEN er en liste, og at HVER eksisterende
oppføring er et objekt/dict -- ellers LoggKorruptError, filen urørt,
akkurat som ved ugyldig JSON.

Bruker UTELUKKENDE tempfile.TemporaryDirectory() via
KVERNHAUG_RECIPES_DIR -- aldri den ekte recipes/-mappen.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest

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

    def _skriv_ny_logg_raw(self, oppskrift_navn, raw_python_verdi):
        # Skriver DIREKTE til den NYE loggplasseringen (recipes/_logs/) --
        # simulerer en logg som allerede finnes der, med feil schema.
        logs_mappe = os.path.join(self._mappe(), "_logs")
        os.makedirs(logs_mappe, exist_ok=True)
        base = recipe_storage.generer_filnavn(oppskrift_navn).replace(".json", "_logg.json")
        with open(os.path.join(logs_mappe, base), "w", encoding="utf-8") as f:
            json.dump(raw_python_verdi, f, ensure_ascii=False)
        return os.path.join(logs_mappe, base)


class TestFeilRotTypeBlokkeres(_IsolertRecipeMappeTestCase):
    def test_objekt_i_stedet_for_liste_reiser_loggkorrupt(self):
        sti = self._skriv_ny_logg_raw("Feil Schema Objekt", {"date": "2026-07-28"})
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Schema Objekt")
        with open(sti, encoding="utf-8") as f:
            self.assertEqual(json.load(f), {"date": "2026-07-28"}, "Filen skal ikke ha blitt endret")

    def test_streng_i_stedet_for_liste_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Schema Streng", "dette er bare tekst")
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Schema Streng")

    def test_tall_i_stedet_for_liste_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Schema Tall", 42)
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Schema Tall")

    def test_null_i_stedet_for_liste_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Schema Null", None)
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Schema Null")


class TestListeMedUgyldigeElementerBlokkeres(_IsolertRecipeMappeTestCase):
    def test_liste_med_streng_element_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Element Streng", [{"date": "2026-07-01"}, "ikke et objekt"])
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Element Streng")

    def test_liste_med_tall_element_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Element Tall", [42, {"date": "2026-07-01"}])
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Element Tall")

    def test_liste_med_null_element_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Element Null", [{"date": "2026-07-01"}, None])
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Element Null")

    def test_liste_med_nestet_liste_element_reiser_loggkorrupt(self):
        self._skriv_ny_logg_raw("Feil Element Liste", [["ikke", "et", "objekt"]])
        with self.assertRaises(LoggKorruptError):
            recipe_storage.hent_logg("Feil Element Liste")


class TestGyldigSchemaFungererFortsatt(_IsolertRecipeMappeTestCase):
    def test_gyldig_tom_liste_er_ikke_en_feil(self):
        self._skriv_ny_logg_raw("Gyldig Tom Logg", [])
        self.assertEqual(recipe_storage.hent_logg("Gyldig Tom Logg"), [])

    def test_gyldig_liste_med_objekter_returneres_uendret(self):
        innhold = [{"date": "2026-07-01", "actual_og": 1.050}, {"date": "2026-08-01", "actual_og": 1.045}]
        self._skriv_ny_logg_raw("Gyldig Logg Med Data", innhold)
        self.assertEqual(recipe_storage.hent_logg("Gyldig Logg Med Data"), innhold)

    def test_lagre_logg_entry_fungerer_fortsatt_normalt_paa_gyldig_schema(self):
        self._skriv_ny_logg_raw("Gyldig Logg Append", [{"date": "2026-07-01"}])
        recipe_storage.lagre_logg_entry("Gyldig Logg Append", {"date": "2026-08-01"})
        self.assertEqual(
            recipe_storage.hent_logg("Gyldig Logg Append"),
            [{"date": "2026-07-01"}, {"date": "2026-08-01"}],
        )


class TestSchemaFeilBlokkererLagreLoggEntry(_IsolertRecipeMappeTestCase):
    def test_lagre_logg_entry_krasjer_ikke_med_attributeerror_men_reiser_loggkorrupt(self):
        # Den konkrete regresjonen dette fant: hent_logg() returnerte
        # tidligere et dict stille, og lagre_logg_entry() krasjet på
        # logg.append(entry) med AttributeError i stedet for en tydelig,
        # forventet LoggKorruptError.
        sti = self._skriv_ny_logg_raw("Feil Schema Append", {"ikke": "en liste"})
        with open(sti, "rb") as f:
            original_bytes = f.read()

        with self.assertRaises(LoggKorruptError):
            recipe_storage.lagre_logg_entry("Feil Schema Append", {"date": "2026-08-01"})

        with open(sti, "rb") as f:
            self.assertEqual(f.read(), original_bytes)
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))


if __name__ == "__main__":
    unittest.main()
