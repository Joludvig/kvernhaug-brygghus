"""
Regresjonstester for modules/flavor_engine.py + data/master_malt.json.

Bakgrunn: Munich I og Munich II manglet Toast-kategori helt i
data/master_malt.json (kun Vienna hadde en verdi der), slik at en oppskrift
med over 70 % Munich II fortsatt endte på Toast 0.6 — hele bidraget kom fra
Viennas beskjedne andel. Dette er en datafeil i maltbiblioteket, ikke en
spesialregel i stilmotoren, og testene her bruker derfor den ekte
data/master_malt.json (samme fil appen faktisk laster via
app.py:last_json_data) i stedet for hardkodede fixtures, slik at de fanger
opp regresjoner i selve dataene.
"""
import json
import os
import unittest

from modules.flavor_engine import generer_smakshjul

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _last_malt_db():
    with open(os.path.join(_REPO_ROOT, "data", "master_malt.json"), encoding="utf-8") as f:
        malt_db = json.load(f)
    return {info.get("display_name", k): info for k, info in malt_db.items() if info}


def _smak(malt_liste, ibu=20.0, gjaer="SafLager W-34/70"):
    _, poeng = generer_smakshjul(malt_liste, _FLATT_MALT, [], {}, ibu, gjaer, {})
    return poeng


_FLATT_MALT = _last_malt_db()


class TestMunichVienneseToastFiks(unittest.TestCase):
    """Regresjonstest for selve datafeilen (0.6 Toast for en Munich-dominert
    oppskrift, se PR-bakgrunn i modulens docstring)."""

    def test_munich_og_vienna_dominert_gir_klart_hoyere_toast_brod_maltfylde_enn_pilsner(self):
        munich_vienna = [
            {"navn": "Munich I", "mengde": 0.70},
            {"navn": "Munich II", "mengde": 4.60},
            {"navn": "Vienna Malt", "mengde": 1.80},
        ]
        pilsner = [
            {"navn": "Pilsner Malt", "mengde": 7.10},
        ]
        p_mv = _smak(munich_vienna)
        p_pils = _smak(pilsner)

        for kat in ("Toast", "Brød", "Maltfylde"):
            self.assertGreater(
                p_mv[kat], p_pils[kat] + 0.5,
                f"{kat}: Munich/Vienna ({p_mv[kat]:.2f}) skal klart overstige "
                f"pilsnermalt ({p_pils[kat]:.2f})",
            )

        # Regresjon for selve den rapporterte bugen: Toast skal ikke lenger
        # kollapse til et lite Vienna-only-bidrag når Munich II dominerer.
        self.assertGreater(p_mv["Toast"], 3.0, f"Toast er fortsatt for lavt: {p_mv['Toast']:.2f}")

    def test_munich_ii_gir_sterkere_toast_enn_munich_i_ved_samme_andel(self):
        toast_ii = _smak([{"navn": "Munich II", "mengde": 5.0}])["Toast"]
        toast_i = _smak([{"navn": "Munich I", "mengde": 5.0}])["Toast"]
        self.assertGreater(toast_ii, toast_i,
                            f"Munich II ({toast_ii:.2f}) skal gi sterkere toast enn Munich I ({toast_i:.2f})")

    def test_tradisjonelle_basemalter_gir_ikke_urimelig_karamell_eller_rostet_preg(self):
        p = _smak([
            {"navn": "Munich I", "mengde": 0.70},
            {"navn": "Munich II", "mengde": 4.60},
            {"navn": "Vienna Malt", "mengde": 1.80},
        ])
        for kat in ("Karamell", "Kaffe", "Sjokolade", "Røyk"):
            self.assertEqual(
                p.get(kat, 0.0), 0.0,
                f"Munich/Vienna-basemalt skal ikke gi {kat}-preg, fikk {p.get(kat)}",
            )

    def test_vienna_alene_gir_lettere_toast_enn_munich_ii_alene(self):
        toast_vienna = _smak([{"navn": "Vienna Malt", "mengde": 5.0}])["Toast"]
        toast_munich_ii = _smak([{"navn": "Munich II", "mengde": 5.0}])["Toast"]
        self.assertLess(toast_vienna, toast_munich_ii)

    def test_bidrag_skalerer_med_maltandelen(self):
        # Dobbel andel Munich II (resten pilsnermalt) skal gi mer Toast enn
        # en liten andel — bidraget skal altså faktisk følge maltandelen,
        # ikke være en fast konstant.
        liten_andel = _smak([
            {"navn": "Munich II", "mengde": 0.5},
            {"navn": "Pilsner Malt", "mengde": 6.5},
        ])["Toast"]
        stor_andel = _smak([
            {"navn": "Munich II", "mengde": 5.5},
            {"navn": "Pilsner Malt", "mengde": 1.5},
        ])["Toast"]
        self.assertGreater(stor_andel, liten_andel)


if __name__ == "__main__":
    unittest.main()
