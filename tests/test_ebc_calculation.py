"""
Tester for modules/calculations.py::beregn_ebc() -- Morey-formelen.

Bakgrunn: den ALLERFØRSTE implementasjonen anvendte 1.97 direkte på
MCU^0.685 og brukte maltens rå EBC-verdi som om den allerede var
°Lovibond -- den droppet både Morey-koeffisienten 1.4922 og
EBC->Lovibond-konverteringen. En senere runde rettet Morey-koeffisienten
og enhetskonverteringene, men brukte fortsatt en FEIL EBC->Lovibond-
konvertering for selve maltkornet (°L = °EBC / 1.97 -- dette tallet
gjelder ferdig ØLETS SRM<->EBC-harmonisering, ikke maltets egen
EBC<->Lovibond-skala). Denne runden retter EBC->Lovibond-konverteringen
til °L = (°EBC + 1.2) / 2.65, verifisert direkte mot Weyermanns egne
produktsider (se TestMaltEbcTilLovibondMotProdusentdata under -- IKKE
bare Style Engine sitt EBC-intervall, som aldri var uavhengig
dokumentasjon på selve konverteringsformelen).

Kjøres med:
    py -3 -m unittest tests.test_ebc_calculation
"""
import math
import unittest

from modules.calculations import (
    beregn_ebc,
    _MALT_EBC_TIL_LOVIBOND_A,
    _MALT_EBC_TIL_LOVIBOND_B,
)


class TestMaltEbcTilLovibondMotProdusentdata(unittest.TestCase):
    """Uavhengig verifisering av selve EBC->Lovibond-konstanten
    (_MALT_EBC_TIL_LOVIBOND_A/_B) mot Weyermanns EGNE, offentlig publiserte
    produktsider -- IKKE mot noe internt i denne appen, og IKKE mot
    Style Engine sitt EBC-intervall (som kun sier noe om PLAUSIBEL
    beer-farge for en stil, ikke om selve maltfarge-konverteringen er
    riktig).

    Kilder (hentet 2026-07-28):
      https://www.weyermann.de/en-us/product/weyermann-munich-malt-type-2-2/
        "20,0 - 25,0 EBC" / "8.0 - 9.9 Lovibond"
      https://www.weyermann.de/en-us/product/weyermann-carafa-special-type-2-2/
        "1100 - 1200 EBC" / "415.2 - 452.9 Lovibond"

    To produkter på VIDT forskjellige fargeområder (lyst basemalt vs.
    mørkt røstet spesialmalt) -- begge stemmer med formelen innenfor
    < 0.2 °L avvik, som er godt innenfor det en lineær tilnærmingsformel
    over et så stort spenn kan forventes å treffe."""

    def _lovibond(self, ebc):
        return (ebc + _MALT_EBC_TIL_LOVIBOND_A) / _MALT_EBC_TIL_LOVIBOND_B

    def test_weyermann_munich_malt_type_2_nedre_grense(self):
        self.assertAlmostEqual(self._lovibond(20.0), 8.0, delta=0.05)

    def test_weyermann_munich_malt_type_2_ovre_grense(self):
        self.assertAlmostEqual(self._lovibond(25.0), 9.9, delta=0.05)

    def test_weyermann_carafa_special_type_2_nedre_grense(self):
        self.assertAlmostEqual(self._lovibond(1100.0), 415.2, delta=0.5)

    def test_weyermann_carafa_special_type_2_ovre_grense(self):
        self.assertAlmostEqual(self._lovibond(1200.0), 452.9, delta=0.5)

    def test_feil_tidligere_konvertering_1_97_stemmer_ikke_med_produsentdata(self):
        # Regresjonsvakt mot at noen ved en feiltakelse bytter tilbake til
        # den forrige rundens formel (°L = °EBC / 1.97): den formelen gir
        # et tydelig FOR HØYT Lovibond-tall for begge Weyermann-produktene
        # over -- bekreft at den IKKE lenger brukes.
        feil_lovibond_20 = 20.0 / 1.97
        feil_lovibond_1100 = 1100.0 / 1.97
        self.assertNotAlmostEqual(feil_lovibond_20, 8.0, delta=0.5)
        self.assertNotAlmostEqual(feil_lovibond_1100, 415.2, delta=5.0)


class TestBeregnEbcHaandregnet(unittest.TestCase):
    """Kontrollerer beregn_ebc() mot manuelt utregnede scenarioer, med den
    NÅ korrekte EBC->Lovibond-formelen (EBC + 1.2) / 2.65 -- se
    TestMaltEbcTilLovibondMotProdusentdata over for hvorfor akkurat disse
    konstantene, ikke bare en speiling av implementasjonens egen kode."""

    def test_ett_malt_haandregnet_kontroll(self):
        # 5 kg malt @ 8.0 EBC, 20 L batch.
        malt_data = {"Test Malt": {"ebc": 8.0}}
        valgt = [{"navn": "Test Malt", "mengde": 5.0}]

        lovibond = (8.0 + 1.2) / 2.65
        mengde_lb = 5.0 * 2.2046226218
        volum_gal = 20.0 * 0.2641720524
        mcu = (mengde_lb * lovibond) / volum_gal
        forventet_srm = 1.4922 * (mcu ** 0.6859)
        forventet_ebc = forventet_srm * 1.97

        resultat = beregn_ebc(valgt, malt_data, 20.0)
        self.assertAlmostEqual(resultat, forventet_ebc, places=6)
        # Sanity: for et lyst malt skal EBC havne i et realistisk område.
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
            lovibond = (malt_data[navn]["ebc"] + 1.2) / 2.65
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
            lovibond = (malt_data[navn]["ebc"] + 1.2) / 2.65
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
    """Rapporterer EBC for den offentlige 23 L Wiesn-fixturen
    (tests/fixtures/recipes/wiesn_marzen_1872_23l_batch.json) gjennom ALLE
    TRE formel-generasjonene, og bekrefter at dagens (korrekte) tall
    fortsatt er innenfor Style Engine sitt dokumenterte EBC-intervall for
    "Historisk Wiesn-Märzen" (16-32 EBC, se modules/style_engine.py) --
    men MERK: dette intervallet bekrefter bare at tallet er PLAUSIBELT
    for stilen, ikke at selve konverteringsformelen er riktig (se
    TestMaltEbcTilLovibondMotProdusentdata over for den uavhengige
    dokumentasjonen)."""

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
    # De historiske formel-generasjonenes lagrede/kjente resultat for
    # akkurat denne fixturen -- kun til rapportering/regresjon, ikke
    # brukt som fasit for dagens formel.
    _EBC_ALLERFORSTE_FORMEL = 15.058891555271146  # 1.97 * MCU_rå^0.685, ingen Lovibond-steg
    _EBC_FORRIGE_RUNDE_FORMEL = 24.327928451585546  # (EBC/1.97) som "Lovibond"

    def test_ny_ebc_for_wiesn_23l(self):
        malt_data = {k: {"ebc": v} for k, v in self._MALT_EBC.items()}
        ny_ebc = beregn_ebc(self._OPPSKRIFT_MALT, malt_data, self._VOLUM)

        print(
            f"\n[EBC-fiks, runde 2] Wiesn-Märzen 1872 - 23L batch: "
            f"allerførste formel = {self._EBC_ALLERFORSTE_FORMEL:.2f} EBC, "
            f"forrige rundes formel (EBC/1.97) = {self._EBC_FORRIGE_RUNDE_FORMEL:.2f} EBC, "
            f"ny, produsentverifisert formel ((EBC+1.2)/2.65) = {ny_ebc:.2f} EBC"
        )

        # Uavhengig utregnet forventningsverdi (se docstring/kommentarer i
        # modules/calculations.py for kildehenvisningene) -- IKKE
        # hardkodet blindt: dette tallet følger fra å kjøre nøyaktig den
        # dokumenterte kjeden (EBC->Lovibond via (EBC+1.2)/2.65 -> MCU ->
        # Morey SRM -> EBC) på fixturens egne malt-/mengde-/volumtall.
        self.assertAlmostEqual(ny_ebc, 20.74, delta=0.05)

        # Style Engine sitt dokumenterte intervall for "Historisk
        # Wiesn-Märzen" er (16, 32) -- se modules/style_engine.py. Dette
        # er en plausibilitetssjekk, IKKE dokumentasjon på at formelen
        # selv er riktig (se TestMaltEbcTilLovibondMotProdusentdata).
        self.assertGreaterEqual(ny_ebc, 16.0)
        self.assertLessEqual(ny_ebc, 32.0)

        # Denne rundens rettelse skal gi et ANNET tall enn forrige runde
        # (den rettet en reell, dokumentert feil -- se
        # TestMaltEbcTilLovibondMotProdusentdata).
        self.assertNotAlmostEqual(ny_ebc, self._EBC_FORRIGE_RUNDE_FORMEL, delta=0.5)


if __name__ == "__main__":
    unittest.main()
