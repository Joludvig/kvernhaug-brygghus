"""
Tester for Steg D: innsamling og modellering av Ølbryggings faktiske
maltpakkealternativer i modules/store_matcher.py::_bygg_ol_variantliste().

Bakgrunn: for Ølbrygging finnes samme malt ofte som flere reelle,
kjøpbare pakker hos samme butikk (f.eks. 1 kg hel, 1 kg knust, 5 kg hel,
5 kg knust, 25 kg hel, 25 kg knust — se ekte data for "Carahell Malt" i
raw_data/malt_raw.json). Før Steg D beholdt butikk_match KUN én
representativ rad per (master_id, butikk) (Steg A). Steg D bevarer i
tillegg ALLE disse pakkene som en additiv "varianter"-liste, i nøyaktig
det formatet modules/malt_packaging.py allerede forventer.

Disse testene bruker utelukkende isolerte temp-filer — ingen ekte
raw_data/*.json eller data/master_*.json røres.
"""
import json
import os
import shutil
import tempfile
import unittest

import modules.malt_packaging as malt_packaging
from modules.store_matcher import (
    match_store_data_to_master_malt,
    match_store_data_to_master,
    match_store_data_to_master_gjaer,
)


def _master_malt_fixture(*alias_par):
    return {
        m_id: {"display_name": navn, "aliases": [navn], "butikk_match": {}, "verified": True}
        for m_id, navn in alias_par
    }


def _kjor_malt(malt_raw_liste, master):
    tmp = tempfile.mkdtemp()
    try:
        raw_path = os.path.join(tmp, "malt_raw.json")
        master_path = os.path.join(tmp, "master_malt.json")
        unmatched_path = os.path.join(tmp, "unmatched_malt.json")
        with open(raw_path, "w", encoding="utf-8") as f:
            json.dump(malt_raw_liste, f)
        with open(master_path, "w", encoding="utf-8") as f:
            json.dump(master, f)
        matched, unmatched = match_store_data_to_master_malt(raw_path, master_path, unmatched_path)
        with open(master_path, encoding="utf-8") as f:
            resultat = json.load(f)
        return resultat, matched, unmatched
    finally:
        shutil.rmtree(tmp)


# Speiler den ekte Carahell Malt-oppføringen hos Ølbrygging (seks reelle
# pakningsalternativer for samme malt).
OL_1KG_HEL = {"navn": "Test Malt 1 kg hel", "butikk": "olbrygging", "pris": 35.0,
              "pakke_gram": 1000.0, "er_knust": False,
              "url": "https://www.olbrygging.no/test/1/test-malt-1-kg-hel"}
OL_1KG_KNUST = {"navn": "Test Malt 1 kg knust", "butikk": "olbrygging", "pris": 40.0,
                "pakke_gram": 1000.0, "er_knust": True,
                "url": "https://www.olbrygging.no/test/2/test-malt-1-kg-knust"}
OL_5KG_HEL = {"navn": "Test Malt 5 kg hel", "butikk": "olbrygging", "pris": 150.0,
              "pakke_gram": 5000.0, "er_knust": False,
              "url": "https://www.olbrygging.no/test/3/test-malt-5-kg-hel"}
OL_5KG_KNUST = {"navn": "Test Malt 5 kg knust", "butikk": "olbrygging", "pris": 170.0,
                "pakke_gram": 5000.0, "er_knust": True,
                "url": "https://www.olbrygging.no/test/4/test-malt-5-kg-knust"}
OL_25KG_HEL = {"navn": "Test Malt 25 kg hel", "butikk": "olbrygging", "pris": 849.0,
               "pakke_gram": 25000.0, "er_knust": False,
               "url": "https://www.olbrygging.no/test/5/test-malt-25-kg-hel"}
OL_25KG_KNUST = {"navn": "Test Malt 25 kg knust", "butikk": "olbrygging", "pris": 949.0,
                 "pakke_gram": 25000.0, "er_knust": True,
                 "url": "https://www.olbrygging.no/test/6/test-malt-25-kg-knust"}

ALLE_SEKS = [OL_1KG_HEL, OL_1KG_KNUST, OL_5KG_HEL, OL_5KG_KNUST, OL_25KG_HEL, OL_25KG_KNUST]


class Test1FlereVarianterSamlesIEnListe(unittest.TestCase):
    def test_seks_reelle_pakker_gir_seks_varianter(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_SEKS, master)

        varianter = resultat["test_malt"]["butikk_match"]["olbrygging"]["varianter"]
        self.assertEqual(len(varianter), 6)


class Test2StorrelserBevares(unittest.TestCase):
    def test_1kg_5kg_25kg_bevares(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_SEKS, master)

        varianter = resultat["test_malt"]["butikk_match"]["olbrygging"]["varianter"]
        storrelser = {v["pakningsstorrelse_gram"] for v in varianter}
        self.assertEqual(storrelser, {1000.0, 5000.0, 25000.0})


class Test3HelOgKnustHoldesSeparate(unittest.TestCase):
    def test_hel_og_knust_er_atskilte_alternativer(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_SEKS, master)

        varianter = resultat["test_malt"]["butikk_match"]["olbrygging"]["varianter"]
        par = {(v["pakningsstorrelse_gram"], v["malttype"]) for v in varianter}
        self.assertEqual(par, {
            (1000.0, "hel"), (1000.0, "knust"),
            (5000.0, "hel"), (5000.0, "knust"),
            (25000.0, "hel"), (25000.0, "knust"),
        })


class Test4PrisOgUrlFraSammeRaRad(unittest.TestCase):
    def test_hver_variant_har_pris_og_url_fra_samme_rad(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_SEKS, master)

        varianter = resultat["test_malt"]["butikk_match"]["olbrygging"]["varianter"]
        per_storrelse_type = {(v["pakningsstorrelse_gram"], v["malttype"]): v for v in varianter}

        v_1kg_hel = per_storrelse_type[(1000.0, "hel")]
        self.assertEqual(v_1kg_hel["pris"], OL_1KG_HEL["pris"])
        self.assertEqual(v_1kg_hel["url"], OL_1KG_HEL["url"])

        v_25kg_knust = per_storrelse_type[(25000.0, "knust")]
        self.assertEqual(v_25kg_knust["pris"], OL_25KG_KNUST["pris"])
        self.assertEqual(v_25kg_knust["url"], OL_25KG_KNUST["url"])

        # Ikke ved et uhell blandet med en annen rads tall:
        self.assertNotEqual(v_1kg_hel["pris"], OL_1KG_KNUST["pris"])
        self.assertNotEqual(v_25kg_knust["url"], OL_25KG_HEL["url"])


class Test5IdentiskeDuplikaterFjernes(unittest.TestCase):
    def test_eksakt_duplikatrad_gir_ikke_ekstra_variant(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        duplikat_av_1kg_hel = dict(OL_1KG_HEL)
        rader = [OL_1KG_HEL, duplikat_av_1kg_hel, OL_5KG_HEL]

        resultat, _, _ = _kjor_malt(rader, master)
        varianter = resultat["test_malt"]["butikk_match"]["olbrygging"]["varianter"]

        self.assertEqual(len(varianter), 2)
        storrelser = sorted(v["pakningsstorrelse_gram"] for v in varianter)
        self.assertEqual(storrelser, [1000.0, 5000.0])


class Test6DeterministiskRekkefolge(unittest.TestCase):
    def test_variantlisten_er_identisk_uansett_inputrekkefolge(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))

        resultat_normal, _, _ = _kjor_malt(ALLE_SEKS, json.loads(json.dumps(master)))
        resultat_omvendt, _, _ = _kjor_malt(list(reversed(ALLE_SEKS)), json.loads(json.dumps(master)))
        resultat_blandet, _, _ = _kjor_malt(
            [OL_25KG_HEL, OL_1KG_KNUST, OL_5KG_KNUST, OL_1KG_HEL, OL_25KG_KNUST, OL_5KG_HEL],
            json.loads(json.dumps(master)),
        )

        v_normal = resultat_normal["test_malt"]["butikk_match"]["olbrygging"]["varianter"]
        v_omvendt = resultat_omvendt["test_malt"]["butikk_match"]["olbrygging"]["varianter"]
        v_blandet = resultat_blandet["test_malt"]["butikk_match"]["olbrygging"]["varianter"]

        self.assertEqual(v_normal, v_omvendt)
        self.assertEqual(v_normal, v_blandet)


class Test7FlatFallbackFolgerStegAsRegel(unittest.TestCase):
    def test_flat_pris_url_peker_pa_1kg_hel_som_i_steg_a(self):
        from modules.store_matcher import _pris_per_kg

        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_SEKS, master)

        flat = resultat["test_malt"]["butikk_match"]["olbrygging"]
        self.assertEqual(flat["url"], OL_1KG_HEL["url"])
        self.assertEqual(flat["pris"], _pris_per_kg(OL_1KG_HEL["pris"], OL_1KG_HEL["pakke_gram"], "malt"))
        # Varianter-feltet endrer ikke det flate valget:
        self.assertIn("varianter", flat)


class Test8EnkeltVariantFungererSomFor(unittest.TestCase):
    def test_ett_treff_gir_enkelt_variantliste_og_uendret_flate_felt(self):
        master = _master_malt_fixture(("enkel_malt", "Enkel Malt"))
        enkel = {"navn": "Enkel Malt 1 kg hel", "butikk": "olbrygging", "pris": 45.0,
                 "pakke_gram": 1000.0, "er_knust": False,
                 "url": "https://www.olbrygging.no/enkel/1/enkel-malt-1kg-hel"}

        resultat, matched, unmatched = _kjor_malt([enkel], master)
        bm = resultat["enkel_malt"]["butikk_match"]["olbrygging"]

        self.assertEqual(matched, 1)
        self.assertEqual(unmatched, 0)
        self.assertEqual(bm["url"], enkel["url"])
        self.assertEqual(bm["pris"], 45.0)
        self.assertEqual(bm["varianter"], [
            {"pakningsstorrelse_gram": 1000.0, "malttype": "hel", "pris": 45.0, "url": enkel["url"]},
        ])


class Test9VestbryggFarIkkeVariantmodell(unittest.TestCase):
    def test_vestbrygg_flere_pakker_far_ingen_varianter_felt(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        v_1kg = {"navn": "Test Malt 1 kg hel", "butikk": "vestbrygg", "pris": 40.0,
                 "pakke_gram": 1000.0, "er_knust": False,
                 "url": "https://vestbrygg.no/test/1/test-malt-1-kg-hel"}
        v_5kg = {"navn": "Test Malt 5 kg hel", "butikk": "vestbrygg", "pris": 180.0,
                 "pakke_gram": 5000.0, "er_knust": False,
                 "url": "https://vestbrygg.no/test/2/test-malt-5-kg-hel"}

        resultat, _, _ = _kjor_malt([v_1kg, v_5kg], master)
        bm_vestbrygg = resultat["test_malt"]["butikk_match"]["vestbrygg"]

        self.assertNotIn("varianter", bm_vestbrygg)
        self.assertEqual(bm_vestbrygg["url"], v_1kg["url"])

    def test_blanding_av_butikker_gir_varianter_kun_for_olbrygging(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        v_1kg = {"navn": "Test Malt 1 kg hel", "butikk": "vestbrygg", "pris": 40.0,
                 "pakke_gram": 1000.0, "er_knust": False,
                 "url": "https://vestbrygg.no/test/1/test-malt-1-kg-hel"}

        resultat, _, _ = _kjor_malt([v_1kg, OL_1KG_HEL, OL_1KG_KNUST], master)
        bm = resultat["test_malt"]["butikk_match"]

        self.assertNotIn("varianter", bm["vestbrygg"])
        self.assertIn("varianter", bm["olbrygging"])
        self.assertEqual(len(bm["olbrygging"]["varianter"]), 2)


class Test10HumleOgGjaerUendret(unittest.TestCase):
    def test_gjaer_matching_far_aldri_varianter_felt(self):
        tmp = tempfile.mkdtemp()
        try:
            master = {"test_gjaer": {"display_name": "Test Gjær", "aliases": ["Test Gjær"],
                                      "butikk_match": {}, "verified": True}}
            rad = {"navn": "Test Gjær", "butikk": "olbrygging", "pris": 59.0,
                   "url": "https://www.olbrygging.no/gjaer/a"}

            raw_path = os.path.join(tmp, "gjaer_raw.json")
            master_path = os.path.join(tmp, "master_gjaer.json")
            unmatched_path = os.path.join(tmp, "unmatched_gjaer.json")

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump([rad], f)
            with open(master_path, "w", encoding="utf-8") as f:
                json.dump(master, f)
            match_store_data_to_master_gjaer(raw_path, master_path, unmatched_path)
            with open(master_path, encoding="utf-8") as f:
                resultat = json.load(f)

            self.assertNotIn("varianter", resultat["test_gjaer"]["butikk_match"]["olbrygging"])
        finally:
            shutil.rmtree(tmp)

    def test_humle_matching_far_aldri_varianter_felt(self):
        tmp = tempfile.mkdtemp()
        try:
            master = {"test_humle": {"display_name": "Test Humle", "aliases": ["Test Humle 2025"],
                                      "butikk_match": {}, "verified": True}}
            rad = {"navn": "Test Humle 2025 Pellets - 100g", "butikk": "olbrygging",
                   "pris": 100.0, "pakke_gram": 100.0, "url": "https://www.olbrygging.no/humle/100g"}

            raw_path = os.path.join(tmp, "humle_raw.json")
            master_path = os.path.join(tmp, "master_humle.json")
            matched_path = os.path.join(tmp, "matched_hops.json")
            unmatched_path = os.path.join(tmp, "unmatched_hops.json")

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump([rad], f)
            with open(master_path, "w", encoding="utf-8") as f:
                json.dump(master, f)
            match_store_data_to_master(raw_path, master_path, matched_path, unmatched_path)
            with open(master_path, encoding="utf-8") as f:
                resultat = json.load(f)

            self.assertNotIn("varianter", resultat["test_humle"]["butikk_match"]["olbrygging"])
        finally:
            shutil.rmtree(tmp)


class Test11MaltPackagingLeserVariantlistenUtenAdapter(unittest.TestCase):
    def test_variantlisten_fra_matcher_kan_brukes_direkte_i_malt_packaging(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_SEKS, master)

        butikk_match = resultat["test_malt"]["butikk_match"]["olbrygging"]
        forslag = malt_packaging.bygg_pakningsforslag(4230.0, butikk_match)

        self.assertIsNotNone(forslag)
        self.assertIn("kjopsresultat", forslag)
        self.assertGreater(forslag["kjopsresultat"]["mottatt_mengde"], 0)


if __name__ == "__main__":
    unittest.main()
