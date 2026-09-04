"""Loader/validator for design/tokens.json — the Kvernhaug Design System's
machine-readable token source (see docs/DESIGN.md for the full principles
doc these tokens back).

Pure module, no Streamlit import (.claude/rules/desktop.md): safe to call
from ui/**, from modules/**, or from a plain test with no Streamlit
context. This is a foundation/consumption-proof module, not a wholesale
palette refactor — most of the app's own colors remain where they already
lived (ui/branding.py, modules/card_template.py) as independent, hand-
maintained copies; only ui/branding.py's accent colors are wired to this
module so far (see its _COLORS dict). tests/test_design_tokens.py guards
those copies (plus web/css/style.css's :root block) against drifting away
from this file's values.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

TOKENS_PATH = Path(__file__).resolve().parent.parent / "design" / "tokens.json"

_HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

_REQUIRED_ACCENT_KEYS = {"gold", "pergament", "moss", "copper", "elfenbein", "danger"}
_REQUIRED_TOP_KEYS = {
    "schema_version", "color", "typography", "spacing_rem", "radius_px", "shadow", "focus_ring",
}
_REQUIRED_RADIUS_KEYS = {"sm", "md", "lg", "xl", "pill"}
_REQUIRED_SHADOW_KEYS = {"sm", "md", "lg"}
_SCHEMA_VERSION_RE = re.compile(r"^\d+\.\d+\.\d+$")


def validate_tokens(data: dict) -> None:
    """Raises ValueError with a specific reason on any malformed/incomplete
    token definition. Does not touch disk — takes an already-parsed dict,
    so it can be exercised directly against synthetic broken data in
    tests without needing a second on-disk fixture file. Every container
    is isinstance-checked before being indexed/iterated, so a malformed
    shape raises this function's own ValueError instead of leaking a
    bare AttributeError/TypeError from deeper inside."""
    if not isinstance(data, dict):
        raise ValueError("tokens.json må være et objekt")

    missing_top = _REQUIRED_TOP_KEYS - data.keys()
    if missing_top:
        raise ValueError(f"tokens.json mangler nøkler: {sorted(missing_top)}")

    schema_version = data["schema_version"]
    if not isinstance(schema_version, str) or not _SCHEMA_VERSION_RE.match(schema_version):
        raise ValueError(
            f"tokens.json schema_version er ikke gyldig (forventet f.eks. '1.0.0'): {schema_version!r}"
        )

    color = data["color"]
    if not isinstance(color, dict):
        raise ValueError("tokens.json color må være et objekt")
    if "accent" not in color:
        raise ValueError("tokens.json color mangler 'accent'")
    accent = color["accent"]
    if not isinstance(accent, dict):
        raise ValueError("tokens.json color.accent må være et objekt")
    missing_accent = _REQUIRED_ACCENT_KEYS - accent.keys()
    if missing_accent:
        raise ValueError(f"tokens.json color.accent mangler nøkler: {sorted(missing_accent)}")

    for group_name, group in color.items():
        if not isinstance(group, dict):
            raise ValueError(f"tokens.json color.{group_name} må være et objekt")
        for key, value in group.items():
            if not isinstance(value, str) or not _HEX_RE.match(value):
                raise ValueError(
                    f"tokens.json color.{group_name}.{key} er ikke gyldig hex-farge: {value!r}"
                )

    typografi = data["typography"]
    if not isinstance(typografi, dict):
        raise ValueError("tokens.json typography må være et objekt")
    for rolle in ("serif", "sans"):
        if not isinstance(typografi.get(rolle), str) or not typografi[rolle].strip():
            raise ValueError(f"tokens.json typography.{rolle} mangler eller er tom")

    spacing = data["spacing_rem"]
    if not isinstance(spacing, list) or not spacing:
        raise ValueError("tokens.json spacing_rem må være en ikke-tom liste")
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) or v <= 0 for v in spacing):
        raise ValueError("tokens.json spacing_rem må inneholde kun positive tall")
    if spacing != sorted(spacing):
        raise ValueError("tokens.json spacing_rem må være stigende sortert")

    radius = data["radius_px"]
    if not isinstance(radius, dict):
        raise ValueError("tokens.json radius_px må være et objekt")
    missing_radius = _REQUIRED_RADIUS_KEYS - radius.keys()
    if missing_radius:
        raise ValueError(f"tokens.json radius_px mangler nøkler: {sorted(missing_radius)}")
    if any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in radius.values()):
        raise ValueError("tokens.json radius_px må inneholde kun positive heltall")

    shadow = data["shadow"]
    if not isinstance(shadow, dict):
        raise ValueError("tokens.json shadow må være et objekt")
    missing_shadow = _REQUIRED_SHADOW_KEYS - shadow.keys()
    if missing_shadow:
        raise ValueError(f"tokens.json shadow mangler nøkler: {sorted(missing_shadow)}")
    if any(not isinstance(v, str) or not v.strip() for v in shadow.values()):
        raise ValueError("tokens.json shadow-verdier må være ikke-tomme strenger")

    if not isinstance(data["focus_ring"], str) or not data["focus_ring"].strip():
        raise ValueError("tokens.json focus_ring mangler eller er tom")


def load_tokens(path: Path = TOKENS_PATH) -> dict:
    """Leser og validerer tokens.json. Kastes bevisst videre uendret ved
    ugyldig JSON eller feilende validate_tokens() -- ingen stille
    fallback til en default-palett, siden det ville skjult nettopp den
    typen token-drift dette systemet finnes for å fange."""
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    validate_tokens(data)
    return data


def get_accent_colors(path: Path = TOKENS_PATH) -> dict:
    """Bekvemmelighetsfunksjon: kun de produktuavhengige aksentfargene
    (gull/pergament/mose/kobber/elfenbein/danger) — de samme seks verdiene
    som allerede var byte-identiske på tvers av ui/branding.py,
    modules/card_template.py og web/css/style.css før denne modulen
    fantes (se docs/DESIGN.md "Produkttilpasning: Web vs. App")."""
    return load_tokens(path)["color"]["accent"]
