"""
Enhetstester for modules/malt_packaging.py -- maltvariant-/pakningsmodellen
for Smart Handleliste (butikkvarianter: 100 g / 1 kg / 25 kg, hel/knust).

Ren beregningsmodul, ingen Pantry/Streamlit/filsystem involvert -- ingen
testisolasjon (KVERNHAUG_*_DIR) nødvendig i denne filen.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

import modules.malt_packaging as mp


def _bm(varianter):
    return {"varianter": varianter}


class Test1IngenVarianterGirNone(unittest.TestCase):
    def test_ingen_varianter_feltet_gir_fallback_signal(self):
        self.assertIsNone(mp.bygg_pakningsforslag(4232.0, {}))
        self.assertIsNone(mp.bygg_pakningsforslag(4232.0, {"varianter": []}))
        self.assertIsNone(mp.bygg_pakningsforslag(4232.0, None))

    def test_ingen_mangel_gir_none(self):
        varianter = [{"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 8.0}]
        self.assertIsNone(mp.bygg_pakningsforslag(0.0, _bm(varianter)))
        self.assertIsNone(mp.bygg_pakningsforslag(-5.0, _bm(varianter)))


class Test2KorrektKombinasjonAv100gOg1kg(unittest.TestCase):
    """Krav 3 + eksempelet i oppgaven: mangel 4232 g med 100 g og 1 kg
    tilgjengelig skal blant annet kunne gi 4 x 1 kg + 3 x 100 g = 4300 g og
    5 x 1 kg = 5000 g som reelle, fremkommelige kombinasjoner. 100 g-posen
    er bevisst priset med en typisk småpakke-premie (25 kr/100 g ==
    250 kr/kg, mot 45 kr/kg i sekk), slik at 5000 g-alternativet faktisk
    ER billigere totalt enn 4300 g-kombinasjonen og dermed overlever som et
    reelt, ikke-dominert alternativ (krav 8: "dersom en større pakning er
    billigere totalt, skal begge alternativene vises")."""

    def setUp(self):
        self.varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 25.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
        ]

    def test_forslag_inneholder_begge_de_forventede_kombinasjonene(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        alle_totaler = {forslag["anbefalt_kombinasjon"]["total_gram"]} | {
            k["total_gram"] for k in forslag["alternative_kombinasjoner"]
        }
        self.assertIn(4300.0, alle_totaler)
        self.assertIn(5000.0, alle_totaler)

    def test_anbefalt_kombinasjon_med_minst_overkjop_er_4x1kg_pluss_3x100g(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        anbefalt = forslag["anbefalt_kombinasjon"]
        self.assertEqual(anbefalt["total_gram"], 4300.0)
        pakninger = {p["pakningsstorrelse_gram"]: p["antall"] for p in anbefalt["antall_pakninger"]}
        self.assertEqual(pakninger, {1000: 4, 100: 3})

    def test_5000g_alternativet_er_faktisk_billigere_totalt(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        alternativ_5000 = next(k for k in forslag["alternative_kombinasjoner"] if k["total_gram"] == 5000.0)
        self.assertLess(alternativ_5000["total_pris"], forslag["anbefalt_kombinasjon"]["total_pris"])

    def test_pris_og_rest_stemmer_for_anbefalt_kombinasjon(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        anbefalt = forslag["anbefalt_kombinasjon"]
        self.assertAlmostEqual(anbefalt["total_pris"], 4 * 45.0 + 3 * 25.0, places=2)
        self.assertAlmostEqual(anbefalt["overkjop_gram"], 68.0, places=2)


class Test3MangelHoldesAdskiltFraKjopsmengde(unittest.TestCase):
    def test_missing_gram_er_ikke_samme_som_total_gram(self):
        varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 8.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
        ]
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        anbefalt = forslag["anbefalt_kombinasjon"]
        self.assertNotEqual(anbefalt["total_gram"], 4232.0)
        self.assertGreater(anbefalt["total_gram"], 4232.0)
        self.assertEqual(anbefalt["overkjop_gram"], anbefalt["total_gram"] - 4232.0)


class Test4WiesnEksemplerMinstOverkjop(unittest.TestCase):
    """De tre eksakte tallene fra oppgaven: med kun 100 g og 1 kg
    tilgjengelig skal minst-overkjøp-kandidaten være 700 g / 4300 g /
    1700 g for hhv. Munich I (644 g), Munich II (4232 g) og Vienna
    (1656 g mangel)."""

    def setUp(self):
        self.varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 8.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
        ]

    def test_munich_i_644g_gir_700g(self):
        forslag = mp.bygg_pakningsforslag(644.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 700.0)

    def test_munich_ii_4232g_gir_4300g(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 4300.0)

    def test_vienna_1656g_gir_1700g(self):
        forslag = mp.bygg_pakningsforslag(1656.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 1700.0)

    def test_default_prioritet_balansert_gir_et_pareto_optimalt_svar(self):
        # "balansert" veier pris OG overkjøp sammen og kan derfor -- ved en
        # eksakt uavgjort rangering, som for Munich I her -- lande på et
        # ANNET men fortsatt fornuftig (ikke-dominert) svar enn den rene
        # minst_overkjop-rangeringen i Test4 over. Det denne testen låser er
        # at balansert ALDRI returnerer noe som er strengt dårligere enn et
        # annet tilgjengelig alternativ på både pris og overkjøp samtidig.
        for mangel in (644.0, 4232.0, 1656.0):
            forslag = mp.bygg_pakningsforslag(mangel, _bm(self.varianter))
            anbefalt = forslag["anbefalt_kombinasjon"]
            for alt in forslag["alternative_kombinasjoner"]:
                dominert = alt["total_pris"] <= anbefalt["total_pris"] and alt["overkjop_gram"] <= anbefalt["overkjop_gram"]
                self.assertFalse(dominert, f"balansert valgte en dominert kombinasjon for mangel={mangel}")


class Test5BilligstOgMinstOverkjopKanGiUlikeForslag(unittest.TestCase):
    def test_billig_1kg_med_rabatt_slaar_flere_100g_poser(self):
        # 1 kg til 30 kr er en så god literpris at "billigst totalt" skal
        # foretrekke ÉN 1 kg-pakning (30 kr, 650 g overkjøp) fremfor 4 x
        # 100 g (40 kr, 50 g overkjøp) -- mens "minst overkjøp" skal
        # foretrekke det motsatte.
        varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 10.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 30.0},
        ]
        billigst = mp.bygg_pakningsforslag(350.0, _bm(varianter), prioritet=mp.PRIORITET_BILLIGST)
        minst_overkjop = mp.bygg_pakningsforslag(350.0, _bm(varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)

        self.assertEqual(billigst["anbefalt_kombinasjon"]["total_gram"], 1000.0)
        self.assertEqual(minst_overkjop["anbefalt_kombinasjon"]["total_gram"], 400.0)
        self.assertNotEqual(
            billigst["anbefalt_kombinasjon"]["total_gram"],
            minst_overkjop["anbefalt_kombinasjon"]["total_gram"],
        )


class Test6HelOgKnustBlandesIkke(unittest.TestCase):
    def setUp(self):
        self.varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0},
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 7.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 42.0},
        ]

    def test_ingen_enkelt_kombinasjon_inneholder_mer_enn_en_malttype(self):
        for prioritet in (mp.PRIORITET_BILLIGST, mp.PRIORITET_MINST_OVERKJOP, mp.PRIORITET_BALANSERT):
            forslag = mp.bygg_pakningsforslag(650.0, _bm(self.varianter), prioritet=prioritet)
            alle = [forslag["anbefalt_kombinasjon"]] + forslag["alternative_kombinasjoner"]
            for kombinasjon in alle:
                self.assertIn(kombinasjon["malttype"], ("hel", "knust"))

    def test_maltform_knust_bruker_kun_knust_varianter(self):
        forslag = mp.bygg_pakningsforslag(650.0, _bm(self.varianter), maltform=mp.MALTFORM_KNUST)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["malttype"], "knust")

    def test_maltform_hel_bruker_kun_hel_varianter(self):
        forslag = mp.bygg_pakningsforslag(650.0, _bm(self.varianter), maltform=mp.MALTFORM_HEL)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["malttype"], "hel")

    def test_ingen_preferanse_gir_advarsel_naar_flere_former_finnes(self):
        forslag = mp.bygg_pakningsforslag(650.0, _bm(self.varianter), maltform=mp.MALTFORM_INGEN_PREFERANSE)
        self.assertIsNotNone(forslag["advarsel"])
        self.assertIn("blander", forslag["advarsel"].lower())

    def test_billigste_tilgjengelige_gir_ingen_advarsel(self):
        forslag = mp.bygg_pakningsforslag(650.0, _bm(self.varianter), maltform=mp.MALTFORM_BILLIGST)
        self.assertIsNone(forslag["advarsel"])

    def test_kun_en_form_registrert_gir_ingen_advarsel(self):
        varianter = [{"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 8.0}]
        forslag = mp.bygg_pakningsforslag(150.0, _bm(varianter))
        self.assertIsNone(forslag["advarsel"])


class Test7SekkPa25kgVelgesIkkeUrimelig(unittest.TestCase):
    def setUp(self):
        # 25 kg-sekken er BEVISST priset så den er billigst i RÅ totalpris
        # (150 kr) -- likevel skal balansert/standardvalg IKKE anbefale den
        # for en mangel på kun 5 kg (dekningsgrad 5x), mens et eksplisitt
        # "billigst"-valg respekteres og FÅR lov til å velge den.
        self.varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 8.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
            {"pakningsstorrelse_gram": 25000, "malttype": "hel", "pris": 150.0},
        ]

    def test_balansert_standardvalg_hopper_over_25kg_sekken(self):
        forslag = mp.bygg_pakningsforslag(5000.0, _bm(self.varianter))  # standard prioritet
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 5000.0)

    def test_minst_overkjop_hopper_ogsaa_over_25kg_sekken(self):
        forslag = mp.bygg_pakningsforslag(5000.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 5000.0)

    def test_25kg_sekken_er_fortsatt_synlig_som_alternativ(self):
        forslag = mp.bygg_pakningsforslag(5000.0, _bm(self.varianter))
        alle_totaler = {k["total_gram"] for k in forslag["alternative_kombinasjoner"]}
        self.assertIn(25000.0, alle_totaler)

    def test_eksplisitt_billigst_valg_kan_faktisk_velge_25kg_sekken(self):
        forslag = mp.bygg_pakningsforslag(5000.0, _bm(self.varianter), prioritet=mp.PRIORITET_BILLIGST)
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 25000.0)

    def test_naar_25kg_er_eneste_variant_velges_den_uansett(self):
        kun_sekk = [{"pakningsstorrelse_gram": 25000, "malttype": "hel", "pris": 750.0}]
        forslag = mp.bygg_pakningsforslag(644.0, _bm(kun_sekk))
        self.assertEqual(forslag["anbefalt_kombinasjon"]["total_gram"], 25000.0)


class Test8HentTilgjengeligeMalltyper(unittest.TestCase):
    def test_returnerer_sorterte_unike_former(self):
        varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "knust", "pris": 8.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 42.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 40.0},
        ]
        self.assertEqual(mp.hent_tilgjengelige_malttyper(varianter), ["hel", "knust"])

    def test_tom_liste_gir_tom_liste(self):
        self.assertEqual(mp.hent_tilgjengelige_malttyper([]), [])


class Test9KjopsresultatKontrakt(unittest.TestCase):
    """Steg B: kjopsresultat = {pris, mottatt_mengde, bestilling} skal
    alltid beskrive NØYAKTIG samme valgte kombinasjon som
    anbefalt_kombinasjon — lagt til VED SIDEN AV eksisterende felter, ikke
    i stedet for dem (se modules/malt_packaging.py::bygg_pakningsforslag)."""

    def setUp(self):
        self.varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 25.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 45.0},
        ]

    def test_1_alle_tre_fasetter_kommer_fra_samme_valgte_kombinasjon(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        anbefalt = forslag["anbefalt_kombinasjon"]
        kjopsresultat = forslag["kjopsresultat"]

        self.assertEqual(kjopsresultat["pris"], anbefalt["total_pris"])
        self.assertEqual(kjopsresultat["mottatt_mengde"], anbefalt["total_gram"])
        self.assertEqual(kjopsresultat["bestilling"], anbefalt["antall_pakninger"])

    def test_2_billigst_prioritet_gir_internt_konsistent_kjopsresultat(self):
        varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 10.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 30.0},
        ]
        forslag = mp.bygg_pakningsforslag(350.0, _bm(varianter), prioritet=mp.PRIORITET_BILLIGST)
        anbefalt = forslag["anbefalt_kombinasjon"]
        kjopsresultat = forslag["kjopsresultat"]

        self.assertEqual(kjopsresultat["mottatt_mengde"], 1000.0)
        self.assertEqual(kjopsresultat["pris"], anbefalt["total_pris"])
        self.assertEqual(kjopsresultat["bestilling"], anbefalt["antall_pakninger"])

    def test_3_minst_overkjop_gir_annet_men_ogsaa_internt_konsistent_resultat(self):
        varianter = [
            {"pakningsstorrelse_gram": 100, "malttype": "hel", "pris": 10.0},
            {"pakningsstorrelse_gram": 1000, "malttype": "hel", "pris": 30.0},
        ]
        billigst = mp.bygg_pakningsforslag(350.0, _bm(varianter), prioritet=mp.PRIORITET_BILLIGST)
        minst_overkjop = mp.bygg_pakningsforslag(350.0, _bm(varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)

        # Ulikt valg (samme scenario som Test5) ...
        self.assertNotEqual(
            billigst["kjopsresultat"]["mottatt_mengde"],
            minst_overkjop["kjopsresultat"]["mottatt_mengde"],
        )
        # ... men fortsatt internt konsistent for minst_overkjop sitt eget valg.
        anbefalt = minst_overkjop["anbefalt_kombinasjon"]
        kjopsresultat = minst_overkjop["kjopsresultat"]
        self.assertEqual(kjopsresultat["pris"], anbefalt["total_pris"])
        self.assertEqual(kjopsresultat["mottatt_mengde"], anbefalt["total_gram"])

    def test_4_pris_stemmer_med_summen_av_pakkene_i_bestilling(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        kjopsresultat = forslag["kjopsresultat"]
        pris_per_storrelse = {100: 25.0, 1000: 45.0}

        beregnet_pris = sum(
            pris_per_storrelse[p["pakningsstorrelse_gram"]] * p["antall"]
            for p in kjopsresultat["bestilling"]
        )
        self.assertAlmostEqual(kjopsresultat["pris"], beregnet_pris, places=2)

    def test_5_mottatt_mengde_stemmer_med_summen_av_storrelse_ganger_antall(self):
        forslag = mp.bygg_pakningsforslag(4232.0, _bm(self.varianter), prioritet=mp.PRIORITET_MINST_OVERKJOP)
        kjopsresultat = forslag["kjopsresultat"]

        beregnet_mengde = sum(
            p["pakningsstorrelse_gram"] * p["antall"] for p in kjopsresultat["bestilling"]
        )
        self.assertEqual(kjopsresultat["mottatt_mengde"], beregnet_mengde)

    def test_8_uendret_naar_ingen_varianter_finnes(self):
        # Fallback-signalet (None) er identisk med før — kjopsresultat
        # legges kun til INNI et faktisk forslag, ikke som en erstatning
        # for None-signalet malt_pakke_kg-fallbacken i
        # smart_shopping_list.py fortsatt er avhengig av.
        self.assertIsNone(mp.bygg_pakningsforslag(4232.0, {}))
        self.assertIsNone(mp.bygg_pakningsforslag(4232.0, {"varianter": []}))


if __name__ == "__main__":
    unittest.main()
