# modules/card_template.py
"""
Pure HTML templates for Kvernhaug Brygghus recipe cards.
No Streamlit imports — safe to call from any context.
  render_card_html()  → inline div for st.markdown(unsafe_allow_html=True)
  render_a4_html()    → full HTML document for download
"""
from __future__ import annotations
import datetime
from modules.export_format import (
    fmt_og, fmt_fg, fmt_abv, fmt_ibu, fmt_ebc,
    fmt_vol, fmt_kg, fmt_gram,
)

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


def _ornament() -> str:
    return (
        f"<div style='display:flex; align-items:center; gap:8px; margin:13px 0;'>"
        f"<div style='flex:1; height:1px; background:{_GOLD}; opacity:0.4;'></div>"
        f"<div style='color:{_GOLD}; font-size:0.55em; opacity:0.7;'>◆</div>"
        f"<div style='flex:1; height:1px; background:{_GOLD}; opacity:0.4;'></div>"
        f"</div>"
    )


def _section_head(label: str) -> str:
    return (
        f"<div style='font-size:0.60em; color:{_GOLD}; letter-spacing:0.16em; "
        f"text-transform:uppercase; border-bottom:1px solid rgba(196,154,42,0.25); "
        f"padding-bottom:4px; margin-bottom:7px;'>{label}</div>"
    )


def _ingredient_table(rows_html: str) -> str:
    return f"<table style='width:100%; border-collapse:collapse; margin-bottom:13px;'>{rows_html}</table>"


def _malt_rows(ctx: dict, malt_db: dict) -> str:
    malts    = ctx["recipe"].get("malts", [])
    total_kg = sum(m.get("mengde", 0) for m in malts) or 1.0
    rows     = []
    for m in malts:
        info = malt_db.get(m["id"], {})
        navn = info.get("display_name", m["id"])
        kg   = m.get("mengde", 0)
        pct  = kg / total_kg * 100
        rows.append(
            f"<tr>"
            f"<td style='padding:3px 8px 3px 0; color:{_BODY}; font-size:0.94em;'>{navn}</td>"
            f"<td style='padding:3px 5px; color:{_BODY}; text-align:right; white-space:nowrap; font-size:0.94em;'>{fmt_kg(kg)}</td>"
            f"<td style='padding:3px 0 3px 6px; color:{_MUTED}; text-align:right; font-size:0.80em;'>{pct:.0f}%</td>"
            f"</tr>"
        )
    return "".join(rows) if rows else (
        f"<tr><td colspan='3' style='color:{_MUTED}; font-style:italic; font-size:0.88em;'>Ingen malt valgt</td></tr>"
    )


def _hop_rows(ctx: dict, humle_db: dict) -> str:
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
            f"<td style='padding:3px 8px 3px 0; color:{_BODY}; font-size:0.94em;'>{navn}</td>"
            f"<td style='padding:3px 5px; color:{_BODY}; text-align:right; white-space:nowrap; font-size:0.94em;'>{fmt_gram(gram)}</td>"
            f"<td style='padding:3px 0 3px 6px; color:{_MUTED}; text-align:right; font-size:0.80em;'>{tid_label}</td>"
            f"</tr>"
        )
    return "".join(rows) if rows else (
        f"<tr><td colspan='3' style='color:{_MUTED}; font-style:italic; font-size:0.88em;'>Ingen humle valgt</td></tr>"
    )


def _stat_boxes(ctx: dict) -> str:
    stats = [
        ("OG",  fmt_og(ctx["og"])),
        ("FG",  fmt_fg(ctx["fg"])),
        ("ABV", fmt_abv(ctx["abv"])),
        ("IBU", fmt_ibu(ctx["ibu"])),
        ("EBC", fmt_ebc(ctx["ebc"])),
    ]
    boxes = "".join(
        f"<div style='"
        f"flex:1; border:1px solid {_GOLD}; border-radius:4px; "
        f"background:rgba(196,154,42,0.06); text-align:center; "
        f"padding:9px 3px 8px 3px;'>"
        f"<div style='font-size:0.55em; color:{_GOLD}; letter-spacing:0.18em; "
        f"text-transform:uppercase; margin-bottom:5px;'>{lbl}</div>"
        f"<div style='font-size:1.12em; font-weight:bold; color:{_PERGAMENT}; line-height:1;'>{val}</div>"
        f"</div>"
        for lbl, val in stats
    )
    return f"<div style='display:flex; gap:6px; margin:0 0 2px 0;'>{boxes}</div>"


def render_card_html(
    ctx:      dict,
    malt_db:  dict,
    humle_db: dict,
    gjaer_db: dict,
    mode:     str = "card",
    logo_b64: str | None = None,
) -> str:
    stil        = ctx["style_analysis"].get("stil", "")
    brygger_stil = ctx.get("brygger_stil", "").strip()
    gjaer_id    = ctx["recipe"].get("yeast", "")
    gjaer_navn  = gjaer_db.get(gjaer_id, {}).get("display_name", gjaer_id)
    summary     = ctx["summary"].replace("**", "")

    # BJCP-score for dominant match
    _stil_score = next(
        (s["score"] for s in ctx["style_analysis"].get("stil_liste", []) if s["stil"] == stil),
        None,
    )

    # Stilblokk: bryggerstil primær + BJCP sekundær, eller bare BJCP
    if brygger_stil:
        _score_txt = f" · {_stil_score}%" if _stil_score is not None else ""
        stil_html = (
            f"<div style='color:{_MOSS}; font-size:0.95em; font-style:italic; "
            f"letter-spacing:0.04em; margin-top:7px;'>{brygger_stil}</div>"
            f"<div style='color:{_MUTED}; font-size:0.62em; "
            f"letter-spacing:0.06em; margin-top:5px;'>Stilmatch: {stil}{_score_txt}</div>"
        )
    else:
        stil_html = (
            f"<div style='color:{_MOSS}; font-size:0.87em; font-style:italic; "
            f"letter-spacing:0.04em; margin-top:7px;'>{stil}</div>"
        )

    logo_block = ""
    if logo_b64:
        logo_block = (
            f"<img src='data:image/png;base64,{logo_b64}' "
            f"style='height:300px; width:auto; display:block; "
            f"margin:6px auto 16px auto; opacity:0.95;'>"
        )

    orn = _ornament()

    return f"""<div style="
  background:{_BG};
  border:1.5px solid {_GOLD};
  border-radius:8px;
  padding:22px 22px 18px 22px;
  font-family:{_SERIF};
  color:{_BODY};
  box-sizing:border-box;
">

  <!-- ── BRAND HEADER ─────────────────────────────────────── -->
  <div style="text-align:center; padding-bottom:2px;">
    {logo_block}
    <div style="
      color:{_PERGAMENT}; font-weight:bold;
      font-size:1.0em; letter-spacing:0.20em;
      text-transform:uppercase; margin-bottom:3px;
    ">Kvernhaug Brygghus</div>
    <div style="
      color:{_GOLD}; font-size:0.60em;
      letter-spacing:0.22em; text-transform:uppercase; opacity:0.80;
    ">Ved Dalelva i Åsane</div>
  </div>

  {orn}

  <!-- ── ØLNAVN ────────────────────────────────────────────── -->
  <div style="text-align:center; padding:6px 0 14px 0;">
    <div style="
      color:{_PERGAMENT};
      font-size:2.15em;
      font-weight:bold;
      letter-spacing:0.13em;
      text-transform:uppercase;
      line-height:1.1;
    ">{ctx['name']}</div>
    {stil_html}
  </div>

  {orn}

  <!-- ── STATS ─────────────────────────────────────────────── -->
  {_stat_boxes(ctx)}

  {orn}

  <!-- ── INGREDIENSER ──────────────────────────────────────── -->
  {_section_head("Meskeplan")}
  {_ingredient_table(_malt_rows(ctx, malt_db))}

  {_section_head("Kokeplan")}
  {_ingredient_table(_hop_rows(ctx, humle_db))}

  {_section_head("Gjær")}
  <div style="color:{_BODY}; font-size:0.94em; margin-bottom:4px;">{gjaer_navn}</div>

  {orn}

  <!-- ── SMAKSPROFIL ───────────────────────────────────────── -->
  <div style="
    background:linear-gradient(135deg, #1e150a 0%, #140e07 100%);
    border:1px solid rgba(196,154,42,0.28);
    border-left:3px solid {_GOLD};
    padding:12px 15px 13px 15px;
    border-radius:0 5px 5px 0;
    margin-bottom:4px;
  ">
    <div style="
      font-size:0.60em; color:{_GOLD};
      letter-spacing:0.16em; text-transform:uppercase;
      margin-bottom:7px;
    ">Smaksprofil</div>
    <div style="
      color:{_PERGAMENT};
      font-size:0.91em;
      line-height:1.58;
      font-style:italic;
    ">{summary}</div>
  </div>

  {orn}

  <!-- ── FOOTER ────────────────────────────────────────────── -->
  <div style="text-align:center;">
    <div style="
      color:{_MUTED}; font-size:0.72em;
      letter-spacing:0.04em; margin-bottom:9px;
    ">{fmt_vol(ctx['volum'])}&nbsp;&nbsp;·&nbsp;&nbsp;{_today_no()}&nbsp;&nbsp;·&nbsp;&nbsp;{ctx['total_pris']:.0f} kr</div>
    <div style="
      color:{_ELFENBEIN}; font-size:0.80em;
      font-style:italic; letter-spacing:0.05em;
      margin-bottom:5px;
    ">Brygg med ild. Del med ære.</div>
    <div style="
      color:{_GOLD}; font-size:0.58em;
      letter-spacing:0.24em; text-transform:uppercase;
      opacity:0.80;
    ">Håndverk&nbsp;&nbsp;•&nbsp;&nbsp;Tradisjon&nbsp;&nbsp;•&nbsp;&nbsp;Karakter</div>
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
        rows.append(f"<li>{navn}: <strong>{fmt_kg(kg)}</strong></li>")
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
        rows.append(f"<li>{navn}: <strong>{fmt_gram(gram)}</strong> {tid_label}</li>")
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
    {fmt_vol(ctx['volum'])} &nbsp;·&nbsp;
    {_today_no()} &nbsp;·&nbsp;
    Kvernhaug Brygghus — Ved Dalelva i Åsane
  </p>

  <h2>Statistikk</h2>
  <div class="stats">
    <div class="stat"><div class="slabel">OG</div><div class="sval">{fmt_og(ctx['og'])}</div></div>
    <div class="stat"><div class="slabel">FG</div><div class="sval">{fmt_fg(ctx['fg'])}</div></div>
    <div class="stat"><div class="slabel">ABV</div><div class="sval">{fmt_abv(ctx['abv'])}</div></div>
    <div class="stat"><div class="slabel">IBU</div><div class="sval">{fmt_ibu(ctx['ibu'])}</div></div>
    <div class="stat"><div class="slabel">EBC</div><div class="sval">{fmt_ebc(ctx['ebc'])}</div></div>
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
