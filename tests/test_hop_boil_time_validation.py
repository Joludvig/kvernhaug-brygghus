"""
Tester for at humletid som overstiger total koketid oppdages og aldri
presenteres som en gyldig, oppnåelig IBU uten videre.

Bakgrunn: en humle lagt inn med f.eks. 90 minutters egen koketid kunne
brukes uendret selv om den totale koken (utstyrsstandard eller valgt
prosessprofil) bare var 60 minutter. UI-et viste tilsetningen som lagt
til VED kokestart (0 min etter start, siden
max(0, total_koketid - tid) klippes til 0) samtidig som IBU-bidraget ble
beregnet med den fulle, umulige 90-minutters utnyttelsen -- et
selvmotsigende og fysisk uoppnåelig resultat.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.brewday_calc import _bygg_humle_entry, lag_brewday_plan

_HUMLE_DB = {
    "test_humle": {"display_name": "Test Humle", "alfa": 10.0},
}


class TestByggHumleEntry(unittest.TestCase):
    def test_tid_innenfor_koketid_flagges_ikke(self):
        entry = _bygg_humle_entry(
            {"id": "test_humle", "gram": 20, "tid": 60},
            _HUMLE_DB, bigness=0.1, volum=20.0, total_koketid_min=60,
        )
        self.assertFalse(entry["tid_over_koketid"])
        self.assertEqual(entry["ibu_bidrag"], entry["ibu_bidrag_faktisk"])
        self.assertEqual(entry["tilsatt_etter_min"], 0)

    def test_tid_over_koketid_flagges_og_reduserer_faktisk_ibu(self):
        entry = _bygg_humle_entry(
            {"id": "test_humle", "gram": 20, "tid": 90},
            _HUMLE_DB, bigness=0.1, volum=20.0, total_koketid_min=60,
        )
        self.assertTrue(entry["tid_over_koketid"])
        # Oppgitt tid beholdes uendret i "planlagt"-bidraget.
        self.assertEqual(entry["tid"], 90)
        # "Faktisk" bidrag bruker klippet tid (60 min, ikke 90) og skal
        # derfor være LAVERE enn det planlagte (Tinseth-utnyttelsen øker
        # monotont med tid, så mindre effektiv tid => mindre IBU).
        self.assertLess(entry["ibu_bidrag_faktisk"], entry["ibu_bidrag"])
        # UI-et viser fortsatt "tilsatt ved kokestart" (0 min) for en
        # humle som ikke rekker sin fulle tid -- denne testen låser bare
        # at IBU-tallet IKKE lenger later som at det er konsistent med det.
        self.assertEqual(entry["tilsatt_etter_min"], 0)

    def test_tid_lik_koketid_er_ikke_over(self):
        entry = _bygg_humle_entry(
            {"id": "test_humle", "gram": 20, "tid": 60},
            _HUMLE_DB, bigness=0.1, volum=20.0, total_koketid_min=60,
        )
        self.assertFalse(entry["tid_over_koketid"], "tid == total_koketid_min er akkurat oppnåelig, ikke et avvik")

    def test_torrhumle_0_min_er_aldri_over_koketid(self):
        entry = _bygg_humle_entry(
            {"id": "test_humle", "gram": 20, "tid": 0},
            _HUMLE_DB, bigness=0.1, volum=20.0, total_koketid_min=60,
        )
        self.assertFalse(entry["tid_over_koketid"])
        self.assertEqual(entry["ibu_bidrag"], 0.0)
        self.assertEqual(entry["ibu_bidrag_faktisk"], 0.0)


class TestLagBrewdayPlanHumletidVarsel(unittest.TestCase):
    _GJAER_INFO = {"display_name": "US-05", "gjaertype": "Ale"}

    def test_ingen_avvik_naar_alle_humletider_er_innenfor_koketiden(self):
        plan = lag_brewday_plan(
            malt_valg=[{"id": "ukjent_malt", "mengde": 5.0}],
            humle_valg=[{"id": "test_humle", "gram": 20, "tid": 60}],
            gjaer_id="us05", gjaer_info=self._GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB,
        )
        self.assertEqual(plan["humle_over_koketid"], [])
        self.assertEqual(plan["ibu_planlagt"], plan["ibu_faktisk_prosess"])

    def test_90_min_humle_i_60_min_kok_gir_avvik_og_lavere_faktisk_ibu(self):
        # Ingen pilsnermalt => standard 60 min koketid (se
        # modules/brewday_calc.py::_koketid og modules/equipment.py
        # default_boil_time_min).
        plan = lag_brewday_plan(
            malt_valg=[{"id": "ukjent_malt", "mengde": 5.0}],
            humle_valg=[{"id": "test_humle", "gram": 20, "tid": 90}],
            gjaer_id="us05", gjaer_info=self._GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB,
        )
        self.assertEqual(plan["koketid_min"], 60)
        self.assertEqual(len(plan["humle_over_koketid"]), 1)
        self.assertEqual(plan["humle_over_koketid"][0]["navn"], "Test Humle")
        self.assertLess(plan["ibu_faktisk_prosess"], plan["ibu_planlagt"])
        # Oppskriften muteres ALDRI automatisk -- den oppgitte tiden i
        # humleplan-tabellen skal fortsatt vise 90, ikke en stille klippet 60.
        self.assertEqual(plan["humleplan"][0]["tid"], 90)

    def test_avvik_via_eksplisitt_prosessprofil_med_kortere_koketid(self):
        # Samme scenario, men koketiden kommer fra en VALGT prosessprofil
        # (boil_minutes) i stedet for utstyrsstandarden -- se
        # ui/process_panel.py sin "Total koketid (min)"-widget.
        profil = {
            "mash_steps": [{"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": ""}],
            "boil_minutes": 60,
            "sparge_method": "batch_sparge",
        }
        plan = lag_brewday_plan(
            malt_valg=[{"id": "ukjent_malt", "mengde": 5.0}],
            humle_valg=[
                {"id": "test_humle", "gram": 20, "tid": 90},
                {"id": "test_humle", "gram": 10, "tid": 15},
            ],
            gjaer_id="us05", gjaer_info=self._GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB,
            process_profile=profil,
        )
        self.assertEqual(plan["koketid_min"], 60)
        self.assertEqual(len(plan["humle_over_koketid"]), 1)
        self.assertEqual(plan["humle_over_koketid"][0]["tid"], 90)
        self.assertLess(plan["ibu_faktisk_prosess"], plan["ibu_planlagt"])


if __name__ == "__main__":
    unittest.main()
