"""
modules/export_format.py — shared formatting helpers for all export/print surfaces.

Layer 1: atomic number formatters (no dependencies).
Layer 2: composite string builders (consume ctx dict or asset files).

Import from here instead of duplicating format strings across card_template,
brewday_panel, shopping_list, etc.
"""

import base64
import os

# ── Path to shared logo asset ──────────────────────────────────────────────
_LOGO_PATH = os.path.join("assets", "branding", "master_v1_transparent.png")


# ══════════════════════════════════════════════════════════════════════════
# LAYER 1 — atomic formatters
# ══════════════════════════════════════════════════════════════════════════

def fmt_og(v: float) -> str:
    """Original gravity  →  '1.052'"""
    return f"{v:.3f}"


def fmt_fg(v: float) -> str:
    """Final gravity  →  '1.012'"""
    return f"{v:.3f}"


def fmt_abv(v: float) -> str:
    """Alcohol by volume  →  '5.2%'"""
    return f"{v:.1f}%"


def fmt_ibu(v: float) -> str:
    """Bitterness units, rounded  →  '38'"""
    return f"{round(v)}"


def fmt_ebc(v: float) -> str:
    """Colour units, rounded  →  '14'"""
    return f"{round(v)}"


def fmt_vol(v: float) -> str:
    """Batch volume  →  '25 L'"""
    return f"{v:.0f} L"


def fmt_kg(v: float) -> str:
    """Malt weight  →  '6.44 kg'"""
    return f"{v:.2f} kg"


def fmt_gram(v: float) -> str:
    """Hop weight  →  '65 g'"""
    return f"{v:.0f} g"


def fmt_ibu_bid(v: float) -> str:
    """Per-hop IBU contribution  →  '34.2'"""
    return f"{v:.1f}"


# ══════════════════════════════════════════════════════════════════════════
# LAYER 2 — composite builders
# ══════════════════════════════════════════════════════════════════════════

def stats_linje(ctx: dict, html: bool = False) -> str:
    """
    Build the stats summary line from a recipe context dict.

    Plain text (html=False):
        '25 L  ·  OG 1.052  ·  FG 1.012  ·  ABV 5.2%  ·  IBU 38  ·  EBC 14'

    HTML (html=True) — uses non-breaking separators and appends efficiency:
        '25 L &nbsp;·&nbsp; OG 1.052 &nbsp;·&nbsp; ... &nbsp;·&nbsp; Effektivitet 75%'
    """
    sep = " &nbsp;·&nbsp; " if html else "  ·  "
    parts = [
        fmt_vol(ctx["volum"]),
        f"OG {fmt_og(ctx['og'])}",
        f"FG {fmt_fg(ctx['fg'])}",
        f"ABV {fmt_abv(ctx['abv'])}",
        f"IBU {fmt_ibu(ctx['ibu'])}",
        f"EBC {fmt_ebc(ctx['ebc'])}",
    ]
    if html:
        parts.append(f"Effektivitet {ctx['effektivitet'] * 100:.0f}%")
    return sep.join(parts)


def logo_img_tag(height_px: int = 24) -> str:
    """
    Return an <img> tag with the KBH logo embedded as a base64 data URI.
    Returns an empty string if the logo file is not found.
    """
    if not os.path.exists(_LOGO_PATH):
        return ""
    with open(_LOGO_PATH, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    return (
        f'<img src="data:image/png;base64,{b64}" '
        f'alt="KBH" style="height:{height_px}px; opacity:0.85;">'
    )
