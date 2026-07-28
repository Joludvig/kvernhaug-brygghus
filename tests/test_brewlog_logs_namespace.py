"""
Tester for at bryggelogger har et EGET filnavnrom (recipes/_logs/),
adskilt fra selve oppskriftsfilenes navnerom i oppskriftsmappens rot.

Bakgrunn: bryggelogger ble tidligere lagret som
"<oppskriftsnavn>_logg.json" DIREKTE i oppskriftsmappen, mens
_skann_oppskriftsfiler() samtidig filtrerte bort alle filer som endte
på "_logg.json". Det ga to problemer:

  1. En oppskrift som selv heter noe som ender på ordet "logg" -- f.eks.
     "Brygg Logg" -> kanonisk filnavn "brygg_logg.json" -- ble FEILAKTIG
     filtrert bort av skanningen, som om DEN var en loggfil.
  2. Oppskriften "Brygg" sin logg ("brygg_logg.json") kunne kollidere
     med -- eller bli overskrevet av -- en annen oppskrift som
     tilfeldigvis het "Brygg Logg" og dermed produserte akkurat det
     samme filnavnet.

Nye logger skrives nå til recipes/_logs/ -- et helt eget navnerom som
aldri kan kollidere med en oppskriftsfil. Eksisterende, PRIVATE
legacy-logger i oppskriftsmappens rot forblir der de er (lesetilgang
bevares via _legacy_logg_filsti()) -- denne endringen migrerer/flytter
ALDRI eksisterende data automatisk, verken ved vanlig lesing, vanlig
"legg til brygg"-bruk, eller ved omdøping av oppskriften loggen
tilhører.

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

    def _filer(self):
        return set(os.listdir(self._mappe()))

    def _logs_filer(self):
        mappe = self._logs_mappe()
        return set(os.listdir(mappe)) if os.path.isdir(mappe) else set()

    def _skriv_legacy_logg(self, filnavn, innhold):
        # Simulerer en logg som ble opprettet FØR recipes/_logs/ ble
        # innført -- direkte i oppskriftsmappens rot.
        with open(os.path.join(self._mappe(), filnavn), "w", encoding="utf-8") as f:
            json.dump(innhold, f, ensure_ascii=False, indent=2)


class TestOppskriftMedLoggIeNavnetFungererNormalt(_IsolertRecipeMappeTestCase):
    def test_lagres_lastes_og_vises_normalt(self):
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))
        self.assertEqual(filnavn, "brygg_logg.json")
        self.assertIn("brygg_logg.json", self._filer())

        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg Logg", alle, "Oppskriften skal IKKE filtreres bort bare fordi filnavnet ender på _logg.json")

        kart = recipe_storage.hent_oppskrift_filnavn_kart()
        self.assertEqual(kart["Brygg Logg"], "brygg_logg.json")

    def test_kan_omdoepes_normalt(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))
        nytt_filnavn = recipe_storage.lagre_oppskrift(
            _oppskrift("Brygg Logg V2"), kilde_filnavn="brygg_logg.json",
        )
        self.assertEqual(nytt_filnavn, "brygg_logg_v2.json")
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg Logg V2", alle)
        self.assertNotIn("Brygg Logg", alle)


class TestToOppskrifterDelerAldriLogg(_IsolertRecipeMappeTestCase):
    def test_to_urelaterte_oppskrifter_har_hver_sin_uavhengige_logg(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Vinterøl"))
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))

        recipe_storage.lagre_logg_entry("Vinterøl", {"date": "2026-07-01", "note": "Vinterøl sin logg"})
        recipe_storage.lagre_logg_entry("Brygg Logg", {"date": "2026-07-02", "note": "Brygg Logg sin logg"})

        logg_vinterol = recipe_storage.hent_logg("Vinterøl")
        logg_brygg_logg = recipe_storage.hent_logg("Brygg Logg")

        self.assertEqual(len(logg_vinterol), 1)
        self.assertEqual(logg_vinterol[0]["note"], "Vinterøl sin logg")
        self.assertEqual(len(logg_brygg_logg), 1)
        self.assertEqual(logg_brygg_logg[0]["note"], "Brygg Logg sin logg")

        logg_filer = self._logs_filer()
        self.assertIn("vinterol_logg.json", logg_filer)
        self.assertIn("brygg_logg_logg.json", logg_filer)
        self.assertEqual(len(logg_filer), 2)

        # Og begge oppskriftene er fortsatt synlige og uavhengige.
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Vinterøl", alle)
        self.assertIn("Brygg Logg", alle)


class TestLegacyFallbackKollidererAldriMedEnAnnenOppskriftsfil(_IsolertRecipeMappeTestCase):
    """Dokumenterer og bekrefter et bevisst, trygt "fail closed"-valg for
    et ekstremt sjeldent grensetilfelle: en oppskrift "Brygg" sin
    LEGACY-loggsti (mappe-roten, "brygg_logg.json") er, ren tekstlig,
    NØYAKTIG samme filnavn som en HELT ANNEN oppskrift "Brygg Logg" sin
    faktiske OPPSKRIFTFIL ville hatt. Dette kan bare skje for et
    "X"/"X Logg"-navnepar der "X" ALDRI har hatt en logg fra før (ingen
    fil i _logs/ for X) OG "Brygg Logg" faktisk finnes som lagret
    oppskrift. Schema-valideringen i hent_logg() (se
    tests/test_brewlog_schema_validation.py) sørger for at dette ALDRI
    fører til datatap eller krasj -- et forsøk på å logge "Brygg" i
    dette tilfellet reiser LoggKorruptError, og "Brygg Logg" sin
    faktiske oppskriftfil forblir fullstendig, byte-for-byte uendret."""

    def test_kolliderende_legacy_sti_reiser_loggkorrupt_uten_aa_roere_den_andre_oppskriften(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg"))
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg Logg"))

        brygg_logg_recipe_sti = os.path.join(self._mappe(), "brygg_logg.json")
        with open(brygg_logg_recipe_sti, "rb") as f:
            original_bytes = f.read()

        with self.assertRaises(recipe_storage.LoggKorruptError):
            recipe_storage.lagre_logg_entry("Brygg", {"date": "2026-07-01", "note": "Skal ikke skrives"})

        # "Brygg Logg" sin EGEN oppskriftfil skal stå fullstendig uendret
        # -- IKKE ha blitt "sikkerhetskopiert og overskrevet" som om den
        # var "Brygg" sin loggfil.
        with open(brygg_logg_recipe_sti, "rb") as f:
            self.assertEqual(f.read(), original_bytes)
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg Logg", alle)


class TestNyLoggHavnerILogsUndermappe(_IsolertRecipeMappeTestCase):
    def test_ny_logg_skrives_til_logs_undermappe_ikke_til_mapperoten(self):
        recipe_storage.lagre_logg_entry("Ny Logg Test", {"date": "2026-07-28"})
        self.assertIn("ny_logg_test_logg.json", self._logs_filer())
        self.assertNotIn("ny_logg_test_logg.json", self._filer())


class TestLegacyLoggLesesUtenMigrering(_IsolertRecipeMappeTestCase):
    def test_legacy_logg_leses_korrekt_uten_aa_bli_flyttet(self):
        self._skriv_legacy_logg("legacy_brygg_logg.json", [{"date": "2020-01-01", "note": "Gammel logg"}])

        logg = recipe_storage.hent_logg("Legacy Brygg")
        self.assertEqual(logg, [{"date": "2020-01-01", "note": "Gammel logg"}])

        # Filen skal fortsatt ligge i roten -- IKKE ha blitt flyttet til
        # _logs/ bare fordi den ble lest.
        self.assertIn("legacy_brygg_logg.json", self._filer())
        self.assertNotIn("legacy_brygg_logg.json", self._logs_filer())

    def test_ny_oppfoering_i_legacy_logg_forblir_i_legacy_plassering(self):
        self._skriv_legacy_logg("legacy_brygg_2_logg.json", [{"date": "2020-01-01"}])

        recipe_storage.lagre_logg_entry("Legacy Brygg 2", {"date": "2026-07-28"})

        # Loggen skal fortsatt stå i ROTEN, med BEGGE oppføringene --
        # IKKE ha blitt (implisitt) migrert til _logs/ bare fordi en ny
        # oppføring ble lagt til.
        self.assertIn("legacy_brygg_2_logg.json", self._filer())
        self.assertNotIn("legacy_brygg_2_logg.json", self._logs_filer())
        with open(os.path.join(self._mappe(), "legacy_brygg_2_logg.json"), encoding="utf-8") as f:
            innhold = json.load(f)
        self.assertEqual(len(innhold), 2)

    def test_legacy_logg_tar_ogsaa_backup_foer_ny_oppfoering(self):
        self._skriv_legacy_logg("legacy_brygg_3_logg.json", [{"date": "2020-01-01"}])
        recipe_storage.lagre_logg_entry("Legacy Brygg 3", {"date": "2026-07-28"})

        backup_mappe = os.path.join(self._mappe(), "_backup")
        self.assertTrue(os.path.isdir(backup_mappe))
        backupfiler = [f for f in os.listdir(backup_mappe) if f.startswith("legacy_brygg_3_logg.json.backup_")]
        self.assertEqual(len(backupfiler), 1)


class TestOmdoepingRespekterLoggensNavnerom(_IsolertRecipeMappeTestCase):
    def test_ny_logg_forblir_i_logs_mappe_ved_omdoeping(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Med Ny Logg"))
        recipe_storage.lagre_logg_entry("Med Ny Logg", {"date": "2026-07-27"})

        recipe_storage.lagre_oppskrift(_oppskrift("Med Ny Logg V2"), kilde_filnavn="med_ny_logg.json")

        self.assertIn("med_ny_logg_v2_logg.json", self._logs_filer())
        self.assertNotIn("med_ny_logg_logg.json", self._logs_filer())
        self.assertEqual(recipe_storage.hent_logg("Med Ny Logg V2"), [{"date": "2026-07-27"}])

    def test_legacy_logg_forblir_i_mapperoten_ved_omdoeping(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Med Legacy Logg"))
        self._skriv_legacy_logg("med_legacy_logg_logg.json", [{"date": "2019-05-05"}])

        recipe_storage.lagre_oppskrift(
            _oppskrift("Med Legacy Logg V2"), kilde_filnavn="med_legacy_logg.json",
        )

        # Loggen omdøpes til det NYE navnet, men blir værende i SAMME
        # (legacy) mappe -- ingen implisitt migrering til _logs/.
        self.assertIn("med_legacy_logg_v2_logg.json", self._filer())
        self.assertNotIn("med_legacy_logg_v2_logg.json", self._logs_filer())
        self.assertEqual(recipe_storage.hent_logg("Med Legacy Logg V2"), [{"date": "2019-05-05"}])


class TestSlettingArkivererLoggFraBeggeNavnerom(_IsolertRecipeMappeTestCase):
    def test_sletting_arkiverer_ny_logg_fra_logs_mappe(self):
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Slett Med Ny Logg"))
        recipe_storage.lagre_logg_entry("Slett Med Ny Logg", {"date": "2026-07-27"})

        recipe_storage.slett_oppskrift_fil(filnavn)

        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertIn("slett_med_ny_logg_logg.json", os.listdir(arkiv_mappe))
        self.assertNotIn("slett_med_ny_logg_logg.json", self._logs_filer())

    def test_sletting_arkiverer_legacy_logg_fra_mapperoten(self):
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Slett Med Legacy Logg"))
        self._skriv_legacy_logg("slett_med_legacy_logg_logg.json", [{"date": "2019-01-01"}])

        recipe_storage.slett_oppskrift_fil(filnavn)

        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertIn("slett_med_legacy_logg_logg.json", os.listdir(arkiv_mappe))
        self.assertNotIn("slett_med_legacy_logg_logg.json", self._filer())


if __name__ == "__main__":
    unittest.main()
