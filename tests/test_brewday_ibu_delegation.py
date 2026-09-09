"""
Regresjonstester for A2.2 (issue #161): Brewday (modules/brewday_calc.py)
skal delegere selve Tinseth-/alfa-aritmetikken til den autoritative
modules.calculations.beregn_total_ibu() i stedet for å regne den ut på
nytt lokalt -- uten å kollapse de to bevisst forskjellige IBU-kontekstene
(oppskrift/planlegging vs. bryggedag/prosess, se
tests/test_brewday_export_hop_mismatch.py).

Bakgrunn (kildebeviste feil rettet her):
  - alfa-fallback brukte `h_info.get("alfa") or ...`, som feilaktig
    behandlet en eksplisitt alfa=0.0 som "mangler" (samme F11G/F11I-bug
    som beregn_total_ibu() allerede fikk fikset -- se
    tests/test_calculations_ibu_alfa.py -- men som fortsatt fantes lokalt
    i modules/brewday_calc.py::_bygg_humle_entry).
  - per-tilsetning-IBU ble avrundet FØR summering, mens den autoritative
    recipe-stien (modules/recipe_context.py) summerer RÅ bidrag og
    avrunder først til slutt -- en reell avrundingsrekkefølge-divergens.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.brewday_calc import lag_brewday_plan
from modules.calculations import beregn_total_ibu

_MALT_DB = {"vienna": {"display_name": "Vienna Malt", "potensiale": 1.036}}
_GJAER_INFO = {"display_name": "US-05", "gjaertype": "Ale"}


class TestBrewdayPlanlagtIbuMatcherBeregnTotalIbu(unittest.TestCase):
    """Uten prosessbegrensning (ingen humle med lengre tid enn koketiden)
    skal Brewdays planlagte IBU være tallidentisk med den autoritative
    beregn_total_ibu() -- samme volum/OG, kun forskjellig nøkkel (hop-id
    i stedet for display-navn, som beregn_total_ibu() selv ikke bryr seg
    om -- se modules/calculations.py::beregn_total_ibu())."""

    _HUMLE_DB = {
        "magnum":   {"display_name": "Magnum",   "alfa": 12.0},
        "tettnang": {"display_name": "Tettnang", "alfa_typisk": 4.0},
        "citra":    {"display_name": "Citra",    "alfa": 13.5},
    }

    def _plan(self, humle_valg):
        return lag_brewday_plan(
            malt_valg=[{"id": "vienna", "mengde": 5.0}],
            humle_valg=humle_valg,
            gjaer_id="us05", gjaer_info=_GJAER_INFO,
            og=1.050, batch_volum_l=20.0,
            humle_database=self._HUMLE_DB, malt_database=_MALT_DB,
        )

    def test_flere_tilsetninger_innenfor_koketiden(self):
        humle_valg = [
            {"id": "magnum", "gram": 20, "tid": 60},
            {"id": "tettnang", "gram": 15, "tid": 20},
            {"id": "citra", "gram": 30, "tid": 5},
        ]
        plan = self._plan(humle_valg)

        humle_calc = [{"navn": h["id"], "gram": h["gram"], "tid": h["tid"]} for h in humle_valg]
        humle_data = {h["id"]: self._HUMLE_DB[h["id"]] for h in humle_valg}
        forventet_ibu = round(beregn_total_ibu(humle_calc, humle_data, 20.0, 1.050), 1)

        self.assertEqual(plan["koketid_min"], 60, "Ingen humle skal her overstige total koketid")
        self.assertEqual(plan["humle_over_koketid"], [])
        self.assertEqual(plan["ibu_planlagt"], forventet_ibu)
        self.assertEqual(plan["ibu_faktisk_prosess"], forventet_ibu)
        self.assertGreater(plan["ibu_planlagt"], 0.0)

    def test_enkelt_tilsetning_tordypp_0_min(self):
        humle_valg = [{"id": "citra", "gram": 30, "tid": 0}]
        plan = self._plan(humle_valg)

        humle_calc = [{"navn": "citra", "gram": 30, "tid": 0}]
        forventet_ibu = round(beregn_total_ibu(humle_calc, {"citra": self._HUMLE_DB["citra"]}, 20.0, 1.050), 1)

        self.assertEqual(forventet_ibu, 0.0, "Tørrhumle (0 min) skal ikke gi kokebitterhet")
        self.assertEqual(plan["ibu_planlagt"], 0.0)
        self.assertEqual(plan["ibu_faktisk_prosess"], 0.0)


class TestBrewdayEksplisittAlfaNull(unittest.TestCase):
    """Regresjon for F11G/F11I-bugen: en humle med EKSPLISITT alfa=0.0
    skal bidra 0 IBU via lag_brewday_plan(), ikke falle tilbake til
    alfa_typisk eller standard-alfa 5.0 (se
    tests/test_calculations_ibu_alfa.py for samme sjekk direkte mot
    beregn_total_ibu())."""

    def test_alfa_0_gir_ingen_ibu_selv_med_hoy_alfa_typisk(self):
        humle_db = {"null_alfa": {"display_name": "Null Alfa Humle", "alfa": 0.0, "alfa_typisk": 12.0}}
        plan = lag_brewday_plan(
            malt_valg=[{"id": "vienna", "mengde": 5.0}],
            humle_valg=[{"id": "null_alfa", "gram": 30, "tid": 60}],
            gjaer_id="us05", gjaer_info=_GJAER_INFO,
            og=1.050, batch_volum_l=20.0,
            humle_database=humle_db, malt_database=_MALT_DB,
        )
        self.assertEqual(plan["ibu_planlagt"], 0.0)
        self.assertEqual(plan["ibu_faktisk_prosess"], 0.0)
        self.assertEqual(plan["humleplan"][0]["ibu_bidrag"], 0.0)
        self.assertEqual(plan["humleplan"][0]["ibu_bidrag_faktisk"], 0.0)

    def test_alfa_0_forskjellig_fra_manglende_alfa(self):
        """Kontrollgruppe: uten NOEN alfa/alfa_typisk faller
        beregn_total_ibu() tilbake til 5.0 og gir IBU > 0 -- alfa=0.0 skal
        derfor gi et FORSKJELLIG (0.0) resultat enn en helt manglende
        alfa-nøkkel, ikke bare "tilfeldigvis begge 0"."""
        humle_db_null   = {"h": {"display_name": "H", "alfa": 0.0}}
        humle_db_mangler = {"h": {"display_name": "H"}}
        felles_kwargs = dict(
            malt_valg=[{"id": "vienna", "mengde": 5.0}],
            humle_valg=[{"id": "h", "gram": 30, "tid": 60}],
            gjaer_id="us05", gjaer_info=_GJAER_INFO,
            og=1.050, batch_volum_l=20.0, malt_database=_MALT_DB,
        )
        plan_null    = lag_brewday_plan(humle_database=humle_db_null, **felles_kwargs)
        plan_mangler = lag_brewday_plan(humle_database=humle_db_mangler, **felles_kwargs)

        self.assertEqual(plan_null["ibu_planlagt"], 0.0)
        self.assertGreater(plan_mangler["ibu_planlagt"], 0.0)


if __name__ == "__main__":
    unittest.main()
