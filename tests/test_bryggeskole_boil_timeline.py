"""
Tests for bryggeskole/boil_timeline.py -- the static boil/hop timeline
visual (issue #366, V2.2 G3C).

Run with:
    python3 -m unittest tests.test_bryggeskole_boil_timeline
"""
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

    def test_no_interactivity_anywhere(self):
        for lang in ("no", "en"):
            svg = render_boil_timeline_svg(lang)
            self.assertNotIn("<a ", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("onclick", svg)
            self.assertNotIn("href=", svg)

    def test_no_numeric_ibu_scale_or_axis(self):
        for lang in ("no", "en"):
            svg = render_boil_timeline_svg(lang).lower()
            self.assertNotIn("ibu", svg)

    def test_norwegian_labels_present(self):
        svg = render_boil_timeline_svg("no")
        for expected in (
            "Kokestart", "Kokeslutt", "Hot break", "60 min igjen",
            "5 min igjen", "Flameout", "Whirlpool", "Økende bitterhet", "Økende aroma",
        ):
            self.assertIn(expected, svg)

    def test_english_labels_present(self):
        svg = render_boil_timeline_svg("en")
        for expected in (
            "Boil start", "Boil end", "Hot break", "60 min remaining",
            "5 min remaining", "Flameout", "Whirlpool", "Increasing bitterness",
            "Increasing aroma retention",
        ):
            self.assertIn(expected, svg)

    def test_whirlpool_zone_is_visually_distinct_from_boil_zone(self):
        # Different fill (pattern vs. solid color) and a dashed border --
        # the contract's explicit "visually distinct... different
        # shading/pattern" requirement for the whirlpool/hop-stand zone.
        svg = render_boil_timeline_svg("en")
        self.assertIn("whirlpool-hatch", svg)
        self.assertIn("stroke-dasharray", svg)

    def test_hot_break_zone_present_near_boil_start(self):
        svg = render_boil_timeline_svg("en")
        self.assertIn("Hot break", svg)

    def test_two_opposing_directional_cues_present(self):
        # Bitterness cue points one way, aroma cue points the other --
        # verified here by the presence of both distinct arrow markers.
        svg = render_boil_timeline_svg("en")
        self.assertIn("arrow-left", svg)
        self.assertIn("arrow-right", svg)

    def test_no_streamlit_import(self):
        import bryggeskole.boil_timeline as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("import streamlit", source.lower())


if __name__ == "__main__":
    unittest.main()
