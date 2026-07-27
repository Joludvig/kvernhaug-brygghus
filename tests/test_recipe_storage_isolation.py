"""
Regresjonstest: AppTest/E2E-tester som lagrer testoppskrifter skal ALDRI
skrive til den ekte recipes/-mappen (brukerens virkelige, lagrede brygg).

Bakgrunn: en tidligere runde oppdaget at tre E2E-testoppskrifter (bl.a.
"E2E Enkel infusjon", "E2E Korrupt Hochkurz", "E2E Real App Wiesn") hadde
lekket inn i den virkelige recipes/-mappen. Årsaken: modules/recipe_storage.py
leste miljøvariabelen KVERNHAUG_RECIPES_DIR inn i en MODULNIVÅ-konstant
(`MAPPE = os.getenv(...)`), evaluert kun ÉN gang — ved modulens FØRSTE
import i hele testprosessen. Siden tests/test_process_profiles.py
importerer recipe_storage ved modulnivå, kunne modulen bli importert (og
MAPPE dermed frosset til "recipes") lenge før en senere test rakk å sette
miljøvariabelen i sin egen setUp(). Fikset ved å lese miljøvariabelen
FRISKT ved hvert filoppslag (se _mappe() i modules/recipe_storage.py) —
denne testen låser fast at mekanismen faktisk virker.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest

from modules.recipe import bygg_recipe_object

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EKTE_RECIPES_MAPPE = os.path.join(_REPO_ROOT, "recipes")

# De konkrete filnavnene som tidligere lekket inn i den ekte mappen — en
# varig vaktpost mot at akkurat disse kommer tilbake, uansett hvilken
# fremtidig test som måtte (feilaktig) opprette dem igjen.
_KJENTE_LEKKASJENAVN = {
    "e2e_enkel_infusjon.json",
    "e2e_korrupt_hochkurz.json",
    "e2e_korrupt_kockhurz.json",
    "e2e_real_app_wiesn.json",
    "e2e_real_app_weizen.json",
}


def _snapshot(mappe):
    if not os.path.isdir(mappe):
        return frozenset()
    return frozenset(os.listdir(mappe))


class TestRecipeStorageIsolasjon(unittest.TestCase):
    """Bekrefter at KVERNHAUG_RECIPES_DIR-isolasjonen faktisk fungerer, og
    at den ekte recipes/-mappen forblir fysisk uendret — hverken opprettet,
    endret eller slettet noe i den — under en full lagre/lese-runde via
    modules/recipe_storage.py."""

    def setUp(self):
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        self._snapshot_for = _snapshot(_EKTE_RECIPES_MAPPE)

    def tearDown(self):
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env
        # Selve garantien denne testklassen finnes for: uansett hva
        # testmetoden over gjorde, skal den EKTE mappen aldri ha endret
        # innhold underveis.
        self.assertEqual(
            _snapshot(_EKTE_RECIPES_MAPPE), self._snapshot_for,
            "Den EKTE recipes/-mappen ble endret under en isolert test!",
        )

    def test_lagring_gjennom_isolert_mappe_paavirker_ikke_ekte_recipes(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KVERNHAUG_RECIPES_DIR"] = tmp

            import modules.recipe_storage as recipe_storage
            recipe = bygg_recipe_object(
                "Isolasjonstest", 20.0, 0.75,
                [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
                "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
            )
            recipe_storage.lagre_oppskrift(recipe)

            # Lagret i den ISOLERTE mappen...
            self.assertIn("isolasjonstest.json", os.listdir(tmp))
            # ...og IKKE i den ekte recipes/-mappen.
            self.assertNotIn("isolasjonstest.json", os.listdir(_EKTE_RECIPES_MAPPE))

    def test_isolasjonen_virker_selv_om_recipe_storage_allerede_er_importert(self):
        # Gjenskaper NØYAKTIG lekkasje-scenarioet: recipe_storage er
        # ALLEREDE importert (av denne test-modulens egne import over,
        # og av tests/test_process_profiles.py tidligere i samme
        # prosess) FØR miljøvariabelen settes her.
        import modules.recipe_storage as recipe_storage
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KVERNHAUG_RECIPES_DIR"] = tmp
            recipe = bygg_recipe_object(
                "Isolasjonstest Sen Import", 20.0, 0.75,
                [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
                "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
            )
            recipe_storage.lagre_oppskrift(recipe)
            self.assertIn("isolasjonstest_sen_import.json", os.listdir(tmp))
            self.assertNotIn("isolasjonstest_sen_import.json", os.listdir(_EKTE_RECIPES_MAPPE))

    def test_ingen_kjente_e2e_testoppskrifter_ligger_igjen_i_ekte_recipes(self):
        faktiske_filer = set(os.listdir(_EKTE_RECIPES_MAPPE)) if os.path.isdir(_EKTE_RECIPES_MAPPE) else set()
        overlapp = _KJENTE_LEKKASJENAVN & faktiske_filer
        self.assertFalse(overlapp, f"Tidligere lekkede testoppskrifter funnet i EKTE recipes/: {overlapp}")


if __name__ == "__main__":
    unittest.main()
