"""
Regresjonstest for #544: oppskriftskortet og A4-eksporten viste stilmatch fra
den numeriske «nærmeste stil» (style_analysis["stil"], raw_score) mens
analyselisten «Samlet stiltreff» viste en annen toppstil. Kort og eksport skal
bruke samme rangering som analyselisten (modules.style_engine.
sorter_samlet_stiltreff) — uten å endre scoreformlene.

Kjøres med:
    py -3 -m unittest tests.test_style_match_consistency -b
"""
import unittest

from modules.card_template import render_a4_html, render_card_html
from modules.style_engine import (
    analyser_stil_og_balanse,
    samlet_toppstil,
    sorter_samlet_stiltreff,
)
from tests.test_style_engine import TestNumeriskNaermesteVsSamletTopp


def _stil(navn, score, prio=1):
    return {"stil": navn, "score": score, "prio": prio}


def _ctx(numerisk_stil, stil_liste, brygger_stil=""):
    recipe = {
        "name": "Sommerglød", "batch_size": 20.0, "efficiency": 0.75,
        "brygger_stil": brygger_stil, "malts": [], "hops": [], "yeast": "x",
        "stats": {"og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15},
        "flavor_profile": {}, "process_profile": None,
        "water_source_profile": None, "water_target_profile": None,
        "water_treatment": {"salter": []}, "water_measurements": None,
    }
    return {
        "name": "Sommerglød", "volum": 20.0, "brygger_stil": brygger_stil,
        "og": 1.050, "fg": 1.012, "abv": 5.0, "ibu": 20, "ebc": 15,
        "total_pris": 400, "summary": "s",
        "style_analysis": {"stil": numerisk_stil, "stil_liste": stil_liste},
        "recipe": recipe, "effektivitet": 0.75,
    }


def _render(ctx):
    kort = render_card_html(ctx, {}, {}, {})
    a4 = render_a4_html(ctx, {}, {}, {})
    return kort, a4


class TestSamletRangering(unittest.TestCase):
    def test_hoyeste_score_vinner_uavhengig_av_listeorden(self):
        liste = [_stil("Belgisk Witbier", 75), _stil("Tysk Pilsner", 87)]
        self.assertEqual(samlet_toppstil(liste)["stil"], "Tysk Pilsner")

    def test_like_poeng_bruker_laveste_prio_som_tie_break(self):
        liste = [_stil("B", 80, prio=2), _stil("A", 80, prio=1)]
        self.assertEqual([s["stil"] for s in sorter_samlet_stiltreff(liste)], ["A", "B"])
        self.assertEqual(samlet_toppstil(liste)["stil"], "A")

    def test_tom_og_for_svak_liste_gir_ingen_topp(self):
        self.assertIsNone(samlet_toppstil([]))
        self.assertIsNone(samlet_toppstil([_stil("Svak", 4)]))


class TestKortOgA4FolgerSamletTopp(unittest.TestCase):
    LISTE = [_stil("Belgisk Witbier", 75), _stil("Tysk Pilsner", 87)]

    def test_kort_med_bryggerstil_viser_samlet_vinner_og_prosent(self):
        kort, a4 = _render(_ctx("Belgisk Witbier", self.LISTE, brygger_stil="Sommerglød Blonde"))
        self.assertIn("Sommerglød Blonde", kort)  # bryggerens egen betegnelse beholdes
        self.assertIn("Stilmatch: Tysk Pilsner · 87%", kort)
        self.assertNotIn("Witbier", kort)
        self.assertIn('<div class="stil">Tysk Pilsner</div>', a4)
        self.assertNotIn("Witbier", a4)

    def test_kort_uten_bryggerstil_viser_samlet_vinner(self):
        kort, a4 = _render(_ctx("Belgisk Witbier", self.LISTE))
        self.assertIn(">Tysk Pilsner</div>", kort)
        self.assertNotIn("Witbier", kort)

    def test_like_poeng_gir_samme_vinner_som_analyselisten(self):
        liste = [_stil("B", 80, prio=2), _stil("A", 80, prio=1)]
        kort, a4 = _render(_ctx("B", liste, brygger_stil="Egen"))
        self.assertIn("Stilmatch: A · 80%", kort)
        self.assertIn('<div class="stil">A</div>', a4)

    def test_ingen_sterke_treff_viser_ingen_stilmatch_med_bryggerstil(self):
        kort, a4 = _render(_ctx("Kreativt Brygg", [_stil("Svak", 3)], brygger_stil="Egen"))
        self.assertIn("Egen", kort)
        self.assertNotIn("Stilmatch", kort)
        self.assertNotIn("%</div>", kort.split("Egen")[1][:200])

    def test_ingen_sterke_treff_faller_tilbake_til_numerisk_stil_uten_bryggerstil(self):
        kort, a4 = _render(_ctx("Kreativt Brygg", []))
        self.assertIn(">Kreativt Brygg</div>", kort)
        self.assertIn('<div class="stil">Kreativt Brygg</div>', a4)

    def test_egen_stil_pavirker_ikke_matchen(self):
        a, _ = _render(_ctx("X", self.LISTE, brygger_stil="Tysk Pilsner Light"))
        self.assertIn("Tysk Pilsner Light", a)
        self.assertIn("Stilmatch: Tysk Pilsner · 87%", a)


class TestMotorDivergensGjennomKort(unittest.TestCase):
    """Ekte motorresultat der numerisk og samlet vinner er ulike
    (English Bitter vs English Dark Mild)."""

    def test_kort_og_a4_bruker_samlet_topp_fra_motoren(self):
        resultat = analyser_stil_og_balanse(TestNumeriskNaermesteVsSamletTopp()._oppskrift())
        self.assertEqual(resultat["stil"], "English Bitter")
        topp = samlet_toppstil(resultat["stil_liste"])
        self.assertEqual(topp["stil"], "English Dark Mild")
        ctx = _ctx(resultat["stil"], resultat["stil_liste"], brygger_stil="Min Ale")
        kort, a4 = _render(ctx)
        self.assertIn(f"Stilmatch: English Dark Mild · {topp['score']}%", kort)
        self.assertNotIn("English Bitter", kort)
        self.assertIn('<div class="stil">English Dark Mild</div>', a4)
        self.assertEqual(resultat["stil"], "English Bitter")  # numerisk uendret


if __name__ == "__main__":
    unittest.main()
