"""
modules/export_format.py — shared formatting helpers for all export/print surfaces.

Layer 1: atomic number formatters (no dependencies).
Layer 2: composite string builders (consume ctx dict or asset files).

Import from here instead of duplicating format strings across card_template,
brewday_panel, shopping_list, etc.
"""

import base64
import html
import os
import urllib.parse

# ── Path to shared logo asset ──────────────────────────────────────────────
_LOGO_PATH = os.path.join("assets", "branding", "master_v1_header_24px.png")


def esc(value) -> str:
    """HTML-escapes any dynamic text before it is interpolated into an
    export template (card_template.py, brewday_template.py,
    shopping_template.py) -- recipe/brewer-stil names, comments, water
    source/target profile names, ingredient display names, product URLs,
    and any other user- or database/scraped-controlled text. Numeric
    values formatted by the fmt_*() functions below never need this --
    only free text. `None` becomes an empty string rather than the
    literal "None"."""
    if value is None:
        return ""
    return html.escape(str(value), quote=True)


# Skjema tillatt i klikkbare produktlenker i eksportene. Bevisst en
# ALLOWLIST (ikke en blokkliste over "javascript:"/"data:"/osv.) -- en
# blokkliste må oppdateres for hvert nytt farlig skjema noen finner på;
# en allowlist er trygg mot alle skjema den ikke eksplisitt nevner.
_TILLATTE_URL_SKJEMA = {"http", "https"}


def sanitize_url(url):
    """Validerer at en produkt-URL bruker et TRYGT skjema (kun http/https)
    før den settes inn i en klikkbar lenke i en HTML-eksport. Returnerer
    den rensede URL-en hvis den er trygg, ellers None -- kallestedet skal
    da vise ingrediensnavnet uten lenke i stedet for å risikere en
    javascript:/data:/file:/vbscript:-URL som kjører når lenken klikkes.

    Dette er et EGET, TIDLIGERE steg enn esc()/html.escape(quote=True):
    escaping hindrer HTML-/attributt-utbryting (et anførselstegn i
    URL-en), IKKE et farlig skjema i seg selv -- en fullt escapet
    "javascript:alert(1)" er fortsatt en javascript:-URL. Kallestedene
    (se modules/shopping_template.py::_rad()) kjører derfor BEGGE steg i
    rekkefølge: sanitize_url() først, så esc() på resultatet.

    URL-en kommer i siste instans fra skrapet butikkdata
    (butikk_match.*.url i masterdatabasene, se
    modules/store_matcher.py) -- ikke direkte brukerinput, men likevel
    ekstern, ikke-kuratert tekst appen ikke bør stole blindt på.
    """
    if not url or not isinstance(url, str):
        return None
    # Kontrolltegn (tab, linjeskift, vognretur, osv.) FJERNES -- ikke bare
    # strippes fra start/slutt -- FØR skjemaet leses. Nettlesere har
    # historisk ignorert nettopp slike tegn MIDT I et skjema, noe som gjør
    # "java\tscript:alert(1)" til en reell javascript:-URL i praksis selv
    # om en naiv understreng-sjekk ikke ville gjenkjent det.
    renset = "".join(tegn for tegn in url if tegn.isprintable()).strip()
    if not renset:
        return None
    try:
        parsed = urllib.parse.urlsplit(renset)
    except ValueError:
        return None
    if parsed.scheme.lower() not in _TILLATTE_URL_SKJEMA:
        return None
    if not parsed.netloc:
        return None
    return renset


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
