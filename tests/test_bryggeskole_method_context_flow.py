"""
Tests for bryggeskole/method_context_flow.py -- the static method-context
flow visual (issue #380, V2.2 G3I).

Run with:
    python3 -m unittest tests.test_bryggeskole_method_context_flow
"""
import re
import unittest

from bryggeskole.method_context_flow import render_method_context_flow_svg


class TestRenderMethodContextFlowSvg(unittest.TestCase):
    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_method_context_flow_svg("de")

    def test_returns_well_formed_svg_markup(self):
        svg = render_method_context_flow_svg("no")
        self.assertTrue(svg.strip().startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))

    def test_is_responsive_and_preserves_viewbox(self):
        svg = render_method_context_flow_svg("en")
        self.assertIn('viewBox="0 0 1000 430"', svg)
        self.assertIn('width="100%"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn("max-width:1000px", svg)

    def test_no_interactivity_anywhere(self):
        for lang in ("no", "en"):
            svg = render_method_context_flow_svg(lang)
            self.assertNotIn("<a ", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("onclick", svg)
            self.assertNotIn("href=", svg)

    def test_no_numeric_water_or_efficiency_scale(self):
        # width="100%" is the responsive-sizing attribute every visual in
        # this module family carries -- not a numeric efficiency/water
        # percentage, so it is deliberately excluded from the banned check.
        for lang in ("no", "en"):
            svg = render_method_context_flow_svg(lang).lower()
            for banned in ("liter", "efficiency", "effektivitet"):
                self.assertNotIn(banned, svg)
            self.assertNotRegex(svg, r"\d+\s*%(?!\")")
            self.assertNotRegex(svg, r"\d+\s*l\b")

    def test_norwegian_labels_present(self):
        svg = render_method_context_flow_svg("no")
        for expected in (
            "BIAB", "Tradisjonelt alt-korn", "Alt-i-ett",
            "Kjele + pose (meskepose/BIAB)", "Meskekar/lauterkar", "Kjele",
            "Integrert kar + kurv/malt-rør",
        ):
            self.assertIn(expected, svg)

    def test_english_labels_present(self):
        svg = render_method_context_flow_svg("en")
        for expected in (
            "BIAB", "Traditional all-grain", "All-in-one",
            "Kettle + bag (mash bag/BIAB)", "Mash/lauter vessel", "Kettle",
            "Integrated vessel + basket/malt pipe",
        ):
            self.assertIn(expected, svg)

    def test_shared_downstream_spine_drawn_identically_in_all_three_rows(self):
        # §4 of the module contract: the Kok/Kjøl/Gjær/Pakk sequence is
        # drawn identically in each of the three rows -- so each stage
        # label must appear exactly three times (once per row).
        svg = render_method_context_flow_svg("no")
        for stage in ("Kok", "Kjøl", "Gjær", "Pakk"):
            self.assertEqual(svg.count(f">{stage}<"), 3, f"expected {stage!r} drawn once per row")

    def test_biab_and_all_in_one_zones_share_the_same_box_size_as_traditionals_combined_zone(self):
        # Equal visual weight: BIAB/all-in-one draw ONE box spanning the
        # full "mesk -> skille" zone width; traditional draws TWO boxes of
        # half that width each -- both add up to the identical total zone
        # width, so the shared downstream boxes line up across all rows.
        svg = render_method_context_flow_svg("en")
        self.assertEqual(svg.count('width="280"'), 2, "expected exactly two full-zone (BIAB + all-in-one) boxes")
        self.assertGreaterEqual(svg.count('width="130"'), 2 + 3 * 4, "traditional's two boxes plus 4 stage boxes x 3 rows")

    def test_no_hierarchy_caption_present(self):
        for lang, expected in (
            ("no", "Ingen av metodene er «riktigere» - alle fullfører samme prosess"),
            ("en", 'No method is "more correct" - all complete the same process'),
        ):
            svg = render_method_context_flow_svg(lang)
            self.assertIn(expected, svg)

    def test_no_specific_brand_or_model_named(self):
        svg = render_method_context_flow_svg("en")
        for banned in ("Grainfather", "Blichmann", "SS Brewtech", "BrewZilla", "Anvil"):
            self.assertNotIn(banned, svg)

    def test_process_direction_arrows_present(self):
        svg = render_method_context_flow_svg("en")
        self.assertIn("mcf-arrow", svg)
        self.assertIn("marker-end", svg)

    def test_no_streamlit_import(self):
        import bryggeskole.method_context_flow as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("import streamlit", source.lower())


# ─── Layout: every text node's estimated bounding box stays inside the
# viewBox (mirrors tests/test_bryggeskole_package_flow.py's own
# independent re-check of the module's internal wrapping invariant). ──────

_CHAR_WIDTH_FACTOR = 0.65


def _leaf_text_nodes(svg):
    """Returns (x, y, text, font_size) for every leaf SVG text node in
    `svg` -- both single-line <text> elements with direct content, and
    each <tspan> child of a wrapped multi-line <text> element."""
    nodes = []
    for match in re.finditer(r"<text([^>]*)>(.*?)</text>", svg, re.DOTALL):
        attrs, body = match.groups()
        font_size = float(re.search(r'font-size="([\d.]+)"', attrs).group(1))
        tspans = re.findall(r'<tspan x="(-?[\d.]+)" y="(-?[\d.]+)">([^<]*)</tspan>', body)
        if tspans:
            for x, y, text in tspans:
                nodes.append((float(x), float(y), text, font_size))
            continue
        x_match = re.search(r'x="(-?[\d.]+)"', attrs)
        y_match = re.search(r'y="(-?[\d.]+)"', attrs)
        if x_match and y_match and body.strip():
            nodes.append((float(x_match.group(1)), float(y_match.group(1)), body, font_size))
    return nodes


class TestLongLabelLayoutStaysInsideViewbox(unittest.TestCase):
    VIEWBOX_WIDTH = 1000
    VIEWBOX_HEIGHT = 430

    def test_every_text_lines_estimated_width_fits_inside_viewbox(self):
        for lang in ("no", "en"):
            svg = render_method_context_flow_svg(lang)
            nodes = _leaf_text_nodes(svg)
            self.assertGreater(len(nodes), 0, f"{lang}: no text nodes found to check")
            for x, y, text, font_size in nodes:
                text = text.strip()
                if not text:
                    continue
                estimated_half_width = (len(text) * font_size * _CHAR_WIDTH_FACTOR) / 2
                self.assertGreaterEqual(
                    x - estimated_half_width, -1,
                    f"{lang}: line {text!r} at x={x} would clip the left viewBox edge",
                )
                self.assertLessEqual(
                    x + estimated_half_width, self.VIEWBOX_WIDTH + 1,
                    f"{lang}: line {text!r} at x={x} would clip the right viewBox edge (width={self.VIEWBOX_WIDTH})",
                )
                self.assertLessEqual(
                    y, self.VIEWBOX_HEIGHT,
                    f"{lang}: line {text!r} at y={y} would clip the bottom viewBox edge",
                )

    def test_stages_stay_inside_viewbox(self):
        svg = render_method_context_flow_svg("en")
        matches = re.findall(r'x="(-?\d+(?:\.\d+)?)"', svg)
        for value in matches:
            self.assertGreaterEqual(float(value), 0)
            self.assertLessEqual(float(value), 1000)


if __name__ == "__main__":
    unittest.main()
