"""
Bryggeskole malt roles strip -- static visual (issue #460, V2.2 G3P-6,
contract slice 6 of docs/development/v22_g3p_raw_material_learning_contract.md).

Pure, stdlib-only SVG generator for the Raavarer module's single Malt
visual: one small, qualitative left-to-right strip from "base malt --
supplies most extract / enzymes" towards "specialty malt -- adds more
colour / flavour character", drawn as a soft colour gradient with an
arrow, never as two hard boxes. A short note states that the roles
overlap, so the strip is not read as a binary split.

Source boundary: only wording already carried by the Raavarer module's
verified Course Fact Registry records (FACT-MALT-0002 base vs specialty,
FACT-MALT-0003 colour/flavour). No numeric axis, percentages, EBC,
DP/Lintner or enzyme values, no named malts, and no new factual claim.

No Streamlit dependency here. ui/bryggeskole_panel.py renders the returned
SVG markup via st.markdown(unsafe_allow_html=True), mirroring
bryggeskole/cool_transfer_flow.py's rendering pattern. Deliberately not
interactive (no links, scripts, sliders or animation).

Every line of text is pre-split by hand into short lines (no
auto-measurement) so nothing can clip at the viewBox edge in either
language, and the markup is flattened onto a single line (issue #378) so
Streamlit's CommonMark-based markdown renderer does not fragment it.
The diagram carries its own opaque light background (issue #397) so the
palette keeps contrast on Streamlit's dark theme.
"""

LANGUAGES = ("no", "en")

_CARD_BACKGROUND_FILL = "#fbf3e3"
_CARD_BORDER_STROKE = "#d8c39a"

_LABELS = {
    "no": {
        "title": "Malt: basismalt og spesialmalt",
        "base_title": "Basismalt",
        "base_lines": ("Leverer mesteparten av", "ekstrakt og enzymer"),
        "specialty_title": "Spesialmalt",
        "specialty_lines": ("Gir mer farge- og", "smakspreg"),
        "note_lines": ("Glidende overgang, ikke en skarp todeling:", "rollene kan overlappe."),
    },
    "en": {
        "title": "Malt: base and specialty malt",
        "base_title": "Base malt",
        "base_lines": ("Supplies most of the", "extract and enzymes"),
        "specialty_title": "Specialty malt",
        "specialty_lines": ("Adds more colour and", "flavour character"),
        "note_lines": ("A gradual shift, not a hard split:", "the roles can overlap."),
    },
}


def _require_language(language):
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}; must be one of {LANGUAGES}.")


def _flatten_svg_markup(svg):
    """Collapses the multi-line markup onto one line (issue #378)."""
    return " ".join(line.strip() for line in svg.strip().splitlines())


def _lines_markup(lines, x, y, font_size, fill):
    tspans = "".join(
        f'<tspan x="{x}" y="{y + i * font_size * 1.3:.1f}">{line}</tspan>'
        for i, line in enumerate(lines)
    )
    return f'<text text-anchor="middle" font-size="{font_size}" fill="{fill}">{tspans}</text>'


def render_malt_roles_strip_svg(language):
    """Returns responsive, self-contained static SVG markup for the malt
    roles strip in the requested language."""
    _require_language(language)
    labels = _LABELS[language]

    return _flatten_svg_markup(f"""<svg viewBox="0 0 560 270" width="100%" preserveAspectRatio="xMidYMid meet"
  style="max-width:560px;height:auto;display:block;margin:0 auto;"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{labels['title']}">
  <title>{labels['title']}</title>

  <defs>
    <linearGradient id="mrs-gradient" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0" stop-color="#f2d98a"/>
      <stop offset="1" stop-color="#8a4b1f"/>
    </linearGradient>
    <marker id="mrs-arrow" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#3a2a1a"/>
    </marker>
  </defs>

  <rect x="0" y="0" width="560" height="270" rx="14" fill="{_CARD_BACKGROUND_FILL}" stroke="{_CARD_BORDER_STROKE}"/>
  <text x="280" y="32" text-anchor="middle" font-size="18" font-weight="700" fill="#3a2a1a">{labels['title']}</text>

  <rect x="40" y="52" width="480" height="30" rx="6" fill="url(#mrs-gradient)" stroke="#7a5230"/>
  <line x1="60" y1="100" x2="500" y2="100" stroke="#3a2a1a" stroke-width="2" marker-end="url(#mrs-arrow)"/>

  <text x="140" y="130" text-anchor="middle" font-size="16" font-weight="700" fill="#5a3d10">{labels['base_title']}</text>
  {_lines_markup(labels['base_lines'], 140, 154, 14, "#3a2a1a")}

  <text x="420" y="130" text-anchor="middle" font-size="16" font-weight="700" fill="#5a2d0c">{labels['specialty_title']}</text>
  {_lines_markup(labels['specialty_lines'], 420, 154, 14, "#3a2a1a")}

  {_lines_markup(labels['note_lines'], 280, 225, 14, "#5a3d10")}
</svg>""")
