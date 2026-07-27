"""
Tester for modules/calculations.py::beregn_ebc() -- Morey-formelen.

Bakgrunn: den gamle implementasjonen anvendte 1.97 direkte på
MCU^0.685 og brukte maltens rå EBC-verdi som om den allerede var
°Lovibond -- den droppet både Morey-koeffisienten 1.4922 og
EBC->Lovibond-konverteringen. Disse testene låser den fullstendige,
dokumenterte konverteringskjeden (EBC -> Lovibond -> MCU -> Morey SRM ->
EBC) med hånd-regnede kontrollscenarioer, uavhengig av databasefiler.

Kjøres med:
    py -3 -m unittest tests.test_ebc_calculation
"""
import math
import unittest

from modules.calculations import beregn_ebc


class TestBeregnEbcHaandregnet(unittest.TestCase):
    """Kontrollerer beregn_ebc() mot manuelt utregnede scenarioer."""

    def test_ett_malt_haandregnet_kontroll(self):
        # 5 kg malt @ 8.0 EBC, 20 L batch.
        malt_data = {"Test Malt": {"ebc": 8.0}}
        valgt = [{"navn": "Test Malt", "mengde": 5.0}]

        lovibond = 8.0 / 1.97
        mengde_lb = 5.0 * 2.2046226218
        volum_gal = 20.0 * 0.2641720524
        mcu = (mengde_lb * lovibond) / volum_gal
        forventet_srm = 1.4922 * (mcu ** 0.6859)
        forventet_ebc = forventet_srm * 1.97

        resultat = beregn_ebc(valgt, malt_data, 20.0)
        self.assertAlmostEqual(resultat, forventet_ebc, places=6)
        # Sanity: for et lyst malt skal EBC havne i et realistisk område,
        # ikke i nærheten av den gamle, feilberegnede verdien.
        self.assertGreater(resultat, 5.0)
        self.assertLess(resultat, 20.0)

    def test_flere_malttyper_summerer_mcu_foer_morey(self):
        # To malttyper skal summeres SOM MCU før Morey-eksponenten
        # anvendes -- ikke anvendes hver for seg og så summeres.
        malt_data = {
            "Pils": {"ebc": 4.0},
            "Munich": {"ebc": 23.0},
        }
        valgt = [
            {"navn": "Pils", "mengde": 4.0},
            {"navn": "Munich", "mengde": 1.0},
        ]
        volum = 23.0

        mcu = 0.0
        for navn, mengde in (("Pils", 4.0), ("Munich", 1.0)):
            lovibond = malt_data[navn]["ebc"] / 1.97
            mengde_lb = mengde * 2.2046226218
            volum_gal = volum * 0.2641720524
            mcu += (mengde_lb * lovibond) / volum_gal
        forventet_ebc = (1.4922 * (mcu ** 0.6859)) * 1.97

        resultat = beregn_ebc(valgt, malt_data, volum)
        self.assertAlmostEqual(resultat, forventet_ebc, places=6)

        # Feil implementasjon (summerer EBC^0.6859 per malt og summerer
        # SRM-bidragene etterpå) ville gitt et annet, høyere tall pga.
        # konkavheten i potensfunksjonen -- bekreft at vi IKKE gjør det.
        feil_sum_hver_for_seg = 0.0
        for navn, mengde in (("Pils", 4.0), ("Munich", 1.0)):
            lovibond = malt_data[navn]["ebc"] / 1.97
            mengde_lb = mengde * 2.2046226218
            volum_gal = volum * 0.2641720524
            enkelt_mcu = (mengde_lb * lovibond) / volum_gal
            feil_sum_hver_for_seg += (1.4922 * (enkelt_mcu ** 0.6859)) * 1.97
        self.assertNotAlmostEqual(resultat, feil_sum_hver_for_seg, places=2)

    def test_null_volum_returnerer_null_uten_feil(self):
        malt_data = {"Test Malt": {"ebc": 8.0}}
        valgt = [{"navn": "Test Malt", "mengde": 5.0}]
        self.assertEqual(beregn_ebc(valgt, malt_data, 0), 0)

    def test_negativt_volum_returnerer_null_uten_feil(self):
        malt_data = {"Test Malt": {"ebc": 8.0}}
        valgt = [{"navn": "Test Malt", "mengde": 5.0}]
        self.assertEqual(beregn_ebc(valgt, malt_data, -5.0), 0)

    def test_tom_maltliste_gir_null_ebc(self):
        self.assertEqual(beregn_ebc([], {"Test Malt": {"ebc": 8.0}}, 20.0), 0.0)

    def test_ukjent_malt_ignoreres_stille(self):
        # Samme mønster som beregn_og(): malt som ikke finnes i databasen
        # bidrar ikke til beregningen, i stedet for å kaste en feil.
        malt_data = {"Kjent Malt": {"ebc": 8.0}}
        valgt = [
            {"navn": "Kjent Malt", "mengde": 5.0},
            {"navn": "Ukjent Malt", "mengde": 2.0},
        ]
        med_ukjent = beregn_ebc(valgt, malt_data, 20.0)
        uten_ukjent = beregn_ebc([{"navn": "Kjent Malt", "mengde": 5.0}], malt_data, 20.0)
        self.assertAlmostEqual(med_ukjent, uten_ukjent, places=6)

    def test_svaert_moerkt_malt_gir_hoey_ebc(self):
        # Carafa Special III (1400 EBC) i en liten andel skal likevel gi
        # en tydelig mørk sluttfarge -- Morey-eksponenten er submultiplikativ,
        # så resultatet skal være godt over råverdien til det lyseste maltet
        # i blandingen, men ikke urealistisk høyt for en liten andel.
        malt_data = {"Pils": {"ebc": 4.0}, "Carafa III": {"ebc": 1400.0}}
        valgt = [
            {"navn": "Pils", "mengde": 4.5},
            {"navn": "Carafa III", "mengde": 0.2},
        ]
        resultat = beregn_ebc(valgt, malt_data, 20.0)
        self.assertGreater(resultat, 20.0)


class TestBeregnEbcOffentligWiesnFixture(unittest.TestCase):
    """Rapporterer gammel vs. ny EBC for den offentlige 23 L Wiesn-fixturen
    (tests/fixtures/recipes/wiesn_marzen_1872_23l_batch.json), og
    bekrefter at det nye tallet fortsatt er innenfor Style Engine sitt
    dokumenterte EBC-intervall for "Historisk Wiesn-Märzen" (16-32 EBC,
    se modules/style_engine.py)."""

    _MALT_EBC = {
        "Munich I": 14.5,
        "Munich II": 23.0,
        "Vienna Malt": 7.0,
    }
    _OPPSKRIFT_MALT = [
        {"navn": "Munich I", "mengde": 0.644},
        {"navn": "Munich II", "mengde": 4.232},
        {"navn": "Vienna Malt", "mengde": 1.656},
    ]
    _VOLUM = 23.0
    _GAMMEL_EBC_I_FIXTURE = 15.058891555271146

    def test_gammel_vs_ny_ebc_for_wiesn_23l(self):
        ny_ebc = beregn_ebc(self._OPPSKRIFT_MALT, self._MALT_EBC and {
            k: {"ebc": v} for k, v in self._MALT_EBC.items()
        }, self._VOLUM)

        # Den gamle (feilaktige) formelen matcher fixturens lagrede tall.
        def _gammel_beregn_ebc(valgt, malt_data, volum):
            mcu = 0
            for m in valgt:
                mcu += (m["mengde"] * malt_data[m["navn"]]["ebc"]) / (volum * 0.264)
            return 1.97 * (mcu ** 0.685)

        gammel_ebc = _gammel_beregn_ebc(
            self._OPPSKRIFT_MALT,
            {k: {"ebc": v} for k, v in self._MALT_EBC.items()},
            self._VOLUM,
        )
        self.assertAlmostEqual(gammel_ebc, self._GAMMEL_EBC_I_FIXTURE, places=3)

        print(f"\n[EBC-fiks] Wiesn-Märzen 1872 - 23L batch: "
              f"gammel EBC = {gammel_ebc:.2f}, ny EBC = {ny_ebc:.2f}")

        # Style Engine sitt dokumenterte intervall for "Historisk
        # Wiesn-Märzen" er (16, 32) -- se modules/style_engine.py. Den nye,
        # korrekte EBC-en skal fortsatt falle innenfor dette intervallet
        # (nærmere den øvre enden enn den gamle, undervurderte verdien).
        self.assertGreater(ny_ebc, gammel_ebc)
        self.assertGreaterEqual(ny_ebc, 16.0)
        self.assertLessEqual(ny_ebc, 32.0)


if __name__ == "__main__":
    unittest.main()
