"""
Tester for Steg F2: modellering av Vestbryggs faktiske maltvarianter og
lagerstatus i modules/store_matcher.py::_bygg_vestbrygg_variantliste().

Bakgrunn: Steg F1 lærte scraperen å oppdage og parse Vestbryggs faktiske
barn-/variantprodukter (1 kg hel/knust, 100g knust, 25 kg hel/knust) i
stedet for å stoppe ved mor-sidens "Fra X,-"-teaserpris. Steg F2 samler
disse barn-radene til en butikk_match.vestbrygg.varianter-liste — samme
grunnform som Ølbrygging fikk i Steg D (se
tests/test_store_matcher_ol_variantliste.py), men med ett ekstra felt:
"lagerstatus" ("pa_lager"/"utsolgt"/"ukjent"), lest fra barn-siden sitt
<body class="in-stock"|"not-in-stock">-signal ved skrapetidspunktet (se
modules/product_link_scraper.py::_lagerstatus_fra_html()).

Valgt no-stock-policy (Steg F2, alternativ A): utsolgte varianter BEHOLDES
i masterdata som kjent katalogdata (markert eksplisitt), men filtreres
bort fra kjøpsforslagene i modules/malt_packaging.py (se
tests/test_malt_packaging.py for den delen).

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


# Speiler ekte Vestbrygg-barn-SKU-er for én malt (se Steg E/F1/F2-rapportene):
# 1 kg hel og 1 kg knust på lager, 100g knust på lager, 25 kg hel UTSOLGT,
# 25 kg knust med UKJENT lagerstatus (feltet mangler helt i denne raden —
# simulerer eldre rader/andre kilder uten lagerstatus-signal).
V_1KG_HEL = {"navn": "Test Malt 1 kg hel", "butikk": "vestbrygg", "pris": 49.0,
             "pakke_gram": 1000.0, "er_knust": False, "lagerstatus": "pa_lager",
             "url": "https://vestbrygg.no/test/20110/test-malt-1-kg-hel"}
V_1KG_KNUST = {"navn": "Test Malt 1 kg knust", "butikk": "vestbrygg", "pris": 54.0,
               "pakke_gram": 1000.0, "er_knust": True, "lagerstatus": "pa_lager",
               "url": "https://vestbrygg.no/test/21110/test-malt-1-kg-knust"}
V_100G_KNUST = {"navn": "Test Malt 100g knust", "butikk": "vestbrygg", "pris": 7.0,
                "pakke_gram": 100.0, "er_knust": True, "lagerstatus": "pa_lager",
                "url": "https://vestbrygg.no/test/23110/test-malt-100g-knust"}
V_25KG_HEL_UTSOLGT = {"navn": "Test Malt 25 kg hel", "butikk": "vestbrygg", "pris": 799.0,
                      "pakke_gram": 25000.0, "er_knust": False, "lagerstatus": "utsolgt",
                      "url": "https://vestbrygg.no/test/24110/test-malt-25kg-hel"}
V_25KG_KNUST_UKJENT = {"navn": "Test Malt 25 kg knust", "butikk": "vestbrygg", "pris": 824.0,
                       "pakke_gram": 25000.0, "er_knust": True,
                       # Ingen "lagerstatus"-nøkkel i det hele tatt her -- simulerer manglende signal.
                       "url": "https://vestbrygg.no/test/25110/test-malt-25kg-knust"}

ALLE_FEM = [V_1KG_HEL, V_1KG_KNUST, V_100G_KNUST, V_25KG_HEL_UTSOLGT, V_25KG_KNUST_UKJENT]


class Test1VestbryggVarianterSamlesPerMastermalt(unittest.TestCase):
    def test_fem_barn_sku_er_samles_i_en_variantliste(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        self.assertEqual(len(varianter), 5)


class Test2StorrelserBevaresNarDeFaktiskFinnes(unittest.TestCase):
    def test_100g_1kg_25kg_bevares(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        storrelser = {v["pakningsstorrelse_gram"] for v in varianter}
        self.assertEqual(storrelser, {100.0, 1000.0, 25000.0})


class Test3HelOgKnustHoldesSeparate(unittest.TestCase):
    def test_hel_og_knust_er_atskilte_varianter(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        par = {(v["pakningsstorrelse_gram"], v["malttype"]) for v in varianter}
        self.assertEqual(par, {
            (1000.0, "hel"), (1000.0, "knust"), (100.0, "knust"),
            (25000.0, "hel"), (25000.0, "knust"),
        })


class Test4PrisOgUrlFraSammeBarnSku(unittest.TestCase):
    def test_hver_variant_har_pris_url_og_lagerstatus_fra_samme_rad(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        per_nokkel = {(v["pakningsstorrelse_gram"], v["malttype"]): v for v in varianter}

        v = per_nokkel[(1000.0, "knust")]
        self.assertEqual(v["pris"], V_1KG_KNUST["pris"])
        self.assertEqual(v["url"], V_1KG_KNUST["url"])
        self.assertEqual(v["lagerstatus"], "pa_lager")
        self.assertNotEqual(v["pris"], V_1KG_HEL["pris"])


class Test5And6LagerstatusPaLagerOgUtsolgtBevares(unittest.TestCase):
    def test_pa_lager_variant_far_riktig_lagerstatus(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        v = next(v for v in varianter if v["pakningsstorrelse_gram"] == 1000.0 and v["malttype"] == "hel")
        self.assertEqual(v["lagerstatus"], "pa_lager")

    def test_utsolgt_variant_far_riktig_lagerstatus(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        v = next(v for v in varianter if v["pakningsstorrelse_gram"] == 25000.0 and v["malttype"] == "hel")
        self.assertEqual(v["lagerstatus"], "utsolgt")


class Test7UkjentLagerstatusHandteresEksplisitt(unittest.TestCase):
    def test_manglende_lagerstatus_felt_blir_eksplisitt_ukjent(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        v = next(v for v in varianter if v["pakningsstorrelse_gram"] == 25000.0 and v["malttype"] == "knust")
        self.assertEqual(v["lagerstatus"], "ukjent")


class Test8UtsolgteVariarterBeholdesIMasterdata(unittest.TestCase):
    """Valgt policy (alternativ A): utsolgte varianter fjernes IKKE fra
    masterdata -- de er fortsatt kjent katalogdata. Filtreringen skjer i
    modules/malt_packaging.py, se tests/test_malt_packaging.py."""

    def test_utsolgt_variant_er_fortsatt_med_i_variantlisten(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        self.assertEqual(len(varianter), 5)  # inkl. den utsolgte 25 kg hel-varianten
        self.assertTrue(any(v["lagerstatus"] == "utsolgt" for v in varianter))


class Test11FlatFallbackUendret(unittest.TestCase):
    def test_flat_pris_url_folger_fortsatt_steg_a_sin_regel(self):
        from modules.store_matcher import _pris_per_kg

        master = _master_malt_fixture(("test_malt", "Test Malt"))
        resultat, _, _ = _kjor_malt(ALLE_FEM, master)
        flat = resultat["test_malt"]["butikk_match"]["vestbrygg"]

        # 1 kg hel skal fortsatt vinne det flate valget (Steg A), uansett
        # at alle fem nå også ligger i variantlisten:
        self.assertEqual(flat["url"], V_1KG_HEL["url"])
        self.assertEqual(flat["pris"], _pris_per_kg(V_1KG_HEL["pris"], V_1KG_HEL["pakke_gram"], "malt"))
        self.assertIn("varianter", flat)


class Test12DeterministiskRekkefolge(unittest.TestCase):
    def test_variantlisten_er_identisk_uansett_inputrekkefolge(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))

        resultat_normal, _, _ = _kjor_malt(ALLE_FEM, json.loads(json.dumps(master)))
        resultat_omvendt, _, _ = _kjor_malt(list(reversed(ALLE_FEM)), json.loads(json.dumps(master)))

        v_normal = resultat_normal["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        v_omvendt = resultat_omvendt["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        self.assertEqual(v_normal, v_omvendt)


class Test13DuplikaterFjernes(unittest.TestCase):
    def test_eksakt_duplikatrad_gir_ikke_ekstra_variant(self):
        master = _master_malt_fixture(("test_malt", "Test Malt"))
        duplikat = dict(V_1KG_HEL)
        resultat, _, _ = _kjor_malt([V_1KG_HEL, duplikat, V_100G_KNUST], master)
        varianter = resultat["test_malt"]["butikk_match"]["vestbrygg"]["varianter"]
        self.assertEqual(len(varianter), 2)


class Test14EnkeltVariantFungerer(unittest.TestCase):
    def test_ett_treff_gir_enkelt_variantliste_og_uendret_flate_felt(self):
        master = _master_malt_fixture(("enkel_malt", "Enkel Malt"))
        enkel = {"navn": "Enkel Malt 1 kg hel", "butikk": "vestbrygg", "pris": 45.0,
                 "pakke_gram": 1000.0, "er_knust": False, "lagerstatus": "pa_lager",
                 "url": "https://vestbrygg.no/enkel/20999/enkel-malt-1kg-hel"}

        resultat, matched, unmatched = _kjor_malt([enkel], master)
        bm = resultat["enkel_malt"]["butikk_match"]["vestbrygg"]

        self.assertEqual(matched, 1)
        self.assertEqual(unmatched, 0)
        self.assertEqual(bm["url"], enkel["url"])
        self.assertEqual(bm["varianter"], [
            {"pakningsstorrelse_gram": 1000.0, "malttype": "hel", "pris": 45.0,
             "url": enkel["url"], "lagerstatus": "pa_lager"},
        ])


class Test15VestbryggMorUtenVarianterFolgerFallback(unittest.TestCase):
    def test_kandidat_uten_kjent_pakke_gram_far_ingen_varianter_felt(self):
        # Speiler en mor-side uten variantvelger (f.eks. spraymalt) --
        # F1 lot den URL-en stå uendret, så parse_produktside() gir her
        # samme gamle "Fra X,-"-rad uten pakke_gram, akkurat som før Steg F.
        master = _master_malt_fixture(("spraymalt_test", "Spraymalt Test"))
        mor_uten_varianter = {"navn": "Spraymalt Test", "butikk": "vestbrygg", "pris": 7.0,
                              "pakke_gram": None, "er_knust": False, "lagerstatus": "pa_lager",
                              "url": "https://vestbrygg.no/ekstrakt/103999/spraymalt-test"}

        resultat, _, _ = _kjor_malt([mor_uten_varianter], master)
        bm = resultat["spraymalt_test"]["butikk_match"]["vestbrygg"]

        self.assertNotIn("varianter", bm)
        self.assertEqual(bm["url"], mor_uten_varianter["url"])


class Test16HumleOgGjaerUendret(unittest.TestCase):
    def test_gjaer_matching_far_aldri_varianter_eller_lagerstatus(self):
        tmp = tempfile.mkdtemp()
        try:
            master = {"test_gjaer": {"display_name": "Test Gjær", "aliases": ["Test Gjær"],
                                      "butikk_match": {}, "verified": True}}
            rad = {"navn": "Test Gjær", "butikk": "vestbrygg", "pris": 59.0,
                   "url": "https://vestbrygg.no/gjaer/a"}

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

            bm = resultat["test_gjaer"]["butikk_match"]["vestbrygg"]
            self.assertNotIn("varianter", bm)
            self.assertNotIn("lagerstatus", bm)
        finally:
            shutil.rmtree(tmp)

    def test_humle_matching_far_aldri_varianter_eller_lagerstatus(self):
        tmp = tempfile.mkdtemp()
        try:
            master = {"test_humle": {"display_name": "Test Humle", "aliases": ["Test Humle 2025"],
                                      "butikk_match": {}, "verified": True}}
            rad = {"navn": "Test Humle 2025 Pellets - 100g", "butikk": "vestbrygg",
                   "pris": 100.0, "pakke_gram": 100.0, "url": "https://vestbrygg.no/humle/100g"}

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

            bm = resultat["test_humle"]["butikk_match"]["vestbrygg"]
            self.assertNotIn("varianter", bm)
            self.assertNotIn("lagerstatus", bm)
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main()
