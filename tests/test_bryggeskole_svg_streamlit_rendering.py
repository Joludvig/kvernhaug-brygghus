"""
Regression coverage for the real Streamlit *runtime* rendering path of the
four Bryggeskole static SVG visuals -- boil/hop timeline (issue #366),
cool/transfer flow (issue #370), package flow (issue #374) and
method-context flow (issue #380) -- as opposed to the pure source-string/
viewBox tests each already has in its own `tests/test_bryggeskole_*.py`
file.

## The bug this catches (issue #378)

Owner-PC QA on the real Streamlit app found the Pakking module's SVG
diagram rendering as plain linear text ("Pakking Sanitert
håndteringssone ...") with no visible geometry and a large blank
vertical gap, despite every source/viewBox unit test passing and the
Playwright Critical Browser Gate being green. That gate only ever
serves the static `web/` site (`playwright.config.js` -> `python3 -m
http.server --directory web`) -- it never starts `streamlit run`, so it
cannot see this failure mode at all, and this repo has no other
real-browser harness for the Streamlit app (`app.py`/`ui/`/`modules/`).

Root cause: `ui/bryggeskole_panel.py` renders each of these SVGs via
`st.markdown(svg, unsafe_allow_html=True)`. Streamlit's frontend
markdown renderer is CommonMark-based (remark/rehype-raw), and CommonMark
raw-HTML-block recognition (rule 7) requires a tag's `<name ...>` open
syntax to be complete on a single line before it can start a block, and
terminates any such block at the next blank line. The three generator
modules originally returned the SVG as a human-formatted multi-line
string: the `<svg ...>` opening tag itself spanned three lines, and
blank lines separated visual groups throughout. That combination made
the markdown parser split the markup into a stray leading paragraph
plus several disconnected `html_block` fragments -- so `<rect>`/`<line>`
geometry elements ended up as siblings of (not children of) the actual
`<svg>` element, where a browser renders them as nothing, while
standalone one-line `<text>label</text>` elements fell out of any block
recognition entirely and were parsed as ordinary inline HTML inside a
stray `<p>` -- exactly the reported "just text, no diagram" failure.

## What this test actually proves, and its one known limitation

There is no existing infrastructure in this repo for pointing a real
browser at the Streamlit app (confirmed above), and building one is out
of scope for this bounded runtime fix. This test instead parses each
renderer's returned markup with `markdown-it-py` -- a CommonMark-
conformant implementation of the exact same HTML-block/inline-HTML
rules Streamlit's own frontend markdown pipeline follows -- to prove
the *parsed* result the browser would actually receive, then parses
*that* result as real XML (SVG is valid XML) to inspect genuine
computed tree structure rather than just checking for substrings in the
generator's own source output. This directly catches the failure mode
above: it fails loudly on the pre-fix markup (the extracted `<svg>...
</svg>` slice does not parse as well-formed XML at all -- a stray
`</p>` lands inside it) and passes on the fixed, single-line markup.

It cannot, by itself, verify pixel-level responsive behaviour (desktop
vs. mobile viewport, or NO+EN font metrics) -- that remains the
explicit post-merge owner-PC visual QA step the issue's own "Human QA
after merge" section already calls for. What it *does* prove, for both
languages, on every one of the three visuals: the visual's root survives
as one contiguous, well-formed `<svg>` element (not fragmented); that
element has real shape-geometry children with non-zero dimensions
(rect/line/circle/path); every expected label is attached as text
content of a `<text>`/`<tspan>` element that is a genuine descendant of
that `<svg>` root (not loose page text outside it); and the whole thing
is delivered as a single HTML block/paragraph rather than several,
which is what produced the reported oversized blank gap.

Run with:
    python3 -m unittest tests.test_bryggeskole_svg_streamlit_rendering
"""
import unittest
import xml.etree.ElementTree as ET

from markdown_it import MarkdownIt

from bryggeskole.boil_timeline import render_boil_timeline_svg
from bryggeskole.cool_transfer_flow import render_cool_transfer_flow_svg
from bryggeskole.method_context_flow import render_method_context_flow_svg
from bryggeskole.package_flow import render_package_flow_svg

SVG_NS = "{http://www.w3.org/2000/svg}"

# (render fn, expected labels per language, expected shape tags that must
# be present as real geometry -- not just text -- inside the parsed <svg>)
_CASES = [
    (
        render_boil_timeline_svg,
        {
            "no": ["Kokestart", "Kokeslutt", "Hot break / skum", "Tidlig humletilsetning", "Whirlpool / hop-stand"],
            "en": ["Boil start", "Boil end", "Hot break / foam", "Early hop addition", "Whirlpool / hop-stand"],
        },
        {"rect", "circle", "path"},
    ),
    (
        render_cool_transfer_flow_svg,
        {
            "no": ["Kjele (etter koking)", "Kjøling", "Overføring", "Gjæringskar", "Sanitert håndteringssone"],
            "en": ["Kettle (post-boil)", "Cooling", "Transfer", "Fermenter", "Sanitized handling zone"],
        },
        {"rect", "line", "path"},
    ),
    (
        render_package_flow_svg,
        {
            "no": ["Gjæringskar (ferdig gjæret)", "Sanitert håndteringssone", "Flaske-sti", "Fat-sti", "Klar til servering/lagring"],
            "en": ["Fermenter (done fermenting)", "Sanitized handling zone", "Bottle path", "Keg path", "Ready to serve/store"],
        },
        {"rect", "line", "path"},
    ),
    (
        render_method_context_flow_svg,
        {
            "no": ["BIAB", "Tradisjonelt alt-korn", "Alt-i-ett", "Meskekar/lauterkar", "Kjele"],
            "en": ["BIAB", "Traditional all-grain", "All-in-one", "Mash/lauter vessel", "Kettle"],
        },
        {"rect", "line", "path"},
    ),
]


def _render_through_commonmark(svg_markup):
    """Runs `svg_markup` through a real CommonMark parser configured the
    same way Streamlit's frontend markdown renderer is for
    `unsafe_allow_html=True` (raw HTML passthrough allowed), and returns
    the resulting HTML string -- i.e. what a browser actually receives."""
    md = MarkdownIt("commonmark", {"html": True})
    return md.render(svg_markup)


def _extract_svg_element(rendered_html):
    """Slices out the `<svg ...>...</svg>` span from `rendered_html` and
    parses it as XML (SVG is valid XML), returning the root Element.
    Raises `xml.etree.ElementTree.ParseError` if the markup was
    fragmented/malformed -- the exact way the pre-fix bug manifested."""
    start = rendered_html.index("<svg")
    end = rendered_html.rindex("</svg>") + len("</svg>")
    return ET.fromstring(rendered_html[start:end])


def _all_text_content(root):
    """Concatenates the text content of every descendant node (covers
    both single-line <text> and multi-line <text><tspan> wrapping)."""
    return " ".join(node.text or "" for node in root.iter())


class TestSvgSurvivesStreamlitMarkdownRendering(unittest.TestCase):
    """For each of the three Bryggeskole SVG visuals, in both languages:
    proves the markup a browser actually receives from
    `st.markdown(svg, unsafe_allow_html=True)` is one well-formed,
    un-fragmented <svg> element with real geometry and properly attached
    labels -- not the broken-text/no-diagram failure mode of issue #378.
    """

    def test_delivered_as_a_single_html_block_not_fragmented(self):
        for render_fn, labels_by_lang, _shapes in _CASES:
            for lang in labels_by_lang:
                with self.subTest(fn=render_fn.__name__, lang=lang):
                    svg = render_fn(lang)
                    rendered = _render_through_commonmark(svg)
                    # Exactly one wrapping block -- not several stray
                    # paragraphs/html_block fragments, which is what
                    # produced the reported oversized blank gap.
                    self.assertEqual(rendered.count("<p>"), 1)
                    self.assertEqual(rendered.count("</p>"), 1)
                    self.assertNotIn("&lt;", rendered)

    def test_svg_root_survives_as_well_formed_xml_with_real_geometry(self):
        for render_fn, labels_by_lang, shapes in _CASES:
            for lang in labels_by_lang:
                with self.subTest(fn=render_fn.__name__, lang=lang):
                    svg = render_fn(lang)
                    rendered = _render_through_commonmark(svg)
                    try:
                        root = _extract_svg_element(rendered)
                    except ET.ParseError as exc:
                        self.fail(
                            f"{render_fn.__name__}({lang!r}): the markup Streamlit's "
                            f"frontend markdown renderer would actually deliver is not "
                            f"well-formed <svg> XML (fragmented into broken HTML blocks): {exc}"
                        )
                    self.assertEqual(root.tag, f"{SVG_NS}svg")

                    present_shapes = {el.tag.removeprefix(SVG_NS) for el in root.iter()} & shapes
                    self.assertEqual(
                        present_shapes, shapes,
                        f"{render_fn.__name__}({lang!r}): expected shape geometry {shapes} "
                        f"as real descendants of the parsed <svg> root, found {present_shapes}",
                    )

                    for rect in root.iter(f"{SVG_NS}rect"):
                        self.assertGreater(float(rect.get("width")), 0)
                        self.assertGreater(float(rect.get("height")), 0)

    def test_labels_are_attached_to_the_visual_not_loose_page_text(self):
        for render_fn, labels_by_lang, _shapes in _CASES:
            for lang, expected_labels in labels_by_lang.items():
                with self.subTest(fn=render_fn.__name__, lang=lang):
                    svg = render_fn(lang)
                    rendered = _render_through_commonmark(svg)
                    root = _extract_svg_element(rendered)
                    visual_text = _all_text_content(root)
                    for label in expected_labels:
                        self.assertIn(
                            label, visual_text,
                            f"{render_fn.__name__}({lang!r}): expected label {label!r} to be "
                            f"attached inside the parsed <svg> visual, not merely present "
                            f"somewhere in the page as loose text",
                        )


if __name__ == "__main__":
    unittest.main()
