"""
Bryggeskole cool/transfer flow diagram -- static visual (issue #370,
V2.2 G3E).

Pure, stdlib-only SVG generator for the cool/transfer fundamentals
module's single required visual
(docs/development/v22_g3d_cool_transfer_module_contract.md §4): a
static, non-interactive horizontal flow from the post-boil kettle
through cooling and transfer to the fermenter, with a visually distinct
"sanitized handling zone" shading starting at the cooling stage and
extending through transfer to the fermenter, two small generic
gravity/pump transfer path variants (no specific chiller/pump brand or
model), and two small non-numeric oxygen-timing labels (conditional
pre-pitch benefit, minimize-unnecessary-oxygen once fermentation is
active) -- no dissolved-oxygen scale or numeric axis.

No Streamlit dependency here. ui/bryggeskole_panel.py renders the
returned SVG markup via st.markdown(unsafe_allow_html=True), mirroring
bryggeskole/boil_timeline.py's own rendering pattern exactly.

Deliberately not interactive: no clickable markers, no JavaScript, no
per-marker links -- the contract's own §4 explicitly scopes the first
visual to static only, mirroring the same Chief decision already made
for the boil/hop timeline.

The two oxygen-timing labels are long, centered (text-anchor="middle")
body text placed off-center in the diagram, so their available
left/right margin before the SVG's own hard clip at the viewBox edge
is not symmetric. `_wrap_centered_label` below keeps them layout-safe
in both languages by word-wrapping onto multiple <tspan> lines
whenever the estimated single-line width would not comfortably fit
that margin -- deterministic and stdlib-only (textwrap + a
conservative average-character-width constant), never real
browser/font measurement (Chief review, issue #370).

The returned markup is flattened onto a single line (`_flatten_svg_markup`)
before being returned -- a blank line or a tag split across multiple
source lines both make Streamlit's CommonMark-based frontend markdown
renderer fragment the <svg>...</svg> block into a stray paragraph plus
orphaned elements outside any <svg> context, which the browser then
renders as literal label text with the geometry missing (issue #378).

Legibility pass (issue #397): the diagram carries its own explicit opaque
background rect (`_CARD_BACKGROUND_FILL`) instead of a transparent
canvas, since this palette's dark warm text colors were tuned for a light
backdrop and had weak contrast directly on Streamlit's dark theme page
background. Geometry and font sizes are scaled up from the original #370
draft for comfortable reading without zoom.
"""

import textwrap

LANGUAGES = ("no", "en")

# SVG viewBox width in user units (kept in sync with the literal
# "0 0 1090 340" in the returned markup below -- see
# test_is_responsive_and_preserves_viewbox).
_VIEWBOX_WIDTH = 1090

# Explicit opaque card background (issue #397) -- guarantees the
# original light-backdrop-tuned palette keeps correct contrast
# regardless of Streamlit's active app theme (light or dark).
_CARD_BACKGROUND_FILL = "#fbf3e3"
_CARD_BORDER_STROKE = "#d8c39a"

# Conservative average character-advance width as a fraction of
# font-size for a generic sans-serif proportional font. This is
# deliberately an overestimate (real body text is usually narrower),
# so wrapping decisions err on the side of an extra line rather than
# risking a clipped label -- not a real font metric.
_AVG_CHAR_WIDTH_FACTOR = 0.6

# Vertical spacing between stacked <tspan> lines, as a multiple of
# font-size.
_LINE_HEIGHT_FACTOR = 1.2

_LABELS = {
    "no": {
        "title": "Kjøling og overføring",
        "kettle": "Kjele (etter koking)",
        "cooling": "Kjøling",
        "transfer": "Overføring",
        "fermenter": "Gjæringskar",
        "sanitized_zone": "Sanitert håndteringssone",
        "gravity_path": "Tyngdekraft",
        "pump_path": "Pumpe",
        "oxygen_pre": "Oksygenering kan være nyttig før pitching - behov avhenger av gjær",
        "oxygen_post": "Unngå unødvendig oksygen etter aktiv gjæring",
    },
    "en": {
        "title": "Cooling and transfer",
        "kettle": "Kettle (post-boil)",
        "cooling": "Cooling",
        "transfer": "Transfer",
        "fermenter": "Fermenter",
        "sanitized_zone": "Sanitized handling zone",
        "gravity_path": "Gravity",
        "pump_path": "Pump",
        "oxygen_pre": "Aeration can help before pitching - need depends on the yeast",
        "oxygen_post": "Avoid unnecessary oxygen once fermentation is active",
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
    (text-anchor="middle") at `anchor_x`.

    The usable half-width is the distance from `anchor_x` to the
    *nearer* viewBox edge (text-anchor="middle" grows equally in both
    directions), minus `safety_margin`. A short/already-safe label is
    returned unwrapped as a single line.
    """
    half_width_budget = min(anchor_x, viewbox_width - anchor_x) - safety_margin
    max_chars = _max_chars_for_width(2 * half_width_budget, font_size)
    lines = textwrap.wrap(text, width=max_chars, break_long_words=False, break_on_hyphens=False)
    return lines or [text]


def _centered_label_markup(text, anchor_x, y, font_size, fill):
    """Renders `text` as a single centered <text> element, or as a
    centered multi-line <text> with stacked <tspan> children when
    `_wrap_centered_label` determines it would not otherwise fit
    (issue #370 Chief review: long oxygen-timing labels must not be
    able to overflow past the viewBox edge in either language)."""
    lines = _wrap_centered_label(text, anchor_x, font_size)
    if len(lines) == 1:
        return f'<text x="{anchor_x}" y="{y}" text-anchor="middle" font-size="{font_size}" fill="{fill}">{lines[0]}</text>'
    line_height = font_size * _LINE_HEIGHT_FACTOR
    tspans = "".join(
        f'<tspan x="{anchor_x}" y="{y + i * line_height}">{line}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'<text text-anchor="middle" font-size="{font_size}" fill="{fill}">{tspans}</text>'


def _flatten_svg_markup(svg):
    """Collapses the human-readable, multi-line <svg>...</svg> markup onto
    a single line (see the module docstring for why this matters at
    runtime -- issue #378)."""
    return " ".join(line.strip() for line in svg.strip().splitlines())


def render_cool_transfer_flow_svg(language):
    """Returns responsive, self-contained static SVG markup for the
    cool/transfer flow diagram in the requested language.

    The diagram is intentionally qualitative and generic: the two
    transfer-path variants are unlabeled with any specific equipment
    brand/model, and the sanitized-zone shading marks a boundary, not a
    numeric scale.
    """
    _require_language(language)
    labels = _LABELS[language]

    kettle_x0, kettle_x1 = 50, 260
    cooling_x0, cooling_x1 = 260, 545
    transfer_x0, transfer_x1 = 545, 830
    fermenter_x0, fermenter_x1 = 830, 1040

    return _flatten_svg_markup(f"""<svg viewBox="0 0 1090 340" width="100%" preserveAspectRatio="xMidYMid meet"
  style="max-width:1090px;height:auto;display:block;margin:0 auto;"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{labels['title']}">
  <title>{labels['title']}</title>

  <defs>
    <marker id="ctf-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#3a2a1a"/>
    </marker>
  </defs>

  <rect x="0" y="0" width="1090" height="340" rx="14" fill="{_CARD_BACKGROUND_FILL}" stroke="{_CARD_BORDER_STROKE}"/>
  <text x="545" y="32" text-anchor="middle" font-size="20" font-weight="700" fill="#3a2a1a">{labels['title']}</text>

  <rect x="{cooling_x0}" y="91" width="{fermenter_x1 - cooling_x0}" height="143" fill="#dceedd" stroke="#5a8f63" stroke-dasharray="5,4"/>
  <text x="{(cooling_x0 + fermenter_x1) / 2}" y="81" text-anchor="middle" font-size="14" fill="#2e7d32">{labels['sanitized_zone']}</text>

  <rect x="{kettle_x0}" y="117" width="{kettle_x1 - kettle_x0}" height="78" fill="#f2c14e" stroke="#7a5230"/>
  <text x="{(kettle_x0 + kettle_x1) / 2}" y="163" text-anchor="middle" font-size="14" fill="#5a2d0c">{labels['kettle']}</text>

  <rect x="{cooling_x0 + 13}" y="117" width="{cooling_x1 - cooling_x0 - 26}" height="78" fill="#aee1f2" stroke="#2c6e8e"/>
  <text x="{(cooling_x0 + cooling_x1) / 2}" y="163" text-anchor="middle" font-size="14" fill="#1d4a5f">{labels['cooling']}</text>

  <rect x="{transfer_x0 + 13}" y="117" width="{transfer_x1 - transfer_x0 - 26}" height="78" fill="#f7d9a0" stroke="#a6742f"/>
  <text x="{(transfer_x0 + transfer_x1) / 2}" y="146" text-anchor="middle" font-size="14" fill="#5a3d10">{labels['transfer']}</text>
  <line x1="{transfer_x0 + 33}" y1="166" x2="{transfer_x1 - 72}" y2="156" stroke="#5a3d10" stroke-width="2" marker-end="url(#ctf-arrow)"/>
  <text x="{transfer_x0 + 20}" y="189" font-size="12" fill="#5a3d10">{labels['gravity_path']}</text>
  <line x1="{transfer_x0 + 33}" y1="179" x2="{transfer_x1 - 72}" y2="182" stroke="#5a3d10" stroke-width="2" stroke-dasharray="3,3" marker-end="url(#ctf-arrow)"/>
  <text x="{transfer_x1 - 78}" y="202" font-size="12" fill="#5a3d10">{labels['pump_path']}</text>

  <rect x="{fermenter_x0 + 13}" y="117" width="{fermenter_x1 - fermenter_x0 - 26}" height="78" fill="#c9b7e0" stroke="#5c3d84"/>
  <text x="{(fermenter_x0 + fermenter_x1) / 2}" y="163" text-anchor="middle" font-size="14" fill="#37235a">{labels['fermenter']}</text>

  <line x1="{kettle_x1}" y1="156" x2="{cooling_x0 + 6}" y2="156" stroke="#3a2a1a" stroke-width="2" marker-end="url(#ctf-arrow)"/>
  <line x1="{cooling_x1 - 6}" y1="156" x2="{transfer_x0 + 6}" y2="156" stroke="#3a2a1a" stroke-width="2" marker-end="url(#ctf-arrow)"/>
  <line x1="{transfer_x1 - 6}" y1="156" x2="{fermenter_x0 + 6}" y2="156" stroke="#3a2a1a" stroke-width="2" marker-end="url(#ctf-arrow)"/>

  {_centered_label_markup(labels['oxygen_pre'], (cooling_x1 + transfer_x0) / 2, 267, 13, "#1d4a5f")}
  {_centered_label_markup(labels['oxygen_post'], (fermenter_x0 + fermenter_x1) / 2, 299, 13, "#37235a")}
</svg>""")
