"""
Regresjonstester for oppskriftskortets iframe-høydeberegning
(modules/card_template.beregn_recipe_card_height).

Bakgrunn: kortet rendres av ui/recipe_card.py inne i en
st.components.v1.html(..., height=..., scrolling=False)-iframe -- en FAST
pikselhøyde satt fra Python-siden. Kortets egen <div> (render_card_html) har
verken max-height eller overflow -- den vokser fritt. Feilen var at den
gamle høydeformelen bare tok hensyn til antall malt-/humlerader og
bryggerstil, ikke antall tittellinjer -- en lang tittel som
"Kvernhaug Wiesn-Märzen 1872" brytes over to linjer og gjorde kortet REELT
høyere enn budsjettert, slik at bunnen (footer/gullramme) ble klippet ved
iframe-kanten.

Ren Python, ingen Streamlit -- disse testene kaller kun
modules/card_template.py sine funksjoner direkte.

Kjøres med:
    py -3 -m unittest discover -s tests
"""
import unittest

import modules.card_template as card_template
from modules.card_template import beregn_recipe_card_height, render_card_html, render_a4_html


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


_MALT_DB = {f"malt_{i}": {"display_name": f"Malt {i}"} for i in range(10)}
_HUMLE_DB = {f"humle_{i}": {"display_name": f"Humle {i}", "alfa": 5.0} for i in range(10)}
_GJAER_DB = {"saflager_w3470": {"display_name": "SafLager W-34/70"}}


class Test1TittelLengdeOkerHoyden(unittest.TestCase):
    """Krav: Wiesn-tittelen skal gi en større komponenthøyde enn den
    korte Eldsvenn-tittelen, alt annet likt."""

    def test_wiesn_gir_storre_hoyde_enn_eldsvenn(self):
        eldsvenn = beregn_recipe_card_height(_recipe("Eldsvenn V1"))
        wiesn = beregn_recipe_card_height(_recipe("Kvernhaug Wiesn-Märzen 1872"))
        self.assertGreater(wiesn, eldsvenn)

    def test_gamleguten_klone_er_samme_hoyde_som_eldsvenn(self):
        # To korte, én-linjes titler skal gi lik grunnhøyde (ingen falsk
        # ekstra høyde for en tittel som uansett får plass på én linje).
        eldsvenn = beregn_recipe_card_height(_recipe("Eldsvenn V1"))
        gamleguten = beregn_recipe_card_height(_recipe("Gamleguten Klone"))
        self.assertEqual(eldsvenn, gamleguten)

    def test_tittel_som_bryter_til_to_linjer_gir_ekstra_hoydebudsjett(self):
        # Selve roten til bugen: en lang tittel MÅ faktisk gi mer enn én
        # beregnet linje ved kortets reelle bredde -- ellers er det ikke
        # høyden som er fikset, bare et tall som tilfeldigvis økte.
        linjer_kort = card_template._estimer_linjer(
            "Eldsvenn V1", card_template._CARD_WIDTH_PX, card_template._CARD_TITLE_AVG_CHAR_WIDTH_PX)
        linjer_lang = card_template._estimer_linjer(
            "Kvernhaug Wiesn-Märzen 1872", card_template._CARD_WIDTH_PX, card_template._CARD_TITLE_AVG_CHAR_WIDTH_PX)
        self.assertEqual(linjer_kort, 1)
        self.assertGreaterEqual(linjer_lang, 2)

    def test_svaert_lang_tittel_gir_enda_mer_hoyde_enn_topp_tittel(self):
        to_linjer = beregn_recipe_card_height(_recipe("Kvernhaug Wiesn-Märzen 1872"))
        tre_linjer = beregn_recipe_card_height(
            _recipe("Kvernhaug Historisk Wiesn-Märzen Førkrigsutgave 1872 Spesialtapning"))
        self.assertGreater(tre_linjer, to_linjer)


class Test2MangeIngrediensraderOkerHoyden(unittest.TestCase):
    def test_flere_maltrader_oker_hoyden(self):
        faa = beregn_recipe_card_height(_recipe("Test", n_malt=3))
        mange = beregn_recipe_card_height(_recipe("Test", n_malt=8))
        self.assertGreater(mange, faa)

    def test_flere_humlerader_oker_hoyden(self):
        faa = beregn_recipe_card_height(_recipe("Test", n_humle=3))
        mange = beregn_recipe_card_height(_recipe("Test", n_humle=8))
        self.assertGreater(mange, faa)

    def test_faa_rader_under_grensen_paavirker_ikke_hoyden(self):
        # 1 eller 2 rader skal ikke gi NEGATIV justering -- grunnhøyden
        # forutsetter allerede opptil 3 rader.
        en_rad = beregn_recipe_card_height(_recipe("Test", n_malt=1, n_humle=1))
        tre_rader = beregn_recipe_card_height(_recipe("Test", n_malt=3, n_humle=3))
        self.assertEqual(en_rad, tre_rader)


class Test3LangSmaksprofilOkerHoyden(unittest.TestCase):
    def test_lang_smaksprofil_oker_hoyden(self):
        kort = beregn_recipe_card_height(_recipe("Test"), summary_tekst="Rik smaksprofil.")
        lang = beregn_recipe_card_height(
            _recipe("Test"),
            summary_tekst=(
                "En kompleks, lagdelt smaksprofil med rikelig brødmalt, en anelse honning, "
                "mild humlebitterhet i bakgrunnen og en varm, rund avslutning som utvikler seg "
                "videre med lagring på flaske over flere måneder."
            ),
        )
        self.assertGreater(lang, kort)


class Test4FooterOgRammeFinnesIRendretHtml(unittest.TestCase):
    def test_footer_og_gullramme_er_med_i_html(self):
        recipe = _recipe("Kvernhaug Wiesn-Märzen 1872")
        html = render_card_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Brygg med ild. Del med ære.", html)
        self.assertIn("HÅNDVERK", html.upper())
        # Gullrammen (border rundt hele kortet) -- selve ytre <div>.
        self.assertIn(f"border:1.5px solid {card_template._GOLD}", html)

    def test_ingen_overflow_hidden_skjuler_kortinnholdet(self):
        recipe = _recipe("Kvernhaug Wiesn-Märzen 1872")
        html = render_card_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        html_uten_mellomrom = html.replace(" ", "").lower()
        self.assertNotIn("overflow:hidden", html_uten_mellomrom)

    def test_kortets_egen_div_har_ingen_fast_maxheight(self):
        recipe = _recipe("Kvernhaug Wiesn-Märzen 1872")
        html = render_card_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        html_uten_mellomrom = html.replace(" ", "").lower()
        self.assertNotIn("max-height", html_uten_mellomrom)


class Test5A4KortetPaavirkesIkke(unittest.TestCase):
    """A4-eksporten (render_a4_html) er et helt separat, nedlastbart
    HTML-dokument -- ikke en Streamlit-iframe -- og har derfor aldri hatt
    dette klippingsproblemet. Denne testen bekrefter at A4-eksporten
    fortsatt fungerer uendret og ikke er koblet til den nye
    høydeberegningen i det hele tatt."""

    def test_a4_rendres_fortsatt_uten_a_bruke_hoydeberegningen(self):
        recipe = _recipe("Kvernhaug Wiesn-Märzen 1872")
        html = render_a4_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        self.assertIn("Kvernhaug Wiesn-Märzen 1872", html)
        self.assertIn("Brygg med ild. Del med ære.", html)
        self.assertNotIn("components.v1.html", html)

    def test_a4_html_inneholder_ingen_height_relatert_a4_bug(self):
        recipe = _recipe("Kvernhaug Wiesn-Märzen 1872", n_malt=8, n_humle=8)
        html = render_a4_html(_ctx(recipe), _MALT_DB, _HUMLE_DB, _GJAER_DB)
        # A4-dokumentet er en fritt voksende HTML-side (utskrift/nedlasting)
        # -- ingen iframe-høyde er relevant her i det hele tatt.
        self.assertIn("<h1>Kvernhaug Wiesn-Märzen 1872</h1>", html)


if __name__ == "__main__":
    unittest.main()
