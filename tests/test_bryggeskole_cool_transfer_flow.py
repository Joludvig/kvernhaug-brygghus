"""
Tests for bryggeskole/cool_transfer_flow.py -- the static cool/transfer
flow visual (issue #370, V2.2 G3E).

Run with:
    python3 -m unittest tests.test_bryggeskole_cool_transfer_flow
"""
import re
import unittest

from bryggeskole.cool_transfer_flow import render_cool_transfer_flow_svg


class TestRenderCoolTransferFlowSvg(unittest.TestCase):
    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_cool_transfer_flow_svg("de")

    def test_returns_well_formed_svg_markup(self):
        svg = render_cool_transfer_flow_svg("no")
        self.assertTrue(svg.strip().startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))

    def test_is_responsive_and_preserves_viewbox(self):
        svg = render_cool_transfer_flow_svg("en")
        self.assertIn('viewBox="0 0 840 260"', svg)
        self.assertIn('width="100%"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn("max-width:840px", svg)

    def test_no_interactivity_anywhere(self):
        for lang in ("no", "en"):
            svg = render_cool_transfer_flow_svg(lang)
            self.assertNotIn("<a ", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("onclick", svg)
            self.assertNotIn("href=", svg)

    def test_no_numeric_dissolved_oxygen_or_temperature_scale(self):
        for lang in ("no", "en"):
            svg = render_cool_transfer_flow_svg(lang).lower()
            self.assertNotIn("ppm", svg)
            self.assertNotIn("mg/l", svg)
            self.assertNotIn("°c", svg)
            self.assertNotIn(" c ", svg)

    def test_norwegian_labels_present(self):
        svg = render_cool_transfer_flow_svg("no")
        for expected in (
            "Kjele (etter koking)", "Kjøling", "Overføring", "Gjæringskar",
            "Sanitert håndteringssone", "Tyngdekraft", "Pumpe",
            "Oksygenering kan være nyttig før pitching",
            "Unngå unødvendig oksygen etter aktiv gjæring",
        ):
            self.assertIn(expected, svg)

    def test_english_labels_present(self):
        svg = render_cool_transfer_flow_svg("en")
        for expected in (
            "Kettle (post-boil)", "Cooling", "Transfer", "Fermenter",
            "Sanitized handling zone", "Gravity", "Pump",
            "Aeration can help before pitching",
            "Avoid unnecessary oxygen once fermentation is active",
        ):
            self.assertIn(expected, svg)

    def test_sanitized_zone_is_visually_distinct_shaded_region(self):
        svg = render_cool_transfer_flow_svg("en")
        self.assertIn("stroke-dasharray", svg)
        self.assertIn("Sanitized handling zone", svg)

    def test_two_transfer_path_variants_present_without_brand_or_model(self):
        svg = render_cool_transfer_flow_svg("en")
        self.assertIn("Gravity", svg)
        self.assertIn("Pump", svg)
        for banned in ("Blichmann", "MoreBeer", "March pump", "Chugger"):
            self.assertNotIn(banned, svg)

    def test_process_direction_arrows_present(self):
        svg = render_cool_transfer_flow_svg("en")
        self.assertIn("ctf-arrow", svg)
        self.assertIn("marker-end", svg)

    def test_stages_stay_inside_viewbox(self):
        svg = render_cool_transfer_flow_svg("en")
        matches = re.findall(r'x="(-?\d+(?:\.\d+)?)"', svg)
        for value in matches:
            self.assertGreaterEqual(float(value), 0)
            self.assertLessEqual(float(value), 840)

    def test_no_streamlit_import(self):
        import bryggeskole.cool_transfer_flow as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("import streamlit", source.lower())


if __name__ == "__main__":
    unittest.main()
