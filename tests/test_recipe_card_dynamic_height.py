"""
Regresjonstester for at oppskriftskortet nå får høyden sin fra Streamlits
EGEN, ekte DOM-målte innholdshøyde (st.iframe(..., height="content")) i
stedet for et Python-side pikselanslag.

Bakgrunn: en tidligere "tegn-per-linje"-heuristikk
(modules/card_template.beregn_recipe_card_height, fjernet i denne
commiten) klippet fortsatt enkelte kort (Kvernhaug Sommerglød, Sommerglød
V2 vs. Gamleguten) fordi ekte tekstbryting/bredde/fontrendering aldri kan
predikeres pålitelig fra antall tegn alene. Streamlit >= 1.57 sin
st.iframe(src, height="content") måler den FAKTISKE rendrede høyden i
nettleseren for rå HTML-strenger -- ingen Python-side gjetting er lenger
involvert i det hele tatt.

Dette betyr at selve DOM-målingen ikke er testbar fra ren Python/unittest
(ingen nettleser i denne test-runneren) -- det disse testene i stedet
låser er de tingene som FAKTISK kan verifiseres uten en nettleser:
  1. at ui/recipe_card.py faktisk bruker den innholdsmålte st.iframe-APIen
     og ikke lenger den gamle, fast-høyde st.components.v1.html-varianten
     eller noen gjenværende pikselheuristikk
  2. at kortets egen HTML (modules/card_template.render_card_html) aldri
     legger en kunstig høydebegrensning (max-height/overflow) på seg selv
     -- for et bredt spekter av vidt forskjellige oppskrifter, IKKE bare
     de tre/fem navngitte tilfellene fra tidligere runder, nettopp for å
     bekrefte at egenskapen ikke er knyttet til bestemte oppskriftstyper
  3. at footer/gullramme alltid er med i den rendrede HTML-en, uansett
     tittellengde/antall ingredienser/smaksprofillengde
  4. at A4-eksporten (render_a4_html) er fullstendig urørt og uavhengig

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import inspect
import unittest

import ui.recipe_card as recipe_card_module
import modules.card_template as card_template
from modules.card_template import render_card_html, render_a4_html


def _recipe(navn, n_malt=3, n_humle=3, brygger_stil=""):
    return {
        "name": navn,
        "batch_size": 20.0,
        "efficiency": 0.75,
        "brygger_stil": brygger_stil,
        "malts": [{"id": f"malt_{i}", "mengde": 1.0} for i in range(n_malt)],
        "hops": [{"id": f"humle_{i}", "gram": 20.0, "tid": 60} for i in range(n_humle)],
        "yeast": "saflager_w3470",
        "stats": {"og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15},
        "flavor_profile": {},
        "process_profile": None,
        "water_source_profile": None,
        "water_target_profile": None,
        "water_treatment": None,
        "water_measurements": None,
    }


def _ctx(recipe, summary="Rik, maltrik smaksprofil."):
    return {
        "name": recipe["name"], "volum": recipe["batch_size"], "brygger_stil": recipe.get("brygger_stil", ""),
        "og": recipe["stats"]["og"], "fg": recipe["stats"]["fg"], "abv": recipe["stats"]["abv"],
        "ibu": recipe["stats"]["ibu"], "ebc": recipe["stats"]["ebc"], "total_pris": 400,
        "summary": summary,
        "style_analysis": {"stil": "Märzen", "stil_liste": []},
        "recipe": recipe,
    }


_MALT_DB = {f"malt_{i}": {"display_name": f"Malt {i}"} for i in range(15)}
_HUMLE_DB = {f"humle_{i}": {"display_name": f"Humle {i}", "alfa": 5.0} for i in range(15)}
_GJAER_DB = {"saflager_w3470": {"display_name": "SafLager W-34/70"}}

_LANG_SMAKSPROFIL = (
    "En kompleks, lagdelt smaksprofil med rikelig brødmalt, en anelse honning, "
    "mild humlebitterhet i bakgrunnen og en varm, rund avslutning som utvikler seg "
    "videre med lagring på flaske over flere måneder, og som gjerne kan bli enda "
    "rundere med litt ekstra lagringstid i kaldt rom."
)

# Et bredt, bevisst variert utvalg -- IKKE bare de navngitte oppskriftene
# fra tidligere runder -- for å bekrefte at egenskapen ikke er knyttet til
# bestemte oppskriftstyper (krav 6).
_TEST_OPPSKRIFTER = [
    ("kort_tittel", _recipe("Eldsvenn V1")),
    ("tolinjers_tittel", _recipe("Kvernhaug Wiesn-Märzen 1872")),
    ("trelinjers_tittel", _recipe("Kvernhaug Historisk Wiesn-Märzen Førkrigsutgave 1872 Spesialtapning")),
    ("mange_maltrader", _recipe("Sommerglød V2", n_malt=12)),
    ("mange_humlerader", _recipe("Gamleguten Klone", n_humle=9)),
    ("kvernhaug_sommergloed", _recipe("Kvernhaug Sommerglød", n_malt=6, n_humle=4)),
    ("med_bryggerstil", _recipe("Test", brygger_stil="Imperial Nordisk Røykstaut")),
]


class Test1UietBrukerInnholdsmaaltHoyde(unittest.TestCase):
    """Krav 2 + 5: ui/recipe_card.py skal bruke st.iframe(...,
    height="content") -- ikke den gamle, fast-høyde
    st.components.v1.html(..., height=<tall>)-varianten -- og skal IKKE
    lenger referere til den fjernede pikselheuristikken."""

    def setUp(self):
        self.kilde = inspect.getsource(recipe_card_module)

    def test_bruker_st_iframe_med_height_content(self):
        self.assertIn("st.iframe(", self.kilde)
        self.assertIn('height="content"', self.kilde)

    def test_bruker_ikke_lenger_components_v1_html_for_kortet(self):
        self.assertNotIn("components.v1.html", self.kilde)

    def test_refererer_ikke_lenger_til_fjernet_heuristikk(self):
        self.assertNotIn("beregn_recipe_card_height", self.kilde)
        # NB: sjekker variabelnavnet "_card_h" (den gamle pikselvariabelen),
        # ikke bare understrengen "_card_h" -- den finnes bokstavelig som
        # substreng inne i det fortsatt gyldige funksjonsnavnet
        # "render_card_html", som IKKE skal flagges som et treff her.
        self.assertNotIn("_card_h =", self.kilde)
        self.assertNotIn("_card_h=", self.kilde)


class Test2HeuristikkenErFjernetFraModulen(unittest.TestCase):
    """Krav 5: den gamle tegn-per-linje-heuristikken (og alle dens
    konstanter) skal være helt borte fra modules/card_template.py, ikke
    bare ubrukt."""

    def test_beregn_recipe_card_height_finnes_ikke_lenger(self):
        self.assertFalse(hasattr(card_template, "beregn_recipe_card_height"))

    def test_estimer_linjer_finnes_ikke_lenger(self):
        self.assertFalse(hasattr(card_template, "_estimer_linjer"))

    def test_ingen_card_pikselkonstanter_igjen(self):
        gjenvaerende = [navn for navn in vars(card_template) if navn.startswith("_CARD_")]
        self.assertEqual(gjenvaerende, [])


class Test3KortetsEgenHtmlLeggerAldriHoydebegrensning(unittest.TestCase):
    """Krav 4 + 6: for et bredt, bevisst variert utvalg av oppskrifter
    (ikke bare navngitte enkelttilfeller) skal kortets egen HTML aldri
    inneholde max-height eller overflow:hidden på hovedcontaineren --
    ekte høyde er Streamlit/nettleserens ansvar, ikke noe kortet selv
    begrenser."""

    def test_ingen_max_height_eller_overflow_hidden_uansett_innhold(self):
        for beskrivelse, recipe in _TEST_OPPSKRIFTER:
            with self.subTest(beskrivelse):
                html = render_card_html(
                    _ctx(recipe, summary=_LANG_SMAKSPROFIL), _MALT_DB, _HUMLE_DB, _GJAER_DB,
                )
                kompakt = html.replace(" ", "").lower()
                self.assertNotIn("max-height", kompakt)
                self.assertNotIn("overflow:hidden", kompakt)

    def test_footer_og_gullramme_alltid_med_uansett_innhold(self):
        for beskrivelse, recipe in _TEST_OPPSKRIFTER:
            with self.subTest(beskrivelse):
                html = render_card_html(
                    _ctx(recipe, summary=_LANG_SMAKSPROFIL), _MALT_DB, _HUMLE_DB, _GJAER_DB,
                )
                self.assertIn("Brygg med ild. Del med ære.", html)
                self.assertIn("HÅNDVERK", html.upper())
                self.assertIn(f"border:1.5px solid {card_template._GOLD}", html)

    def test_hoyden_kommer_ikke_fra_oppskriftsnavnet_i_det_hele_tatt(self):
        # Selve poenget med fiksen: HTML-genereringen skal IKKE lenger
        # forgrene seg på tittelen for å bestemme noen høyde -- render_card_html
        # for to helt ulike titler skal ha strukturelt identisk
        # container-CSS (samme <div style="..."> for selve kort-rammen).
        kort_a = render_card_html(_ctx(_recipe("Eldsvenn V1")), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        kort_b = render_card_html(_ctx(_recipe("Kvernhaug Historisk Wiesn-Märzen 1872")), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        ramme_a = kort_a.split("<!-- ── BRAND HEADER")[0]
        ramme_b = kort_b.split("<!-- ── BRAND HEADER")[0]
        self.assertEqual(ramme_a, ramme_b, "Selve kort-rammens CSS skal være uavhengig av tittelen")


class Test4A4EksportenErUroert(unittest.TestCase):
    """A4-eksporten er et separat, nedlastbart HTML-dokument -- ikke en
    Streamlit-iframe -- og skal ikke være påvirket av denne fiksen i det
    hele tatt."""

    def test_a4_rendres_uavhengig_av_iframe_endringen(self):
        recipe = _recipe("Kvernhaug Wiesn-Märzen 1872")
        html = render_a4_html(_ctx(recipe, summary=_LANG_SMAKSPROFIL), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Kvernhaug Wiesn-Märzen 1872", html)
        self.assertIn("Brygg med ild. Del med ære.", html)
        self.assertNotIn("st.iframe", html)
        self.assertNotIn("components.v1.html", html)

    def test_render_a4_html_kildekode_bruker_ikke_iframe_apiet(self):
        kilde = inspect.getsource(card_template.render_a4_html)
        self.assertNotIn("st.iframe", kilde)
        self.assertNotIn("height=", kilde)


if __name__ == "__main__":
    unittest.main()
