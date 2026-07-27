"""
Tester for herdingen av modules/recipe_storage.py: atomisk lagring,
automatisk backup før overskriving, arkivering (aldri permanent
sletting) og navnekollisjon-blokkering ved omdøping/kopiering.

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

from modules.recipe import bygg_recipe_object
import modules.recipe_storage as recipe_storage
from modules.recipe_storage import OppskriftNavnKollisjon


def _oppskrift(navn, mengde=5.0):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": mengde}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {"Brød": 3},
    )


class _IsolertRecipeMappeTestCase(unittest.TestCase):
    """Isolerer recipe_storage._mappe() til en fersk TemporaryDirectory
    per test, via KVERNHAUG_RECIPES_DIR (samme mønster som
    tests/test_recipe_storage_isolation.py). Rører aldri den ekte
    recipes/-mappen."""

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


class TestAtomiskLagring(_IsolertRecipeMappeTestCase):
    def test_ingen_tmp_fil_ligger_igjen_etter_vellykket_lagring(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Atomisk Test"))
        filer = self._filer()
        self.assertIn("atomisk_test.json", filer)
        self.assertFalse(any(f.startswith("atomisk_test.json.tmp") for f in filer))

    def test_lagring_bruker_os_replace_ikke_direkte_write(self):
        # Skriv en første versjon, så en oppdatert versjon -- begge skal
        # være fullt lesbare hele veien, ingen delvis skrevet fil.
        recipe_storage.lagre_oppskrift(_oppskrift("Atomisk Test 2", mengde=5.0))
        recipe_storage.lagre_oppskrift(_oppskrift("Atomisk Test 2", mengde=7.0))
        lest = recipe_storage.hent_alle_oppskrifter()["Atomisk Test 2"]
        self.assertEqual(lest["malts"][0]["mengde"], 7.0)


class TestAutomatiskBackup(_IsolertRecipeMappeTestCase):
    def test_forste_lagring_lager_ingen_backup(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Ny Oppskrift"))
        backup_mappe = os.path.join(self._mappe(), "_backup")
        self.assertFalse(os.path.isdir(backup_mappe))

    def test_overskriving_lager_tidsstemplet_backup_av_forrige_versjon(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Backup Test", mengde=5.0))
        recipe_storage.lagre_oppskrift(_oppskrift("Backup Test", mengde=6.0))

        backup_mappe = os.path.join(self._mappe(), "_backup")
        self.assertTrue(os.path.isdir(backup_mappe))
        backupfiler = [f for f in os.listdir(backup_mappe) if f.startswith("backup_test.json.backup_")]
        self.assertEqual(len(backupfiler), 1)

        with open(os.path.join(backup_mappe, backupfiler[0]), encoding="utf-8") as f:
            backup_innhold = json.load(f)
        self.assertEqual(backup_innhold["malts"][0]["mengde"], 5.0, "Backupen skal inneholde DEN GAMLE verdien")

        lest = recipe_storage.hent_alle_oppskrifter()["Backup Test"]
        self.assertEqual(lest["malts"][0]["mengde"], 6.0, "Selve filen skal ha DEN NYE verdien")

    def test_backup_ryddes_til_maks_antall(self):
        for i in range(recipe_storage.RECIPE_BACKUP_MAKS_ANTALL + 5):
            recipe_storage.lagre_oppskrift(_oppskrift("Rydde Test", mengde=float(i)))
        backup_mappe = os.path.join(self._mappe(), "_backup")
        backupfiler = [f for f in os.listdir(backup_mappe) if f.startswith("rydde_test.json.backup_")]
        self.assertEqual(len(backupfiler), recipe_storage.RECIPE_BACKUP_MAKS_ANTALL)


class TestOmdoeping(_IsolertRecipeMappeTestCase):
    def test_omdoeping_skriver_ny_fil_og_arkiverer_gammel_kildefil(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Gammelt Navn"))
        nytt_filnavn = recipe_storage.lagre_oppskrift(
            _oppskrift("Nytt Navn"), kilde_filnavn="gammelt_navn.json",
        )
        self.assertEqual(nytt_filnavn, "nytt_navn.json")

        filer = self._filer()
        self.assertIn("nytt_navn.json", filer)
        self.assertNotIn("gammelt_navn.json", filer, "Den gamle kildefilen skal IKKE ligge igjen i aktiv mappe")

        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertIn("gammelt_navn.json", os.listdir(arkiv_mappe))

        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertEqual(len(alle), 1, "Skal kun finnes ÉN aktiv oppskrift etter omdøping")
        self.assertIn("Nytt Navn", alle)
        self.assertNotIn("Gammelt Navn", alle)

    def test_omdoeping_migrerer_tilhoerende_loggfil(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Med Logg"))
        recipe_storage.lagre_logg_entry("Med Logg", {"date": "2026-07-27", "actual_og": 1.050})

        recipe_storage.lagre_oppskrift(_oppskrift("Med Logg V2"), kilde_filnavn="med_logg.json")

        self.assertEqual(recipe_storage.hent_logg("Med Logg V2"), [{"date": "2026-07-27", "actual_og": 1.050}])
        self.assertEqual(recipe_storage.hent_logg("Med Logg"), [], "Den gamle loggnøkkelen skal ikke lenger ha noe innhold")
        self.assertNotIn("med_logg_logg.json", self._filer())
        self.assertIn("med_logg_v2_logg.json", self._filer())

    def test_uendret_navn_er_bare_en_vanlig_oppdatering_ingen_arkivering(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Uendret Navn", mengde=5.0))
        recipe_storage.lagre_oppskrift(_oppskrift("Uendret Navn", mengde=9.0), kilde_filnavn="uendret_navn.json")

        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertFalse(os.path.isdir(arkiv_mappe), "Ingen arkivering skal skje når filnavnet ikke endres")
        lest = recipe_storage.hent_alle_oppskrifter()["Uendret Navn"]
        self.assertEqual(lest["malts"][0]["mengde"], 9.0)


class TestNavnekollisjon(_IsolertRecipeMappeTestCase):
    def test_lagre_som_ny_kopi_med_navn_som_allerede_finnes_blokkeres(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Original"))
        with self.assertRaises(OppskriftNavnKollisjon):
            recipe_storage.lagre_oppskrift(
                _oppskrift("Original", mengde=99.0),
                kilde_filnavn=None, bloker_ved_navnekollisjon=True,
            )

        # Originalen skal IKKE ha blitt overskrevet stille.
        lest = recipe_storage.hent_alle_oppskrifter()["Original"]
        self.assertNotEqual(lest["malts"][0]["mengde"], 99.0)

    def test_omdoeping_til_et_navn_som_allerede_er_i_bruk_blokkeres(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg A"))
        recipe_storage.lagre_oppskrift(_oppskrift("Brygg B"))

        with self.assertRaises(OppskriftNavnKollisjon):
            recipe_storage.lagre_oppskrift(_oppskrift("Brygg B", mengde=42.0), kilde_filnavn="brygg_a.json")

        # Ingen av filene skal ha blitt rørt av det avviste forsøket.
        alle = recipe_storage.hent_alle_oppskrifter()
        self.assertIn("Brygg A", alle)
        self.assertIn("Brygg B", alle)
        self.assertNotEqual(alle["Brygg B"]["malts"][0]["mengde"], 42.0)
        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertFalse(os.path.isdir(arkiv_mappe))

    def test_direkte_kall_uten_kildefil_og_uten_blokkering_overskriver_som_foer(self):
        # bloker_ved_navnekollisjon=False (standard) -- et vanlig, direkte
        # lagre_oppskrift(recipe)-kall utenfor "Lagre som ny kopi"-knappen
        # (f.eks. fra et skript eller en annen test) skal beholde den
        # opprinnelige opprett-eller-oppdater-ved-navn-oppførselen.
        recipe_storage.lagre_oppskrift(_oppskrift("Direkte Kall", mengde=1.0))
        recipe_storage.lagre_oppskrift(_oppskrift("Direkte Kall", mengde=2.0))
        lest = recipe_storage.hent_alle_oppskrifter()["Direkte Kall"]
        self.assertEqual(lest["malts"][0]["mengde"], 2.0)

    def test_samme_kildefil_som_maalfil_er_ikke_en_kollisjon(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Selvoppdatering", mengde=1.0))
        try:
            recipe_storage.lagre_oppskrift(
                _oppskrift("Selvoppdatering", mengde=2.0), kilde_filnavn="selvoppdatering.json",
            )
        except OppskriftNavnKollisjon:
            self.fail("En vanlig, ikke-omdøpende oppdatering skal ALDRI regnes som en kollisjon")


class TestSlettingArkivererIkkeSletter(_IsolertRecipeMappeTestCase):
    def test_slett_flytter_til_archive_i_stedet_for_aa_fjerne(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Skal Arkiveres"))
        resultat = recipe_storage.slett_oppskrift_fil("Skal Arkiveres")
        self.assertTrue(resultat)

        self.assertNotIn("skal_arkiveres.json", self._filer())
        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertIn("skal_arkiveres.json", os.listdir(arkiv_mappe))

        # Innholdet skal fortsatt være fullt lesbart i arkivet -- ingen
        # data gikk tapt.
        with open(os.path.join(arkiv_mappe, "skal_arkiveres.json"), encoding="utf-8") as f:
            arkivert = json.load(f)
        self.assertEqual(arkivert["name"], "Skal Arkiveres")

    def test_slett_arkiverer_ogsaa_tilhoerende_loggfil(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Med Logg Slett"))
        recipe_storage.lagre_logg_entry("Med Logg Slett", {"date": "2026-07-27", "actual_og": 1.050})

        recipe_storage.slett_oppskrift_fil("Med Logg Slett")

        self.assertNotIn("med_logg_slett_logg.json", self._filer())
        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertIn("med_logg_slett_logg.json", os.listdir(arkiv_mappe))

    def test_slett_av_ikke_eksisterende_oppskrift_returnerer_false(self):
        self.assertFalse(recipe_storage.slett_oppskrift_fil("Finnes Ikke"))


class TestDuplikatNavnDeteksjon(_IsolertRecipeMappeTestCase):
    def test_ingen_duplikater_i_normal_bruk(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Unikt Navn A"))
        recipe_storage.lagre_oppskrift(_oppskrift("Unikt Navn B"))
        self.assertEqual(recipe_storage.finn_duplikate_oppskrift_navn(), [])

    def test_to_filer_med_samme_name_felt_oppdages(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Duplikat"))
        # Simulerer en historisk/manuelt kopiert fil med samme "name"-felt,
        # men et annet filnavn -- akkurat scenarioet hent_alle_oppskrifter()
        # ellers ville kollapset stille (se docs/PROJECT_STATUS_JULI_2026.md).
        with open(os.path.join(self._mappe(), "duplikat_kopi.json"), "w", encoding="utf-8") as f:
            json.dump(_oppskrift("Duplikat", mengde=999.0), f)

        duplikater = recipe_storage.finn_duplikate_oppskrift_navn()
        self.assertEqual(len(duplikater), 1)
        self.assertEqual(duplikater[0]["navn"], "Duplikat")
        self.assertEqual(set(duplikater[0]["filer"]), {"duplikat.json", "duplikat_kopi.json"})

        # hent_alle_oppskrifter() kollapser fortsatt stille (kjent,
        # dokumentert atferd) -- denne testen bekrefter bare at
        # finn_duplikate_oppskrift_navn() gjør kollisjonen SYNLIG i tillegg.
        self.assertEqual(len(recipe_storage.hent_alle_oppskrifter()), 1)

    def test_arkiverte_filer_telles_ikke_som_duplikater(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Arkivtest"))
        recipe_storage.slett_oppskrift_fil("Arkivtest")
        recipe_storage.lagre_oppskrift(_oppskrift("Arkivtest", mengde=2.0))
        self.assertEqual(recipe_storage.finn_duplikate_oppskrift_navn(), [])


class TestFilnavnKart(_IsolertRecipeMappeTestCase):
    def test_filnavn_kart_matcher_faktisk_fil_paa_disk(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Kvernhaug Sommerglød"))
        kart = recipe_storage.hent_oppskrift_filnavn_kart()
        self.assertEqual(kart["Kvernhaug Sommerglød"], "kvernhaug_sommerglod.json")

    def test_arkiverte_filer_er_ikke_med_i_kartet(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Skal Bort"))
        recipe_storage.slett_oppskrift_fil("Skal Bort")
        self.assertNotIn("Skal Bort", recipe_storage.hent_oppskrift_filnavn_kart())


class TestFlavorProfileBevares(unittest.TestCase):
    """Regresjonsvakt: ui/recipe_card.py sin _bygg_recipe_fra_session()
    lagret tidligere ALLTID flavor_profile={} (hardkodet tomt), uansett
    hva den faktisk beregnede smaksprofilen i ctx["recipe"] inneholdt --
    hver lagring kastet dermed bort smakspoengene. Kildekode-inspeksjon
    (samme mønster som tests/test_recipe_card_dynamic_height.py) siden en
    full Streamlit-widgetflyt krever en kjørende AppTest-sesjon."""

    def test_lagrer_ikke_lenger_en_hardkodet_tom_flavor_profile(self):
        import inspect
        import ui.recipe_card as recipe_card_module
        kilde = inspect.getsource(recipe_card_module)
        self.assertNotIn("flavor_profile={}", kilde)
        self.assertIn('ctx["recipe"].get("flavor_profile"', kilde)


if __name__ == "__main__":
    unittest.main()
