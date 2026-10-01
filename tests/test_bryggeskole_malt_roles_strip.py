"""
Tests for bryggeskole/malt_roles_strip.py -- the static Malt roles strip
(issue #460, V2.2 G3P-6).

Run with:
    python3 -m unittest tests.test_bryggeskole_malt_roles_strip
"""
import re
import unittest
import xml.etree.ElementTree as ET

from bryggeskole.malt_roles_strip import render_malt_roles_strip_svg
from bryggeskole.pilot_raw_materials import read_pilot_file

_VIEWBOX_WIDTH = 560


class TestRenderMaltRolesStripSvg(unittest.TestCase):
    def test_unsupported_language_raises(self):
        with self.assertRaises(ValueError):
            render_malt_roles_strip_svg("de")

    def test_well_formed_single_line_svg_with_responsive_viewbox(self):
        for lang in ("no", "en"):
            svg = render_malt_roles_strip_svg(lang)
            self.assertTrue(svg.startswith("<svg"))
            self.assertTrue(svg.endswith("</svg>"))
            self.assertNotIn("\n", svg)
            self.assertIn('viewBox="0 0 560 270"', svg)
            self.assertIn('width="100%"', svg)
            ET.fromstring(svg)

    def test_legible_font_sizes_and_opaque_background(self):
        svg = render_malt_roles_strip_svg("en")
        for font_size in re.findall(r'font-size="([\d.]+)"', svg):
            self.assertGreaterEqual(float(font_size), 14)
        self.assertIn('<rect x="0" y="0" width="560" height="270"', svg)

    def test_no_interactivity_or_animation(self):
        for lang in ("no", "en"):
            svg = render_malt_roles_strip_svg(lang)
            for forbidden in ("<a ", "<script", "onclick", "href=", "<animate", "<input"):
                self.assertNotIn(forbidden, svg)

    def test_no_numeric_values(self):
        for lang in ("no", "en"):
            root = ET.fromstring(render_malt_roles_strip_svg(lang))
            text = " ".join("".join(el.itertext()) for el in root.iter() if el.tag.endswith("text"))
            self.assertIsNone(re.search(r"\d", text))
            for forbidden in ("ebc", "lintner", "%", "dp "):
                self.assertNotIn(forbidden, text.lower())

    def test_labels_present_in_both_languages(self):
        expected = {
            "no": ("Basismalt", "Spesialmalt", "enzymer", "farge"),
            "en": ("Base malt", "Specialty malt", "enzymes", "colour"),
        }
        for lang, words in expected.items():
            svg = render_malt_roles_strip_svg(lang)
            for word in words:
                self.assertIn(word, svg)

    def test_no_and_en_are_structurally_symmetric(self):
        def structure(svg):
            return re.sub(r">[^<]*<", "><", re.sub(r'aria-label="[^"]*"', "", svg))

        no_svg = render_malt_roles_strip_svg("no")
        en_svg = render_malt_roles_strip_svg("en")
        self.assertEqual(structure(no_svg), structure(en_svg))

    def test_text_lines_fit_inside_viewbox(self):
        # Conservative width estimate (0.6 * font-size per char), as in
        # bryggeskole/cool_transfer_flow.py; centered text grows both ways.
        for lang in ("no", "en"):
            root = ET.fromstring(render_malt_roles_strip_svg(lang))
            for el in root.iter():
                if not el.tag.endswith("text"):
                    continue
                size = float(el.get("font-size"))
                tspans = [c for c in el if c.tag.endswith("tspan")]
                units = [(float(c.get("x")), "".join(c.itertext())) for c in tspans] or [
                    (float(el.get("x")), "".join(el.itertext()))
                ]
                for x, line in units:
                    half = len(line) * size * 0.6 / 2
                    self.assertGreaterEqual(x - half, 10, f"{lang}: {line!r} clips left")
                    self.assertLessEqual(x + half, _VIEWBOX_WIDTH - 10, f"{lang}: {line!r} clips right")

    def test_base_and_specialty_labels_do_not_overlap_horizontally(self):
        # Base label centered at x=140, specialty at x=420; each side
        # must stay within its own half (< x=280).
        for lang in ("no", "en"):
            root = ET.fromstring(render_malt_roles_strip_svg(lang))
            for el in root.iter():
                if not el.tag.endswith("text"):
                    continue
                x = el.get("x")
                if x not in ("140", "420"):
                    continue
                half = len("".join(el.itertext())) * float(el.get("font-size")) * 0.6 / 2
                if x == "140":
                    self.assertLess(140 + half, 280)
                else:
                    self.assertGreater(420 - half, 280)


class TestMaltRolesStripIsSourceBounded(unittest.TestCase):
    def test_integrated_chunk_exists_and_cites_base_vs_specialty_fact(self):
        chunks = read_pilot_file()["chunks"]
        matching = [c for c in chunks if "FACT-MALT-0002" in c["source_claims"]]
        self.assertEqual(len(matching), 1)


if __name__ == "__main__":
    unittest.main()
