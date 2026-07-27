"""
Tester for modules/water_chemistry.py — ren Python, ingen Streamlit-
avhengighet. Dekker konverteringsformler, saltberegninger, fordeling
mesk/skylling, solveren og varselgenerering.

Tester som skriver til disk (lagre_vannkilder/lagre_vannmaal) bruker
KVERNHAUG_WATER_SOURCES_FILE/KVERNHAUG_WATER_TARGETS_FILE for isolasjon —
samme mønster og samme begrunnelse som KVERNHAUG_RECIPES_DIR i
tests/test_recipe_storage_isolation.py: den EKTE data/water_sources.json
(med Jordalsvatnet 2025) og data/water_targets.json skal ALDRI kunne
overskrives av en test.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import os
import tempfile
import unittest

from modules.water_chemistry import (
    IONER,
    hco3_mg_l_til_alkalitet_mmol_l, alkalitet_mmol_l_til_hco3_mg_l,
    alkalitet_mmol_l_til_caco3_mg_l, caco3_mg_l_til_alkalitet_mmol_l,
    hco3_mg_l_til_caco3_mg_l, caco3_mg_l_til_hco3_mg_l,
    normaliser_alkalitet,
    hent_salt, alle_salter, SALTER,
    beregn_ion_bidrag_ppm, gram_for_onsket_ppm,
    beregn_saltbidrag, summer_ionbidrag, beregn_sluttprofil,
    cl_so4_forhold,
    fordel_salttilsetning, fordel_alle_salter,
    PROPORSJONAL, ALT_I_MESK, EGENDEFINERT_FORDELING,
    status_for_ion, bygg_ionrapport,
    generer_varsler, STANDARD_VARSELGRENSER,
    foreslaa_salter,
    bygg_syretilsetning,
    last_vannkilder, lagre_vannkilder, last_vannmaal, lagre_vannmaal,
    tomt_kildevann,
)

_KVERNHAUG_MAAL = {
    "ca_min": 50, "ca_max": 65,
    "mg_min": 0, "mg_max": 8,
    "na_min": 0, "na_max": 20,
    "cl_min": 50, "cl_max": 70,
    "so4_min": 30, "so4_max": 45,
    "hco3_min": 25, "hco3_max": 60,
    "mash_ph_min": 5.30, "mash_ph_max": 5.40,
}

_JORDALSVATNET = {
    "ca": 20.0, "mg": 0.5, "na": 4.5, "cl": 9.7, "so4": 8.1, "hco3": 43.0,
}


class Test1JordalsvatnetProfilLastesKorrekt(unittest.TestCase):
    """Verifiserer at DEN EKTE data/water_sources.json faktisk inneholder
    Jordalsvatnet 2025 med riktige verdier — ren lesing, ingen skriving."""

    def test_jordalsvatnet_profil_lastes_korrekt(self):
        kilder = last_vannkilder()
        self.assertIn("jordalsvatnet_2025", kilder)
        j = kilder["jordalsvatnet_2025"]
        self.assertEqual(j["name"], "Jordalsvatnet 2025")
        self.assertEqual(j["ca"], 20.0)
        self.assertEqual(j["mg"], 0.5)
        self.assertEqual(j["na"], 4.5)
        self.assertEqual(j["cl"], 9.7)
        self.assertEqual(j["so4"], 8.1)
        self.assertEqual(j["hco3"], 43.0)
        self.assertEqual(j["alkalinity_mmol_l"], 0.73)
        self.assertTrue(j.get("is_default"))


class Test2AlkalitetKonvertering(unittest.TestCase):
    def test_hco3_til_mmol_og_tilbake(self):
        mmol = hco3_mg_l_til_alkalitet_mmol_l(61.017)
        self.assertAlmostEqual(mmol, 1.0, places=6)
        self.assertAlmostEqual(alkalitet_mmol_l_til_hco3_mg_l(mmol), 61.017, places=6)

    def test_mmol_til_caco3_og_tilbake(self):
        caco3 = alkalitet_mmol_l_til_caco3_mg_l(1.0)
        self.assertAlmostEqual(caco3, 50.043, places=2)
        self.assertAlmostEqual(caco3_mg_l_til_alkalitet_mmol_l(caco3), 1.0, places=6)

    def test_hco3_til_caco3_rundtur(self):
        hco3 = 43.0
        caco3 = hco3_mg_l_til_caco3_mg_l(hco3)
        tilbake = caco3_mg_l_til_hco3_mg_l(caco3)
        self.assertAlmostEqual(tilbake, hco3, places=6)

    def test_normaliser_alkalitet_merker_grunnlag(self):
        res = normaliser_alkalitet(43.0, "hco3_mg_l")
        self.assertEqual(res["opprinnelig_grunnlag"], "hco3_mg_l")
        self.assertEqual(res["hco3_mg_l"], 43.0)
        self.assertAlmostEqual(res["mmol_l"], 43.0 / 61.017, places=6)

        res2 = normaliser_alkalitet(0.73, "mmol_l")
        self.assertEqual(res2["opprinnelig_grunnlag"], "mmol_l")
        self.assertAlmostEqual(res2["hco3_mg_l"], 0.73 * 61.017, places=6)

    def test_normaliser_alkalitet_none_forblir_none(self):
        res = normaliser_alkalitet(None, "hco3_mg_l")
        self.assertIsNone(res["hco3_mg_l"])
        self.assertIsNone(res["mmol_l"])
        self.assertIsNone(res["caco3_mg_l"])

    def test_ukjent_grunnlag_gir_feil(self):
        with self.assertRaises(ValueError):
            normaliser_alkalitet(1.0, "noe_ukjent")


class Test3til9SaltBeregninger(unittest.TestCase):
    """CaCl2·2H2O, gips, epsomsalt, NaCl, natron, renhet, hydreringsformer."""

    def test_cacl2_dihydrat_beregning(self):
        bidrag = beregn_saltbidrag("cacl2_2h2o", 3.7, 1.0, 35.5)
        self.assertAlmostEqual(bidrag["ca"], 3.7 * 0.27261 * 1000 / 35.5, places=3)
        self.assertAlmostEqual(bidrag["cl"], 3.7 * 0.48226 * 1000 / 35.5, places=3)
        self.assertNotIn("so4", bidrag)

    def test_gips_beregning(self):
        bidrag = beregn_saltbidrag("gips", 2.0, 1.0, 35.5)
        self.assertAlmostEqual(bidrag["ca"], 2.0 * 0.23279 * 1000 / 35.5, places=3)
        self.assertAlmostEqual(bidrag["so4"], 2.0 * 0.55795 * 1000 / 35.5, places=3)

    def test_epsomsalt_beregning(self):
        bidrag = beregn_saltbidrag("epsomsalt", 1.0, 1.0, 20.0)
        self.assertAlmostEqual(bidrag["mg"], 1.0 * 0.09861 * 1000 / 20.0, places=3)
        self.assertAlmostEqual(bidrag["so4"], 1.0 * 0.38975 * 1000 / 20.0, places=3)

    def test_nacl_beregning(self):
        bidrag = beregn_saltbidrag("vanlig_salt", 1.0, 1.0, 20.0)
        self.assertAlmostEqual(bidrag["na"], 1.0 * 0.39337 * 1000 / 20.0, places=3)
        self.assertAlmostEqual(bidrag["cl"], 1.0 * 0.60663 * 1000 / 20.0, places=3)

    def test_natron_beregning(self):
        bidrag = beregn_saltbidrag("natron", 1.0, 1.0, 20.0)
        self.assertAlmostEqual(bidrag["na"], 1.0 * 0.27366 * 1000 / 20.0, places=3)
        self.assertAlmostEqual(bidrag["hco3"], 1.0 * 0.72634 * 1000 / 20.0, places=3)

    def test_kalsiumkarbonat_har_loeselighetsadvarsel(self):
        salt = hent_salt("kalsiumkarbonat")
        self.assertTrue(salt["advarsler"])
        self.assertIn("løselighet", salt["advarsler"][0].lower())

    def test_saltrenhet_skalerer_lineaert(self):
        full = beregn_saltbidrag("gips", 2.0, 1.0, 20.0)
        halv = beregn_saltbidrag("gips", 2.0, 0.5, 20.0)
        self.assertAlmostEqual(halv["ca"], full["ca"] / 2, places=6)
        self.assertAlmostEqual(halv["so4"], full["so4"] / 2, places=6)

    def test_ulike_hydreringsformer_gir_ulikt_ionbidrag(self):
        # Samme antall gram, men CaCl2 (vannfri) skal gi MER Ca/Cl enn
        # CaCl2·2H2O — krystallvannet i dihydratet "fortynner" saltet.
        dihydrat = beregn_saltbidrag("cacl2_2h2o", 5.0, 1.0, 20.0)
        vannfri = beregn_saltbidrag("cacl2_vannfri", 5.0, 1.0, 20.0)
        self.assertGreater(vannfri["ca"], dihydrat["ca"])
        self.assertGreater(vannfri["cl"], dihydrat["cl"])

    def test_hent_salt_returnerer_uavhengig_kopi(self):
        s1 = hent_salt("gips")
        s1["ionfraksjoner"]["ca"] = 999.0
        s2 = hent_salt("gips")
        self.assertNotEqual(s2["ionfraksjoner"]["ca"], 999.0)
        self.assertEqual(SALTER["gips"]["ionfraksjoner"]["ca"], 0.23279)

    def test_alle_salter_inneholder_alle_seks(self):
        alle = alle_salter()
        self.assertEqual(len(alle), 7)
        ider = {s["salt_id"] for s in alle}
        self.assertEqual(
            ider,
            {"cacl2_2h2o", "cacl2_vannfri", "gips", "epsomsalt", "vanlig_salt", "natron", "kalsiumkarbonat"},
        )


class Test10FlereSalterSamtidig(unittest.TestCase):
    def test_flere_salter_summeres_korrekt(self):
        salter = [
            {"salt_id": "cacl2_2h2o", "gram": 3.7, "renhet": 1.0},
            {"salt_id": "gips", "gram": 2.0, "renhet": 1.0},
        ]
        resultat = beregn_sluttprofil(_JORDALSVATNET, salter, 35.5)
        self.assertAlmostEqual(resultat["slutt"]["ca"], 61.5, delta=0.1)
        self.assertAlmostEqual(resultat["slutt"]["cl"], 60.0, delta=0.1)
        self.assertAlmostEqual(resultat["slutt"]["so4"], 39.5, delta=0.1)
        # Ioner uten tilsetning beholder startverdi uendret.
        self.assertEqual(resultat["slutt"]["mg"], _JORDALSVATNET["mg"])
        self.assertEqual(resultat["slutt"]["na"], _JORDALSVATNET["na"])
        self.assertEqual(resultat["slutt"]["hco3"], _JORDALSVATNET["hco3"])


class Test11og12FordelingMeskSkylling(unittest.TestCase):
    def test_proporsjonal_fordeling(self):
        r = fordel_salttilsetning(3.7, 20.9, 14.6, metode=PROPORSJONAL)
        self.assertAlmostEqual(r["gram_mesk"], 2.18, delta=0.01)
        self.assertAlmostEqual(r["gram_skyll"], 1.52, delta=0.01)

        r2 = fordel_salttilsetning(2.0, 20.9, 14.6, metode=PROPORSJONAL)
        self.assertAlmostEqual(r2["gram_mesk"], 1.18, delta=0.01)
        self.assertAlmostEqual(r2["gram_skyll"], 0.82, delta=0.01)

    def test_alt_i_mesk(self):
        r = fordel_salttilsetning(3.7, 20.9, 14.6, metode=ALT_I_MESK)
        self.assertEqual(r["gram_mesk"], 3.7)
        self.assertEqual(r["gram_skyll"], 0.0)

    def test_egendefinert_fordeling(self):
        r = fordel_salttilsetning(10.0, 20.9, 14.6, metode=EGENDEFINERT_FORDELING, egendefinert_meskeandel=0.75)
        self.assertAlmostEqual(r["gram_mesk"], 7.5)
        self.assertAlmostEqual(r["gram_skyll"], 2.5)

    def test_ingen_dobbelttelling_for_flere_salter(self):
        salter = [
            {"salt_id": "cacl2_2h2o", "gram": 3.7, "renhet": 1.0},
            {"salt_id": "gips", "gram": 2.0, "renhet": 1.0},
        ]
        fordelt = fordel_alle_salter(salter, 20.9, 14.6, metode=PROPORSJONAL)
        for original, f in zip(salter, fordelt):
            self.assertAlmostEqual(f["gram_mesk"] + f["gram_skyll"], original["gram"], places=9)

    def test_null_totalvann_faller_tilbake_til_alt_i_mesk(self):
        r = fordel_salttilsetning(5.0, 0.0, 0.0, metode=PROPORSJONAL)
        self.assertEqual(r["gram_mesk"], 5.0)
        self.assertEqual(r["gram_skyll"], 0.0)


class Test13Kontrollscenario35_5L(unittest.TestCase):
    """Regresjonstest for Wiesn-Märzen-kontrollscenarioet fra spesifikasjonen."""

    def test_full_flyt_kontrollscenario(self):
        meskevann_l, skyllevann_l = 20.9, 14.6
        totalvann_l = meskevann_l + skyllevann_l
        self.assertAlmostEqual(totalvann_l, 35.5, places=1)

        salter = [
            {"salt_id": "cacl2_2h2o", "gram": 3.7, "renhet": 1.0},
            {"salt_id": "gips", "gram": 2.0, "renhet": 1.0},
        ]
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, salter, totalvann_l)
        self.assertAlmostEqual(sluttprofil["slutt"]["ca"], 61.5, delta=0.1)
        self.assertAlmostEqual(sluttprofil["slutt"]["cl"], 60.0, delta=0.1)
        self.assertAlmostEqual(sluttprofil["slutt"]["so4"], 39.5, delta=0.1)

        fordelt = fordel_alle_salter(salter, meskevann_l, skyllevann_l, metode=PROPORSJONAL)
        cacl2_fordelt = next(f for f in fordelt if f["salt_id"] == "cacl2_2h2o")
        gips_fordelt = next(f for f in fordelt if f["salt_id"] == "gips")

        self.assertAlmostEqual(cacl2_fordelt["gram_mesk"], 2.18, delta=0.01)
        self.assertAlmostEqual(cacl2_fordelt["gram_skyll"], 1.52, delta=0.01)
        self.assertAlmostEqual(gips_fordelt["gram_mesk"], 1.18, delta=0.01)
        self.assertAlmostEqual(gips_fordelt["gram_skyll"], 0.82, delta=0.01)

    def test_cl_so4_forhold_og_absolutte_niva(self):
        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, [
            {"salt_id": "cacl2_2h2o", "gram": 3.7, "renhet": 1.0},
            {"salt_id": "gips", "gram": 2.0, "renhet": 1.0},
        ], 35.5)
        forhold = cl_so4_forhold(sluttprofil["slutt"]["cl"], sluttprofil["slutt"]["so4"])
        self.assertAlmostEqual(forhold, 60.0 / 39.5, delta=0.05)
        # Absolutte ionnivåer må ALLTID være tilgjengelige ved siden av forholdet.
        self.assertGreater(sluttprofil["slutt"]["cl"], 0)
        self.assertGreater(sluttprofil["slutt"]["so4"], 0)


class Test14og15Solver(unittest.TestCase):
    def test_solver_treffer_maalprofil_innen_toleranse(self):
        forslag, forklaring = foreslaa_salter(_JORDALSVATNET, _KVERNHAUG_MAAL, 35.5)
        self.assertTrue(forslag)
        self.assertIn("Kalsiumklorid", forklaring)

        sluttprofil = beregn_sluttprofil(_JORDALSVATNET, forslag, 35.5)
        rapport = bygg_ionrapport(sluttprofil, _KVERNHAUG_MAAL)
        for row in rapport:
            if row["ion"] in ("cl", "so4"):
                self.assertEqual(row["status"], "innenfor", msg=f"{row['ion']} havnet {row['status']}: {row['slutt']}")

    def test_solver_bruker_faerrest_mulig_salttyper(self):
        forslag, _ = foreslaa_salter(_JORDALSVATNET, _KVERNHAUG_MAAL, 35.5)
        ider = {f["salt_id"] for f in forslag}
        self.assertTrue(ider.issubset({"cacl2_2h2o", "gips"}))
        # Ingen unødvendig natrium/magnesium for denne profilen.
        self.assertNotIn("vanlig_salt", ider)
        self.assertNotIn("epsomsalt", ider)

    def test_solver_gir_aldri_negative_mengder(self):
        # Kildevann som ALLEREDE ligger over målet for cl/so4 — solveren skal
        # ikke foreslå negative gram for å "trekke fra".
        hoyt_kildevann = {"ca": 200.0, "mg": 5.0, "na": 5.0, "cl": 300.0, "so4": 300.0, "hco3": 40.0}
        forslag, _ = foreslaa_salter(hoyt_kildevann, _KVERNHAUG_MAAL, 20.0)
        for f in forslag:
            self.assertGreaterEqual(f["gram"], 0.0)

    def test_solver_ugyldig_volum_gir_tom_liste_og_feilmelding(self):
        forslag, forklaring = foreslaa_salter(_JORDALSVATNET, _KVERNHAUG_MAAL, 0.0)
        self.assertEqual(forslag, [])
        self.assertTrue(forklaring)


class Test16UmuligMaal(unittest.TestCase):
    def test_kildevann_over_maks_gir_tydelig_varsel(self):
        salt_kildevann = {"ca": 20.0, "mg": 0.5, "na": 4.5, "cl": 500.0, "so4": 8.1, "hco3": 43.0}
        sluttprofil = beregn_sluttprofil(salt_kildevann, [], 20.0)
        varsler = generer_varsler(salt_kildevann, _KVERNHAUG_MAAL, sluttprofil, [])
        self.assertTrue(any("kan ikke nås" in v for v in varsler))
        self.assertTrue(any("CL" in v and "500" in v for v in varsler))


class Test17ManglendeIonverdier(unittest.TestCase):
    def test_ukjent_kildevann_gir_ukjent_status_ikke_diktet_tall(self):
        ukjent = tomt_kildevann()
        self.assertTrue(all(v is None for v in ukjent.values()))

        sluttprofil = beregn_sluttprofil(ukjent, [
            {"salt_id": "gips", "gram": 2.0, "renhet": 1.0},
        ], 20.0)
        # Tilført er beregnet (kjent), men slutt (som avhenger av ukjent
        # startverdi) skal IKKE dikte opp et tall.
        self.assertIsNone(sluttprofil["slutt"]["ca"])
        self.assertGreater(sluttprofil["tilfort"]["ca"], 0)

        rapport = bygg_ionrapport(sluttprofil, _KVERNHAUG_MAAL)
        for row in rapport:
            if row["ion"] == "ca":
                self.assertEqual(row["status"], "ukjent")

        varsler = generer_varsler(ukjent, _KVERNHAUG_MAAL, sluttprofil, [])
        self.assertTrue(any("ukjent" in v.lower() for v in varsler))

    def test_delvis_ukjent_kildevann(self):
        delvis = dict(_JORDALSVATNET)
        delvis["hco3"] = None
        varsler = generer_varsler(delvis, _KVERNHAUG_MAAL, beregn_sluttprofil(delvis, [], 20.0), [])
        self.assertTrue(any("alkalitet" in v.lower() or "hco3" in v.lower() for v in varsler))


class Test18SyrerDatamodell(unittest.TestCase):
    def test_syre_krever_eksplisitt_prosent(self):
        s = bygg_syretilsetning("melkesyre", prosent=80.0, mengde_ml=5.0)
        self.assertEqual(s["prosent"], 80.0)
        varsler = generer_varsler(_JORDALSVATNET, _KVERNHAUG_MAAL, beregn_sluttprofil(_JORDALSVATNET, [], 20.0), [], syrer=[s])
        self.assertFalse(any("konsentrasjon" in v for v in varsler))

    def test_syre_uten_prosent_gir_varsel(self):
        s = bygg_syretilsetning("fosforsyre", prosent=None, mengde_ml=3.0)
        varsler = generer_varsler(_JORDALSVATNET, _KVERNHAUG_MAAL, beregn_sluttprofil(_JORDALSVATNET, [], 20.0), [], syrer=[s])
        self.assertTrue(any("konsentrasjon" in v for v in varsler))

    def test_ulik_konsentrasjon_gir_ulik_syre(self):
        s10 = bygg_syretilsetning("fosforsyre", prosent=10.0, mengde_ml=5.0)
        s85 = bygg_syretilsetning("fosforsyre", prosent=85.0, mengde_ml=5.0)
        self.assertNotEqual(s10["prosent"], s85["prosent"])


class Test19VektOppløsningVarsel(unittest.TestCase):
    def test_saltmengde_under_vektopplosning_gir_varsel(self):
        fordelt = fordel_alle_salter(
            [{"salt_id": "gips", "gram": 0.03, "renhet": 1.0}], 20.9, 14.6,
        )
        varsler = generer_varsler(
            _JORDALSVATNET, _KVERNHAUG_MAAL,
            beregn_sluttprofil(_JORDALSVATNET, [{"salt_id": "gips", "gram": 0.03, "renhet": 1.0}], 35.5),
            fordelt,
        )
        self.assertTrue(any("oppløsning" in v for v in varsler))


class Test20EgendefinerteProfilerMutererIkkeStandard(unittest.TestCase):
    """Bekrefter at lagring av brukerdefinerte kilde-/målprofiler bruker en
    ISOLERT fil under testkjøring, og aldri kan mutere den ekte
    data/water_sources.json eller data/water_targets.json."""

    def setUp(self):
        self._gammel_kilder_env = os.environ.get("KVERNHAUG_WATER_SOURCES_FILE")
        self._gammel_maal_env = os.environ.get("KVERNHAUG_WATER_TARGETS_FILE")
        self._ekte_kilder_snapshot = dict(last_vannkilder())
        self._ekte_maal_snapshot = dict(last_vannmaal())

    def tearDown(self):
        if self._gammel_kilder_env is None:
            os.environ.pop("KVERNHAUG_WATER_SOURCES_FILE", None)
        else:
            os.environ["KVERNHAUG_WATER_SOURCES_FILE"] = self._gammel_kilder_env
        if self._gammel_maal_env is None:
            os.environ.pop("KVERNHAUG_WATER_TARGETS_FILE", None)
        else:
            os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = self._gammel_maal_env
        self.assertEqual(dict(last_vannkilder()), self._ekte_kilder_snapshot,
                          "Den EKTE data/water_sources.json ble endret under en isolert test!")
        self.assertEqual(dict(last_vannmaal()), self._ekte_maal_snapshot,
                          "Den EKTE data/water_targets.json ble endret under en isolert test!")

    def test_egendefinert_kilde_lagres_isolert(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KVERNHAUG_WATER_SOURCES_FILE"] = os.path.join(tmp, "water_sources.json")
            kilder = last_vannkilder()  # tom, siden filen ikke finnes ennå
            self.assertEqual(kilder, {})
            kilder["min_egen_kilde"] = {
                "water_id": "min_egen_kilde", "name": "Min egen kilde",
                "ca": None, "mg": None, "na": None, "cl": None, "so4": None, "hco3": None,
                "ph": None, "notes": "Ukjent — brukeren har ikke analysert vannet ennå.",
            }
            lagre_vannkilder(kilder)
            lest_tilbake = last_vannkilder()
            self.assertIn("min_egen_kilde", lest_tilbake)
            self.assertIsNone(lest_tilbake["min_egen_kilde"]["ca"])

    def test_egendefinert_maal_lagres_isolert(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["KVERNHAUG_WATER_TARGETS_FILE"] = os.path.join(tmp, "water_targets.json")
            maal = last_vannmaal()
            maal["min_egen_maal"] = dict(_KVERNHAUG_MAAL, target_id="min_egen_maal", name="Test")
            lagre_vannmaal(maal)
            lest_tilbake = last_vannmaal()
            self.assertIn("min_egen_maal", lest_tilbake)


class Test21StatusForIon(unittest.TestCase):
    def test_status_grenser(self):
        self.assertEqual(status_for_ion(50, 40, 60), "innenfor")
        self.assertEqual(status_for_ion(30, 40, 60), "under")
        self.assertEqual(status_for_ion(70, 40, 60), "over")
        self.assertEqual(status_for_ion(None, 40, 60), "ukjent")
        self.assertEqual(status_for_ion(50, None, None), "ukjent")


if __name__ == "__main__":
    unittest.main()
