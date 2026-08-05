"""
Tester for Steg F10D: valgfritt butikkfilter (`butikker`) og ekte,
skrivefri forhåndsvisning (`dry_run`) i det eksisterende entrypointet
modules/store_matcher.py::match_store_data_to_master_malt().

Bakgrunn: Steg F10B/F10C bygget den forrige "trygg dry-run-metode" ved å
kopiere hovedløkken inn i engangs-diagnoseskript utenfor produksjonskoden.
F10D gjør dette til en offisiell, testet del av selve entrypointet i
stedet — dry-run og ekte, filskrivende kjøring deler nå NØYAKTIG samme
kodebane (modules/store_matcher.py::_bygg_malt_matchresultat()), slik at
en dry-run-forhåndsvisning aldri kan avvike fra hva en ekte aktivering
faktisk ville gjort.

`butikker` begrenser KUN hvilke butikker som får lov til å skrive et
oppdatert butikk_match-forslag inn i master — matching, kandidatinnsamling
og statistikk kjøres uansett for HELE rådatasettet, slik at unmatched og
statistikk alltid dekker begge butikker uavhengig av filter (se Fase 4/6 i
oppdraget).

Disse testene bruker utelukkende isolerte temp-filer og syntetiske
fixture-verdier — ingen ekte raw_data/*.json eller data/master_*.json
røres.
"""
import copy
import json
import os
import shutil
import tempfile
import unittest

from modules.store_matcher import match_store_data_to_master_malt


def _master_malt_fixture(id_navn_par, forhandsutfylt_butikk_match=None):
    """Bygger en master_malt-fixture. `forhandsutfylt_butikk_match` er en
    dict {master_id: {butikk: {...}}} som legges inn FØR kjøring, for å
    simulere data fra en tidligere, allerede aktivert scraping-runde."""
    forhandsutfylt_butikk_match = forhandsutfylt_butikk_match or {}
    master = {}
    for m_id, navn in id_navn_par:
        master[m_id] = {
            "display_name": navn, "aliases": [navn],
            "butikk_match": copy.deepcopy(forhandsutfylt_butikk_match.get(m_id, {})),
            "verified": True,
        }
    return master


def _skriv_fixture_filer(tmp, malt_raw_liste, master):
    raw_path = os.path.join(tmp, "malt_raw.json")
    master_path = os.path.join(tmp, "master_malt.json")
    unmatched_path = os.path.join(tmp, "unmatched_malt.json")
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(malt_raw_liste, f)
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master, f)
    return raw_path, master_path, unmatched_path


def _kjor_dryrun(testcase, malt_raw_liste, master, **kwargs):
    """Kjører dry-run i en tempkatalog. Opprydding skjer via
    testcase.addCleanup() -- den kjører ETTER testmetoden er ferdig, så
    testen kan trygt inspisere tmp-katalogen/filene i kroppen sin (i
    motsetning til try/finally i selve hjelpefunksjonen, som ville
    ryddet opp FØR kalleren fikk sjekket noe)."""
    tmp = tempfile.mkdtemp()
    testcase.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
    raw_path, master_path, unmatched_path = _skriv_fixture_filer(tmp, malt_raw_liste, master)
    resultat = match_store_data_to_master_malt(raw_path, master_path, unmatched_path, dry_run=True, **kwargs)
    return resultat, tmp, master_path, unmatched_path


def _kjor_filskrivende(malt_raw_liste, master, **kwargs):
    tmp = tempfile.mkdtemp()
    try:
        raw_path, master_path, unmatched_path = _skriv_fixture_filer(tmp, malt_raw_liste, master)
        matched, unmatched_n = match_store_data_to_master_malt(raw_path, master_path, unmatched_path, **kwargs)
        with open(master_path, encoding="utf-8") as f:
            resultat_master = json.load(f)
        with open(unmatched_path, encoding="utf-8") as f:
            resultat_unmatched = json.load(f)
        return resultat_master, resultat_unmatched, matched, unmatched_n
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


VEST_1KG = {"navn": "CaraMalt - 1 kg Hel", "butikk": "vestbrygg", "pris": 44.0,
            "pakke_gram": 1000.0, "er_knust": False, "lagerstatus": "pa_lager",
            "url": "https://vestbrygg.no/test/1/caramalt-1kg-hel"}
OL_1KG = {"navn": "Caramalt 1 kg hel", "butikk": "olbrygging", "pris": 45.0,
          "pakke_gram": 1000.0, "er_knust": False,
          "url": "https://olbrygging.no/test/1/caramalt-1kg-hel"}
OL_KUN_OLBRYGGING = {"navn": "Kun Ol Malt 1 kg hel", "butikk": "olbrygging", "pris": 39.0,
                     "pakke_gram": 1000.0, "er_knust": False,
                     "url": "https://olbrygging.no/test/2/kun-ol-1kg-hel"}
OL_UNMATCHED = {"navn": "Helt Ukjent Maltsort", "butikk": "olbrygging", "pris": 20.0,
                "pakke_gram": 500.0, "er_knust": True,
                "url": "https://olbrygging.no/test/3/ukjent"}


class Test1DryRunSkriverIkkeFiler(unittest.TestCase):
    def test_dry_run_skriver_ikke_masterfil(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        original_innhold = json.dumps(master)
        resultat, tmp, master_path, unmatched_path = _kjor_dryrun(self, [VEST_1KG], master)
        with open(master_path, encoding="utf-8") as f:
            faktisk_innhold = f.read()
        self.assertEqual(json.loads(faktisk_innhold), json.loads(original_innhold))

    def test_dry_run_skriver_ikke_unmatched_fil(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        resultat, tmp, master_path, unmatched_path = _kjor_dryrun(self, [VEST_1KG, OL_UNMATCHED], master)
        self.assertFalse(os.path.exists(unmatched_path))


class Test2StrukturertResultat(unittest.TestCase):
    def test_resultatet_inneholder_forventede_nokler(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG, OL_UNMATCHED], master)
        for nokkel in ("master_forslag", "unmatched", "statistikk", "butikker", "dry_run"):
            self.assertIn(nokkel, resultat)
        self.assertTrue(resultat["dry_run"])

    def test_unmatched_inneholder_forventet_rad(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG, OL_UNMATCHED], master)
        navn_i_unmatched = {u["navn"] for u in resultat["unmatched"]}
        self.assertIn(OL_UNMATCHED["navn"], navn_i_unmatched)


class Test3ProposedMasterBrukerEkteMatcherlogikk(unittest.TestCase):
    def test_dry_run_master_forslag_er_identisk_med_ekte_kjoring(self):
        master_dry = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        master_ekte = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        raw = [VEST_1KG, OL_1KG]

        dry_resultat, _, _, _ = _kjor_dryrun(self, raw, master_dry)
        ekte_master, _, _, _ = _kjor_filskrivende(raw, master_ekte)

        self.assertEqual(dry_resultat["master_forslag"], ekte_master)


class Test4OriginalMasterInputMutertesIkke(unittest.TestCase):
    def test_master_dict_sendt_inn_forblir_uendret(self):
        from modules.store_matcher import _bygg_malt_matchresultat

        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        original_kopi = copy.deepcopy(master)
        _bygg_malt_matchresultat([VEST_1KG], master, None)
        self.assertEqual(master, original_kopi)


class Test5IngenTempfilLiggerIgjen(unittest.TestCase):
    def test_ingen_ekstra_filer_i_tempkatalogen_etter_dry_run(self):
        # unmatched_malt.json inngår bevisst IKKE i forventet sett: den
        # blir aldri opprettet i dry-run-modus, kun de to inputfilene
        # _skriv_fixture_filer() selv skrev før kallet.
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        resultat, tmp, master_path, unmatched_path = _kjor_dryrun(self, [VEST_1KG], master)
        filer = set(os.listdir(tmp))
        self.assertEqual(filer, {"malt_raw.json", "master_malt.json"})
        self.assertFalse(os.path.exists(unmatched_path))
        self.assertFalse(any(f.endswith(".tmp") for f in filer))


class Test6IngenAINormaliseringKalles(unittest.TestCase):
    def test_store_matcher_har_ingen_ai_relatert_navn(self):
        import modules.store_matcher as store_matcher_mod
        for navn in dir(store_matcher_mod):
            self.assertNotIn("ai_normaliser", navn.lower())
            self.assertNotIn("anthropic", navn.lower())
            self.assertNotIn("openai", navn.lower())


class Test7VestbryggOnlyOppdatererKunVestbrygg(unittest.TestCase):
    def test_vestbrygg_match_oppdateres(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG, OL_1KG], master, butikker={"vestbrygg"})
        bm = resultat["master_forslag"]["caramalt_test"]["butikk_match"]
        self.assertIn("vestbrygg", bm)
        self.assertEqual(bm["vestbrygg"]["url"], VEST_1KG["url"])

    def test_olbrygging_match_for_samme_id_forblir_identisk(self):
        forhandsutfylt = {"caramalt_test": {"olbrygging": {"pris": 45.0, "url": "https://olbrygging.no/gammel-url"}}}
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")], forhandsutfylt)
        original_olbrygging = copy.deepcopy(master["caramalt_test"]["butikk_match"]["olbrygging"])

        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG, OL_1KG], master, butikker={"vestbrygg"})
        bm = resultat["master_forslag"]["caramalt_test"]["butikk_match"]
        self.assertEqual(bm["olbrygging"], original_olbrygging)

    def test_ny_olbrygging_kandidat_oppretter_ikke_ny_butikkmatch(self):
        master = _master_malt_fixture([("kun_ol_malt", "Kun Ol Malt")])
        resultat, _, _, _ = _kjor_dryrun(self, [OL_KUN_OLBRYGGING], master, butikker={"vestbrygg"})
        bm = resultat["master_forslag"]["kun_ol_malt"]["butikk_match"]
        self.assertNotIn("olbrygging", bm)
        self.assertEqual(bm, {})

    def test_olbrygging_unmatched_fortsatt_i_resultatet(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG, OL_UNMATCHED], master, butikker={"vestbrygg"})
        navn_i_unmatched = {u["navn"] for u in resultat["unmatched"]}
        self.assertIn(OL_UNMATCHED["navn"], navn_i_unmatched)

    def test_master_id_settet_er_uendret(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt"), ("kun_ol_malt", "Kun Ol Malt")])
        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG, OL_KUN_OLBRYGGING], master, butikker={"vestbrygg"})
        self.assertEqual(set(resultat["master_forslag"].keys()), {"caramalt_test", "kun_ol_malt"})

    def test_ingen_eksisterende_butikkmatcher_slettes(self):
        forhandsutfylt = {"kun_ol_malt": {"olbrygging": {"pris": 39.0, "url": OL_KUN_OLBRYGGING["url"]}}}
        master = _master_malt_fixture([("caramalt_test", "CaraMalt"), ("kun_ol_malt", "Kun Ol Malt")], forhandsutfylt)
        original_olbrygging = copy.deepcopy(master["kun_ol_malt"]["butikk_match"]["olbrygging"])

        resultat, _, _, _ = _kjor_dryrun(self, [VEST_1KG], master, butikker={"vestbrygg"})
        bm = resultat["master_forslag"]["kun_ol_malt"]["butikk_match"]
        self.assertEqual(bm["olbrygging"], original_olbrygging)

    def test_crystal_maple_lignende_tilfelle_uten_vestbrygg_raw_forblir_urort(self):
        # Simulerer Crystal Maple/Carapils: eksisterende Vestbrygg-match
        # fra en tidligere kjøring, men INGEN Vestbrygg-raw-kandidat i
        # denne kjøringen (kun en urelatert Ølbrygging-rad et annet sted).
        forhandsutfylt = {"crystal_maple_test": {"vestbrygg": {"pris": 199.0, "url": "https://vestbrygg.no/gammel/crystal-maple"}}}
        master = _master_malt_fixture([("crystal_maple_test", "Crystal Maple")], forhandsutfylt)
        original_vestbrygg = copy.deepcopy(master["crystal_maple_test"]["butikk_match"]["vestbrygg"])

        resultat, _, _, _ = _kjor_dryrun(self, [OL_UNMATCHED], master, butikker={"vestbrygg"})
        bm = resultat["master_forslag"]["crystal_maple_test"]["butikk_match"]
        self.assertEqual(bm["vestbrygg"], original_vestbrygg)
        self.assertNotIn("olbrygging", bm)

    def test_ukjent_butikkfilter_gir_valueerror(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        with self.assertRaises(ValueError):
            _kjor_dryrun(self, [VEST_1KG], master, butikker={"litebrygg"})

    def test_tomt_butikksett_gir_valueerror(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        with self.assertRaises(ValueError):
            _kjor_dryrun(self, [VEST_1KG], master, butikker=set())

    def test_butikker_none_gir_samme_proposed_master_som_gammel_fullkjoring(self):
        master_dry = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        master_ekte = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        raw = [VEST_1KG, OL_1KG]

        dry_resultat, _, _, _ = _kjor_dryrun(self, raw, master_dry, butikker=None)
        ekte_master, _, matched, unmatched_n = _kjor_filskrivende(raw, master_ekte)

        self.assertEqual(dry_resultat["master_forslag"], ekte_master)
        self.assertEqual(dry_resultat["statistikk"]["matchet_totalt"], matched)
        self.assertEqual(len(dry_resultat["unmatched"]), unmatched_n)


class Test8BakoverkompatibelReturverdi(unittest.TestCase):
    def test_kall_uten_nye_parametre_gir_samme_tuppel_som_for(self):
        master = _master_malt_fixture([("caramalt_test", "CaraMalt")])
        ekte_master, ekte_unmatched, matched, unmatched_n = _kjor_filskrivende([VEST_1KG, OL_UNMATCHED], master)
        self.assertEqual(matched, 1)
        self.assertEqual(unmatched_n, 1)
        self.assertIsInstance(matched, int)
        self.assertIsInstance(unmatched_n, int)


if __name__ == "__main__":
    unittest.main()
