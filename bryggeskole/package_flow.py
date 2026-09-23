"""
Bryggeskole package flow diagram -- static visual (issue #374, V2.2
G3G).

Pure, stdlib-only SVG generator for the package-fundamentals module's
single required visual
(docs/development/v22_g3f_package_module_contract.md §4): a static,
non-interactive fermenter -> split-path -> serve/store flow, with two
equal-weight, side-by-side packaging paths (bottle: bottling wand ->
bottle + priming sugar; keg: transfer -> keg + external CO2) inside the
same "sanitized handling zone" shading technique already established by
bryggeskole/cool_transfer_flow.py, reconverging at a single shared
"ready to serve/store" end node, plus two small non-numeric labels
(avoid unnecessary oxygen during transfer; use pressure-suitable
equipment) -- no numeric carbonation/pressure scale, no brand/model.

No Streamlit dependency here. ui/bryggeskole_panel.py renders the
returned SVG markup via st.markdown(unsafe_allow_html=True), mirroring
bryggeskole/cool_transfer_flow.py's own rendering pattern exactly.

Deliberately not interactive: no clickable markers, no JavaScript, no
per-marker links -- the contract's own §4 explicitly scopes the first
visual to static only, mirroring the same Chief decision already made
for the boil/hop timeline and cool/transfer flow diagrams.

Both packaging paths are drawn with identical box sizes, identical
stroke widths and the same vertical prominence -- deliberately equal
visual weight, so neither reads as the "main" or "upgraded" route
(CHUNK-PACK-E's "not a quality hierarchy" point).

Long labels are word-wrapped onto multiple <tspan> lines using the same
deterministic, stdlib-only heuristic bryggeskole/cool_transfer_flow.py
already established (`_wrap_centered_label`), rather than real
browser/font measurement -- copied here unmodified since both modules
independently need the same layout-safety property for long NO/EN
labels near the viewBox edge.
"""

import textwrap

LANGUAGES = ("no", "en")

# SVG viewBox width in user units (kept in sync with the literal
# "0 0 880 330" in the returned markup below).
_VIEWBOX_WIDTH = 880

# Conservative average character-advance width as a fraction of
# font-size for a generic sans-serif proportional font. Deliberately an
# overestimate, so wrapping decisions err on the side of an extra line
# rather than risking a clipped label -- not a real font metric.
_AVG_CHAR_WIDTH_FACTOR = 0.6

# Vertical spacing between stacked <tspan> lines, as a multiple of
# font-size.
_LINE_HEIGHT_FACTOR = 1.2

_LABELS = {
    "no": {
        "title": "Pakking",
        "fermenter": "Gjæringskar (ferdig gjæret)",
        "sanitized_zone": "Sanitert håndteringssone",
        "bottle_path": "Flaske-sti",
        "keg_path": "Fat-sti",
        "bottle_transfer": "Tappestav / overføring",
        "bottle_step": "Flaske + primesukker",
        "keg_transfer": "Overføring",
        "keg_step": "Fat + ekstern CO2",
        "serve_store": "Klar til servering/lagring",
        "oxygen_label": "Unngå unødvendig oksygen ved overføring",
        "pressure_label": "Bruk trykkegnet utstyr - flaske og fat er under trykk",
    },
    "en": {
        "title": "Packaging",
        "fermenter": "Fermenter (done fermenting)",
        "sanitized_zone": "Sanitized handling zone",
        "bottle_path": "Bottle path",
        "keg_path": "Keg path",
        "bottle_transfer": "Bottling wand / transfer",
        "bottle_step": "Bottle + priming sugar",
        "keg_transfer": "Transfer",
        "keg_step": "Keg + external CO2",
        "serve_store": "Ready to serve/store",
        "oxygen_label": "Avoid unnecessary oxygen during transfer",
        "pressure_label": "Use pressure-suitable equipment - bottle and keg are under pressure",
    },
}


def _require_language(language):
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}; must be one of {LANGUAGES}.")


def _max_chars_for_width(available_width, font_size):
    """Deterministic, stdlib-only estimate of how many characters of body
    text fit inside `available_width` px at `font_size`, using
    `_AVG_CHAR_WIDTH_FACTOR` -- not a real font measurement."""
    char_width = font_size * _AVG_CHAR_WIDTH_FACTOR
    if available_width <= 0 or char_width <= 0:
        return 1
    return max(1, int(available_width // char_width))


def _wrap_centered_label(text, anchor_x, font_size, safety_margin=20, viewbox_width=_VIEWBOX_WIDTH):
    """Word-wraps `text` into the fewest lines whose estimated rendered
    width stays comfortably inside the SVG viewBox when centered
    (text-anchor="middle") at `anchor_x`."""
    half_width_budget = min(anchor_x, viewbox_width - anchor_x) - safety_margin
    max_chars = _max_chars_for_width(2 * half_width_budget, font_size)
    lines = textwrap.wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False)
    return lines or [text]


def _centered_label_markup(text, anchor_x, y, font_size, fill):
    """Renders `text` as a single centered <text> element, or as a
    centered multi-line <text> with stacked <tspan> children when
    `_wrap_centered_label` determines it would not otherwise fit."""
    lines = _wrap_centered_label(text, anchor_x, font_size)
    if len(lines) == 1:
        return f'<text x="{anchor_x}" y="{y}" text-anchor="middle" font-size="{font_size}" fill="{fill}">{lines[0]}</text>'
    line_height = font_size * _LINE_HEIGHT_FACTOR
    tspans = "".join(
        f'<tspan x="{anchor_x}" y="{y + i * line_height}">{line}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'<text text-anchor="middle" font-size="{font_size}" fill="{fill}">{tspans}</text>'


def render_package_flow_svg(language):
    """Returns responsive, self-contained static SVG markup for the
    package flow diagram in the requested language: fermenter -> split
    path -> bottle/keg -> serve/store, with two equal-weight legitimate
    packaging routes reconverging at one shared completion node.
    """
    _require_language(language)
    labels = _LABELS[language]

    fermenter_x0, fermenter_x1 = 40, 220
    split_x = 260
    path_x0, path_x1 = 300, 620
    serve_x0, serve_x1 = 680, 840

    bottle_y0, bottle_y1 = 40, 130
    keg_y0, keg_y1 = 190, 280
    serve_y_mid = 165

    return f"""<svg viewBox="0 0 880 330" width="100%" preserveAspectRatio="xMidYMid meet"
  style="max-width:880px;height:auto;display:block;margin:0 auto;"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{labels['title']}">
  <title>{labels['title']}</title>
  <text x="440" y="22" text-anchor="middle" font-size="16" font-weight="700" fill="#3a2a1a">{labels['title']}</text>

  <defs>
    <marker id="pkf-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#3a2a1a"/>
    </marker>
  </defs>

  <rect x="{path_x0 - 10}" y="{bottle_y0 - 20}" width="{serve_x1 - (path_x0 - 10)}" height="{keg_y1 - bottle_y0 + 40}" fill="#dceedd" stroke="#5a8f63" stroke-dasharray="5,4"/>
  <text x="{(path_x0 + serve_x1) / 2}" y="{bottle_y0 - 26}" text-anchor="middle" font-size="11" fill="#2e7d32">{labels['sanitized_zone']}</text>

  <rect x="{fermenter_x0}" y="{serve_y_mid - 35}" width="{fermenter_x1 - fermenter_x0}" height="70" fill="#c9b7e0" stroke="#5c3d84"/>
  <text x="{(fermenter_x0 + fermenter_x1) / 2}" y="{serve_y_mid + 5}" text-anchor="middle" font-size="11" fill="#37235a">{labels['fermenter']}</text>

  <line x1="{fermenter_x1}" y1="{serve_y_mid}" x2="{split_x}" y2="{serve_y_mid}" stroke="#3a2a1a" stroke-width="2"/>
  <line x1="{split_x}" y1="{serve_y_mid}" x2="{path_x0}" y2="{(bottle_y0 + bottle_y1) / 2}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#pkf-arrow)"/>
  <line x1="{split_x}" y1="{serve_y_mid}" x2="{path_x0}" y2="{(keg_y0 + keg_y1) / 2}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#pkf-arrow)"/>

  <text x="{(path_x0 + path_x1) / 2}" y="{bottle_y0 - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#5a3d10">{labels['bottle_path']}</text>
  <rect x="{path_x0}" y="{bottle_y0}" width="150" height="{bottle_y1 - bottle_y0}" fill="#f7d9a0" stroke="#a6742f"/>
  <text x="{path_x0 + 75}" y="{bottle_y0 + 25}" text-anchor="middle" font-size="10" fill="#5a3d10">{labels['bottle_transfer']}</text>
  <line x1="{path_x0 + 150}" y1="{(bottle_y0 + bottle_y1) / 2}" x2="{path_x0 + 190}" y2="{(bottle_y0 + bottle_y1) / 2}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#pkf-arrow)"/>
  <rect x="{path_x0 + 190}" y="{bottle_y0}" width="150" height="{bottle_y1 - bottle_y0}" fill="#aee1f2" stroke="#2c6e8e"/>
  <text x="{path_x0 + 265}" y="{bottle_y0 + 25}" text-anchor="middle" font-size="10" fill="#1d4a5f">{labels['bottle_step']}</text>
  <line x1="{path_x0 + 340}" y1="{(bottle_y0 + bottle_y1) / 2}" x2="{serve_x0}" y2="{serve_y_mid}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#pkf-arrow)"/>

  <text x="{(path_x0 + path_x1) / 2}" y="{keg_y0 - 6}" text-anchor="middle" font-size="11" font-weight="700" fill="#5a3d10">{labels['keg_path']}</text>
  <rect x="{path_x0}" y="{keg_y0}" width="150" height="{keg_y1 - keg_y0}" fill="#f7d9a0" stroke="#a6742f"/>
  <text x="{path_x0 + 75}" y="{keg_y0 + 25}" text-anchor="middle" font-size="10" fill="#5a3d10">{labels['keg_transfer']}</text>
  <line x1="{path_x0 + 150}" y1="{(keg_y0 + keg_y1) / 2}" x2="{path_x0 + 190}" y2="{(keg_y0 + keg_y1) / 2}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#pkf-arrow)"/>
  <rect x="{path_x0 + 190}" y="{keg_y0}" width="150" height="{keg_y1 - keg_y0}" fill="#aee1f2" stroke="#2c6e8e"/>
  <text x="{path_x0 + 265}" y="{keg_y0 + 25}" text-anchor="middle" font-size="10" fill="#1d4a5f">{labels['keg_step']}</text>
  <line x1="{path_x0 + 340}" y1="{(keg_y0 + keg_y1) / 2}" x2="{serve_x0}" y2="{serve_y_mid}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#pkf-arrow)"/>

  <rect x="{serve_x0}" y="{serve_y_mid - 35}" width="{serve_x1 - serve_x0}" height="70" fill="#f2c14e" stroke="#7a5230"/>
  {_centered_label_markup(labels['serve_store'], (serve_x0 + serve_x1) / 2, serve_y_mid + 5, 10, "#5a2d0c")}

  {_centered_label_markup(labels['oxygen_label'], split_x, 305, 10, "#1d4a5f")}
  {_centered_label_markup(labels['pressure_label'], (path_x0 + serve_x1) / 2, 320, 10, "#37235a")}
</svg>"""
