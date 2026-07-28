"""
Tester for _klassifiser_legacy_kandidat() (modules/recipe_storage.py) og
hvordan den brukes til å beskytte omdøping, sletting og ny loggoppføring
mot «X / X Logg»-kollisjonen: en oppskrift "Brygg" sin legacy-loggsti i
oppskriftsmappens rot ("brygg_logg.json") kan, ved ren navnetilfeldighet,
være NØYAKTIG samme filnavn som en HELT ANNEN oppskrift "Brygg Logg" sin
faktiske oppskriftfil.

Bakgrunn: en tidligere runde ga bryggelogger et eget filnavnrom
(recipes/_logs/) og validerte SCHEMAET til en etablert loggfil
(hent_logg()), men _omdoep_logg_hvis_finnes(),
_arkiver_kildefil_etter_omdoeping() og slett_oppskrift_fil() behandlet
fortsatt ENHVER eksisterende "<navn>_logg.json" i mapperoten som en
legacy-logg UTEN å sjekke om rotfilen faktisk var det. Codex reproduserte
konkret: sletting av "brygg.json" arkiverte BEGGE oppskriftene (siden
"brygg_logg.json" ble feiltolket som "Brygg" sin legacy-logg), og
omdøping av "Brygg" til "Brygg V2" flyttet "Brygg Logg" sin faktiske
oppskriftfil til "brygg_v2_logg.json".

_klassifiser_legacy_kandidat() løser dette ved å faktisk lese og
klassifisere innholdet FØR noen sideeffekt: en gyldig JSON-liste av
objekter er en ekte legacy-logg; et JSON-objekt med et "name"-felt er en
ANNEN oppskrift (skal aldri røres); alt annet er "ukjent" og blokkerer
hele operasjonen FØR noe skrives.

Bruker UTELUKKENDE tempfile.TemporaryDirectory() via
KVERNHAUG_RECIPES_DIR -- aldri den ekte recipes/-mappen.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest

from modules.recipe import bygg_recipe_object
import modules.recipe_storage as recipe_storage
from modules.recipe_storage import LegacyLoggKandidatUkjent


def _oppskrift(navn, mengde=5.0):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": mengde}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
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

    def _logs_mappe(self):
        return os.path.join(self._mappe(), "_logs")

    def _archive_mappe(self):
        return os.path.join(self._mappe(), "_archive")

    def _filer(self):
        return set(os.listdir(self._mappe()))

    def _logs_filer(self):
        mappe = self._logs_mappe()
        return set(os.listdir(mappe)) if os.path.isdir(mappe) else set()

    def _archive_filer(self):
        mappe = self._archive_mappe()
        return set(os.listdir(mappe)) if os.path.isdir(mappe) else set()

    def _skriv_legacy_logg(self, filnavn, innhold):
        with open(os.path.join(self._mappe(), filnavn), "w", encoding="utf-8") as f:
            json.dump(innhold, f, ensure_ascii=False, indent=2)

    def _skriv_raw(self, filnavn, raw_tekst):
        with open(os.path.join(self._mappe(), filnavn), "w", encoding="utf-8") as f:
            f.write(raw_tekst)


# --------------------------------------------------------------------
# 1. Sletting av "Brygg" når "Brygg Logg" finnes
# --------------------------------------------------------------------
class TestSlettingRoererAldriEnAnnenOppskriftMedKolliderendeLoggnavn(_IsolertRecipeMappeTestCase):
    def test_sletting_arkiverer_bare_brygg_og_lar_brygg_logg_staa_aktiv(self):
        brygg_filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Brygg"))
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))
        brygg_logg_sti = os.path.join(self._mappe(), "brygg_logg.json")
        with open(brygg_logg_sti, "rb") as f:
            original_bytes = f.read()

        resultat = recipe_storage.slett_oppskrift_fil(brygg_filnavn)

        self.assertTrue(resultat)
        # Bare brygg.json er arkivert.
        self.assertIn("brygg.json", self._archive_filer())
        self.assertNotIn("brygg_logg.json", self._archive_filer())
        # "Brygg Logg" er fortsatt aktiv, byte-for-byte uendret.
        self.assertIn("brygg_logg.json", self._filer())
        with open(brygg_logg_sti, "rb") as f:
            self.assertEqual(f.read(), original_bytes)
        # ... og fortsatt synlig i oppskriftslisten.
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg Logg", alle)
        self.assertNotIn("Brygg", alle)


# --------------------------------------------------------------------
# 2. Omdøping av "Brygg" til "Brygg V2" når "Brygg Logg" finnes
# --------------------------------------------------------------------
class TestOmdoepingRoererAldriEnAnnenOppskriftMedKolliderendeLoggnavn(_IsolertRecipeMappeTestCase):
    def test_omdoeping_lar_brygg_logg_staa_uendret_og_oppretter_ingen_brygg_v2_logg(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg"))
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))
        brygg_logg_sti = os.path.join(self._mappe(), "brygg_logg.json")
        with open(brygg_logg_sti, "rb") as f:
            original_bytes = f.read()

        nytt_filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Brygg V2"), kilde_filnavn="brygg.json")

        self.assertEqual(nytt_filnavn, "brygg_v2.json")
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg V2", alle)
        self.assertNotIn("Brygg", alle)

        # "Brygg Logg" beholder FILNAVN og INNHOLD byte-for-byte.
        self.assertIn("brygg_logg.json", self._filer())
        with open(brygg_logg_sti, "rb") as f:
            self.assertEqual(f.read(), original_bytes)
        self.assertIn("Brygg Logg", alle)

        # Ingen brygg_v2_logg.json opprettet i mapperoten på grunn av
        # den andre oppskriften.
        self.assertNotIn("brygg_v2_logg.json", self._filer())


# --------------------------------------------------------------------
# 3. lagre_logg_entry("Brygg", ...) når "Brygg Logg" finnes
# --------------------------------------------------------------------
class TestNyLoggOppfoeringRoererAldriEnAnnenOppskrift(_IsolertRecipeMappeTestCase):
    def test_lagre_logg_entry_lykkes_og_oppretter_logs_brygg_logg_json(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg"))
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))
        brygg_logg_sti = os.path.join(self._mappe(), "brygg_logg.json")
        with open(brygg_logg_sti, "rb") as f:
            original_bytes = f.read()

        recipe_storage.lagre_logg_entry("Brygg", {"date": "2026-07-01"})

        self.assertIn("brygg_logg.json", self._logs_filer())
        self.assertEqual(recipe_storage.hent_logg("Brygg"), [{"date": "2026-07-01"}])
        # Oppskriften "Brygg Logg" er verken lest inn som loggdata eller
        # endret -- fortsatt nøyaktig samme bytes på disk.
        with open(brygg_logg_sti, "rb") as f:
            self.assertEqual(f.read(), original_bytes)
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg Logg", alle)


# --------------------------------------------------------------------
# 4. En EKTE legacy-logg fungerer fortsatt helt normalt
# --------------------------------------------------------------------
class TestEkteLegacyLoggFungererFortsattNormalt(_IsolertRecipeMappeTestCase):
    def test_kan_leses(self):
        self._skriv_legacy_logg("ekte_legacy_logg.json", [{"date": "2020-01-01", "note": "gammelt brygg"}])
        self.assertEqual(
            recipe_storage.hent_logg("Ekte Legacy"),
            [{"date": "2020-01-01", "note": "gammelt brygg"}],
        )

    def test_kan_oppdateres_i_mapperoten_uten_migrering(self):
        self._skriv_legacy_logg("ekte_legacy_2_logg.json", [{"date": "2020-01-01"}])
        recipe_storage.lagre_logg_entry("Ekte Legacy 2", {"date": "2026-07-28"})

        self.assertIn("ekte_legacy_2_logg.json", self._filer())
        self.assertNotIn("ekte_legacy_2_logg.json", self._logs_filer())
        with open(os.path.join(self._mappe(), "ekte_legacy_2_logg.json"), encoding="utf-8") as f:
            self.assertEqual(len(json.load(f)), 2)

    def test_foelger_riktig_oppskrift_ved_omdoeping(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Ekte Legacy 3"))
        self._skriv_legacy_logg("ekte_legacy_3_logg.json", [{"date": "2019-05-05"}])

        recipe_storage.lagre_oppskrift(
            _oppskrift("Ekte Legacy 3 V2"), kilde_filnavn="ekte_legacy_3.json",
        )

        self.assertIn("ekte_legacy_3_v2_logg.json", self._filer())
        self.assertNotIn("ekte_legacy_3_logg.json", self._filer())
        self.assertEqual(recipe_storage.hent_logg("Ekte Legacy 3 V2"), [{"date": "2019-05-05"}])

    def test_arkiveres_sammen_med_riktig_oppskrift(self):
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Ekte Legacy 4"))
        self._skriv_legacy_logg("ekte_legacy_4_logg.json", [{"date": "2018-03-03"}])

        recipe_storage.slett_oppskrift_fil(filnavn)

        self.assertIn("ekte_legacy_4_logg.json", self._archive_filer())
        self.assertNotIn("ekte_legacy_4_logg.json", self._filer())


# --------------------------------------------------------------------
# 5. Korrupt/uleselig legacy-kandidat blokkerer FØR enhver sideeffekt
# --------------------------------------------------------------------
class TestKorruptLegacyKandidatBlokkererFoerSideeffekt(_IsolertRecipeMappeTestCase):
    def test_korrupt_kandidat_blokkerer_omdoeping_uten_sideeffekt(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Ukjent Kandidat"))
        self._skriv_raw("ukjent_kandidat_logg.json", "{ikke gyldig json")
        with open(os.path.join(self._mappe(), "ukjent_kandidat.json"), "rb") as f:
            recipe_bytes = f.read()
        with open(os.path.join(self._mappe(), "ukjent_kandidat_logg.json"), "rb") as f:
            logg_bytes = f.read()

        with self.assertRaises(LegacyLoggKandidatUkjent):
            recipe_storage.lagre_oppskrift(_oppskrift("Ukjent Kandidat V2"), kilde_filnavn="ukjent_kandidat.json")

        # INGEN sideeffekt: hverken ny fil, arkivering, eller endring av
        # noen av de berørte filene.
        self.assertIn("ukjent_kandidat.json", self._filer())
        self.assertNotIn("ukjent_kandidat_v2.json", self._filer())
        with open(os.path.join(self._mappe(), "ukjent_kandidat.json"), "rb") as f:
            self.assertEqual(f.read(), recipe_bytes)
        with open(os.path.join(self._mappe(), "ukjent_kandidat_logg.json"), "rb") as f:
            self.assertEqual(f.read(), logg_bytes)
        self.assertFalse(os.path.isdir(self._archive_mappe()))
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))
        self.assertFalse(os.path.isdir(self._logs_mappe()))
        self.assertFalse(any(".tmp_" in f for f in self._filer()))

    def test_korrupt_kandidat_blokkerer_sletting_uten_sideeffekt(self):
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Ukjent Kandidat Slett"))
        self._skriv_raw("ukjent_kandidat_slett_logg.json", "42")  # gyldig JSON, men verken liste eller objekt-med-name
        with open(os.path.join(self._mappe(), filnavn), "rb") as f:
            recipe_bytes = f.read()

        with self.assertRaises(LegacyLoggKandidatUkjent):
            recipe_storage.slett_oppskrift_fil(filnavn)

        self.assertIn(filnavn, self._filer())
        with open(os.path.join(self._mappe(), filnavn), "rb") as f:
            self.assertEqual(f.read(), recipe_bytes)
        self.assertIn("ukjent_kandidat_slett_logg.json", self._filer())
        self.assertFalse(os.path.isdir(self._archive_mappe()))
        self.assertFalse(any(".tmp_" in f for f in self._filer()))

    def test_uleselig_utf8_kandidat_blokkerer_ny_loggoppfoering(self):
        # Ugyldige UTF-8-bytes -- kan ikke engang åpnes med
        # encoding="utf-8" for å klassifiseres.
        with open(os.path.join(self._mappe(), "ukjent_kandidat_utf8_logg.json"), "wb") as f:
            f.write(b"\xff\xfe\x00\xff ikke gyldig utf-8")

        with self.assertRaises(recipe_storage.LoggKorruptError):
            recipe_storage.lagre_logg_entry("Ukjent Kandidat Utf8", {"date": "2026-07-28"})

        with open(os.path.join(self._mappe(), "ukjent_kandidat_utf8_logg.json"), "rb") as f:
            self.assertEqual(f.read(), b"\xff\xfe\x00\xff ikke gyldig utf-8")
        self.assertFalse(os.path.isdir(self._logs_mappe()))
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))


# --------------------------------------------------------------------
# 6. Ny _logs-logg, legacy-logg, og begge samtidig
# --------------------------------------------------------------------
class TestNyLoggOgLegacyLoggSamtidig(_IsolertRecipeMappeTestCase):
    def test_kun_ny_logs_logg_brukes_direkte(self):
        recipe_storage.lagre_logg_entry("Kun Ny", {"date": "2026-07-01"})
        self.assertIn("kun_ny_logg.json", self._logs_filer())
        self.assertEqual(recipe_storage.hent_logg("Kun Ny"), [{"date": "2026-07-01"}])

    def test_kun_legacy_logg_brukes_uten_migrering(self):
        self._skriv_legacy_logg("kun_legacy_logg.json", [{"date": "2020-01-01"}])
        self.assertEqual(recipe_storage.hent_logg("Kun Legacy"), [{"date": "2020-01-01"}])
        self.assertNotIn("kun_legacy_logg.json", self._logs_filer())

    def test_begge_finnes_ny_plassering_vinner_og_legacy_roeres_ikke(self):
        os.makedirs(self._logs_mappe(), exist_ok=True)
        with open(os.path.join(self._logs_mappe(), "begge_logg.json"), "w", encoding="utf-8") as f:
            json.dump([{"date": "2026-08-01", "note": "ny"}], f)
        self._skriv_legacy_logg("begge_logg.json", [{"date": "2020-01-01", "note": "legacy"}])
        with open(os.path.join(self._mappe(), "begge_logg.json"), "rb") as f:
            legacy_original_bytes = f.read()

        # Lesing: den NYE plasseringen vinner, legacy ignoreres helt.
        self.assertEqual(recipe_storage.hent_logg("Begge"), [{"date": "2026-08-01", "note": "ny"}])

        # Skriving: fortsetter i den NYE plasseringen.
        recipe_storage.lagre_logg_entry("Begge", {"date": "2026-08-02", "note": "enda nyere"})
        self.assertEqual(
            recipe_storage.hent_logg("Begge"),
            [{"date": "2026-08-01", "note": "ny"}, {"date": "2026-08-02", "note": "enda nyere"}],
        )

        # Legacy-filen er HELT urørt.
        with open(os.path.join(self._mappe(), "begge_logg.json"), "rb") as f:
            self.assertEqual(f.read(), legacy_original_bytes)

    def test_sletting_med_begge_arkiverer_begge(self):
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Begge Slett"))
        os.makedirs(self._logs_mappe(), exist_ok=True)
        with open(os.path.join(self._logs_mappe(), "begge_slett_logg.json"), "w", encoding="utf-8") as f:
            json.dump([{"date": "2026-08-01"}], f)
        self._skriv_legacy_logg("begge_slett_logg.json", [{"date": "2020-01-01"}])

        recipe_storage.slett_oppskrift_fil(filnavn)

        arkiv = self._archive_filer()
        self.assertEqual(len([f for f in arkiv if f.startswith("begge_slett_logg")]), 2)
        self.assertNotIn("begge_slett_logg.json", self._filer())
        self.assertNotIn("begge_slett_logg.json", self._logs_filer())


if __name__ == "__main__":
    unittest.main()
