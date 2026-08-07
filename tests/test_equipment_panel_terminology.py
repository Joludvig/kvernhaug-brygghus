"""
Tester for Steg F11H (2026-08-07): terminologirettingen rundt den
globale, planlagte effektivitetsinnstillingen.

Bakgrunn (Steg F11G): `beregn_og()` bruker effektivitetsverdien
matematisk som BRYGGHUSEFFEKTIVITET (gravity points i FERDIG
batchvolum), ikke meskeeffektivitet -- men `ui/equipment_panel.py`
kalte den feilaktig "Meskeeffektivitet (%)". Denne filen bekrefter at:
  1. UI-labelen nå er korrekt ("Brygghuseffektivitet (%)"), med en kort
     forklarende hjelpetekst.
  2. Den faktisk MÅLTE meske-/brygghuseffektiviteten i
     bryggedagsloggen (ui/brewday_panel.py, modules/brewday_template.py)
     beholder sin egen, allerede korrekte distinksjon.
  3. Lagringskontrakten (`efficiency`-nøkkelen i data/equipment.json) er
     UENDRET.
  4. Selve beregningsresultatene (OG/FG/ABV/IBU/EBC) er bit-for-bit
     identiske med før terminologiendringen.
  5. Demo Mode fungerer uendret.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import json
import os
import tempfile
import unittest

import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)

from modules.calculations import beregn_og, beregn_ebc, beregn_total_ibu, beregn_fg_og_abv
from modules.brewday_template import render_brewday_html
from modules.brewday_calc import lag_brewday_plan


class TestEquipmentPanelViserBrygghuseffektivitet(unittest.TestCase):
    """AppTest av den ekte ui/equipment_panel.py."""

    def _kjor(self):
        from streamlit.testing.v1 import AppTest
        app_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_equipment_panel_app.py")
        at = AppTest.from_file(app_py)
        at.run()
        self.assertFalse(at.exception, f"_equipment_panel_app.py kastet exception: {at.exception}")
        return at

    def test_viser_brygghuseffektivitet_label(self):
        at = self._kjor()
        labels = [w.label for w in at.number_input]
        self.assertIn("Brygghuseffektivitet (%)", labels)

    def test_viser_ikke_lenger_meskeeffektivitet_label(self):
        at = self._kjor()
        labels = [w.label for w in at.number_input]
        self.assertNotIn("Meskeeffektivitet (%)", labels)

    def test_hjelpetekst_forklarer_begrepet_kort(self):
        at = self._kjor()
        eff_widget = next(w for w in at.number_input if w.label == "Brygghuseffektivitet (%)")
        self.assertIsNotNone(eff_widget.help)
        self.assertIn("brygghuseffektivitet", eff_widget.help.lower())
        self.assertIn("meskeeffektivitet", eff_widget.help.lower())

    def test_lagringsnokkel_efficiency_uendret(self):
        # Selve number_input-widgeten er koblet til data-nøkkelen
        # "efficiency" via lagre_equipment() i render_equipment_panel()
        # -- bekreftet indirekte ved at panelet laster/viser dagens
        # lagrede eq["efficiency"]*100 uten feil eller KeyError.
        at = self._kjor()
        eff_widget = next(w for w in at.number_input if w.label == "Brygghuseffektivitet (%)")
        self.assertGreaterEqual(eff_widget.value, 50)
        self.assertLessEqual(eff_widget.value, 100)


class TestBryggedagsloggBeholderMaltMeskeOgBrygghusDistinksjon(unittest.TestCase):
    """Bekrefter at DEN FAKTISK MÅLTE meske-/brygghuseffektiviteten i
    bryggedagspanelet (ui/brewday_panel.py, live UI) IKKE ble rørt av
    F11H -- kun den planlagte, globale utstyrsinnstillingen."""

    def _kjor(self):
        from streamlit.testing.v1 import AppTest
        app_py = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_brewday_panel_app.py")
        at = AppTest.from_file(app_py)
        at.run()
        self.assertFalse(at.exception, f"_brewday_panel_app.py kastet exception: {at.exception}")
        return at

    def test_maskeeffektivitet_og_brygghuseffektivitet_begge_vises_atskilt(self):
        at = self._kjor()
        alle_tekster = " ".join(m.value for m in at.markdown) + " ".join(
            str(getattr(el, "label", "")) for el in at.get("metric")
        )
        self.assertIn("Maskeeffektivitet", alle_tekster)
        self.assertIn("Brygghuseffektivitet", alle_tekster)
        self.assertIn("Planlagt effektivitet", alle_tekster)


class TestBrewdayTemplatePlanEffektivitetKorrektMerket(unittest.TestCase):
    """Bekrefter at den nedlastbare bryggedagsplan-HTML-en (modules/
    brewday_template.py) ikke lenger viser "Plan: X%" under "Maskeeff",
    og at den planlagte prosenten i stedet står ved
    "Brygghuseffektivitet"."""

    _MALT_DB = {"test_malt": {"display_name": "Test Malt", "ebc": 5.0, "potensiale": 1.037}}
    _HUMLE_DB = {"test_humle": {"display_name": "Test Humle", "alfa": 10.0}}
    _GJAER_INFO = {"display_name": "Test Gjær", "gjaertype": "Ale"}

    def _plan(self):
        return lag_brewday_plan(
            malt_valg=[{"id": "test_malt", "mengde": 5.0}],
            humle_valg=[{"id": "test_humle", "gram": 20.0, "tid": 60}],
            gjaer_id="test_gjaer", gjaer_info=self._GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=self._HUMLE_DB,
            malt_database=self._MALT_DB,
        )

    def _ctx(self, effektivitet=0.75):
        return {
            "name": "Test", "volum": 20.0, "brygger_stil": "",
            "og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15,
            "total_pris": 300, "summary": "",
            "style_analysis": {"stil": "Test", "stil_liste": []},
            "recipe": {
                "name": "Test", "batch_size": 20.0, "efficiency": effektivitet,
                "malts": [{"id": "test_malt", "mengde": 5.0}],
                "hops": [{"id": "test_humle", "gram": 20.0, "tid": 60}],
                "yeast": "test_gjaer",
                "stats": {"og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15},
                "flavor_profile": {}, "process_profile": None,
                "water_source_profile": None, "water_target_profile": None,
                "water_treatment": None, "water_measurements": None,
            },
            "effektivitet": effektivitet,
        }

    def test_maskeeff_boksen_viser_ikke_lenger_plan_prosent(self):
        html_output = render_brewday_html(self._ctx(0.75), self._plan())
        self.assertNotIn("Maskeeff</div>\n    <div class='stat-maal'>Plan:", html_output)
        # Mer robust: selve "Plan: 75%"-frasen skal ikke lenger stå i
        # nærheten av "Maskeeff"-cellen.
        maskeeff_idx = html_output.index("Maskeeff")
        naerliggende = html_output[maskeeff_idx:maskeeff_idx + 200]
        self.assertNotIn("Plan:", naerliggende)

    def test_brygghuseffektivitet_feltet_viser_plan_prosent(self):
        html_output = render_brewday_html(self._ctx(0.75), self._plan())
        self.assertIn("Brygghuseffektivitet (plan: 75%)", html_output)

    def test_ulik_planlagt_effektivitet_vises_korrekt(self):
        html_output = render_brewday_html(self._ctx(0.80), self._plan())
        self.assertIn("Brygghuseffektivitet (plan: 80%)", html_output)


class TestBeregningerUendretEtterTerminologiendring(unittest.TestCase):
    """Bekrefter at selve tallene (OG/FG/ABV/IBU/EBC) for en kjent
    oppskrift er BIT-FOR-BIT identiske med verdiene dokumentert før
    Steg F11H -- kun tekst/labels er endret, ingen matematikk."""

    def test_wiesn_referansen_gir_identiske_tall(self):
        with open("data/master_malt.json", encoding="utf-8") as f:
            malt_db = json.load(f)
        with open("data/master_humle_v2.json", encoding="utf-8") as f:
            humle_db = json.load(f)
        flatt_malt = {v.get("display_name", k): v for k, v in malt_db.items() if v}
        flatt_humle = {v.get("display_name", k): v for k, v in humle_db.items() if v}
        malt_calc = [
            {"navn": malt_db["weyermann_munich_1"]["display_name"], "mengde": 0.7},
            {"navn": malt_db["munich_ii"]["display_name"], "mengde": 4.6},
            {"navn": malt_db["vienna"]["display_name"], "mengde": 1.8},
        ]
        humle_calc = [{"navn": humle_db["tettnang"]["display_name"], "gram": 88.0, "tid": 60}]

        og = beregn_og(malt_calc, flatt_malt, 25.0, 0.75)
        ebc = beregn_ebc(malt_calc, flatt_malt, 25.0)
        ibu = beregn_total_ibu(humle_calc, flatt_humle, 25.0, og)
        fg, abv = beregn_fg_og_abv(og, 0.82)

        self.assertEqual(og, 1.0639925272000001)
        self.assertEqual(ebc, 20.743948714358822)
        self.assertEqual(ibu, 22.19577066725207)
        self.assertEqual(fg, 1.011518654896)
        self.assertEqual(abv, 6.887195739900018)


class TestEquipmentPanelDemoModeUendret(unittest.TestCase):
    """Bekrefter at Demo Mode fortsatt fungerer uendret med den nye
    labelen, og at ingen skriving skjer til den ekte data/equipment.json."""

    def test_demo_mode_viser_samme_label_uten_a_skrive_ekte_fil(self):
        ekte_fil = os.path.join("data", "equipment.json")
        hash_for = None
        if os.path.exists(ekte_fil):
            with open(ekte_fil, "rb") as f:
                hash_for = f.read()

        env = dict(os.environ)
        env["DEMO_MODE"] = "1"
        import subprocess
        import sys as _sys
        script = (
            "import sys, os, logging; "
            "logging.getLogger('streamlit').setLevel(logging.ERROR); "
            "from streamlit.testing.v1 import AppTest; "
            "at = AppTest.from_file(r'tests/_equipment_panel_app.py'); "
            "at.run(); "
            "assert not at.exception, at.exception; "
            "labels = [w.label for w in at.number_input]; "
            "assert 'Brygghuseffektivitet (%)' in labels, labels; "
            "print('OK')"
        )
        result = subprocess.run(
            [_sys.executable, "-c", script],
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            env=env, capture_output=True, text=True, timeout=60,
        )
        self.assertEqual(result.returncode, 0, f"stdout={result.stdout}\nstderr={result.stderr}")
        self.assertIn("OK", result.stdout)

        if hash_for is not None:
            with open(ekte_fil, "rb") as f:
                hash_etter = f.read()
            self.assertEqual(hash_for, hash_etter, "Demo Mode skrev til ekte data/equipment.json!")


if __name__ == "__main__":
    unittest.main()
