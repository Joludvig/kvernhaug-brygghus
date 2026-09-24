"""
Bryggeskole method-context flow diagram -- static visual (issue #380,
V2.2 G3I).

Pure, stdlib-only SVG generator for the method-context-fundamentals
module's single required visual
(docs/development/v22_g3h_prepare_method_module_contract.md §4): three
parallel, equal-weight horizontal rows (BIAB, traditional separate-
vessel all-grain, all-in-one), each showing the identical downstream
process spine (Kok -> Kjøl -> Gjær -> Pakk / Boil -> Cool -> Ferment ->
Package) drawn identically across all three rows, but with a different
equipment icon/label at the "Mesk -> Skille vørt fra korn" segment only
-- kettle+bag for BIAB, mash/lauter vessel -> kettle for traditional,
one integrated vessel+basket for all-in-one. No numeric water/dead-space/
efficiency scale, no brand/model icon.

No Streamlit dependency here. ui/bryggeskole_panel.py renders the
returned SVG markup via st.markdown(unsafe_allow_html=True), mirroring
bryggeskole/package_flow.py's own rendering pattern exactly.

Deliberately not interactive: no clickable markers, no JavaScript, no
per-marker links -- the contract's own §4 explicitly scopes the first
visual to static only, mirroring the same Chief decision already made
for the boil/hop timeline, cool/transfer flow and package flow diagrams.

All three rows are drawn with identical box sizes, identical stroke
widths and the same vertical prominence -- deliberately equal visual
weight, so no row reads as the "main", "beginner" or "upgraded" method
(CHUNK-METHOD-E's "no quality hierarchy" point). Each method's own
"Mesk -> Skille" zone occupies the same total width regardless of
whether it is drawn as one combined box (BIAB, all-in-one) or two
separate boxes (traditional), so the shared downstream boxes -- drawn
once per row, but at identical x-positions across all three rows --
visually line up, reinforcing "same process, different layout".

Long labels are word-wrapped onto multiple <tspan> lines using the same
deterministic, stdlib-only heuristic bryggeskole/cool_transfer_flow.py
and bryggeskole/package_flow.py already established
(`_wrap_centered_label`), copied here unmodified since this module
independently needs the same layout-safety property for long NO/EN
labels near the viewBox edge.

The returned markup is flattened onto a single line (`_flatten_svg_markup`)
before being returned -- a blank line or a tag split across multiple
source lines both make Streamlit's CommonMark-based frontend markdown
renderer fragment the <svg>...</svg> block into a stray paragraph plus
orphaned elements outside any <svg> context (issue #378) -- see
bryggeskole/package_flow.py's own docstring for the full failure-mode
explanation this pattern avoids.
"""

import textwrap

LANGUAGES = ("no", "en")

# SVG viewBox width in user units (kept in sync with the literal
# "0 0 1000 430" in the returned markup below).
_VIEWBOX_WIDTH = 1000

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
        "title": "Metodevalg: samme prosess, tre utstyrsoppsett",
        "row_biab": "BIAB",
        "row_traditional": "Tradisjonelt alt-korn",
        "row_all_in_one": "Alt-i-ett",
        "biab_combined": "Kjele + pose (meskepose/BIAB)",
        "traditional_mash": "Meskekar/lauterkar",
        "traditional_kettle": "Kjele",
        "all_in_one_combined": "Integrert kar + kurv/malt-rør",
        "stage_boil": "Kok",
        "stage_cool": "Kjøl",
        "stage_ferment": "Gjær",
        "stage_package": "Pakk",
        "no_hierarchy_caption": "Ingen av metodene er «riktigere» - alle fullfører samme prosess",
    },
    "en": {
        "title": "Method choice: same process, three equipment layouts",
        "row_biab": "BIAB",
        "row_traditional": "Traditional all-grain",
        "row_all_in_one": "All-in-one",
        "biab_combined": "Kettle + bag (mash bag/BIAB)",
        "traditional_mash": "Mash/lauter vessel",
        "traditional_kettle": "Kettle",
        "all_in_one_combined": "Integrated vessel + basket/malt pipe",
        "stage_boil": "Boil",
        "stage_cool": "Cool",
        "stage_ferment": "Ferment",
        "stage_package": "Package",
        "no_hierarchy_caption": "No method is \"more correct\" - all complete the same process",
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


def _flatten_svg_markup(svg):
    """Collapses the human-readable, multi-line <svg>...</svg> markup onto
    a single line (see the module docstring for why this matters at
    runtime -- issue #378)."""
    return " ".join(line.strip() for line in svg.strip().splitlines())


def _stage_box(x, y0, y1, width, label, fill, stroke, text_fill):
    cx = x + width / 2
    cy = (y0 + y1) / 2
    return (
        f'<rect x="{x}" y="{y0}" width="{width}" height="{y1 - y0}" fill="{fill}" stroke="{stroke}"/>'
        f'{_centered_label_markup(label, cx, cy + 4, 10, text_fill)}'
    )


def _arrow(x0, y, x1, y2=None):
    y2 = y if y2 is None else y2
    return f'<line x1="{x0}" y1="{y}" x2="{x1}" y2="{y2}" stroke="#3a2a1a" stroke-width="2" marker-end="url(#mcf-arrow)"/>'


def render_method_context_flow_svg(language):
    """Returns responsive, self-contained static SVG markup for the
    method-context flow diagram in the requested language: three
    parallel, equal-weight rows (BIAB, traditional all-grain, all-in-one),
    each with its own equipment icon at the "mash -> separate" segment,
    reconverging into the identical "boil -> cool -> ferment -> package"
    process spine, drawn once per row at identical positions -- no
    numeric water/efficiency scale, no brand/model.
    """
    _require_language(language)
    labels = _LABELS[language]

    zone_x0 = 60
    zone_width = 280
    zone_x1 = zone_x0 + zone_width
    downstream_x0 = zone_x1 + 30
    stage_width = 130
    stage_gap = 20
    stage_xs = [downstream_x0 + i * (stage_width + stage_gap) for i in range(4)]
    box_height = 60

    row_centers = {"biab": 90, "traditional": 220, "all_in_one": 350}

    def row(center):
        return center - box_height / 2, center + box_height / 2

    biab_y0, biab_y1 = row(row_centers["biab"])
    trad_y0, trad_y1 = row(row_centers["traditional"])
    aio_y0, aio_y1 = row(row_centers["all_in_one"])

    stage_labels = [labels["stage_boil"], labels["stage_cool"], labels["stage_ferment"], labels["stage_package"]]

    def downstream_markup(y0, y1):
        parts = []
        for i, x in enumerate(stage_xs):
            parts.append(_stage_box(x, y0, y1, stage_width, stage_labels[i], "#f2c14e", "#7a5230", "#5a2d0c"))
            if i < len(stage_xs) - 1:
                parts.append(_arrow(x + stage_width, (y0 + y1) / 2, stage_xs[i + 1]))
        return "".join(parts)

    return _flatten_svg_markup(f"""<svg viewBox="0 0 1000 430" width="100%" preserveAspectRatio="xMidYMid meet"
  style="max-width:1000px;height:auto;display:block;margin:0 auto;"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{labels['title']}">
  <title>{labels['title']}</title>
  <text x="500" y="22" text-anchor="middle" font-size="16" font-weight="700" fill="#3a2a1a">{labels['title']}</text>

  <defs>
    <marker id="mcf-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#3a2a1a"/>
    </marker>
  </defs>

  <text x="{zone_x0 + zone_width / 2}" y="{biab_y0 - 12}" text-anchor="middle" font-size="12" font-weight="700" fill="#5a3d10">{labels['row_biab']}</text>
  <rect x="{zone_x0}" y="{biab_y0}" width="{zone_width}" height="{biab_y1 - biab_y0}" fill="#f7d9a0" stroke="#a6742f"/>
  {_centered_label_markup(labels['biab_combined'], zone_x0 + zone_width / 2, (biab_y0 + biab_y1) / 2 + 4, 10, "#5a3d10")}
  {_arrow(zone_x1, (biab_y0 + biab_y1) / 2, downstream_x0)}
  {downstream_markup(biab_y0, biab_y1)}

  <text x="{zone_x0 + zone_width / 2}" y="{trad_y0 - 12}" text-anchor="middle" font-size="12" font-weight="700" fill="#5a3d10">{labels['row_traditional']}</text>
  <rect x="{zone_x0}" y="{trad_y0}" width="{stage_width}" height="{trad_y1 - trad_y0}" fill="#f7d9a0" stroke="#a6742f"/>
  {_centered_label_markup(labels['traditional_mash'], zone_x0 + stage_width / 2, (trad_y0 + trad_y1) / 2 + 4, 10, "#5a3d10")}
  {_arrow(zone_x0 + stage_width, (trad_y0 + trad_y1) / 2, zone_x0 + stage_width + stage_gap)}
  <rect x="{zone_x0 + stage_width + stage_gap}" y="{trad_y0}" width="{stage_width}" height="{trad_y1 - trad_y0}" fill="#aee1f2" stroke="#2c6e8e"/>
  {_centered_label_markup(labels['traditional_kettle'], zone_x0 + stage_width + stage_gap + stage_width / 2, (trad_y0 + trad_y1) / 2 + 4, 10, "#1d4a5f")}
  {_arrow(zone_x1, (trad_y0 + trad_y1) / 2, downstream_x0)}
  {downstream_markup(trad_y0, trad_y1)}

  <text x="{zone_x0 + zone_width / 2}" y="{aio_y0 - 12}" text-anchor="middle" font-size="12" font-weight="700" fill="#5a3d10">{labels['row_all_in_one']}</text>
  <rect x="{zone_x0}" y="{aio_y0}" width="{zone_width}" height="{aio_y1 - aio_y0}" fill="#c9b7e0" stroke="#5c3d84"/>
  {_centered_label_markup(labels['all_in_one_combined'], zone_x0 + zone_width / 2, (aio_y0 + aio_y1) / 2 + 4, 10, "#37235a")}
  {_arrow(zone_x1, (aio_y0 + aio_y1) / 2, downstream_x0)}
  {downstream_markup(aio_y0, aio_y1)}

  {_centered_label_markup(labels['no_hierarchy_caption'], 500, 410, 11, "#3a2a1a")}
</svg>""")
