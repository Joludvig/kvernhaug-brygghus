"""
Tester for Steg F11I (2026-08-07): 0%-alfasyre-fallback-bugen i
beregn_total_ibu() (modules/calculations.py).

Bakgrunn (Steg F11G): den gamle koden brukte
    alfa = entry.get("alfa") or entry.get("alfa_typisk") or 5.0
som feilaktig behandlet en eksplisitt alfa=0.0 som "mangler" (Python
tolker 0.0 som falsy), og falt videre til alfa_typisk eller 5.0.
Ny kode (_hent_alfa()) bruker eksplisitt None-sjekk i stedet, slik at
0.0 alltid respekteres som en gyldig, eksplisitt alfasyreverdi.

Ingen eksisterende humle i data/master_humle_v2.json har en aktiv
alfa=0.0 (bekreftet separat) -- denne filen tester derfor kun det
latente feilscenarioet direkte mot beregn_total_ibu(), ikke via
style engine eller frosne recipe stats.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.calculations import beregn_total_ibu


class TestAlfaNullFallback(unittest.TestCase):
    """Case A-D: fallback-prioritet for alfa/alfa_typisk/5.0."""

    def test_a_eksplisitt_alfa_0_gir_ibu_0(self):
        humle_data = {"Test Humle": {"alfa": 0.0}}
        humle_calc = [{"navn": "Test Humle", "gram": 30, "tid": 60}]
        ibu = beregn_total_ibu(humle_calc, humle_data, 20.0, 1.050)
        self.assertEqual(ibu, 0.0)

    def test_b_eksplisitt_alfa_0_vinner_over_alfa_typisk(self):
        humle_data = {"Test Humle": {"alfa": 0.0, "alfa_typisk": 6.0}}
        humle_calc = [{"navn": "Test Humle", "gram": 30, "tid": 60}]
        ibu = beregn_total_ibu(humle_calc, humle_data, 20.0, 1.050)
        self.assertEqual(ibu, 0.0)

    def test_c_alfa_mangler_bruker_alfa_typisk(self):
        humle_data = {"Test Humle": {"alfa_typisk": 6.0}}
        humle_calc = [{"navn": "Test Humle", "gram": 30, "tid": 60}]
        ibu_via_typisk = beregn_total_ibu(humle_calc, humle_data, 20.0, 1.050)

        humle_data_direkte = {"Test Humle": {"alfa": 6.0}}
        ibu_direkte = beregn_total_ibu(humle_calc, humle_data_direkte, 20.0, 1.050)

        self.assertEqual(ibu_via_typisk, ibu_direkte)
        self.assertGreater(ibu_via_typisk, 0.0)

    def test_d_baade_alfa_og_alfa_typisk_mangler_bruker_5_0(self):
        humle_data = {"Test Humle": {}}
        humle_calc = [{"navn": "Test Humle", "gram": 30, "tid": 60}]
        ibu_uten_alfa = beregn_total_ibu(humle_calc, humle_data, 20.0, 1.050)

        humle_data_5 = {"Test Humle": {"alfa": 5.0}}
        ibu_med_5 = beregn_total_ibu(humle_calc, humle_data_5, 20.0, 1.050)

        self.assertEqual(ibu_uten_alfa, ibu_med_5)

    def test_e_vanlig_positiv_alfa_uendret(self):
        humle_data = {"Test Humle": {"alfa": 10.0}}
        humle_calc = [{"navn": "Test Humle", "gram": 40, "tid": 45}]
        ibu = beregn_total_ibu(humle_calc, humle_data, 22.0, 1.055)
        self.assertGreater(ibu, 0.0)
        # Regresjonsvakt: samme tall som normal alfa alltid har gitt.
        self.assertAlmostEqual(ibu, 36.807320318853144, places=9)

    def test_f_flere_tilsetninger_0_prosent_bidrar_0_normal_bidrar_korrekt(self):
        humle_data = {
            "Null Alfa Humle": {"alfa": 0.0},
            "Normal Humle": {"alfa": 10.0},
        }
        humle_calc = [
            {"navn": "Null Alfa Humle", "gram": 30, "tid": 60},
            {"navn": "Normal Humle", "gram": 30, "tid": 60},
        ]
        total_ibu = beregn_total_ibu(humle_calc, humle_data, 20.0, 1.050)

        kun_normal = beregn_total_ibu(
            [{"navn": "Normal Humle", "gram": 30, "tid": 60}],
            humle_data, 20.0, 1.050,
        )
        self.assertEqual(total_ibu, kun_normal)
        self.assertGreater(total_ibu, 0.0)


class TestTinsethUavhengigReferanse(unittest.TestCase):
    """Direkte regresjonsvakt på selve Tinseth-tallet, med en forventet
    verdi utledet uavhengig av produksjonskoden (se F11I-sluttrapport
    for utregningen: gram=50, alfa=12%, tid=60 min, volum=20L,
    OG=1.055)."""

    def test_kjent_referanseverdi(self):
        humle_data = {"Test Humle": {"alfa": 12.0}}
        humle_calc = [{"navn": "Test Humle", "gram": 50.0, "tid": 60}]
        ibu = beregn_total_ibu(humle_calc, humle_data, 20.0, 1.055)
        self.assertAlmostEqual(ibu, 66.15851816172872, places=9)


if __name__ == "__main__":
    unittest.main()
