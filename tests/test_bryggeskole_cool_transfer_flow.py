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
        # oxygen_post is intentionally excluded here: it is long enough to
        # wrap onto multiple <tspan> lines (see the dedicated long-label
        # layout tests below), so it is no longer guaranteed to appear as
        # one contiguous substring. Its full message is instead verified,
        # reconstructed from its wrapped lines, by
        # test_oxygen_post_wrapped_lines_reconstruct_the_original_message.
        svg = render_cool_transfer_flow_svg("no")
        for expected in (
            "Kjele (etter koking)", "Kjøling", "Overføring", "Gjæringskar",
            "Sanitert håndteringssone", "Tyngdekraft", "Pumpe",
            "Oksygenering kan være nyttig før pitching",
        ):
            self.assertIn(expected, svg)

    def test_english_labels_present(self):
        # See the note on test_norwegian_labels_present: oxygen_post is
        # verified separately because it wraps onto multiple lines.
        svg = render_cool_transfer_flow_svg("en")
        for expected in (
            "Kettle (post-boil)", "Cooling", "Transfer", "Fermenter",
            "Sanitized handling zone", "Gravity", "Pump",
            "Aeration can help before pitching",
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


# ─── Long oxygen-label layout (Chief review, issue #370) ──────────────────
#
# The old x-anchor-only assertion above (test_stages_stay_inside_viewbox)
# proves nothing about a long label's actual rendered width -- a
# text-anchor="middle" label can have a perfectly in-bounds anchor while
# its text still overflows past the viewBox edge. These tests instead
# check the real layout invariant: every individual text line's
# *estimated bounding box* stays inside the viewBox, using a simple,
# deterministic stdlib character-count heuristic (no browser/font
# measurement, no new dependency, per the review's own constraint).
#
# The width estimate used here (_CHAR_WIDTH_FACTOR) is deliberately WIDER
# than the module's own internal wrapping estimate
# (bryggeskole.cool_transfer_flow._AVG_CHAR_WIDTH_FACTOR), so this is an
# independent, stricter re-check of the invariant rather than a
# re-derivation of the production code's own math.
_CHAR_WIDTH_FACTOR = 0.65

_OXYGEN_POST_MESSAGE = {
    "no": "Unngå unødvendig oksygen etter aktiv gjæring",
    "en": "Avoid unnecessary oxygen once fermentation is active",
}
_OXYGEN_PRE_MESSAGE = {
    "no": "Oksygenering kan være nyttig før pitching - behov avhenger av gjær",
    "en": "Aeration can help before pitching - need depends on the yeast",
}


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


def _last_text_block(svg):
    blocks = re.findall(r"<text[^>]*>.*?</text>", svg, re.DOTALL)
    return blocks[-1]


class TestLongOxygenLabelLayoutStaysInsideViewbox(unittest.TestCase):
    VIEWBOX_WIDTH = 840
    VIEWBOX_HEIGHT = 260

    def test_every_text_lines_estimated_width_fits_inside_viewbox(self):
        for lang in ("no", "en"):
            svg = render_cool_transfer_flow_svg(lang)
            nodes = _leaf_text_nodes(svg)
            self.assertGreater(len(nodes), 0, f"{lang}: no text nodes found to check")
            for x, y, text, font_size in nodes:
                text = text.strip()
                if not text:
                    continue
                estimated_half_width = (len(text) * font_size * _CHAR_WIDTH_FACTOR) / 2
                self.assertGreaterEqual(
                    x - estimated_half_width, 0,
                    f"{lang}: line {text!r} at x={x} would clip the left viewBox edge",
                )
                self.assertLessEqual(
                    x + estimated_half_width, self.VIEWBOX_WIDTH,
                    f"{lang}: line {text!r} at x={x} would clip the right viewBox edge (width={self.VIEWBOX_WIDTH})",
                )
                self.assertLessEqual(
                    y, self.VIEWBOX_HEIGHT,
                    f"{lang}: line {text!r} at y={y} would clip the bottom viewBox edge",
                )

    def test_oxygen_post_label_wraps_onto_multiple_tspan_lines(self):
        # This is the label the Chief review named as overflowing
        # (English: "Avoid unnecessary oxygen once fermentation is
        # active"), so this test proves wrapping actually happens rather
        # than the fix being a silent no-op.
        for lang in ("no", "en"):
            svg = render_cool_transfer_flow_svg(lang)
            block = _last_text_block(svg)
            tspans = re.findall(r"<tspan[^>]*>([^<]*)</tspan>", block)
            self.assertGreaterEqual(
                len(tspans), 2,
                f"{lang}: expected the long oxygen_post label to wrap onto >=2 tspan lines, got block: {block}",
            )

    def test_oxygen_post_wrapped_lines_reconstruct_the_original_message(self):
        # Proves "samme NO/EN-budskap": wrapping must never drop or
        # reorder words, only add line breaks.
        for lang, expected_message in _OXYGEN_POST_MESSAGE.items():
            svg = render_cool_transfer_flow_svg(lang)
            block = _last_text_block(svg)
            lines = re.findall(r"<tspan[^>]*>([^<]*)</tspan>", block)
            self.assertTrue(lines, f"{lang}: expected wrapped tspan lines in {block!r}")
            reconstructed = " ".join(line.strip() for line in lines)
            self.assertEqual(reconstructed, expected_message)

    def test_oxygen_pre_label_has_generous_margin_and_stays_single_line(self):
        # oxygen_pre is anchored at the horizontal center of the viewBox
        # (symmetric ~400px margin on both sides), so it is not expected
        # to need wrapping even though it is also a long label -- this
        # documents that expectation so a future geometry change that
        # breaks it is caught here rather than only visually.
        for lang, expected_message in _OXYGEN_PRE_MESSAGE.items():
            svg = render_cool_transfer_flow_svg(lang)
            self.assertIn(f">{expected_message}</text>", svg)


if __name__ == "__main__":
    unittest.main()
