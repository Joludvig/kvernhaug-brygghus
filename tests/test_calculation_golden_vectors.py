"""
Kvernhaug Core -- PRI 1: golden cross-runtime calculation tests
(Python-siden).

Leser den teknologiuavhengige, Core-eide fixturen
core/calculation_golden_vectors.json og kjører hver vector gjennom
DAGENS produksjonsimplementasjon i modules/calculations.py -- IKKE en
kopi av formlene. Testen adapterer kun canonical inputs/expected
(feltnavn/enheter) til de faktiske Python-funksjonssignaturene og
sammenligner rå returverdi mot `expected` innenfor `tolerance`.

Samme fixture kjøres uavhengig gjennom web/js/calc.js (JavaScript-
siden) -- se docs/development/CORE_CALCULATION_CONTRACT.md.

Kjøres med:
    py -3 -m unittest tests.test_calculation_golden_vectors
    py -3 -m unittest discover -s tests
"""
import io
import json
import os
import unittest

from modules.calculations import (
    beregn_og,
    beregn_ebc,
    beregn_fg_og_abv,
    beregn_total_ibu,
    beregn_gram_fra_ibu,
)

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_VECTORS_PATH = os.path.join(_ROOT, "core", "calculation_golden_vectors.json")


def _last_golden_vectors():
    with io.open(_VECTORS_PATH, encoding="utf-8") as f:
        return json.load(f)


# --- Adaptere: canonical vector-inputs -> faktiske funksjonsargumenter ----
# Reshaper KUN felt/enheter -- ingen beregning gjøres her.

def _kjor_og(inputs):
    malt_liste = [{"navn": f"malt_{i}", "mengde": m["amount_kg"]} for i, m in enumerate(inputs["malts"])]
    malt_data = {f"malt_{i}": {"potensiale": m["potential_sg"]} for i, m in enumerate(inputs["malts"])}
    return {"og_sg": beregn_og(malt_liste, malt_data, inputs["batch_volume_l"], inputs["efficiency_fraction"])}


def _kjor_fg_abv(inputs):
    fg, abv = beregn_fg_og_abv(inputs["og_sg"], inputs["attenuation_fraction"])
    return {"fg_sg": fg, "abv_percent": abv}


def _kjor_ebc(inputs):
    malt_liste = [{"navn": f"malt_{i}", "mengde": m["amount_kg"]} for i, m in enumerate(inputs["malts"])]
    malt_data = {f"malt_{i}": {"ebc": m["ebc"]} for i, m in enumerate(inputs["malts"])}
    return {"ebc": beregn_ebc(malt_liste, malt_data, inputs["batch_volume_l"])}


def _kjor_tinseth_ibu(inputs):
    humle_liste = [
        {"navn": f"hop_{i}", "gram": h["amount_g"], "tid": h["boil_time_min"]}
        for i, h in enumerate(inputs["hops"])
    ]
    humle_data = {f"hop_{i}": {"alfa": h["alpha_acid_percent"]} for i, h in enumerate(inputs["hops"])}
    return {"ibu": beregn_total_ibu(humle_liste, humle_data, inputs["batch_volume_l"], inputs["wort_gravity_sg"])}


def _kjor_invers_tinseth(inputs):
    gram = beregn_gram_fra_ibu(
        inputs["target_ibu"],
        inputs["alpha_acid_percent"],
        inputs["boil_time_min"],
        inputs["batch_volume_l"],
        inputs["wort_gravity_sg"],
    )
    return {"hop_amount_g": gram}


_ADAPTERE = {
    "og": _kjor_og,
    "fg_abv": _kjor_fg_abv,
    "ebc_morey": _kjor_ebc,
    "tinseth_ibu": _kjor_tinseth_ibu,
    "inverse_tinseth": _kjor_invers_tinseth,
}


class TestGoldenVectorsFixtureParserOgStruktur(unittest.TestCase):

    def test_fixture_parser_som_gyldig_json(self):
        data = _last_golden_vectors()
        self.assertIsInstance(data, dict)
        self.assertIn("cases", data)
        self.assertGreater(len(data["cases"]), 0)

    def test_alle_seks_scope_beregninger_dekket(self):
        data = _last_golden_vectors()
        dekket = {c["calculation"] for c in data["cases"]}
        # "fg" og "abv" er én delt Core-beregning (fg_abv) -- se
        # calculation_golden_vectors.json sin tolerance_principle.
        self.assertEqual(dekket, {"og", "fg_abv", "ebc_morey", "tinseth_ibu", "inverse_tinseth"})

    def test_alle_cases_har_unik_id(self):
        data = _last_golden_vectors()
        ider = [c["id"] for c in data["cases"]]
        self.assertEqual(len(ider), len(set(ider)))

    def test_alle_cases_har_pakrevde_felt(self):
        data = _last_golden_vectors()
        for case in data["cases"]:
            with self.subTest(id=case["id"]):
                for felt in ("id", "calculation", "description", "inputs", "expected", "tolerance"):
                    self.assertIn(felt, case)


class TestGoldenVectorsMotProduksjonsimplementasjon(unittest.TestCase):
    """Kjører hver golden vector gjennom DAGENS modules/calculations.py
    -- ingen formel kopiert inn her, kun input/output-adaptering."""

    def test_alle_golden_vectors_matcher_python_produksjon(self):
        data = _last_golden_vectors()
        for case in data["cases"]:
            with self.subTest(id=case["id"], calculation=case["calculation"]):
                adapter = _ADAPTERE[case["calculation"]]
                faktisk = adapter(case["inputs"])
                for felt, forventet_verdi in case["expected"].items():
                    self.assertAlmostEqual(
                        faktisk[felt], forventet_verdi,
                        delta=case["tolerance"],
                        msg=(
                            f"{case['id']} ({case['calculation']}.{felt}): "
                            f"fikk {faktisk[felt]!r}, forventet {forventet_verdi!r} "
                            f"innen {case['tolerance']!r}"
                        ),
                    )


if __name__ == "__main__":
    unittest.main()
