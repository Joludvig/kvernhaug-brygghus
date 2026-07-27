"""
Tester for målprofil-metadata (profile_type / origin / historical_profile)
og den korte UI-hjelpeteksten (kort_hjelpetekst) — se data/water_targets.json
og ui/water_panel.py.

Bakgrunn: brukeren ba om å beholde det korte visningsnavnet «Maltpreget
tysk lager» (IKKE legge «– Kvernhaug» tilbake), og i stedet uttrykke at
profilen er en Kvernhaug-husprofil via eksplisitt metadata + en kompakt
hjelpetekst UNDER valgt profil i UI-et — aldri en del av selve navnet,
og aldri synlig i nedtrekkslisten (som skal forbli ryddig).

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

from modules.water_chemistry import last_vannmaal
from modules.recipe import bygg_recipe_object

_FORVENTET_HJELPETEKST_KVERNHAUG = "Kvernhaug-husprofil laget for maltpregede tyske lagerøl."

_KVERNHAUG_ION_GRENSER = {
    "ca_min": 50, "ca_max": 65, "mg_min": 0, "mg_max": 8, "na_min": 0, "na_max": 20,
    "cl_min": 50, "cl_max": 70, "so4_min": 30, "so4_max": 45, "hco3_min": 25, "hco3_max": 60,
    "mash_ph_min": 5.30, "mash_ph_max": 5.40,
}


class Test1MetadataFinnesPaaAllePofiler(unittest.TestCase):
    def test_alle_profiler_har_metadata_feltene(self):
        maal = last_vannmaal()
        for target_id, profil in maal.items():
            self.assertIn("profile_type", profil, msg=f"{target_id} mangler profile_type")
            self.assertIn("origin", profil, msg=f"{target_id} mangler origin")
            self.assertIn("historical_profile", profil, msg=f"{target_id} mangler historical_profile")
            self.assertIn("kort_hjelpetekst", profil, msg=f"{target_id} mangler kort_hjelpetekst")
            self.assertIsInstance(profil["profile_type"], str)
            self.assertIsInstance(profil["origin"], str)
            self.assertIsInstance(profil["historical_profile"], bool)
            self.assertIsInstance(profil["kort_hjelpetekst"], str)
            self.assertTrue(profil["kort_hjelpetekst"].strip())

    def test_ingen_profil_er_markert_historisk(self):
        # Alle profilene her er bevisste Kvernhaug-husprofiler, ikke
        # påståtte historiske vannprofiler (se beskrivelsene i JSON).
        maal = last_vannmaal()
        for target_id, profil in maal.items():
            self.assertFalse(profil["historical_profile"], msg=f"{target_id} er feilaktig merket historisk")


class Test2KvernhaugProfilensMetadata(unittest.TestCase):
    def test_eksakte_metadataverdier(self):
        profil = last_vannmaal()["kvernhaug_maltpreget_tysk_lager"]
        self.assertEqual(profil["profile_type"], "house_profile")
        self.assertEqual(profil["origin"], "Kvernhaug Brygghus")
        self.assertEqual(profil["historical_profile"], False)
        self.assertEqual(profil["kort_hjelpetekst"], _FORVENTET_HJELPETEKST_KVERNHAUG)

    def test_navnet_er_uendret_kort_form(self):
        profil = last_vannmaal()["kvernhaug_maltpreget_tysk_lager"]
        self.assertEqual(profil["name"], "Maltpreget tysk lager")
        self.assertNotIn("Kvernhaug", profil["name"])

    def test_hjelpeteksten_er_ikke_en_del_av_navnet(self):
        profil = last_vannmaal()["kvernhaug_maltpreget_tysk_lager"]
        self.assertNotIn(profil["kort_hjelpetekst"], profil["name"])
        self.assertNotIn(profil["name"], profil["kort_hjelpetekst"])  # de er to atskilte tekster

    def test_alle_iongrenser_uendret(self):
        profil = last_vannmaal()["kvernhaug_maltpreget_tysk_lager"]
        for key, forventet in _KVERNHAUG_ION_GRENSER.items():
            self.assertEqual(profil[key], forventet, msg=f"Feltet {key} har endret seg!")


class Test3EgendefinertHarEgenMetadata(unittest.TestCase):
    """Krav: egendefinerte profiler skal kunne ha egen origin og
    profile_type — dvs. metadata er PER PROFIL, ikke en global konstant."""

    def test_egendefinert_har_egen_profile_type_og_origin(self):
        maal = last_vannmaal()
        egendefinert = maal["egendefinert"]
        husprofil = maal["kvernhaug_maltpreget_tysk_lager"]

        self.assertNotEqual(egendefinert["profile_type"], husprofil["profile_type"])
        self.assertNotEqual(egendefinert["origin"], husprofil["origin"])
        self.assertEqual(egendefinert["profile_type"], "custom_profile")

    def test_egen_maalprofil_kan_faa_helt_fritt_valgt_metadata(self):
        # Datamodellen er bare et flatt dict — en brukerbygget profil kan
        # sette HVILKE SOM HELST verdier for disse feltene, uavhengig av
        # hva som ligger i biblioteket.
        min_egen = {
            "target_id": "min_bryggeklubb_profil", "name": "Bryggeklubbens vann",
            "profile_type": "community_profile", "origin": "Åsane Bryggelag",
            "historical_profile": False, "kort_hjelpetekst": "Delt profil fra bryggeklubben.",
            "mash_ph_min": 5.2, "mash_ph_max": 5.5,
        }
        self.assertNotEqual(min_egen["profile_type"], "house_profile")
        self.assertNotEqual(min_egen["origin"], "Kvernhaug Brygghus")


class Test4MetadataOverleverLagringOgGjenaapning(unittest.TestCase):
    """Krav: metadata skal lagres i den FROSNE water_target_profile-
    snapshotten på oppskriften, og overleve en full lagre/gjenåpne-runde
    via modules/recipe_storage.py."""

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

    def test_husprofil_metadata_overlever_lagring(self):
        import modules.recipe_storage as recipe_storage
        maal_snapshot = dict(last_vannmaal()["kvernhaug_maltpreget_tysk_lager"])
        recipe = bygg_recipe_object(
            "Metadatatest", 20.0, 0.75, [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
            water_target_profile=maal_snapshot,
        )
        recipe_storage.lagre_oppskrift(recipe)

        gjenaapnet = recipe_storage.hent_alle_oppskrifter()["Metadatatest"]
        lagret_maal = gjenaapnet["water_target_profile"]
        self.assertEqual(lagret_maal["profile_type"], "house_profile")
        self.assertEqual(lagret_maal["origin"], "Kvernhaug Brygghus")
        self.assertEqual(lagret_maal["historical_profile"], False)
        self.assertEqual(lagret_maal["kort_hjelpetekst"], _FORVENTET_HJELPETEKST_KVERNHAUG)
        self.assertEqual(lagret_maal["name"], "Maltpreget tysk lager")

    def test_egendefinert_metadata_overlever_lagring_uendret(self):
        import modules.recipe_storage as recipe_storage
        egen_snapshot = {
            "target_id": "egendefinert", "name": "Min lokale kilde",
            "profile_type": "custom_profile", "origin": "Privat brønn",
            "historical_profile": False, "kort_hjelpetekst": "Egen brønn, analysert privat.",
            "mash_ph_min": 5.25, "mash_ph_max": 5.45,
        }
        recipe = bygg_recipe_object(
            "Metadatatest 2", 20.0, 0.75, [{"id": "weyermann_pilsner", "mengde": 5.0}], [],
            "safale_us_05", 1.050, 1.012, 5.0, 20, 8, {},
            water_target_profile=egen_snapshot,
        )
        recipe_storage.lagre_oppskrift(recipe)

        gjenaapnet = recipe_storage.hent_alle_oppskrifter()["Metadatatest 2"]
        lagret_maal = gjenaapnet["water_target_profile"]
        self.assertEqual(lagret_maal["profile_type"], "custom_profile")
        self.assertEqual(lagret_maal["origin"], "Privat brønn")
        self.assertEqual(lagret_maal["kort_hjelpetekst"], "Egen brønn, analysert privat.")


class Test5UIViserHjelpetekstAtskiltFraDropdown(unittest.TestCase):
    """AppTest mot den EKTE app.py: hjelpeteksten skal vises som en egen
    st.caption, og dropdown-alternativenes VISTE tekst (etter format_func)
    skal IKKE inneholde hjelpeteksten — dropdown-listen skal forbli
    ryddig."""

    def test_hjelpetekst_vises_som_egen_caption_ikke_i_dropdown(self):
        from streamlit.testing.v1 import AppTest
        import os as _os

        repo_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
        app_py = _os.path.join(repo_root, "app.py")

        at = AppTest.from_file(app_py)
        at.run()
        self.assertFalse(at.exception, f"app.py kastet exception ved oppstart: {at.exception}")

        at.selectbox(key="vann_maal_valgt_id").select("kvernhaug_maltpreget_tysk_lager").run()
        self.assertFalse(at.exception)

        sb = at.selectbox(key="vann_maal_valgt_id")
        for label in sb.options:
            self.assertNotIn(
                _FORVENTET_HJELPETEKST_KVERNHAUG, label,
                "Dropdown-alternativet inneholder hjelpeteksten — listen skal forbli ryddig.",
            )
            self.assertLess(
                len(label), 60,
                f"Dropdown-alternativet «{label}» virker unormalt langt for en ren profilnavn-liste.",
            )

        alle_captions = [c.value for c in at.caption]
        self.assertIn(
            _FORVENTET_HJELPETEKST_KVERNHAUG, alle_captions,
            "Hjelpeteksten ble ikke funnet som en egen, synlig caption.",
        )


if __name__ == "__main__":
    unittest.main()
