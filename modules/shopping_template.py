from modules.export_format import logo_img_tag, fmt_vol, fmt_kg, fmt_gram, esc


def render_shopping_list_html(ctx: dict, malt_items: list, humle_items: list, gjaer_item: dict | None, butikk: str) -> str:
    logo_img = logo_img_tag(24)

    def _rad(navn, mengde_str, total, er_estimat, url):
        est = " <em>(estimert)</em>" if er_estimat else ""
        navn_esc = esc(navn)
        # `url` kommer i siste instans fra skrapet butikkdata
        # (butikk_match.*.url i masterdatabasene) -- escapes FØR den
        # havner i et anførselstegn-omsluttet href-attributt, slik at et
        # anførselstegn i en (kompromittert/uventet) produkt-URL aldri kan
        # bryte ut av attributtet.
        lenke = f"<a href='{esc(url)}'>{navn_esc}</a>" if url else navn_esc
        return (
            f"<tr>"
            f"<td>{lenke}</td>"
            f"<td class='r'>{mengde_str}</td>"
            f"<td class='r'>ca {total:.0f} kr{est}</td>"
            f"</tr>"
        )

    malt_rows = "".join(
        _rad(m["navn"], f"{m['mengde']:.2f} kg", m["total"], m["er_estimat"], m["url"])
        for m in malt_items
    ) or "<tr><td colspan='3'>Ingen malt.</td></tr>"

    humle_rows = "".join(
        _rad(h["navn"], f"{h['gram']:.0f} g ({h['tid']} min)", h["total"], h["er_estimat"], h["url"])
        for h in humle_items
    ) or "<tr><td colspan='3'>Ingen humle.</td></tr>"

    gjaer_rows = ""
    if gjaer_item:
        g = gjaer_item
        gjaer_rows = _rad(g["navn"], "1 pakke", g["pris"], g["er_estimat"], g["url"])
    else:
        gjaer_rows = "<tr><td colspan='3'>Ingen gjær valgt.</td></tr>"

    total_sum = (
        sum(m["total"] for m in malt_items)
        + sum(h["total"] for h in humle_items)
        + (gjaer_item["pris"] if gjaer_item else 0)
    )

    return f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Handleliste — {esc(ctx['name'])}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt; color: #111; background: #fff;
    padding: 8mm 10mm 6mm 10mm;
  }}
  .kbh-header {{
    display: flex; align-items: center; gap: 5mm;
    border-bottom: 2px solid #222; padding-bottom: 3px; margin-bottom: 6px;
  }}
  .kbh-header img {{ height: 24px; opacity: 0.85; }}
  .kbh-name {{ font-size: 9.5pt; font-weight: bold; letter-spacing: 0.04em; }}
  .kbh-sub  {{ font-size: 8pt; color: #666; margin-left: 3px; }}
  h1 {{ font-size: 16pt; font-weight: bold; margin: 4px 0 1px 0; }}
  .meta {{ font-size: 9pt; color: #555; margin-bottom: 8px; }}
  h2 {{
    font-size: 10pt; font-weight: bold; text-transform: uppercase;
    letter-spacing: 0.06em; border-bottom: 1.5px solid #555;
    padding-bottom: 2px; margin: 10px 0 4px 0;
  }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 2px; }}
  td {{ padding: 4px 6px; border-bottom: 1px dotted #ccc; font-size: 10.5pt; }}
  td.r {{ text-align: right; white-space: nowrap; }}
  a {{ color: #111; }}
  .totallinje {{
    border-top: 2px solid #333; margin-top: 10px;
    padding-top: 6px; text-align: right;
    font-size: 12pt; font-weight: bold;
  }}
  .footer {{
    margin-top: 12px; border-top: 1px solid #ccc;
    padding-top: 5px; font-size: 8pt; color: #888; text-align: center;
  }}
  @media print {{
    @page {{ size: A4; margin: 0; }}
    body {{ padding: 7mm 9mm 5mm 9mm; }}
    a {{ text-decoration: none; color: #111; }}
  }}
</style>
</head>
<body>

<div class="kbh-header">
  {logo_img}
  <span class="kbh-name">KVERNHAUG BRYGGHUS</span>
  <span class="kbh-sub">· Ved Dalelva i Åsane</span>
</div>

<h1>{esc(ctx['name'])}</h1>
<p class="meta">{fmt_vol(ctx['volum'])} &nbsp;·&nbsp; Butikk: {esc(butikk)}</p>

<h2>Malt</h2>
<table>{malt_rows}</table>

<h2>Humle</h2>
<table>{humle_rows}</table>

<h2>Gjær</h2>
<table>{gjaer_rows}</table>

<div class="totallinje">TOTAL: ca {total_sum:.0f} kr</div>

<div class="footer">Kvernhaug Brygghus &nbsp;·&nbsp; Brygg med ild. Del med ære.</div>

</body>
</html>"""
