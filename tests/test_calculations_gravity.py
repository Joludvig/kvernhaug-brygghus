"""
Tester for Steg F11J (2026-08-07): direkte, deterministiske
regresjonstester for beregn_og() og beregn_fg_og_abv() (modules/
calculations.py).

Bakgrunn (Steg F11G): selve beregningsmotoren ble verifisert som
matematisk korrekt (standard gravity-points/PPG-modell for OG,
standard apparent-attenuation-modell for FG/ABV), men manglet egne,
direkte enhetstester på samme nivå som beregn_ebc() allerede har.
Denne filen legger IKKE til ny matematikk -- kun testdekning for
eksisterende, uendret produksjonskode.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import unittest

from modules.calculations import beregn_og, beregn_fg_og_abv


# --- Uavhengig OG-fasitmetode -----------------------------------------
#
# beregn_og() bruker konstanten 8.3454, som IKKE er en vilkårlig
# "magisk" faktor -- den er selve produksjonsformelens interne snarvei
# for å konvertere den klassiske imperiale PPG-formelen (points per
# pound per gallon, brukt av så godt som all engelskspråklig
# hjemmebryggerlitteratur) til metriske enheter (kg, liter):
#
#     8.3454 = kg->lb-faktor / liter->US-gallon-faktor
#            = 2.2046226218 / 0.2641720524
#
# For å teste OG UAVHENGIG av produksjonens egen formelstruktur,
# regner _og_imperial_fasit() ut akkurat samme fysikk via den
# opprinnelige, imperiale PPG-formelen -- ikke via 8.3454-konstanten:
#
#     points = vekt_lb * PPG * effektivitet / volum_gal
#     OG = 1 + points / 1000
#
# der PPG = (potensiale - 1) * 1000 (f.eks. 37 for potensiale 1.037).
# Denne funksjonen er BEVISST en annen utregningsvei enn
# produksjonskoden (imperiale mellomsteg, ikke 8.3454 direkte) -- den
# er derfor en reell, uavhengig kontroll, ikke en kopi av
# produksjonsformelen. Små avvik i siste 7.-8. desimal (ren
# flyttallsavrunding fra ulik utregningsrekkefølge) er forventet og
# tolereres med assertAlmostEqual.
_KG_TIL_LB_FASIT = 2.2046226218
_LITER_TIL_GAL_FASIT = 0.2641720524


def _og_imperial_fasit(malter, volum_l, effektivitet):
    """malter: liste av (mengde_kg, potensiale)."""
    volum_gal = volum_l * _LITER_TIL_GAL_FASIT
    total_points = 0.0
    for mengde_kg, potensiale in malter:
        ppg = (potensiale - 1) * 1000
        vekt_lb = mengde_kg * _KG_TIL_LB_FASIT
        total_points += (vekt_lb * ppg * effektivitet) / volum_gal
    return 1 + total_points / 1000


class TestBeregnOgUavhengigReferanse(unittest.TestCase):
    """A-E: uavhengig imperial-fasit, ikke produksjonens egen formel."""

    def test_a_en_malt_standard_scenario(self):
        # 5.0 kg, potensiale 1.037, 20 L, 75% effektivitet.
        fasit = _og_imperial_fasit([(5.0, 1.037)], 20.0, 0.75)
        og = beregn_og([{"navn": "Test Malt", "mengde": 5.0}],
                        {"Test Malt": {"potensiale": 1.037}}, 20.0, 0.75)
        self.assertAlmostEqual(og, fasit, places=6)
        # Regresjonsvakt: produksjonens eget, eksakte flyttallsresultat.
        self.assertEqual(og, 1.0578962124999998)

    def test_b_to_malter_ulik_potensiale_summeres_korrekt(self):
        fasit = _og_imperial_fasit([(3.0, 1.037), (2.0, 1.030)], 20.0, 0.70)
        og = beregn_og(
            [{"navn": "Malt1", "mengde": 3.0}, {"navn": "Malt2", "mengde": 2.0}],
            {"Malt1": {"potensiale": 1.037}, "Malt2": {"potensiale": 1.030}},
            20.0, 0.70,
        )
        self.assertAlmostEqual(og, fasit, places=6)

    def test_c_lav_effektivitet_55_prosent(self):
        fasit = _og_imperial_fasit([(5.0, 1.037)], 20.0, 0.55)
        og = beregn_og([{"navn": "Test Malt", "mengde": 5.0}],
                        {"Test Malt": {"potensiale": 1.037}}, 20.0, 0.55)
        self.assertAlmostEqual(og, fasit, places=6)

    def test_d_hoy_effektivitet_90_prosent(self):
        fasit = _og_imperial_fasit([(5.0, 1.037)], 20.0, 0.90)
        og = beregn_og([{"navn": "Test Malt", "mengde": 5.0}],
                        {"Test Malt": {"potensiale": 1.037}}, 20.0, 0.90)
        self.assertAlmostEqual(og, fasit, places=6)

    def test_e_invers_volumavhengighet(self):
        # Samme malt/effektivitet, ulikt batchvolum -- OG skal falle
        # når volumet øker (invers sammenheng), og matche den
        # uavhengige fasiten i begge tilfeller.
        fasit_15l = _og_imperial_fasit([(5.0, 1.037)], 15.0, 0.75)
        fasit_30l = _og_imperial_fasit([(5.0, 1.037)], 30.0, 0.75)
        og_15l = beregn_og([{"navn": "Test Malt", "mengde": 5.0}],
                            {"Test Malt": {"potensiale": 1.037}}, 15.0, 0.75)
        og_30l = beregn_og([{"navn": "Test Malt", "mengde": 5.0}],
                            {"Test Malt": {"potensiale": 1.037}}, 30.0, 0.75)
        self.assertAlmostEqual(og_15l, fasit_15l, places=6)
        self.assertAlmostEqual(og_30l, fasit_30l, places=6)
        self.assertGreater(og_15l, og_30l)


class TestBeregnOgDokumentertOppforsel(unittest.TestCase):
    """F-H: dagens TILSIKTEDE oppførsel dokumentert som tester --
    ikke uavhengig fysikk-fasit, men et eksplisitt "dette er hva
    koden faktisk gjør i dag"-avtrykk."""

    def test_f_tom_maltliste_gir_og_1000(self):
        og = beregn_og([], {"X": {"potensiale": 1.037}}, 20.0, 0.75)
        self.assertEqual(og, 1.000)

    def test_g_ukjent_malt_id_ignoreres_stille(self):
        # Dagens oppførsel: `if navn in malt_data` -- en ukjent
        # malt-ID bidrar rett og slett ingenting, uten feilmelding.
        # Denne testen dokumenterer det, endrer det IKKE.
        malt_data = {"Kjent Malt": {"potensiale": 1.037}}
        og_med_ukjent = beregn_og(
            [{"navn": "Kjent Malt", "mengde": 5.0}, {"navn": "Ukjent Malt", "mengde": 3.0}],
            malt_data, 20.0, 0.75,
        )
        og_kun_kjent = beregn_og(
            [{"navn": "Kjent Malt", "mengde": 5.0}], malt_data, 20.0, 0.75,
        )
        self.assertEqual(og_med_ukjent, og_kun_kjent)

    def test_h_manglende_potensiale_bruker_fallback_1036(self):
        og_uten_felt = beregn_og(
            [{"navn": "Malt Uten Potensiale", "mengde": 5.0}],
            {"Malt Uten Potensiale": {}}, 20.0, 0.75,
        )
        og_eksplisitt_1036 = beregn_og(
            [{"navn": "Malt Uten Potensiale", "mengde": 5.0}],
            {"Malt Uten Potensiale": {"potensiale": 1.036}}, 20.0, 0.75,
        )
        self.assertEqual(og_uten_felt, og_eksplisitt_1036)


class TestBeregnFgOgAbv(unittest.TestCase):
    """FG/ABV direkte, med hardkodede forventede resultater fra
    formlene gitt i F11J-spesifikasjonen (ikke en kopi av
    produksjonens hjelpefunksjon -- kun selve formeluttrykket):
        FG  = 1 + (OG - 1) * (1 - attenuation)
        ABV = (OG - FG) * 131.25
    """

    def test_fg_ved_fire_attenuation_niva(self):
        cases = [
            (0.70, 1.018, 5.512500000000005),
            (0.75, 1.0150000000000001, 5.906249999999991),
            (0.80, 1.012, 6.300000000000006),
            (0.85, 1.0090000000000001, 6.693749999999992),
        ]
        for attenuation, forventet_fg, forventet_abv in cases:
            with self.subTest(attenuation=attenuation):
                fg, abv = beregn_fg_og_abv(1.060, attenuation)
                self.assertEqual(fg, forventet_fg)
                self.assertEqual(abv, forventet_abv)

    def test_abv_normal_sterk_og_ekstra_sterk_ol(self):
        # OG=1.050/1.070/1.100 ved 75% utgjæring -> ca. 4.9%/6.9%/9.8%
        cases = [
            (1.050, 0.75, 1.0125, 4.9218750000000115),
            (1.070, 0.75, 1.0175, 6.890624999999999),
            (1.100, 0.75, 1.025, 9.843750000000023),
        ]
        for og, attenuation, forventet_fg, forventet_abv in cases:
            with self.subTest(og=og):
                fg, abv = beregn_fg_og_abv(og, attenuation)
                self.assertEqual(fg, forventet_fg)
                self.assertAlmostEqual(abv, forventet_abv, places=9)


class TestBeregnFgOgAbvEdgeCases(unittest.TestCase):
    """Dagens tilsiktede matematiske grenser -- IKKE attenuation <0
    eller >1, som ble klassifisert som defensive P2-funn i F11G og
    bevisst holdes utenfor F11J."""

    def test_attenuation_0_gir_fg_lik_og_og_abv_0(self):
        fg, abv = beregn_fg_og_abv(1.060, 0.0)
        self.assertEqual(fg, 1.060)
        self.assertEqual(abv, 0.0)

    def test_attenuation_1_gir_fg_1000_og_hele_gravity_dropen(self):
        fg, abv = beregn_fg_og_abv(1.060, 1.0)
        self.assertEqual(fg, 1.000)
        self.assertAlmostEqual(abv, (1.060 - 1.000) * 131.25, places=9)

    def test_og_1000_gir_fg_1000_og_abv_0(self):
        fg, abv = beregn_fg_og_abv(1.000, 0.75)
        self.assertEqual(fg, 1.000)
        self.assertEqual(abv, 0.0)


class TestWiesnReferanseOgFgAbv(unittest.TestCase):
    """Sekundær, integrasjonsnær regresjon mot de kjente live-tallene
    for Wiesn-Märzen-referansen (samme mønster som eksisterende
    Wiesn-tester i test_calculations_ibu_alfa.py). De rene
    enhetstestene over er hovedfasiten -- denne testen er et ekstra
    sikkerhetsnett mot at en fremtidig endring i beregn_og()/
    beregn_fg_og_abv() upåaktet endrer et kjent, reelt scenario."""

    def test_wiesn_referansen_gir_kjente_og_fg_abv_verdier(self):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with open(os.path.join(base, "data", "master_malt.json"), encoding="utf-8") as f:
            malt_db = json.load(f)
        with open(os.path.join(base, "data", "master_gjaer_v2.json"), encoding="utf-8") as f:
            gjaer_db = json.load(f)
        flatt_malt = {v.get("display_name", k): v for k, v in malt_db.items() if v}

        malt_calc = [
            {"navn": malt_db["weyermann_munich_1"]["display_name"], "mengde": 0.7},
            {"navn": malt_db["munich_ii"]["display_name"], "mengde": 4.6},
            {"navn": malt_db["vienna"]["display_name"], "mengde": 1.8},
        ]
        attenuation = gjaer_db["saflager_w3470"]["attenuation"]

        og = beregn_og(malt_calc, flatt_malt, 25.0, 0.75)
        fg, abv = beregn_fg_og_abv(og, attenuation)

        self.assertEqual(og, 1.0639925272000001)
        self.assertEqual(fg, 1.011518654896)
        self.assertEqual(abv, 6.887195739900018)


class TestFullPresisjonIkkeAvrundet(unittest.TestCase):
    """Beskytter prinsippet 'beregn med full presisjon, avrund kun ved
    visning' -- bekrefter at beregn_og()/beregn_fg_og_abv() returnerer
    uavrundede floats med full flyttallspresisjon, ikke tall
    forhåndsavrundet for visning."""

    def test_beregn_og_returnerer_uavrundet_float(self):
        og = beregn_og([{"navn": "Test Malt", "mengde": 5.0}],
                        {"Test Malt": {"potensiale": 1.037}}, 20.0, 0.75)
        self.assertEqual(og, 1.0578962124999998)
        self.assertNotEqual(og, round(og, 4))

    def test_beregn_fg_og_abv_returnerer_uavrundede_floats(self):
        fg, abv = beregn_fg_og_abv(1.060, 0.75)
        self.assertEqual(fg, 1.0150000000000001)
        self.assertEqual(abv, 5.906249999999991)
        self.assertNotEqual(abv, round(abv, 4))


if __name__ == "__main__":
    unittest.main()
