"""
Tests for bryggeskole/boil_timeline.py -- the static boil/hop timeline
visual (issue #366, V2.2 G3C).

Run with:
    python3 -m unittest tests.test_bryggeskole_boil_timeline
"""
import re
import unittest

from bryggeskole.boil_timeline import render_boil_timeline_svg


class TestRenderBoilTimelineSvg(unittest.TestCase):
    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_boil_timeline_svg("de")

    def test_returns_well_formed_svg_markup(self):
        svg = render_boil_timeline_svg("no")
        self.assertTrue(svg.strip().startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))

    def test_is_responsive_and_preserves_viewbox(self):
        svg = render_boil_timeline_svg("en")
        self.assertIn('viewBox="0 0 820 220"', svg)
        self.assertIn('width="100%"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn("max-width:820px", svg)

    def test_no_interactivity_anywhere(self):
        for lang in ("no", "en"):
            svg = render_boil_timeline_svg(lang)
            self.assertNotIn("<a ", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("onclick", svg)
            self.assertNotIn("href=", svg)

    def test_no_numeric_ibu_or_fixed_duration_scale(self):
        for lang in ("no", "en"):
            svg = render_boil_timeline_svg(lang).lower()
            self.assertIsNone(re.search(r"\\bibu\\b", svg))
            self.assertNotIn("60 min", svg)
            self.assertNotIn("5 min", svg)

    def test_norwegian_labels_present(self):
        svg = render_boil_timeline_svg("no")
        for expected in (
            "Kokestart", "Kokeslutt", "Hot break", "Tidlig humletilsetning",
            "Sen humletilsetning", "Flameout", "Whirlpool",
            "Mer bitterhetsbidrag", "Mer aromabevaring",
        ):
            self.assertIn(expected, svg)

    def test_english_labels_present(self):
        svg = render_boil_timeline_svg("en")
        for expected in (
            "Boil start", "Boil end", "Hot break", "Early hop addition",
            "Late hop addition", "Flameout", "Whirlpool",
            "More bitterness contribution", "More aroma retention",
        ):
            self.assertIn(expected, svg)

    def test_whirlpool_zone_is_visually_distinct_from_boil_zone(self):
        svg = render_boil_timeline_svg("en")
        self.assertIn("whirlpool-hatch", svg)
        self.assertIn("stroke-dasharray", svg)

    def test_hot_break_zone_present_near_boil_start(self):
        svg = render_boil_timeline_svg("en")
        self.assertIn("Hot break", svg)

    def test_directional_cues_stay_inside_viewbox(self):
        # The two teaching cues must be visible, not merely present as
        # clipped strings outside the 0..820 viewBox.
        svg = render_boil_timeline_svg("en")
        self.assertIn('x1="330" y1="50" x2="180" y2="50"', svg)
        self.assertIn('x="255" y="42" text-anchor="middle"', svg)
        self.assertIn('x1="490" y1="50" x2="640" y2="50"', svg)
        self.assertIn('x="565" y="42" text-anchor="middle"', svg)
        self.assertIn("arrow-left", svg)
        self.assertIn("arrow-right", svg)

    def test_no_streamlit_import(self):
        import bryggeskole.boil_timeline as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("import streamlit", source.lower())


if __name__ == "__main__":
    unittest.main()
