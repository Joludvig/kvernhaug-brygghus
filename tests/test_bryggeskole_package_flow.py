"""
Tests for bryggeskole/package_flow.py -- the static package flow visual
(issue #374, V2.2 G3G).

Owner-QA correction (issue #397 follow-up, see the module's own
docstring): several labels now conditionally wrap onto multiple <tspan>
lines via the new box-width-aware `_box_label_markup` (fermenter,
bottle_transfer, bottle_step, keg_transfer, keg_step, serve_store) --
`_visible_text()` below reconstructs a whitespace-joined blob of every
text/tspan node's content so label-presence assertions keep matching a
label regardless of whether it happened to wrap for a given language.

Run with:
    python3 -m unittest tests.test_bryggeskole_package_flow
"""
import re
import unittest

from bryggeskole.package_flow import render_package_flow_svg


def _visible_text(svg):
    parts = []
    for match in re.finditer(r"<text[^>]*>(.*?)</text>", svg, re.DOTALL):
        body = match.group(1)
        tspans = re.findall(r"<tspan[^>]*>([^<]*)</tspan>", body)
        parts.append(" ".join(tspans) if tspans else body)
    return re.sub(r"\s+", " ", " ".join(parts))


class TestRenderPackageFlowSvg(unittest.TestCase):
    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_package_flow_svg("de")

    def test_returns_well_formed_svg_markup(self):
        svg = render_package_flow_svg("no")
        self.assertTrue(svg.strip().startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))

    def test_is_responsive_and_preserves_viewbox(self):
        svg = render_package_flow_svg("en")
        self.assertIn('viewBox="0 0 1145 360"', svg)
        self.assertIn('width="100%"', svg)
        self.assertIn('preserveAspectRatio="xMidYMid meet"', svg)
        self.assertIn("max-width:1145px", svg)

    def test_minimum_legible_font_size_and_contrast_background(self):
        # Issue #397: labels must not regress back to the pre-fix 9-11px
        # sizing, and the diagram must carry its own explicit opaque
        # background so the light-backdrop-tuned palette has guaranteed
        # contrast regardless of Streamlit's active theme. Owner-QA
        # follow-up: only the background rect HEIGHT shrank (bulkiness
        # fix); width and font floor are unchanged from #397.
        svg = render_package_flow_svg("en")
        for font_size in re.findall(r'font-size="([\d.]+)"', svg):
            self.assertGreaterEqual(float(font_size), 13)
        self.assertIn('<rect x="0" y="0" width="1145" height="360"', svg)

    def test_no_interactivity_anywhere(self):
        for lang in ("no", "en"):
            svg = render_package_flow_svg(lang)
            self.assertNotIn("<a ", svg)
            self.assertNotIn("<script", svg)
            self.assertNotIn("onclick", svg)
            self.assertNotIn("href=", svg)

    def test_no_numeric_carbonation_or_pressure_scale(self):
        for lang in ("no", "en"):
            svg = render_package_flow_svg(lang).lower()
            for banned in ("ppm", "co2 vol", "vol co2"):
                self.assertNotIn(banned, svg)
            self.assertNotRegex(svg, r"\d+\s*bar\b")
            self.assertNotRegex(svg, r"\bpsi\b")

    def test_norwegian_labels_present(self):
        # Reconstructed via _visible_text(): some of these now
        # conditionally wrap onto multiple <tspan> lines
        # (_box_label_markup, issue #397 follow-up), so a raw substring
        # check on the SVG source is no longer reliable for all of them.
        svg = render_package_flow_svg("no")
        tekst = _visible_text(svg)
        for expected in (
            "Gjæringskar (ferdig gjæret)", "Sanitert håndteringssone",
            "Flaske-sti", "Fat-sti", "Tappestav / overføring",
            "Flaske + primesukker", "Fat + ekstern CO2",
        ):
            self.assertIn(expected, tekst)

    def test_english_labels_present(self):
        svg = render_package_flow_svg("en")
        tekst = _visible_text(svg)
        for expected in (
            "Fermenter (done fermenting)", "Sanitized handling zone",
            "Bottle path", "Keg path", "Bottling wand / transfer",
            "Bottle + priming sugar", "Keg + external CO2",
        ):
            self.assertIn(expected, tekst)

    def test_both_paths_reconverge_at_shared_serve_store_node(self):
        for lang, expected in (("no", "Klar til servering/lagring"), ("en", "Ready to serve/store")):
            svg = render_package_flow_svg(lang)
            tekst = _visible_text(svg)
            self.assertIn(expected, tekst)
            # Exactly one serve/store node -- both paths reconverge at the
            # SAME shared end point, not two separate end states.
            self.assertEqual(tekst.count(expected), 1)

    def test_sanitized_zone_is_visually_distinct_shaded_region(self):
        svg = render_package_flow_svg("en")
        self.assertIn("stroke-dasharray", svg)
        self.assertIn("Sanitized handling zone", svg)

    def test_two_packaging_paths_present_without_brand_or_model(self):
        svg = render_package_flow_svg("en")
        self.assertIn("Bottle path", svg)
        self.assertIn("Keg path", svg)
        for banned in ("Cornelius", "Corny", "SS Brewtech", "Grainfather", "Blichmann"):
            self.assertNotIn(banned, svg)

    def test_process_direction_arrows_present(self):
        svg = render_package_flow_svg("en")
        self.assertIn("pkf-arrow", svg)
        self.assertIn("marker-end", svg)

    def test_oxygen_and_pressure_labels_present(self):
        svg = render_package_flow_svg("en")
        self.assertIn("Avoid unnecessary oxygen during transfer", svg)
        self.assertIn("Use pressure-suitable equipment", svg)

    def test_no_streamlit_import(self):
        import bryggeskole.package_flow as module
        with open(module.__file__, encoding="utf-8") as fh:
            source = fh.read()
        self.assertNotIn("import streamlit", source.lower())


# ─── Layout: every text node's estimated bounding box stays inside the
# viewBox (mirrors tests/test_bryggeskole_cool_transfer_flow.py's own
# stricter, independent re-check of the module's internal wrapping
# invariant -- issue #370 Chief review, applied proactively here since
# this module shares the same wrapping helper). ────────────────────────

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
    VIEWBOX_WIDTH = 1145
    VIEWBOX_HEIGHT = 360

    def test_every_text_lines_estimated_width_fits_inside_viewbox(self):
        for lang in ("no", "en"):
            svg = render_package_flow_svg(lang)
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
        svg = render_package_flow_svg("en")
        matches = re.findall(r'x="(-?\d+(?:\.\d+)?)"', svg)
        for value in matches:
            self.assertGreaterEqual(float(value), 0)
            self.assertLessEqual(float(value), 1145)


# ─── Owner-QA correction (issue #397 follow-up): every box-contained
# label's estimated rendered width must stay inside its OWN box, not just
# somewhere inside the overall viewBox -- this is the actual defect an
# owner-PC screenshot reported ("noe tekst er skjult/klippet/obscured").
# `TestLongLabelLayoutStaysInsideViewbox` above only ever proved the much
# weaker "fits somewhere in the whole diagram" property. ──────────────────

# (x0, x1) for every box a label is drawn inside, matching the geometry
# render_package_flow_svg() itself computes (path_x0=390, box_w=195,
# gap=52, fermenter/serve widths unchanged from #397).
_BOX_X_RANGES = {
    "fermenter": (50, 285),
    "bottle_transfer": (390, 585),
    "bottle_step": (637, 832),
    "keg_transfer": (390, 585),
    "keg_step": (637, 832),
    "serve_store": (885, 1090),
}


class TestBoxLabelsNeverClipTheirOwnBox(unittest.TestCase):
    def test_every_box_label_line_fits_inside_its_own_box(self):
        for lang in ("no", "en"):
            svg = render_package_flow_svg(lang)
            nodes = _leaf_text_nodes(svg)
            by_x = {}
            for x, y, text, font_size in nodes:
                by_x.setdefault(round(x, 1), []).append((y, text.strip(), font_size))
            for label_name, (box_x0, box_x1) in _BOX_X_RANGES.items():
                box_cx = round((box_x0 + box_x1) / 2, 1)
                matches = by_x.get(box_cx)
                self.assertTrue(
                    matches, f"{lang}: expected a text node centered at x={box_cx} for {label_name!r}",
                )
                for y, text, font_size in matches:
                    if not text:
                        continue
                    estimated_half_width = (len(text) * font_size * _CHAR_WIDTH_FACTOR) / 2
                    self.assertGreaterEqual(
                        box_cx - estimated_half_width, box_x0,
                        f"{lang}: {label_name} line {text!r} would spill past its own box's LEFT edge "
                        f"(box=[{box_x0},{box_x1}])",
                    )
                    self.assertLessEqual(
                        box_cx + estimated_half_width, box_x1,
                        f"{lang}: {label_name} line {text!r} would spill past its own box's RIGHT edge "
                        f"(box=[{box_x0},{box_x1}])",
                    )

    def test_bottle_and_keg_rows_remain_clearly_separate_vertically(self):
        # #397 owner-QA requirement: "bottle/flaske- og fat-sti skal
        # fortsatt være tydelig separate" -- the two rows' boxes must not
        # touch or overlap after the height reduction.
        svg = render_package_flow_svg("en")
        bottle_rect = re.search(r'<rect x="390" y="(\d+)" width="195" height="(\d+)" fill="#f7d9a0"', svg)
        keg_rect = re.search(r'<rect x="390" y="(\d+)" width="195" height="(\d+)" fill="#f7d9a0"', svg[bottle_rect.end():])
        bottle_bottom = int(bottle_rect.group(1)) + int(bottle_rect.group(2))
        keg_top = int(keg_rect.group(1))
        self.assertGreater(keg_top, bottle_bottom, "bottle and keg rows must not touch/overlap")


if __name__ == "__main__":
    unittest.main()
