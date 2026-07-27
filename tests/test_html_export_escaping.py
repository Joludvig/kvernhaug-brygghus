"""
Tester for at dynamisk (bruker-/database-/skrapet) tekst escapes før den
havner i de nedlastbare HTML-eksportene: modules/card_template.py,
modules/brewday_template.py og modules/shopping_template.py.

Bakgrunn: oppskriftsnavn, bryggerstil, prosessprofil-kommentarer,
vannkilde-/målprofilnavn, salt-/tilsetningsnavn og produkt-URL-er ble
tidligere satt DIREKTE inn i f-string-HTML-en uten escaping. Et
oppskriftsnavn eller en prosesskommentar som inneholder
`<script>...</script>`, anførselstegn eller `&` kunne dermed bryte
HTML-strukturen eller kjøre i nettleseren når arket ble åpnet.

Disse testene bruker EKTE onde nyttelaster (script-tag, anførselstegn,
&, < og >) i akkurat de feltene brukeren selv kontrollerer (oppskriftsnavn,
bryggerstil, meskestegs-kommentar, faktisk OG/FG/ABV-fritekst i
bryggedagsloggen, samt en URL-attributt-utbryting i handlelisten), og
bekrefter at ingen av dem overlever uescaped i utdataen.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

from modules.card_template import render_card_html, render_a4_html
from modules.brewday_template import render_brewday_html
from modules.shopping_template import render_shopping_list_html
from modules.brewday_calc import lag_brewday_plan

_ONDSINNET_NAVN = 'Kvernhaug "Ond" <script>alert(1)</script> & Sønn'
_FORVENTET_RAA_STRENGER_SOM_ALDRI_SKAL_FOREKOMME = [
    "<script>alert(1)</script>",
]


def _assert_ingen_raa_nyttelast(testcase, html_output, kontekst=""):
    for raa in _FORVENTET_RAA_STRENGER_SOM_ALDRI_SKAL_FOREKOMME:
        testcase.assertNotIn(raa, html_output, f"Uescaped <script> funnet i {kontekst}")
    # Selve navnet skal likevel være LESBART i utdataen -- escaped, ikke fjernet.
    testcase.assertIn("&lt;script&gt;", html_output, f"Escaped variant mangler i {kontekst}")
    testcase.assertIn("&amp;", html_output, f"Escaped & mangler i {kontekst}")
    testcase.assertIn("&quot;", html_output, f"Escaped anførselstegn mangler i {kontekst}")


def _recipe(navn=_ONDSINNET_NAVN, brygger_stil=_ONDSINNET_NAVN):
    return {
        "name": navn,
        "batch_size": 20.0,
        "efficiency": 0.75,
        "brygger_stil": brygger_stil,
        "malts": [{"id": "ond_malt", "mengde": 5.0}],
        "hops": [{"id": "ond_humle", "gram": 20.0, "tid": 60}],
        "yeast": "ond_gjaer",
        "stats": {"og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15},
        "flavor_profile": {},
        "process_profile": None,
        "water_source_profile": {"name": _ONDSINNET_NAVN, "ca": 50, "cl": 50, "so4": 50},
        "water_target_profile": {"name": _ONDSINNET_NAVN, "mash_ph_min": 5.2, "mash_ph_max": 5.6},
        "water_treatment": {"salter": []},
        "water_measurements": None,
    }


def _ctx(recipe):
    return {
        "name": recipe["name"], "volum": recipe["batch_size"], "brygger_stil": recipe["brygger_stil"],
        "og": recipe["stats"]["og"], "fg": recipe["stats"]["fg"], "abv": recipe["stats"]["abv"],
        "ibu": recipe["stats"]["ibu"], "ebc": recipe["stats"]["ebc"], "total_pris": 400,
        "summary": _ONDSINNET_NAVN,
        "style_analysis": {"stil": _ONDSINNET_NAVN, "stil_liste": []},
        "recipe": recipe,
        "effektivitet": 0.75,
    }


_MALT_DB = {"ond_malt": {"display_name": _ONDSINNET_NAVN}}
_HUMLE_DB = {"ond_humle": {"display_name": _ONDSINNET_NAVN, "alfa": 5.0}}
_GJAER_DB = {"ond_gjaer": {"display_name": _ONDSINNET_NAVN}}


class TestCardTemplateEscaping(unittest.TestCase):
    def test_render_card_html_escaper_alle_dynamiske_felt(self):
        recipe = _recipe()
        html_output = render_card_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        _assert_ingen_raa_nyttelast(self, html_output, "render_card_html")

    def test_render_a4_html_escaper_alle_dynamiske_felt(self):
        recipe = _recipe()
        # Legg til en prosessprofil med en ondsinnet kommentar, og en
        # vannbehandling med ondsinnede salt-/kildenavn -- begge går
        # gjennom egne A4-spesifikke hjelpefunksjoner
        # (_prosess_html_a4/_vann_html_a4).
        recipe["process_profile"] = {
            "navn": _ONDSINNET_NAVN,
            "boil_minutes": 60,
            "mash_steps": [{"temperatur": 66.0, "varighet": 60, "kommentar": _ONDSINNET_NAVN}],
        }
        html_output = render_a4_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        _assert_ingen_raa_nyttelast(self, html_output, "render_a4_html")

    def test_a4_og_kort_layout_uendret_utenom_escaping(self):
        # Krav: A4- og kortlayout skal forbli uendret -- bekreft at
        # gullramme/footer fortsatt er der, uavhengig av escaping-fiksen.
        recipe = _recipe(navn="Vanlig Navn", brygger_stil="")
        kort = render_card_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Brygg med ild. Del med ære.", kort)
        a4 = render_a4_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("HÅNDVERK", a4.upper())


class TestBrewdayTemplateEscaping(unittest.TestCase):
    _GJAER_INFO = {"display_name": _ONDSINNET_NAVN, "gjaertype": "Ale"}

    def _plan(self):
        profil = {
            "navn": _ONDSINNET_NAVN,
            "boil_minutes": 60,
            "sparge_method": "batch_sparge",
            "mash_steps": [{"temperatur": 66.0, "varighet": 60, "stegtype": "infusjon", "kommentar": _ONDSINNET_NAVN}],
        }
        return lag_brewday_plan(
            malt_valg=[{"id": "ond_malt", "mengde": 5.0}],
            humle_valg=[{"id": "ond_humle", "gram": 20.0, "tid": 60}],
            gjaer_id="ond_gjaer", gjaer_info=self._GJAER_INFO,
            og=1.050, batch_volum_l=20.0, humle_database=_HUMLE_DB,
            malt_database=_MALT_DB, process_profile=profil,
        )

    def test_render_brewday_html_escaper_navn_stil_og_kommentar(self):
        recipe = _recipe()
        ctx = _ctx(recipe)
        html_output = render_brewday_html(ctx, self._plan())
        _assert_ingen_raa_nyttelast(self, html_output, "render_brewday_html (navn/stil/kommentar)")

    def test_render_brewday_html_escaper_fritekst_loggfelt(self):
        # og/fg/abv i "log" kommer fra st.text_input FRITEKST-felter i
        # ui/brewday_panel.py -- helt fri brukerinnlagt tekst, ikke bare
        # database-navn.
        recipe = _recipe(navn="Vanlig Navn", brygger_stil="")
        ctx = _ctx(recipe)
        log = {"og": _ONDSINNET_NAVN, "fg": _ONDSINNET_NAVN, "abv": _ONDSINNET_NAVN}
        html_output = render_brewday_html(ctx, self._plan(), log=log)
        _assert_ingen_raa_nyttelast(self, html_output, "render_brewday_html (log og/fg/abv)")

    def test_render_brewday_html_escaper_vannkilde_og_maalprofil(self):
        recipe = _recipe(navn="Vanlig Navn", brygger_stil="")
        ctx = _ctx(recipe)
        water = {
            "kilde": {"name": _ONDSINNET_NAVN},
            "maal": {"name": _ONDSINNET_NAVN, "mash_ph_min": 5.2, "mash_ph_max": 5.6},
            "behandling": {"salter": [
                {"navn": _ONDSINNET_NAVN, "kjemisk_form": _ONDSINNET_NAVN, "gram_mesk": 1.0, "gram_skyll": 1.0},
            ]},
            "maalinger": {"syrer": [{"navn": _ONDSINNET_NAVN, "mengde_ml": 2.0}]},
        }
        html_output = render_brewday_html(ctx, self._plan(), water=water)
        _assert_ingen_raa_nyttelast(self, html_output, "render_brewday_html (vann)")

    def test_bryggedagsark_layout_uendret_utenom_escaping(self):
        recipe = _recipe(navn="Vanlig Navn", brygger_stil="")
        html_output = render_brewday_html(_ctx(recipe), self._plan())
        self.assertIn("KVERNHAUG BRYGGHUS", html_output)
        self.assertIn("Bryggedags-sjekkliste", html_output)


class TestShoppingTemplateEscaping(unittest.TestCase):
    def test_render_shopping_list_html_escaper_navn_og_butikk(self):
        recipe = _recipe()
        ctx = _ctx(recipe)
        malt_items = [{"navn": _ONDSINNET_NAVN, "mengde": 5.0, "total": 100.0, "er_estimat": False, "url": None}]
        humle_items = [{"navn": _ONDSINNET_NAVN, "gram": 20.0, "tid": 60, "total": 50.0, "er_estimat": False, "url": None}]
        gjaer_item = {"navn": _ONDSINNET_NAVN, "pris": 59.0, "er_estimat": False, "url": None}
        html_output = render_shopping_list_html(ctx, malt_items, humle_items, gjaer_item, _ONDSINNET_NAVN)
        _assert_ingen_raa_nyttelast(self, html_output, "render_shopping_list_html (navn/butikk)")

    def test_render_shopping_list_html_escaper_url_attributt_utbryting(self):
        # Klassisk attributt-utbrytingsforsøk: en URL med et anførselstegn
        # etterfulgt av et nytt attributt/tag skal ALDRI kunne bryte ut av
        # href='...'-attributtet.
        ond_url = "javascript:alert(1)' onmouseover='alert(2)"
        recipe = _recipe(navn="Vanlig Navn", brygger_stil="")
        ctx = _ctx(recipe)
        malt_items = [{"navn": "Pilsner", "mengde": 5.0, "total": 100.0, "er_estimat": False, "url": ond_url}]
        html_output = render_shopping_list_html(ctx, malt_items, [], None, "Vestbrygg.no")
        self.assertNotIn("onmouseover='alert(2)'", html_output)
        self.assertNotIn("' onmouseover=", html_output)
        self.assertIn("&#x27; onmouseover=&#x27;alert(2)", html_output)

    def test_handleliste_layout_uendret_utenom_escaping(self):
        recipe = _recipe(navn="Vanlig Navn", brygger_stil="")
        html_output = render_shopping_list_html(_ctx(recipe), [], [], None, "Vestbrygg.no")
        self.assertIn("KVERNHAUG BRYGGHUS", html_output)
        self.assertIn("TOTAL:", html_output)


if __name__ == "__main__":
    unittest.main()
