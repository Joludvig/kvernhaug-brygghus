# modules/card_template.py
"""
Pure HTML templates for Kvernhaug Brygghus recipe cards.
No Streamlit imports — safe to call from any context.
  render_card_html()  → inline div for st.components.v1.html()
  render_a4_html()    → full HTML document for download
"""
from __future__ import annotations
import datetime

# ── Master Design V1 palette ──────────────────────────────────────────────────
# Source: docs/branding/master_design_v1.md
_BG        = "#0f0c07"    # skifer-sort (warm)
_BG_SECT   = "#1a1208"    # section background
_GOLD      = "#c49a2a"    # antikk gull
_PERGAMENT = "#dfd0a0"    # pergament
_MOSS      = "#3d6b2a"    # mosegrønn
_COPPER    = "#9e6030"    # kobber
_ELFENBEIN = "#c8b882"    # elfenbein
_BODY      = "#e8e0d0"    # warm off-white
_MUTED     = "#9a9080"    # muted captions

_SERIF = "'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif"

_MONTHS_NO = ["jan","feb","mar","apr","mai","jun","jul","aug","sep","okt","nov","des"]


def _today_no() -> str:
    d = datetime.date.today()
    return f"{d.day}. {_MONTHS_NO[d.month - 1]} {d.year}"


def _malt_rows_dark(ctx: dict, malt_db: dict) -> str:
    malts = ctx["recipe"].get("malts", [])
    total_kg = sum(m.get("mengde", 0) for m in malts) or 1.0
    rows = []
    for m in malts:
        info = malt_db.get(m["id"], {})
        navn = info.get("display_name", m["id"])
        kg   = m.get("mengde", 0)
        pct  = kg / total_kg * 100
        rows.append(
            f"<tr>"
            f"<td style='padding:3px 8px 3px 0; color:{_BODY};'>{navn}</td>"
            f"<td style='padding:3px 4px; color:{_BODY}; text-align:right; white-space:nowrap;'>{kg:.2f} kg</td>"
            f"<td style='padding:3px 0 3px 8px; color:{_MUTED}; text-align:right; font-size:0.85em;'>{pct:.0f}%</td>"
            f"</tr>"
        )
    return "".join(rows) if rows else (
        f"<tr><td colspan='3' style='color:{_MUTED}; font-style:italic;'>Ingen malt valgt</td></tr>"
    )


def _hop_rows_dark(ctx: dict, humle_db: dict) -> str:
    hops = sorted(ctx["recipe"].get("hops", []), key=lambda h: h.get("tid", 0), reverse=True)
    rows = []
    for h in hops:
        info      = humle_db.get(h["id"], {})
        navn      = info.get("display_name", h["id"])
        gram      = h.get("gram", 0)
        tid       = h.get("tid", 0)
        tid_label = "tørrhumle" if tid == 0 else f"@{tid} min"
        rows.append(
            f"<tr>"
            f"<td style='padding:3px 8px 3px 0; color:{_BODY};'>{navn}</td>"
            f"<td style='padding:3px 4px; color:{_BODY}; text-align:right; white-space:nowrap;'>{gram:.0f} g</td>"
            f"<td style='padding:3px 0 3px 8px; color:{_MUTED}; text-align:right; font-size:0.85em;'>{tid_label}</td>"
            f"</tr>"
        )
    return "".join(rows) if rows else (
        f"<tr><td colspan='3' style='color:{_MUTED}; font-style:italic;'>Ingen humle valgt</td></tr>"
    )


def _logo_header(logo_b64: str | None) -> str:
    place = "VED DALELVA I ÅSANE"
    if logo_b64:
        return (
            f"<div style='display:flex; align-items:center; justify-content:center; "
            f"gap:12px; padding:8px 0 6px 0;'>"
            f"<img src='data:image/png;base64,{logo_b64}' "
            f"style='height:46px; width:auto; opacity:0.90;'>"
            f"<div style='font-family:{_SERIF}; font-size:0.68em; color:{_GOLD}; "
            f"letter-spacing:0.18em; text-transform:uppercase;'>{place}</div>"
            f"</div>"
        )
    return (
        f"<div style='font-family:{_SERIF}; font-size:0.68em; color:{_GOLD}; "
        f"letter-spacing:0.18em; text-transform:uppercase; "
        f"text-align:center; padding:10px 0 6px 0;'>{place}</div>"
    )


def _divider() -> str:
    return f"<hr style='border:none; border-top:1px solid {_GOLD}; opacity:0.35; margin:11px 0;'>"


def render_card_html(
    ctx:      dict,
    malt_db:  dict,
    humle_db: dict,
    gjaer_db: dict,
    mode:     str = "card",
    logo_b64: str | None = None,
) -> str:
    stil       = ctx["style_analysis"].get("stil", "")
    gjaer_id   = ctx["recipe"].get("yeast", "")
    gjaer_navn = gjaer_db.get(gjaer_id, {}).get("display_name", gjaer_id)
    summary    = ctx["summary"].replace("**", "")

    stat_labels = ["OG", "FG", "ABV", "IBU", "EBC"]
    stat_values = [
        f"{ctx['og']:.3f}",
        f"{ctx['fg']:.3f}",
        f"{ctx['abv']:.1f}%",
        f"{ctx['ibu']:.0f}",
        f"{ctx['ebc']:.0f}",
    ]
    stat_heads = "".join(
        f"<th style='text-align:center; padding:2px 4px; font-size:0.63em; "
        f"color:{_GOLD}; font-weight:normal; letter-spacing:0.14em; text-transform:uppercase;'>{l}</th>"
        for l in stat_labels
    )
    stat_vals = "".join(
        f"<td style='text-align:center; padding:4px; font-size:1.18em; "
        f"font-weight:bold; color:{_PERGAMENT};'>{v}</td>"
        for v in stat_values
    )

    return f"""<div style="
  background:{_BG};
  border:1.5px solid {_GOLD};
  border-radius:8px;
  padding:16px 20px 14px 20px;
  font-family:{_SERIF};
  color:{_BODY};
  box-sizing:border-box;
">

  {_logo_header(logo_b64)}
  {_divider()}

  <div style="text-align:center; padding:6px 0 10px 0;">
    <div style="color:{_PERGAMENT}; font-size:1.65em; font-weight:bold;
      letter-spacing:0.10em; text-transform:uppercase; line-height:1.1;">{ctx['name']}</div>
    <div style="color:{_MOSS}; font-size:0.88em; font-style:italic;
      letter-spacing:0.04em; margin-top:5px;">{stil}</div>
  </div>

  {_divider()}

  <table style="width:100%; border-collapse:collapse; margin:2px 0 8px 0;">
    <tr>{stat_heads}</tr>
    <tr>{stat_vals}</tr>
  </table>

  {_divider()}

  <div style="font-size:0.65em; color:{_GOLD}; letter-spacing:0.14em;
    text-transform:uppercase; margin-bottom:5px;">Meskeplan</div>
  <table style="width:100%; border-collapse:collapse; margin-bottom:12px;">
    {_malt_rows_dark(ctx, malt_db)}
  </table>

  <div style="font-size:0.65em; color:{_GOLD}; letter-spacing:0.14em;
    text-transform:uppercase; margin-bottom:5px;">Kokeplan</div>
  <table style="width:100%; border-collapse:collapse; margin-bottom:12px;">
    {_hop_rows_dark(ctx, humle_db)}
  </table>

  <div style="font-size:0.65em; color:{_GOLD}; letter-spacing:0.14em;
    text-transform:uppercase; margin-bottom:5px;">Gjær</div>
  <div style="color:{_BODY}; font-size:0.94em; margin-bottom:12px;">{gjaer_navn}</div>

  <div style="background:{_BG_SECT}; border-left:3px solid {_COPPER};
    padding:8px 12px; border-radius:0 4px 4px 0; margin-bottom:12px;">
    <div style="font-size:0.65em; color:{_GOLD}; letter-spacing:0.14em;
      text-transform:uppercase; margin-bottom:4px;">Smaksprofil</div>
    <div style="color:{_BODY}; font-size:0.90em; line-height:1.5;
      font-style:italic;">{summary}</div>
  </div>

  {_divider()}

  <div style="display:flex; justify-content:space-between; align-items:baseline;
    font-size:0.76em; color:{_MUTED}; margin-bottom:10px;">
    <span>{ctx['volum']:.0f} L&nbsp;&nbsp;·&nbsp;&nbsp;{_today_no()}</span>
    <span>Estimert pris: {ctx['total_pris']:.0f} kr</span>
  </div>

  <div style="text-align:center; border-top:1px solid {_GOLD};
    padding-top:9px; opacity:0.80;">
    <div style="color:{_ELFENBEIN}; font-size:0.77em; font-style:italic;
      letter-spacing:0.05em; margin-bottom:3px;">Brygg med ild. Del med ære.</div>
    <div style="color:{_GOLD}; font-size:0.60em; letter-spacing:0.20em;
      text-transform:uppercase;">Håndverk&nbsp;&nbsp;•&nbsp;&nbsp;Tradisjon&nbsp;&nbsp;•&nbsp;&nbsp;Karakter</div>
  </div>

</div>"""


# ── A4 print document ─────────────────────────────────────────────────────────

def _malt_rows_a4(ctx: dict, malt_db: dict) -> str:
    malts = ctx["recipe"].get("malts", [])
    rows = []
    for m in malts:
        info = malt_db.get(m["id"], {})
        navn = info.get("display_name", m["id"])
        kg   = m.get("mengde", 0)
        rows.append(f"<li>{navn}: <strong>{kg:.2f} kg</strong></li>")
    return "".join(rows) if rows else "<li>Ingen malt valgt</li>"


def _hop_rows_a4(ctx: dict, humle_db: dict) -> str:
    hops = sorted(ctx["recipe"].get("hops", []), key=lambda h: h.get("tid", 0), reverse=True)
    rows = []
    for h in hops:
        info      = humle_db.get(h["id"], {})
        navn      = info.get("display_name", h["id"])
        gram      = h.get("gram", 0)
        tid       = h.get("tid", 0)
        tid_label = "tørrhumle" if tid == 0 else f"@{tid} min"
        rows.append(f"<li>{navn}: <strong>{gram:.0f} g</strong> {tid_label}</li>")
    return "".join(rows) if rows else "<li>Ingen humle valgt</li>"


def render_a4_html(
    ctx:      dict,
    malt_db:  dict,
    humle_db: dict,
    gjaer_db: dict,
) -> str:
    stil       = ctx["style_analysis"].get("stil", "")
    gjaer_id   = ctx["recipe"].get("yeast", "")
    gjaer_navn = gjaer_db.get(gjaer_id, {}).get("display_name", gjaer_id)
    summary    = ctx["summary"].replace("**", "")
    gold_a4    = "#8a6a10"   # darker gold — readable on white paper

    return f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>{ctx['name']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Palatino Linotype', Palatino, 'Book Antiqua', Georgia, serif;
    font-size: 11pt; color: #111; background: #fff;
    padding: 12mm 14mm 10mm 14mm;
  }}
  h1 {{ font-size: 18pt; color: #111; letter-spacing: 0.06em; margin-bottom: 1px; }}
  .stil {{ font-size: 10pt; color: {gold_a4}; font-style: italic; margin-bottom: 2px; }}
  .sub {{ font-size: 9pt; color: #555; margin-bottom: 8px;
          padding-bottom: 6px; border-bottom: 1.5px solid {gold_a4}; }}
  h2 {{
    font-size: 8pt; font-weight: bold; text-transform: uppercase;
    letter-spacing: 0.12em; color: {gold_a4};
    border-bottom: 1px solid #ddd; padding-bottom: 2px;
    margin: 9px 0 4px 0;
  }}
  ul {{ list-style: disc; padding-left: 16px; margin-bottom: 2px; }}
  li {{ margin: 2px 0; line-height: 1.5; }}
  .stats {{
    display: grid; grid-template-columns: repeat(5, 1fr);
    gap: 5px; margin: 6px 0 4px 0;
  }}
  .stat {{
    border: 1px solid #ccc; border-radius: 3px;
    text-align: center; padding: 4px 2px;
  }}
  .slabel {{ font-size: 7pt; color: #777; text-transform: uppercase; letter-spacing: 0.1em; }}
  .sval   {{ font-size: 13pt; font-weight: bold; line-height: 1.3; }}
  .smak   {{ font-size: 9pt; color: #444; font-style: italic;
             margin-top: 3px; line-height: 1.4; }}
  .footer {{
    margin-top: 10px; border-top: 1px solid {gold_a4}; padding-top: 6px;
    font-size: 7.5pt; color: #888; text-align: center; letter-spacing: 0.06em;
  }}
  .motto {{ font-size: 8pt; color: {gold_a4}; font-style: italic; }}
  @media print {{
    @page {{ size: A4; margin: 0; }}
    body {{ padding: 10mm 12mm 8mm 12mm; }}
  }}
</style>
</head>
<body>
  <h1>{ctx['name']}</h1>
  <div class="stil">{stil}</div>
  <p class="sub">
    {ctx['volum']:.0f} L &nbsp;·&nbsp;
    {_today_no()} &nbsp;·&nbsp;
    Kvernhaug Brygghus — Ved Dalelva i Åsane
  </p>

  <h2>Statistikk</h2>
  <div class="stats">
    <div class="stat"><div class="slabel">OG</div><div class="sval">{ctx['og']:.3f}</div></div>
    <div class="stat"><div class="slabel">FG</div><div class="sval">{ctx['fg']:.3f}</div></div>
    <div class="stat"><div class="slabel">ABV</div><div class="sval">{ctx['abv']:.1f}%</div></div>
    <div class="stat"><div class="slabel">IBU</div><div class="sval">{ctx['ibu']:.0f}</div></div>
    <div class="stat"><div class="slabel">EBC</div><div class="sval">{ctx['ebc']:.0f}</div></div>
  </div>
  <p class="smak">{summary}</p>

  <h2>Malt</h2>
  <ul>{_malt_rows_a4(ctx, malt_db)}</ul>

  <h2>Humle</h2>
  <ul>{_hop_rows_a4(ctx, humle_db)}</ul>

  <h2>Gjær</h2>
  <ul><li>{gjaer_navn}</li></ul>

  <div class="footer">
    <div class="motto">Brygg med ild. Del med ære.</div>
    <div style="margin-top:2px; letter-spacing:0.14em;">
      HÅNDVERK &nbsp;•&nbsp; TRADISJON &nbsp;•&nbsp; KARAKTER
    </div>
  </div>
</body>
</html>"""
