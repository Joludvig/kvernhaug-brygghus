"""
Tester for at et humletidsavvik (planlagt IBU vs. faktisk mulig IBU,
se modules/brewday_calc.py::lag_brewday_plan()) faktisk følger med inn i
DET EKSPORTERTE bryggedagsarket (modules/brewday_template.py::
render_brewday_html()) -- ikke bare i den levende Streamlit-økten.

Bakgrunn: UI-et (ui/process_panel.py + ui/brewday_panel.py) viste
allerede planlagt/faktisk IBU og et varsel, med eksporten låst til
brukeren bekreftet avviket. Men selve HTML-en som til slutt lastes ned
brukte fortsatt bare humlepostens PLANLAGTE ibu_bidrag, uten noen
indikasjon på at bidraget var fysisk uoppnåelig -- varselet forsvant i
det øyeblikket filen ble åpnet på nytt uten den opprinnelige økten.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.brewday_calc import lag_brewday_plan
from modules.brewday_template import render_brewday_html

_MALT_DB = {"vienna": {"display_name": "Vienna Malt", "potensiale": 1.036}}
_HUMLE_DB = {
    "magnum": {"display_name": "Magnum", "alfa": 12.0},
    "tettnang": {"display_name": "Tettnang", "alfa": 4.0},
}
_GJAER_INFO = {"display_name": "US-05", "gjaertype": "Ale"}


def _ctx(navn="Test Brygg"):
    return {
        "name": navn, "brygger_stil": "", "og": 1.050, "fg": 1.012, "abv": 5.0,
        "ibu": 20.0, "ebc": 15.0, "volum": 20.0, "effektivitet": 0.75,
    }


class TestEksportMedHumletidsavvik(unittest.TestCase):
    def _plan_med_avvik(self):
        # Ingen pilsnermalt => standard 60 min koketid (se
        # modules/brewday_calc.py::_koketid). 90 min humle er derfor
        # fysisk uoppnåelig som oppgitt.
        return lag_brewday_plan(
            malt_valg=[{"id": "vienna", "mengde": 5.0}],
            humle_valg=[{"id": "magnum", "gram": 20, "tid": 90}],
            gjaer_id="us05", gjaer_info=_GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB, malt_database=_MALT_DB,
        )

    def test_html_viser_oppgitt_tid_og_total_koketid(self):
        plan = self._plan_med_avvik()
        html = render_brewday_html(_ctx(), plan)
        self.assertIn("90 min", html)  # oppgitt humletid
        self.assertIn(f"{plan['koketid_min']} min", html)  # total koketid
        self.assertEqual(plan["koketid_min"], 60)

    def test_html_viser_baade_planlagt_og_faktisk_ibu(self):
        plan = self._plan_med_avvik()
        html = render_brewday_html(_ctx(), plan)
        self.assertIn("Planlagt IBU", html)
        self.assertIn("Faktisk mulig IBU", html)
        # Selve tallverdiene skal faktisk stå i HTML-en, ikke bare etikettene.
        from modules.export_format import fmt_ibu_bid
        self.assertIn(fmt_ibu_bid(plan["ibu_planlagt"]), html)
        self.assertIn(fmt_ibu_bid(plan["ibu_faktisk_prosess"]), html)
        # Og de to tallene skal faktisk VÆRE forskjellige for dette scenarioet.
        self.assertNotAlmostEqual(plan["ibu_planlagt"], plan["ibu_faktisk_prosess"], places=1)

    def test_html_viser_tydelig_avviksvarsel(self):
        plan = self._plan_med_avvik()
        html = render_brewday_html(_ctx(), plan)
        self.assertIn("AVVIK", html.upper())
        self.assertIn("ikke fysisk oppnåelig", html.lower())
        self.assertIn("Magnum", html)

    def test_umulig_ibu_raden_er_visuelt_markert_ikke_alene_som_gyldig(self):
        plan = self._plan_med_avvik()
        html = render_brewday_html(_ctx(), plan)
        self.assertIn("rad-avvik", html)
        self.assertIn("⚠️", html)

    def test_eksport_muterer_aldri_den_oppgitte_humletiden(self):
        plan = self._plan_med_avvik()
        render_brewday_html(_ctx(), plan)
        self.assertEqual(plan["humleplan"][0]["tid"], 90, "Den oppgitte tiden skal aldri klippes/endres av eksporten selv")


class TestEksportUtenAvvikBeholderDagensLayout(unittest.TestCase):
    def _plan_uten_avvik(self):
        return lag_brewday_plan(
            malt_valg=[{"id": "vienna", "mengde": 5.0}],
            humle_valg=[{"id": "tettnang", "gram": 20, "tid": 60}],
            gjaer_id="us05", gjaer_info=_GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB, malt_database=_MALT_DB,
        )

    def test_ingen_avvikspanel_naar_alt_er_innenfor_koketiden(self):
        plan = self._plan_uten_avvik()
        self.assertEqual(plan["humle_over_koketid"], [])
        html = render_brewday_html(_ctx(), plan)
        # NB: sjekker den faktisk RENDREDE div-klassen (bruken), ikke om
        # strengen "ibu-avvik" finnes noe sted -- selve CSS-regelen for
        # klassen ligger alltid statisk i <style>-blokken, uavhengig av om
        # det finnes noe avvik å vise akkurat nå.
        # NB: sjekker den faktisk RENDREDE bruken av klassene (attributt-
        # verdien i en <div>/<tr>), ikke bare om understrengene finnes et
        # sted i dokumentet -- selve CSS-REGLENE for klassene ligger
        # alltid statisk i <style>-blokken, uavhengig av om det finnes
        # noe avvik å vise akkurat nå.
        self.assertNotIn('class="ibu-avvik"', html)
        self.assertNotIn('class="rad-avvik"', html)

    def test_vanlig_layout_uendret(self):
        plan = self._plan_uten_avvik()
        html = render_brewday_html(_ctx(), plan)
        self.assertIn("KVERNHAUG BRYGGHUS", html)
        self.assertIn("Bryggedags-sjekkliste", html)
        self.assertIn("<table class=\"humle\">", html)


if __name__ == "__main__":
    unittest.main()
