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

Oppfølging (Kvernhaug-gjennomgang 2026-07-27): isolasjonstestene under brukte
tidligere `os.listdir()` direkte på den EKTE repo-rot recipes/-mappen (uten
eksistenssjekk) for å bekrefte at den ikke ble skrevet til. En helt fersk
`git worktree` fra en committet commit har ingen recipes/-mappe i det hele
tatt (den er gitignoret) — det ga FileNotFoundError på første kjøring i en
slik worktree. Isolasjonstestene bruker nå IKKE den ekte mappen i det hele
tatt (verken for å lese eller skrive): de simulerer en hel fersk prosjektrot
i en tempfile.TemporaryDirectory() og bytter midlertidig arbeidskatalog dit,
slik at recipe_storage.py sin RELATIVE standardsti ("recipes", brukt når
KVERNHAUG_RECIPES_DIR ikke er satt) aldri kan peke på den virkelige
repo-roten. Den ene testen som fortsatt bevisst inspiserer den ekte mappen
(regresjonsvakten mot de konkrete lekkasjenavnene) står i en egen klasse
nederst, og er skrivebeskyttet og trygg på manglende mappe.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest
from pathlib import Path

from modules.recipe import bygg_recipe_object

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


def _lag_oppskrift(navn):
    return bygg_recipe_object(
        navn, 20.0, 0.75,
        [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
        "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
    )


class TestRecipeStorageIsolasjonUtenLokalRecipesMappe(unittest.TestCase):
    """
    Ingen av testene i denne klassen leser eller skriver den ekte repo-rot
    recipes/-mappen — de gjelder utelukkende KVERNHAUG_RECIPES_DIR-
    isolasjonsmekanismen mot midlertidige, kontrollerte mapper. Skal være
    grønne på en helt fersk `git worktree` uten noen lokal recipes/-mappe.
    """

    def setUp(self):
        self._gammel_env = os.environ.get("KVERNHAUG_RECIPES_DIR")
        self._gammel_cwd = os.getcwd()

    def tearDown(self):
        # Sikkerhetsnett i tillegg til chdir-tilbakestillingen inni hver
        # testmetode (se kommentar der for hvorfor den skjer FØR
        # TemporaryDirectory sin egen opprydning).
        os.chdir(self._gammel_cwd)
        if self._gammel_env is None:
            os.environ.pop("KVERNHAUG_RECIPES_DIR", None)
        else:
            os.environ["KVERNHAUG_RECIPES_DIR"] = self._gammel_env

    def test_lagring_gjennom_isolert_mappe_paavirker_ikke_standardmappen(self):
        with tempfile.TemporaryDirectory() as fersk_prosjektrot:
            try:
                isolert_mappe = Path(fersk_prosjektrot) / "test_isolasjon"
                isolert_mappe.mkdir(parents=True, exist_ok=True)
                os.chdir(fersk_prosjektrot)
                os.environ["KVERNHAUG_RECIPES_DIR"] = str(isolert_mappe)

                import modules.recipe_storage as recipe_storage
                recipe_storage.lagre_oppskrift(_lag_oppskrift("Isolasjonstest"))

                self.assertIn("isolasjonstest.json", os.listdir(isolert_mappe))
                standard_mappe = Path(fersk_prosjektrot) / "recipes"
                self.assertFalse(
                    standard_mappe.exists(),
                    "Standardmappen ('recipes' relativt til cwd) ble opprettet, "
                    "til tross for at KVERNHAUG_RECIPES_DIR pekte på en annen mappe",
                )
            finally:
                # MÅ skje FØR TemporaryDirectory-konteksten over rydder opp —
                # på Windows kan en mappe som fortsatt er prosessens cwd ikke
                # slettes, noe som ville gitt en PermissionError ved utgang.
                os.chdir(self._gammel_cwd)

    def test_isolasjonen_virker_selv_om_recipe_storage_allerede_er_importert(self):
        # Gjenskaper lekkasje-scenarioet: recipe_storage er ALLEREDE importert
        # (av denne modulens egen import over, og av andre testmoduler
        # tidligere i samme prosess) FØR miljøvariabelen/cwd settes her.
        import modules.recipe_storage as recipe_storage
        with tempfile.TemporaryDirectory() as fersk_prosjektrot:
            try:
                isolert_mappe = Path(fersk_prosjektrot) / "nested" / "test_isolasjon"
                isolert_mappe.mkdir(parents=True, exist_ok=True)
                os.chdir(fersk_prosjektrot)
                os.environ["KVERNHAUG_RECIPES_DIR"] = str(isolert_mappe)

                recipe_storage.lagre_oppskrift(_lag_oppskrift("Isolasjonstest Sen Import"))

                self.assertIn("isolasjonstest_sen_import.json", os.listdir(isolert_mappe))
                standard_mappe = Path(fersk_prosjektrot) / "recipes"
                self.assertFalse(standard_mappe.exists())
            finally:
                os.chdir(self._gammel_cwd)

    def test_standardmappen_opprettes_med_foreldrekataloger_ved_behov(self):
        # Bekrefter at KVERNHAUG_RECIPES_DIR kan peke på en dyp, ennå
        # ikke-eksisterende sti — akkurat situasjonen på en fersk sjekk-ut —
        # og at sikre_mappe()/lagre_oppskrift() oppretter ALLE mellomliggende
        # foreldrekataloger (parents=True-semantikk), ikke bare siste ledd.
        # Bruker en absolutt sti direkte, uten chdir, siden dette ikke
        # tester den relative standardstien.
        import modules.recipe_storage as recipe_storage
        with tempfile.TemporaryDirectory() as fersk_prosjektrot:
            dyp_sti = Path(fersk_prosjektrot) / "a" / "b" / "c" / "recipes"
            self.assertFalse(dyp_sti.exists(), "Testforutsetningen (stien finnes ikke fra før) holder ikke")
            os.environ["KVERNHAUG_RECIPES_DIR"] = str(dyp_sti)

            recipe_storage.lagre_oppskrift(_lag_oppskrift("Dyp Sti Test"))

            self.assertTrue(dyp_sti.is_dir())
            self.assertIn("dyp_sti_test.json", os.listdir(dyp_sti))


class TestIngenKjenteLekkasjerIEkteRecipesMappe(unittest.TestCase):
    """
    Egen, bevisst ADSKILT klasse: dette er den ENESTE testen i filen som
    fortsatt inspiserer den virkelige repo-rot recipes/-mappen — en
    regresjonsvakt mot det konkrete tidligere hendelsesforløpet der E2E-
    testoppskrifter lekket inn i brukerens ekte, lagrede oppskrifter (se
    docstringen øverst). Den er bevisst beholdt (fjernes ikke av samme grunn
    som resten av filen ble strammet inn): hele poenget er å se etter
    lekkasjer i AKKURAT den ekte mappen. Ren lesing, aldri skriving, og
    en manglende mappe (fersk sjekk-ut) telles som "ingen lekkasje", ikke
    en feil.
    """

    def test_ingen_kjente_e2e_testoppskrifter_ligger_igjen_i_ekte_recipes(self):
        repo_root = Path(__file__).resolve().parent.parent
        ekte_mappe = repo_root / "recipes"
        faktiske_filer = set(os.listdir(ekte_mappe)) if ekte_mappe.is_dir() else set()
        overlapp = _KJENTE_LEKKASJENAVN & faktiske_filer
        self.assertFalse(overlapp, f"Tidligere lekkede testoppskrifter funnet i EKTE recipes/: {overlapp}")


if __name__ == "__main__":
    unittest.main()
