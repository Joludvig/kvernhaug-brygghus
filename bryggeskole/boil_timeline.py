"""
Bryggeskole boil/hop timeline -- static visual (issue #366, V2.2 G3C).

Pure, stdlib-only SVG generator for the boil/hop fundamentals module's
single required visual (docs/development/v22_g3b_boil_hop_module_contract.md
§4): a static, non-interactive horizontal timeline from boil start to
boil end, with a labeled hot-break/foam observation zone near the start,
early/late hop-addition timing markers, a visually distinct post-boil
whirlpool/hop-stand zone extending past the boil-end marker, and two
opposing qualitative directional cues (bitterness toward the left/
longer-hot-exposure end, aroma/flavor retention toward the right/later
end) -- no numeric IBU axis or implied fixed boil-duration scale.

No Streamlit dependency here. ui/bryggeskole_panel.py renders the returned
SVG markup via st.markdown(unsafe_allow_html=True).

Deliberately not interactive: no clickable markers, no JavaScript, no
per-marker links -- exactly the "first visual is the static timeline
only" scope the contract's own Chief decision (§7.3) settled.

The returned markup is flattened onto a single line (`_flatten_svg_markup`)
before being returned -- a blank line or a tag split across multiple
source lines both make Streamlit's CommonMark-based frontend markdown
renderer fragment the <svg>...</svg> block into a stray paragraph plus
orphaned elements outside any <svg> context, which the browser then
renders as literal label text with the geometry missing (issue #378).
"""

LANGUAGES = ("no", "en")

_LABELS = {
    "no": {
        "boil_start": "Kokestart",
        "boil_end": "Kokeslutt",
        "hot_break": "Hot break / skum",
        "early_marker": "Tidlig humletilsetning",
        "late_marker": "Sen humletilsetning",
        "flameout": "Flameout",
        "whirlpool": "Whirlpool / hop-stand",
        "bitterness_cue": "Mer bitterhetsbidrag",
        "aroma_cue": "Mer aromabevaring",
        "title": "Koking og humletidspunkt",
    },
    "en": {
        "boil_start": "Boil start",
        "boil_end": "Boil end",
        "hot_break": "Hot break / foam",
        "early_marker": "Early hop addition",
        "late_marker": "Late hop addition",
        "flameout": "Flameout",
        "whirlpool": "Whirlpool / hop-stand",
        "bitterness_cue": "More bitterness contribution",
        "aroma_cue": "More aroma retention",
        "title": "Boil and hop timing",
    },
}


def _require_language(language):
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}; must be one of {LANGUAGES}.")


def _flatten_svg_markup(svg):
    """Collapses the human-readable, multi-line <svg>...</svg> markup onto
    a single line (see the module docstring for why this matters at
    runtime -- issue #378)."""
    return " ".join(line.strip() for line in svg.strip().splitlines())


def render_boil_timeline_svg(language):
    """Returns responsive, self-contained static SVG markup for the
    boil/hop timeline in the requested language.

    The diagram is intentionally qualitative: early/late markers do not
    encode a fixed 60-minute boil, and the directional cue labels are
    placed fully inside the viewBox so they cannot be clipped by normal
    responsive rendering.
    """
    _require_language(language)
    labels = _LABELS[language]

    boil_x0, boil_x1 = 60, 620
    whirlpool_x1 = 760
    hot_break_x1 = 160
    early_x = 220
    late_x = 560

    return _flatten_svg_markup(f"""<svg viewBox="0 0 820 220" width="100%" preserveAspectRatio="xMidYMid meet"
  style="max-width:820px;height:auto;display:block;margin:0 auto;"
  xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{labels['title']}">
  <title>{labels['title']}</title>
  <text x="410" y="24" text-anchor="middle" font-size="16" font-weight="700" fill="#3a2a1a">{labels['title']}</text>

  <defs>
    <marker id="arrow-left" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M8,0 L0,4 L8,8 Z" fill="#b23b2e"/>
    </marker>
    <marker id="arrow-right" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 Z" fill="#2e7d32"/>
    </marker>
    <pattern id="whirlpool-hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
      <rect width="8" height="8" fill="#e0d6c3"/>
      <line x1="0" y1="0" x2="0" y2="8" stroke="#a68a5b" stroke-width="2"/>
    </pattern>
  </defs>

  <line x1="330" y1="50" x2="180" y2="50" stroke="#b23b2e" stroke-width="2" marker-end="url(#arrow-left)"/>
  <text x="255" y="42" text-anchor="middle" font-size="11" fill="#b23b2e">{labels['bitterness_cue']}</text>
  <line x1="490" y1="50" x2="640" y2="50" stroke="#2e7d32" stroke-width="2" marker-end="url(#arrow-right)"/>
  <text x="565" y="42" text-anchor="middle" font-size="11" fill="#2e7d32">{labels['aroma_cue']}</text>

  <rect x="{boil_x0}" y="90" width="{boil_x1 - boil_x0}" height="40" fill="#f2c14e" stroke="#7a5230"/>
  <rect x="{boil_x0}" y="90" width="{hot_break_x1 - boil_x0}" height="40" fill="#f7a072" stroke="#7a5230"/>
  <text x="{(boil_x0 + hot_break_x1) / 2}" y="115" text-anchor="middle" font-size="10" fill="#5a2d0c">{labels['hot_break']}</text>

  <rect x="{boil_x1}" y="90" width="{whirlpool_x1 - boil_x1}" height="40" fill="url(#whirlpool-hatch)" stroke="#7a5230" stroke-dasharray="4,3"/>
  <text x="{(boil_x1 + whirlpool_x1) / 2}" y="150" text-anchor="middle" font-size="11" fill="#5a2d0c">{labels['whirlpool']}</text>

  <text x="{boil_x0}" y="150" text-anchor="middle" font-size="11" fill="#3a2a1a">{labels['boil_start']}</text>
  <text x="{boil_x1}" y="150" text-anchor="middle" font-size="11" fill="#3a2a1a">{labels['boil_end']} / {labels['flameout']}</text>

  <circle cx="{early_x}" cy="110" r="5" fill="#3a2a1a"/>
  <text x="{early_x}" y="180" text-anchor="middle" font-size="11" fill="#3a2a1a">{labels['early_marker']}</text>
  <circle cx="{late_x}" cy="110" r="5" fill="#3a2a1a"/>
  <text x="{late_x}" y="180" text-anchor="middle" font-size="11" fill="#3a2a1a">{labels['late_marker']}</text>
</svg>""")
