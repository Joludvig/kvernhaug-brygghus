"""
Tester for at lagre_oppskrift() validerer `kilde_filnavn` FØR noe annet
skjer -- før kollisjonssjekk, backup, skriving av den nye filen, eller
arkivering av den gamle.

Bakgrunn: lagre_oppskrift() brukte tidligere `kilde_filnavn` direkte til
omdøping/arkivering (se _arkiver_kildefil_etter_omdoeping()) uten først
å kalle den etablerte _valider_kildefilnavn() -- samme validator som
slett_oppskrift_fil() allerede bruker (se
tests/test_recipe_storage_hardening.py). Et direkte kall med et
ondsinnet eller feilformet `kilde_filnavn` (path traversal, absolutt
sti, mappekomponent) kunne dermed forsøke å peke utenfor den aktive
oppskriftsmappen. `None` er unntaket -- betyr eksplisitt "ingen kjent
kildefil" og krever ingen validering.

Bruker UTELUKKENDE tempfile.TemporaryDirectory() via
KVERNHAUG_RECIPES_DIR -- aldri den ekte recipes/-mappen (samme mønster
som tests/test_recipe_storage_hardening.py).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest

from modules.recipe import bygg_recipe_object
import modules.recipe_storage as recipe_storage
from modules.recipe_storage import UgyldigKildefilnavn


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

    def _filer(self):
        return set(os.listdir(self._mappe())) if os.path.isdir(self._mappe()) else set()


_UGYLDIGE_KILDEFILNAVN = [
    ("relativ_traversal", "../pantry.json"),
    ("relativ_traversal_dobbel_backslash", "..\\..\\pantry.json"),
    ("rotsti_uten_stasjon", "/etc/passwd"),
    ("absolutt_windows_sti", "C:\\Users\\noen\\pantry.json"),
    ("undermappe", "sub/mappe.json"),
    ("kun_punktum", "."),
    ("dobbelt_punktum", ".."),
    ("tom_streng", ""),
]


class TestUgyldigKildefilnavnBlokkererLagring(_IsolertRecipeMappeTestCase):
    def test_ugyldige_kildefilnavn_reiser_ugyldigkildefilnavn_uten_aa_skrive_noe(self):
        for _navn, ondsinnet in _UGYLDIGE_KILDEFILNAVN:
            with self.subTest(kilde_filnavn=ondsinnet):
                with self.assertRaises(UgyldigKildefilnavn):
                    recipe_storage.lagre_oppskrift(
                        _oppskrift("Forsøk På Ondsinnet Lagring"), kilde_filnavn=ondsinnet,
                    )
                # Ingenting skal ha blitt skrevet til den isolerte
                # mappen i det hele tatt -- verken den nye filen,
                # backup-mappen eller arkiv-mappen.
                self.assertEqual(self._filer(), set())

    def test_ingen_backup_eller_arkiv_mappe_opprettes_ved_ugyldig_kildefilnavn(self):
        with self.assertRaises(UgyldigKildefilnavn):
            recipe_storage.lagre_oppskrift(_oppskrift("Uten Bivirkninger"), kilde_filnavn="../pantry.json")
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_backup")))
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_archive")))

    def test_fil_utenfor_isolert_mappe_forblir_byte_for_byte_uendret(self):
        # Simulerer en ekte privat fil UTENFOR den isolerte
        # oppskriftsmappen (f.eks. data/pantry.json i den virkelige
        # appen) -- et path-traversal-forsøk skal aldri kunne røre den.
        foreldre_mappe = os.path.dirname(self._mappe())
        offer_sti = os.path.join(foreldre_mappe, "offer_utenfor_recipes.json")
        with open(offer_sti, "w", encoding="utf-8") as f:
            f.write('{"name": "Skal forbli urort"}')
        try:
            with self.assertRaises(UgyldigKildefilnavn):
                recipe_storage.lagre_oppskrift(
                    _oppskrift("Traversal-forsøk"), kilde_filnavn="../offer_utenfor_recipes.json",
                )
            with open(offer_sti, encoding="utf-8") as f:
                self.assertEqual(f.read(), '{"name": "Skal forbli urort"}')
        finally:
            os.remove(offer_sti)

    def test_tom_kildefil_streng_arkiverer_ikke_hele_oppskriftsmappen(self):
        # Konkret regresjonsvakt for det farligste enkelttilfellet: en
        # tom streng er IKKE None (som betyr "ingen kjent kildefil"),
        # men FØR denne fiksen ville navn_endret blitt True og
        # _arkiver_kildefil_etter_omdoeping("", ...) forsøkt å arkivere
        # os.path.join(mappe, "") -- altså selve oppskriftsmappen.
        recipe_storage.lagre_oppskrift(_oppskrift("Eksisterende Oppskrift"))
        with self.assertRaises(UgyldigKildefilnavn):
            recipe_storage.lagre_oppskrift(_oppskrift("Nytt Navn"), kilde_filnavn="")
        # Den eksisterende oppskriften og selve mappen skal stå urørt.
        self.assertIn("eksisterende_oppskrift.json", self._filer())
        self.assertFalse(os.path.isdir(os.path.join(self._mappe(), "_archive")))


class TestGyldigKildefilnavnFungererSomFoer(_IsolertRecipeMappeTestCase):
    def test_none_krever_ingen_validering_ny_oppskrift(self):
        # kilde_filnavn=None (ny oppskrift / ingen kjent kildefil) skal
        # aldri utløse validering eller feile.
        filnavn = recipe_storage.lagre_oppskrift(_oppskrift("Helt Ny Oppskrift"), kilde_filnavn=None)
        self.assertEqual(filnavn, "helt_ny_oppskrift.json")

    def test_gyldig_rent_kildefilnavn_fungerer_normalt(self):
        recipe_storage.lagre_oppskrift(_oppskrift("Gammelt Rent Navn"))
        nytt_filnavn = recipe_storage.lagre_oppskrift(
            _oppskrift("Nytt Rent Navn"), kilde_filnavn="gammelt_rent_navn.json",
        )
        self.assertEqual(nytt_filnavn, "nytt_rent_navn.json")
        self.assertIn("nytt_rent_navn.json", self._filer())
        arkiv_mappe = os.path.join(self._mappe(), "_archive")
        self.assertIn("gammelt_rent_navn.json", os.listdir(arkiv_mappe))


if __name__ == "__main__":
    unittest.main()
