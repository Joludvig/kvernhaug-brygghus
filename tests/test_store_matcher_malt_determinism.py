"""
Regresjonstester for determinismefiksen i
modules/store_matcher.py::match_store_data_to_master_malt().

Bakgrunn (se rotårsaksrapporten fra samme økt): når flere rå
maltprodukter (ulike pakningsstørrelser/format hos samme butikk)
matcher samme master-alias, skrev den gamle koden ubetinget siste
behandlede rad til butikk_match — "siste rad vinner". Siden
modules/product_link_scraper.py::finn_produktsider() samler URL-er via
et set() hvis iterasjonsrekkefølge er hash-randomisert per Python-
prosess, var resultatet ikke-deterministisk på tvers av scrape-kjøringer
selv når butikkens faktiske sortiment ikke hadde endret seg.

Disse testene bruker utelukkende isolerte temp-filer — ingen ekte
raw_data/*.json eller data/master_*.json røres.
"""
import json
import os
import shutil
import tempfile
import unittest
from itertools import permutations

from modules.store_matcher import (
    match_store_data_to_master_malt,
    match_store_data_to_master,
    match_store_data_to_master_gjaer,
)


def _master_malt_fixture(*alias_par):
    """alias_par: (master_id, visningsnavn)-par."""
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


# Fire pakningsvarianter av samme malt hos vestbrygg — 1 kg hel skal
# alltid vinne (1 kg foretrukket fremfor 5/25 kg, og hel fremfor knust
# ved lik størrelse).
V_1KG_HEL = {"navn": "Test Malt 1 kg hel", "butikk": "vestbrygg", "pris": 40.0,
             "pakke_gram": 1000.0, "er_knust": False,
             "url": "https://vestbrygg.no/test/1/test-malt-1-kg-hel"}
V_1KG_KNUST = {"navn": "Test Malt 1 kg knust", "butikk": "vestbrygg", "pris": 42.0,
               "pakke_gram": 1000.0, "er_knust": True,
               "url": "https://vestbrygg.no/test/2/test-malt-1-kg-knust"}
V_5KG_HEL = {"navn": "Test Malt 5 kg hel", "butikk": "vestbrygg", "pris": 180.0,
             "pakke_gram": 5000.0, "er_knust": False,
             "url": "https://vestbrygg.no/test/3/test-malt-5-kg-hel"}
V_25KG_HEL = {"navn": "Test Malt 25 kg hel", "butikk": "vestbrygg", "pris": 800.0,
              "pakke_gram": 25000.0, "er_knust": False,
              "url": "https://vestbrygg.no/test/4/test-malt-25-kg-hel"}


class Test1SammeKandidaterOmvendtRekkefolge(unittest.TestCase):
    def test_normal_og_omvendt_rekkefolge_gir_identisk_resultat(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        rader = [V_1KG_HEL, V_1KG_KNUST, V_5KG_HEL, V_25KG_HEL]

        resultat_normal, _, _ = _kjor_malt(rader, json.loads(json.dumps(master)))
        resultat_omvendt, _, _ = _kjor_malt(list(reversed(rader)), json.loads(json.dumps(master)))

        self.assertEqual(
            resultat_normal["test_malt"]["butikk_match"],
            resultat_omvendt["test_malt"]["butikk_match"],
        )
        self.assertEqual(
            resultat_normal["test_malt"]["butikk_match"]["vestbrygg"]["url"],
            V_1KG_HEL["url"],
        )


class Test2FlerePermutasjonerGirIdentiskResultat(unittest.TestCase):
    def test_alle_24_permutasjoner_gir_samme_butikk_match(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        rader = [V_1KG_HEL, V_1KG_KNUST, V_5KG_HEL, V_25KG_HEL]

        resultater = []
        for rekkefolge in permutations(rader):
            resultat, _, _ = _kjor_malt(list(rekkefolge), json.loads(json.dumps(master)))
            resultater.append(resultat["test_malt"]["butikk_match"])

        forste = resultater[0]
        for r in resultater[1:]:
            self.assertEqual(r, forste)


class Test3StorrelserRangeresDeterministisk(unittest.TestCase):
    def test_1kg_foretrekkes_fremfor_5kg_og_25kg_uansett_rekkefolge(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        rader = [V_25KG_HEL, V_5KG_HEL, V_1KG_HEL]  # bevisst "feil" rekkefølge

        resultat, _, _ = _kjor_malt(rader, master)
        self.assertEqual(resultat["test_malt"]["butikk_match"]["vestbrygg"]["url"], V_1KG_HEL["url"])

    def test_uten_1kg_variant_foretrekkes_minste_kjente_storrelse(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        rader = [V_25KG_HEL, V_5KG_HEL]

        resultat, _, _ = _kjor_malt(rader, master)
        self.assertEqual(resultat["test_malt"]["butikk_match"]["vestbrygg"]["url"], V_5KG_HEL["url"])


class Test4HelOgKnustRangeresEtterRegel(unittest.TestCase):
    def test_hel_foretrekkes_fremfor_knust_ved_lik_storrelse(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        rader = [V_1KG_KNUST, V_1KG_HEL]  # knust først i input — skal likevel tape

        resultat, _, _ = _kjor_malt(rader, master)
        self.assertEqual(resultat["test_malt"]["butikk_match"]["vestbrygg"]["url"], V_1KG_HEL["url"])


class Test5UkjentPakningsstorrelseHandteresStabilt(unittest.TestCase):
    def test_ukjent_storrelse_for_alle_kandidater_gir_stabilt_valg(self):
        master = _master_malt_fixture(("ukjent_malt", "Ukjent Malt"))
        a = {"navn": "Ukjent Malt A", "butikk": "vestbrygg", "pris": 50.0,
             "pakke_gram": None, "er_knust": False, "url": "https://vestbrygg.no/ukjent/a"}
        b = {"navn": "Ukjent Malt B", "butikk": "vestbrygg", "pris": 55.0,
             "pakke_gram": None, "er_knust": False, "url": "https://vestbrygg.no/ukjent/b"}

        resultat_1, _, _ = _kjor_malt([a, b], json.loads(json.dumps(master)))
        resultat_2, _, _ = _kjor_malt([b, a], json.loads(json.dumps(master)))

        self.assertIsNotNone(resultat_1["ukjent_malt"]["butikk_match"]["vestbrygg"]["url"])
        self.assertEqual(
            resultat_1["ukjent_malt"]["butikk_match"],
            resultat_2["ukjent_malt"]["butikk_match"],
        )

    def test_kjent_storrelse_foretrekkes_fremfor_ukjent(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        ukjent = {"navn": "Test Malt variant", "butikk": "vestbrygg", "pris": 50.0,
                  "pakke_gram": None, "er_knust": False, "url": "https://vestbrygg.no/test/ukjent"}

        resultat, _, _ = _kjor_malt([ukjent, V_5KG_HEL], master)
        self.assertEqual(resultat["test_malt"]["butikk_match"]["vestbrygg"]["url"], V_5KG_HEL["url"])


class Test6EnkeltKandidatUpavirket(unittest.TestCase):
    def test_ett_treff_gir_uendret_resultat(self):
        master = _master_malt_fixture(("enkel_malt", "Enkel Malt"))
        enkel = {"navn": "Enkel Malt 1 kg hel", "butikk": "vestbrygg", "pris": 45.0,
                 "pakke_gram": 1000.0, "er_knust": False,
                 "url": "https://vestbrygg.no/enkel/1/enkel-malt-1kg-hel"}

        resultat, matched, unmatched = _kjor_malt([enkel], master)

        self.assertEqual(matched, 1)
        self.assertEqual(unmatched, 0)
        self.assertEqual(resultat["enkel_malt"]["butikk_match"]["vestbrygg"]["url"], enkel["url"])
        self.assertEqual(resultat["enkel_malt"]["butikk_match"]["vestbrygg"]["pris"], 45.0)


class Test7ToButikkerHoldesSeparate(unittest.TestCase):
    def test_vestbrygg_og_olbrygging_kollisjoner_pavirker_ikke_hverandre(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        o_1kg = {"navn": "Test Malt 1 kg hel", "butikk": "olbrygging", "pris": 38.0,
                 "pakke_gram": 1000.0, "er_knust": False,
                 "url": "https://www.olbrygging.no/test/1/test-malt-1kg-hel"}
        o_100g = {"navn": "Test Malt 100 g knust", "butikk": "olbrygging", "pris": 9.0,
                  "pakke_gram": 100.0, "er_knust": True,
                  "url": "https://www.olbrygging.no/test/2/test-malt-100g-knust"}

        rader = [V_25KG_HEL, o_100g, V_1KG_HEL, o_1kg, V_5KG_HEL]
        resultat, _, _ = _kjor_malt(rader, master)

        bm = resultat["test_malt"]["butikk_match"]
        self.assertEqual(bm["vestbrygg"]["url"], V_1KG_HEL["url"])
        self.assertEqual(bm["olbrygging"]["url"], o_1kg["url"])


class Test8PrisOgUrlFraSammeValgteRad(unittest.TestCase):
    def test_pris_og_url_stemmer_overens_med_samme_kandidat(self):
        from modules.store_matcher import _pris_per_kg

        master = _master_malt_fixture(("test_malt", "Test Malt"))
        rader = [V_5KG_HEL, V_1KG_HEL, V_25KG_HEL]  # V_1KG_HEL skal vinne

        resultat, _, _ = _kjor_malt(rader, master)
        bm = resultat["test_malt"]["butikk_match"]["vestbrygg"]

        forventet_pris = _pris_per_kg(V_1KG_HEL["pris"], V_1KG_HEL["pakke_gram"], "malt")
        self.assertEqual(bm["pris"], forventet_pris)
        self.assertEqual(bm["url"], V_1KG_HEL["url"])
        # Ikke ved et uhell blandet med en tapende kandidats tall:
        self.assertNotEqual(bm["url"], V_5KG_HEL["url"])
        self.assertNotEqual(bm["url"], V_25KG_HEL["url"])


class Test9HumleOgGjaerMatchingUendret(unittest.TestCase):
    def test_gjaer_beholder_ubetinget_siste_rad_vinner(self):
        tmp = tempfile.mkdtemp()
        try:
            master = {"test_gjaer": {"display_name": "Test Gjær", "aliases": ["Test Gjær"],
                                      "butikk_match": {}, "verified": True}}
            rad_a = {"navn": "Test Gjær", "butikk": "vestbrygg", "pris": 59.0,
                     "url": "https://vestbrygg.no/gjaer/a"}
            rad_b = {"navn": "Test Gjær", "butikk": "vestbrygg", "pris": 65.0,
                     "url": "https://vestbrygg.no/gjaer/b"}

            raw_path = os.path.join(tmp, "gjaer_raw.json")
            master_path = os.path.join(tmp, "master_gjaer.json")
            unmatched_path = os.path.join(tmp, "unmatched_gjaer.json")

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump([rad_a, rad_b], f)
            with open(master_path, "w", encoding="utf-8") as f:
                json.dump(master, f)
            match_store_data_to_master_gjaer(raw_path, master_path, unmatched_path)
            with open(master_path, encoding="utf-8") as f:
                resultat = json.load(f)

            # Uendret oppførsel: SISTE rad i lista vinner ubetinget (rad_b),
            # ikke den nye maltrangeringen — gjærmatching er ikke rørt.
            self.assertEqual(resultat["test_gjaer"]["butikk_match"]["vestbrygg"]["url"], rad_b["url"])
        finally:
            shutil.rmtree(tmp)

    def test_humle_beholder_eksisterende_minste_pakke_gram_regel(self):
        tmp = tempfile.mkdtemp()
        try:
            master = {"test_humle": {"display_name": "Test Humle", "aliases": ["Test Humle 2025"],
                                      "butikk_match": {}, "verified": True}}
            stor = {"navn": "Test Humle 2025 Pellets - 500g", "butikk": "vestbrygg",
                    "pris": 400.0, "pakke_gram": 500.0, "url": "https://vestbrygg.no/humle/500g"}
            liten = {"navn": "Test Humle 2025 Pellets - 100g", "butikk": "vestbrygg",
                     "pris": 100.0, "pakke_gram": 100.0, "url": "https://vestbrygg.no/humle/100g"}

            raw_path = os.path.join(tmp, "humle_raw.json")
            master_path = os.path.join(tmp, "master_humle.json")
            matched_path = os.path.join(tmp, "matched_hops.json")
            unmatched_path = os.path.join(tmp, "unmatched_hops.json")

            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump([stor, liten], f)
            with open(master_path, "w", encoding="utf-8") as f:
                json.dump(master, f)
            match_store_data_to_master(raw_path, master_path, matched_path, unmatched_path)
            with open(master_path, encoding="utf-8") as f:
                resultat = json.load(f)

            # Uendret, eksisterende humle-regel (upåvirket av denne rundens
            # maltfiks): minste kjente pakke_gram vinner.
            self.assertEqual(resultat["test_humle"]["butikk_match"]["vestbrygg"]["url"], liten["url"])
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
