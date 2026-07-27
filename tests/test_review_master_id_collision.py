"""
Tester for at «Opprett i master» i ui/review_panel.py aldri kan
overskrive en ALLEREDE eksisterende master-ID stille.

Bakgrunn: _opprett_og_fjern() gjorde tidligere `master[ny_id] = ny_entry`
uten noen sjekk på om `ny_id` allerede fantes. Siden review nå skriver
DIREKTE til de aktive masterdatabasene appen laster ved oppstart (se
ui/review_panel.py::MASTER_PATHS), kunne en godkjenning i review-panelet
dermed stille slette en eksisterende, gyldig ingrediens.

Bruker samme mønster som tests/test_humle_import_runtime_integration.py:
en HELT ISOLERT tempfile.TemporaryDirectory() som fungerer som en fersk
prosjektrot (data/ + raw_data/), aldri de ekte masterfilene i data/.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest

import ui.review_panel as review_panel


def _last_json(sti):
    with open(sti, encoding="utf-8") as f:
        return json.load(f)


class _IsolertProsjektrotTestCase(unittest.TestCase):
    """Simulerer en fersk prosjektrot (data/ + raw_data/) i en isolert
    tempdir og bytter cwd dit -- review_panel.py sine MASTER_PATHS/
    UNMATCHED_PATHS er relative stier ("data/...", "raw_data/..."), så
    dette er den samme isolasjonsteknikken som allerede etablert i
    tests/test_humle_import_runtime_integration.py."""

    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self._gammel_cwd = os.getcwd()
        os.chdir(self._tmpdir.name)
        os.makedirs("data", exist_ok=True)
        os.makedirs("raw_data", exist_ok=True)

    def tearDown(self):
        os.chdir(self._gammel_cwd)
        self._tmpdir.cleanup()

    def _skriv_master(self, kat, innhold):
        with open(review_panel.MASTER_PATHS[kat], "w", encoding="utf-8") as f:
            json.dump(innhold, f, ensure_ascii=False, indent=2)

    def _skriv_unmatched(self, kat, innhold):
        with open(review_panel.UNMATCHED_PATHS[kat], "w", encoding="utf-8") as f:
            json.dump(innhold, f, ensure_ascii=False, indent=2)

    def _les_master_bytes(self, kat):
        with open(review_panel.MASTER_PATHS[kat], "rb") as f:
            return f.read()


class TestOpprettUtenKollisjonFungererSomFoer(_IsolertProsjektrotTestCase):
    def test_humle_opprettes_naar_id_ikke_finnes(self):
        self._skriv_master("humle", {"cascade_us": {"display_name": "Cascade"}})
        self._skriv_unmatched("humle", [{"navn": "Splendour 2026", "butikk": "vestbrygg", "pris": 75.0}])

        review_panel._opprett_og_fjern("humle", "splendour", {"display_name": "Splendour"}, 0)

        master = _last_json(review_panel.MASTER_PATHS["humle"])
        self.assertIn("splendour", master)
        self.assertEqual(_last_json(review_panel.UNMATCHED_PATHS["humle"]), [])

    def test_malt_opprettes_naar_id_ikke_finnes(self):
        self._skriv_master("malt", {"weyermann_pilsner": {"display_name": "Pilsner"}})
        self._skriv_unmatched("malt", [{"navn": "Nytt Malt", "butikk": "vestbrygg", "pris": 40.0}])

        review_panel._opprett_og_fjern("malt", "nytt_malt", {"display_name": "Nytt Malt"}, 0)

        master = _last_json(review_panel.MASTER_PATHS["malt"])
        self.assertIn("nytt_malt", master)
        self.assertEqual(_last_json(review_panel.UNMATCHED_PATHS["malt"]), [])

    def test_gjaer_opprettes_naar_id_ikke_finnes(self):
        self._skriv_master("gjaer", {"safale_us05": {"display_name": "US-05"}})
        self._skriv_unmatched("gjaer", [{"navn": "Ny Gjær", "butikk": "vestbrygg", "pris": 59.0}])

        review_panel._opprett_og_fjern("gjaer", "ny_gjaer", {"display_name": "Ny Gjær"}, 0)

        master = _last_json(review_panel.MASTER_PATHS["gjaer"])
        self.assertIn("ny_gjaer", master)
        self.assertEqual(_last_json(review_panel.UNMATCHED_PATHS["gjaer"]), [])


class TestKollisjonBlokkeres(_IsolertProsjektrotTestCase):
    def test_humle_kollisjon_blokkeres_og_master_er_byte_for_byte_uendret(self):
        self._skriv_master("humle", {"cascade_us": {"display_name": "Cascade (Original)"}})
        self._skriv_unmatched("humle", [{"navn": "Cascade Forsøk 2", "butikk": "vestbrygg", "pris": 89.0}])
        original_bytes = self._les_master_bytes("humle")

        with self.assertRaises(review_panel.MasterIdKollisjon) as ctx:
            review_panel._opprett_og_fjern(
                "humle", "cascade_us", {"display_name": "Cascade (Forsøk 2 -- SKAL IKKE SKRIVES)"}, 0,
            )
        self.assertEqual(ctx.exception.ny_id, "cascade_us")
        self.assertEqual(ctx.exception.eksisterende_navn, "Cascade (Original)")

        # Masterfilen er HELT uendret -- ikke bare "samme logiske innhold",
        # men byte-for-byte identisk (ingen skriving skjedde i det hele tatt).
        self.assertEqual(self._les_master_bytes("humle"), original_bytes)
        # Pending-elementet er IKKE fjernet -- forsøket skal fortsatt stå
        # klart for et nytt, korrigert forsøk.
        self.assertEqual(len(_last_json(review_panel.UNMATCHED_PATHS["humle"])), 1)

    def test_malt_kollisjon_blokkeres_og_master_er_byte_for_byte_uendret(self):
        self._skriv_master("malt", {"weyermann_pilsner": {"display_name": "Weyermann Pilsner (Original)"}})
        self._skriv_unmatched("malt", [{"navn": "Duplikat Pilsner", "butikk": "vestbrygg", "pris": 40.0}])
        original_bytes = self._les_master_bytes("malt")

        with self.assertRaises(review_panel.MasterIdKollisjon):
            review_panel._opprett_og_fjern("malt", "weyermann_pilsner", {"display_name": "Duplikat"}, 0)

        self.assertEqual(self._les_master_bytes("malt"), original_bytes)
        self.assertEqual(len(_last_json(review_panel.UNMATCHED_PATHS["malt"])), 1)

    def test_gjaer_kollisjon_blokkeres_og_master_er_byte_for_byte_uendret(self):
        self._skriv_master("gjaer", {"safale_us05": {"display_name": "SafAle US-05 (Original)"}})
        self._skriv_unmatched("gjaer", [{"navn": "Duplikat US-05", "butikk": "vestbrygg", "pris": 59.0}])
        original_bytes = self._les_master_bytes("gjaer")

        with self.assertRaises(review_panel.MasterIdKollisjon):
            review_panel._opprett_og_fjern("gjaer", "safale_us05", {"display_name": "Duplikat"}, 0)

        self.assertEqual(self._les_master_bytes("gjaer"), original_bytes)
        self.assertEqual(len(_last_json(review_panel.UNMATCHED_PATHS["gjaer"])), 1)


class TestTomIdBlokkeres(_IsolertProsjektrotTestCase):
    def test_tom_id_reiser_tommasterid_uten_aa_skrive(self):
        self._skriv_master("humle", {"cascade_us": {"display_name": "Cascade"}})
        self._skriv_unmatched("humle", [{"navn": "???", "butikk": "vestbrygg", "pris": 10.0}])
        original_bytes = self._les_master_bytes("humle")

        with self.assertRaises(review_panel.TomMasterId):
            review_panel._opprett_og_fjern("humle", "", {"display_name": "???"}, 0)

        self.assertEqual(self._les_master_bytes("humle"), original_bytes)
        self.assertEqual(len(_last_json(review_panel.UNMATCHED_PATHS["humle"])), 1)

    def test_lag_kanonisk_id_av_kun_symboler_gir_tom_streng(self):
        # Bekrefter selve premisset: et navn som består utelukkende av
        # tegn _lag_kanonisk_id() strimler bort, gir faktisk en tom ID --
        # dette er IKKE et oppdiktet scenario.
        self.assertEqual(review_panel._lag_kanonisk_id("???"), "")
        self.assertEqual(review_panel._lag_kanonisk_id("---"), "")
        self.assertEqual(review_panel._lag_kanonisk_id(""), "")


if __name__ == "__main__":
    unittest.main()
