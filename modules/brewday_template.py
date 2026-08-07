from modules.export_format import (
    fmt_kg, fmt_gram, fmt_ibu_bid,
    fmt_og, fmt_fg, fmt_abv,
    stats_linje, logo_img_tag, esc,
)


def render_brewday_html(ctx: dict, plan: dict, log: dict = None, water: dict = None) -> str:
    log = log or {}
    water = water or {}
    w   = plan["vann"]

    logo_img = logo_img_tag(24)

    # ── Malt list ─────────────────────────────────────────────────────────
    malt_li = "".join(
        f"<li><span class='cb'>☐</span><span class='m-kg'>{fmt_kg(m['mengde'])}</span>{esc(m['navn'])}</li>"
        for m in plan["malt_liste"]
    ) or "<li>Ingen malt registrert.</li>"

    # ── Maskeplan ─────────────────────────────────────────────────────────
    maskeplan_li = "".join(
        f"<li><span class='cb'>☐</span> {s['temp_c']}°C – {s['varighet_min']} min <em>({esc(s['label'])})</em></li>"
        for s in plan["maskeplan"]
    )

    # ── Hop table — minimum 5 visible rows ────────────────────────────────
    # Rader der humlens EGEN oppgitte koketid overstiger kokens totale
    # lengde (h["tid_over_koketid"], se
    # modules/brewday_calc.py::_bygg_humle_entry) markeres tydelig -- IBU-
    # kolonnen viser fortsatt oppskriftens PLANLAGTE bidrag (ibu_bidrag,
    # uendret tid), aldri det stille klippede tallet, men raden i seg selv
    # varsler at det ikke er fysisk oppnåelig som oppgitt.
    humle_data_rows = "".join(
        f"<tr{' class=\"rad-avvik\"' if h.get('tid_over_koketid') else ''}>"
        f"<td>{'⚠️ ' if h.get('tid_over_koketid') else ''}{h['tid']} min</td>"
        f"<td>{h.get('tilsatt_etter_min', 0)} min</td><td>{esc(h['navn'])}</td>"
        f"<td>{fmt_gram(h['gram'])}</td><td>{fmt_ibu_bid(h['ibu_bidrag'])}</td></tr>"
        for h in plan["humleplan"]
    )
    n_tomme = max(0, 5 - len(plan["humleplan"]))
    humle_tomme_rows = "".join(
        "<tr><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td><td>&nbsp;</td></tr>"
        for _ in range(n_tomme)
    )
    humle_rows = humle_data_rows + humle_tomme_rows or (
        "<tr><td colspan='5'>Ingen humle.</td></tr>" + humle_tomme_rows
    )

    # Et eget, tydelig AVVIK-panel rett under tabellen -- vises KUN når
    # det faktisk finnes en umulig humletid (plan["humle_over_koketid"]),
    # slik at en vanlig oppskrift uten avvik beholder dagens rene layout
    # helt uendret. Viser oppgitt tid, total koketid, OG begge IBU-tallene
    # side om side, slik at en umulig IBU aldri kan stå alene som om den
    # var gyldig -- heller ikke etter at siden er skrevet ut eller åpnet
    # på nytt uten Streamlit-sesjonen som viste det opprinnelige varselet.
    humle_avvik_html = ""
    if plan.get("humle_over_koketid"):
        avvik_li = "".join(
            f"<li>{esc(h['navn'])}: oppgitt <strong>{h['tid']} min</strong> "
            f"— total koketid er kun <strong>{plan['koketid_min']} min</strong></li>"
            for h in plan["humle_over_koketid"]
        )
        humle_avvik_html = f"""
    <div class="ibu-avvik">
      <p class="ibu-avvik-tittel">⚠️ AVVIK: humletid overstiger total koketid — IBU under er IKKE fysisk oppnåelig som oppgitt</p>
      <ul>{avvik_li}</ul>
      <div class="ibu-avvik-sammenligning">
        <div><span class="ibu-avvik-lbl">Planlagt IBU</span><span class="ibu-avvik-val">{fmt_ibu_bid(plan['ibu_planlagt'])}</span></div>
        <div><span class="ibu-avvik-lbl">Faktisk mulig IBU</span><span class="ibu-avvik-val">{fmt_ibu_bid(plan['ibu_faktisk_prosess'])}</span></div>
      </div>
    </div>"""

    # ── Vannbehandling (se modules/water_chemistry.py) ───────────────────────
    vann_kilde      = water.get("kilde")
    vann_maal       = water.get("maal")
    vann_behandling = water.get("behandling") or {}
    vann_maalinger  = water.get("maalinger") or {}
    vann_salter     = vann_behandling.get("salter") or []

    vannkilde_li = (
        f"<li><span class='cb'>☐</span> Vannkilde: <strong>{esc(vann_kilde['name'])}</strong></li>"
        if vann_kilde and vann_kilde.get("name") else ""
    )
    # Navnet hentes fra profilens EGEN "name" — aldri target_id — og fra
    # den FROSNE snapshotten som fulgte med denne oppskriften (water_target_
    # profile), ikke fra det gjeldende biblioteket i data/water_targets.json.
    # Et senere redigert/omdøpt bibliotek skal derfor ALDRI kunne endre
    # navnet en allerede lagret oppskrift viser fram.
    maalprofil_navn = (vann_maal or {}).get("name")
    maalprofil_li = f"<li>Målprofil: <strong>{esc(maalprofil_navn or 'Ikke valgt')}</strong></li>"
    salter_mesk_li = "".join(
        f"<li><span class='cb'>☐</span> {esc(s['navn'])} ({esc(s['kjemisk_form'])}) i meskevann: <strong>{s['gram_mesk']:.2f} g</strong></li>"
        for s in vann_salter if s.get("gram_mesk", 0) > 0.005
    )
    salter_skyll_li = "".join(
        f"<li><span class='cb'>☐</span> {esc(s['navn'])} ({esc(s['kjemisk_form'])}) i skyllevann: <strong>{s['gram_skyll']:.2f} g</strong></li>"
        for s in vann_salter if s.get("gram_skyll", 0) > 0.005
    )
    mash_ph_maal_li = (
        f"<li>Mål meske-pH: <strong>{vann_maal['mash_ph_min']:.2f}–{vann_maal['mash_ph_max']:.2f}</strong></li>"
        if vann_maal and vann_maal.get("mash_ph_min") is not None else ""
    )
    faktisk_ph = vann_maalinger.get("maalt_mash_ph")
    faktisk_ph_val = f"{faktisk_ph:.2f}" if faktisk_ph else ""
    maaletemp_val = "Romtemperatur" if vann_maalinger.get("malt_ved_romtemperatur") else ""
    syrer_tilsatt_val = ", ".join(
        f"{esc(s['navn'])} {s['mengde_ml']:.1f} mL" + (f" ({s['prosent']:.0f}%)" if s.get("prosent") else " (konsentrasjon ikke angitt)")
        for s in (vann_maalinger.get("syrer") or [])
    )

    # ── Prosessprofil / bryggemåte ──────────────────────────────────────────
    prosess_profil = plan.get("prosess_profil")
    prosess_line = (
        f"<p class='recipe-stil'>Bryggemåte: {esc(prosess_profil['navn'])}</p>"
        if prosess_profil else ""
    )
    dekoksjon_li = ""
    if plan.get("dekoksjon"):
        d = plan["dekoksjon"]
        dekoksjon_li = (
            f"<li class='note'>🔥 Dekoksjon: ta ut {d['uttak_liter']:.2f} L tykkmesk ved "
            f"{d['fra_temp_c']}°C, kok {d['koketid_min']} min, før tilbake for å nå {d['til_temp_c']}°C.</li>"
        )
    reiterated_li = ""
    if plan.get("reiterated_mash_flyt"):
        r = plan["reiterated_mash_flyt"]
        reiterated_li = (
            f"<li class='note'>🔁 Dobbelmesk: Mesk 1 ({r['malt_1_kg']:.2f} kg + {r['vann_mesk_1_l']:.1f} L "
            f"ferskt vann → {r['vort_1_l']:.1f} L vørt) brukes som meskevann til Mesk 2 "
            f"({r['malt_2_kg']:.2f} kg → {r['vort_2_l']:.1f} L sluttvørt).</li>"
        )

    # ── Brewing additions ─────────────────────────────────────────────────
    tilsetninger = plan.get("tilsetninger", [])
    tilsetninger_html = ""
    if tilsetninger:
        rows_t = "".join(
            f"<tr><td>{esc(t['navn'])}</td><td>{esc(t['dose'])}</td><td>{esc(t['timing'])}</td></tr>"
            for t in tilsetninger
        )
        tilsetninger_html = f"""
    <h2>Tilsetninger</h2>
    <table class="humle">
      <tr><th>Tilsetning</th><th>Dose</th><th>Tidspunkt</th></tr>
      {rows_t}
    </table>"""

    # ── Gjær notes ────────────────────────────────────────────────────────
    noter_li = "".join(f"<li class='note'>ℹ️ {esc(n)}</li>" for n in plan["noter"])
    dms_note = (
        "<li class='note'>90 min anbefalt for Pilsnermalt</li>"
        if plan["koketid_min"] == 90 else ""
    )
    stil_line = (
        f"<p class='recipe-stil'>{esc(ctx['brygger_stil'])}</p>"
        if ctx.get("brygger_stil") else ""
    )

    # ── Log pre-fills ─────────────────────────────────────────────────────
    # og_v/fg_v/abv_v kommer fra FRITEKST-felter (st.text_input) i
    # ui/brewday_panel.py Steg 4/5 -- brukerinnlagt, ikke tallformatert
    # her i Python, og må derfor escapes før de havner i det nedlastede
    # HTML-dokumentet.
    pre_sg_v    = f"{log['pre_boil_sg']:.3f}" if log.get("pre_boil_sg", 1.000) > 1.001 else ""
    pre_vol_v   = f"{log['pre_boil_vol']:.1f} L" if log.get("pre_boil_vol", 0) > 0 else ""
    post_vol_v  = f"{log['post_boil_vol']:.1f} L" if log.get("post_boil_vol", 0) > 0 else ""
    og_v        = esc(log.get("og", ""))
    fg_v        = esc(log.get("fg", ""))
    abv_v       = esc(log.get("abv", ""))
    pitch_v     = f"{log['pitch_temp']:.1f}°C" if log.get("pitch_temp", 0) > 0 else ""
    mash_eff_v  = f"{log['mash_eff'] * 100:.1f}%" if log.get("mash_eff", 0) > 0 else ""
    bh_eff_v    = f"{log['brewhouse_eff'] * 100:.1f}%" if log.get("brewhouse_eff", 0) > 0 else ""

    def stat_box(label, maal="", faktisk=""):
        maal_html = f"<div class='stat-maal'>{maal}</div>" if maal else ""
        fakt_val  = f"<div class='stat-faktisk-val'>{faktisk}</div>" if faktisk else ""
        fakt_line = "<div class='stat-faktisk-line'></div>" if not faktisk else ""
        return f"""<div class="stat-box">
      <div class="stat-label">{label}</div>
      {maal_html}
      <div class="stat-faktisk-lbl">{'Faktisk:' if maal else 'Målt:'}</div>
      {fakt_val}{fakt_line}
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Bryggedagsark — {esc(ctx['name'])}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: Arial, Helvetica, sans-serif;
    font-size: 11pt;
    color: #111;
    background: #fff;
    padding: 8mm 10mm 6mm 10mm;
  }}

  /* ── HEADER ── */
  .header {{
    display: flex;
    align-items: center;
    gap: 5mm;
    border-bottom: 2px solid #222;
    padding-bottom: 3px;
    margin-bottom: 4px;
  }}
  .header img {{ height: 24px; opacity: 0.85; }}
  .kbh-name {{ font-size: 9.5pt; font-weight: bold; letter-spacing: 0.04em; }}
  .kbh-sub  {{ font-size: 8pt; color: #666; margin-left: 3px; }}

  /* ── RECIPE TITLE ── */
  .recipe-title {{
    font-size: 22pt;
    font-weight: bold;
    margin: 5px 0 1px 0;
    line-height: 1.1;
  }}
  .recipe-stil {{
    font-size: 10pt;
    color: #555;
    font-style: italic;
    margin: 2px 0;
  }}
  .stats-bar {{
    font-size: 10pt;
    color: #333;
    padding-bottom: 4px;
    border-bottom: 1px solid #bbb;
    margin-bottom: 5px;
  }}

  /* ── BATCH-INFO ── */
  .batch-info {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4mm;
    margin: 5px 0;
  }}
  .bi-field .lbl {{ font-size: 9pt; color: #444; font-weight: bold; }}
  .bi-line {{
    border-bottom: 2px solid #666;
    height: 34px;
    margin-top: 2px;
  }}

  /* ── SEKSJONSOVERSKRIFTER ── */
  h2 {{
    font-size: 12pt;
    font-weight: bold;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    border-bottom: 1.5px solid #555;
    padding-bottom: 2px;
    margin: 8px 0 4px 0;
    color: #111;
  }}

  /* ── LISTER ── */
  ul.cb-list {{ list-style: none; margin: 0; padding: 0; }}
  ul.cb-list li {{
    margin: 3px 0;
    font-size: 11pt;
    line-height: 1.6;
  }}
  .cb {{ font-size: 12pt; margin-right: 4px; }}
  .note {{ font-size: 9pt; color: #555; font-style: italic; }}

  /* ── MALTLISTE: kolonnejustert ── */
  ul.malt-list {{ list-style: none; margin: 0; padding: 0; }}
  ul.malt-list li {{
    display: flex;
    align-items: baseline;
    gap: 6px;
    margin: 2px 0;
    font-size: 11pt;
    line-height: 1.6;
  }}
  .m-kg {{ min-width: 55px; font-weight: bold; flex-shrink: 0; }}

  /* ── LAYOUT ── */
  .main {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 8mm; }}
  .divider {{ border-top: 2px solid #333; margin: 8px 0 5px 0; }}

  /* ── HUMLE- OG TILSETNINGS-TABELL ── */
  table.humle {{
    width: 100%;
    border-collapse: collapse;
    font-size: 11pt;
    margin-top: 2px;
  }}
  table.humle th {{
    background: #ebebeb;
    padding: 3px 7px;
    text-align: left;
    font-size: 9pt;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1.5px solid #888;
  }}
  table.humle td {{
    padding: 4px 7px;
    border-bottom: 1px dotted #ccc;
    font-size: 10pt;
  }}
  table.humle tr.rad-avvik td {{
    background: #fdf1f1;
    font-weight: bold;
  }}

  /* ── HUMLETID/IBU-AVVIK (se modules/brewday_calc.py sin
     tid_over_koketid/ibu_faktisk_prosess) -- vises ALLTID på papiret når
     en humle er tilsatt med lengre egen koketid enn selve kokens totale
     lengde, slik at avviket ikke forsvinner sammen med Streamlit-
     varselet når arket senere åpnes eller skrives ut. Farge ALENE er
     bevisst ikke eneste signal (kan falle bort ved svart/hvitt-utskrift)
     -- selve teksten i .ibu-avvik-tittel under bærer meningen uansett. */
  .ibu-avvik {{
    border: 2px solid #b02a2a;
    border-radius: 3px;
    background: #fdf1f1;
    padding: 5px 8px 6px 8px;
    margin-top: 4px;
  }}
  .ibu-avvik-tittel {{
    font-size: 9.5pt;
    font-weight: bold;
    color: #8a1f1f;
    margin-bottom: 3px;
  }}
  .ibu-avvik ul {{
    margin: 0 0 4px 0;
    padding-left: 16px;
  }}
  .ibu-avvik li {{
    font-size: 9pt;
    margin: 1px 0;
  }}
  .ibu-avvik-sammenligning {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 4px;
    margin-top: 4px;
  }}
  .ibu-avvik-lbl {{
    display: block;
    font-size: 8pt;
    color: #8a1f1f;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }}
  .ibu-avvik-val {{
    display: block;
    font-size: 13pt;
    font-weight: bold;
    color: #8a1f1f;
  }}

  /* ── FERMENTERING ── */
  .ferm-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 2px 5mm;
    margin-top: 4px;
  }}
  .field-lbl {{
    font-size: 9pt;
    color: #555;
    font-weight: bold;
    margin-top: 5px;
  }}
  .field-line {{
    border-bottom: 1.5px solid #888;
    height: 22px;
  }}

  /* ── SJEKKLISTE (1 rad) ── */
  .checklist {{
    display: grid;
    grid-template-columns: repeat(8, 1fr);
    gap: 2px 1mm;
    margin: 3px 0;
  }}
  .check-item {{ font-size: 9pt; white-space: nowrap; }}

  /* ── MÅLEBOKSER: 4-kolonne grid (2 rader) ── */
  .stats-4 {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 5px;
    margin-top: 3px;
  }}
  .stat-box {{
    border: 1.5px solid #888;
    border-radius: 3px;
    padding: 4px 7px 6px 7px;
    min-height: 17mm;
    display: flex;
    flex-direction: column;
  }}
  .stat-label {{
    font-size: 8.5pt;
    text-transform: uppercase;
    color: #555;
    font-weight: bold;
    letter-spacing: 0.05em;
  }}
  .stat-maal {{
    font-size: 12pt;
    font-weight: bold;
    margin: 3px 0 0 0;
  }}
  .stat-faktisk-lbl {{
    font-size: 8pt;
    color: #666;
    margin-top: auto;
    padding-top: 6px;
  }}
  .stat-faktisk-line {{
    border-bottom: 2px solid #555;
    height: 26px;
    margin-top: 3px;
  }}
  .stat-faktisk-val {{
    font-size: 13pt;
    font-weight: bold;
    margin-top: 3px;
  }}

  /* ── EFFEKTIVITET-RAD ── */
  .eff-row {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 5px;
    margin-top: 5px;
  }}
  .eff-field .eff-lbl {{
    font-size: 9pt;
    color: #444;
    font-weight: bold;
  }}
  .eff-field .eff-line {{
    border-bottom: 1.5px solid #888;
    height: 20px;
    margin-top: 2px;
  }}
  .eff-field .eff-val {{
    font-size: 11pt;
    font-weight: bold;
  }}

  /* ── NOTER: fyller gjenværende høyde ── */
  .page-wrapper {{
    display: flex;
    flex-direction: column;
  }}
  .notes-section {{
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
  }}
  .note-lines {{
    flex: 1;
    display: flex;
    flex-direction: column;
    padding-top: 4px;
    overflow: hidden;
  }}
  .note-lines div {{
    flex: 1;
    border-bottom: 1px solid #ccc;
    max-height: 36px;
  }}

  @media print {{
    @page {{ size: A4; margin: 0; }}
    body {{ padding: 7mm 9mm 5mm 9mm; }}
    .page-wrapper {{ min-height: 283mm; }}
  }}
</style>
</head>
<body>
<div class="page-wrapper">

<!-- HEADER -->
<div class="header">
  {logo_img}
  <span class="kbh-name">KVERNHAUG BRYGGHUS</span>
  <span class="kbh-sub">· Ved Dalelva i Åsane</span>
</div>

<!-- RECIPE NAME -->
<p class="recipe-title">{esc(ctx['name'])}</p>
{stil_line}
{prosess_line}
<p class="stats-bar">{stats_linje(ctx, html=True)}</p>

<!-- BATCH-INFO -->
<div class="batch-info">
  <div class="bi-field"><div class="lbl">Batchnummer</div><div class="bi-line"></div></div>
  <div class="bi-field"><div class="lbl">Bryggedato</div><div class="bi-line"></div></div>
  <div class="bi-field"><div class="lbl">Brygger</div><div class="bi-line"></div></div>
</div>

<div class="divider"></div>

<!-- HOVED: TO KOLONNER -->
<div class="main">

  <!-- VENSTRE: Malt · Vann · Mesking · Kok -->
  <div>
    <h2>Malt — {fmt_kg(plan['total_korn_kg'])}</h2>
    <ul class="malt-list">{malt_li}</ul>

    <h2>Vann</h2>
    <ul class="cb-list">
      {vannkilde_li}
      {maalprofil_li}
      <li><span class="cb">☐</span> Meskevann: <strong>{w['mash_vann_l']:.1f} L</strong></li>
      <li><span class="cb">☐</span> Skyllevann: <strong>{w['sparge_vann_l']:.1f} L</strong></li>
      <li><span class="cb">☐</span> Pre-boil: <strong>{w['pre_boil_l']:.1f} L</strong>
          &nbsp;<em style="font-size:9pt;color:#777;">(maks 30 L — BrewZilla)</em></li>
      {salter_mesk_li}{salter_skyll_li}{mash_ph_maal_li}
    </ul>
    <div class="ferm-grid" style="margin-top:2px;">
      <div>
        <div class="field-lbl">Faktisk meske-pH</div>
        <div class="field-line">{faktisk_ph_val}</div>
      </div>
      <div>
        <div class="field-lbl">Måletemperatur</div>
        <div class="field-line">{maaletemp_val}</div>
      </div>
    </div>
    <div style="margin-top:2px;">
      <div class="field-lbl">Syrer tilsatt</div>
      <div class="field-line">{syrer_tilsatt_val}</div>
    </div>

    <h2>Mesking</h2>
    <ul class="cb-list">{maskeplan_li}{dekoksjon_li}{reiterated_li}</ul>

    <h2>Koking</h2>
    <ul class="cb-list">
      <li><span class="cb">☐</span> {plan['koketid_min']} min kok
          &nbsp;·&nbsp; Est. koketap: <strong>{plan['estimert_koketap_l']:.1f} L</strong></li>
      {dms_note}
    </ul>
  </div>

  <!-- HØYRE: Humle · Tilsetninger · Gjær -->
  <div>
    <h2>Humle</h2>
    <table class="humle">
      <tr><th>Tid igjen</th><th>Tilsatt etter</th><th>Humle</th><th>Gram</th><th>IBU</th></tr>
      {humle_rows}
    </table>
    {humle_avvik_html}

    {tilsetninger_html}

    <h2>Gjær</h2>
    <ul class="cb-list">
      <li><span class="cb">☐</span> <strong>{esc(plan['gjaer_navn'])}</strong></li>
      <li><span class="cb">☐</span> {plan['pakker']} pakke(r) anbefalt</li>
      <li>Fermenterer {plan['temp_min']}–{plan['temp_maks']}°C</li>
      {noter_li}
    </ul>
    <div class="ferm-grid">
      <div>
        <div class="field-lbl">Gjæringsstart</div>
        <div class="field-line"></div>
      </div>
      <div>
        <div class="field-lbl">Cold crash / tapping</div>
        <div class="field-line"></div>
      </div>
    </div>
  </div>

</div><!-- /main -->

<!-- SJEKKLISTE -->
<div class="divider"></div>
<h2>Bryggedags-sjekkliste</h2>
<div class="checklist">
  <div class="check-item"><span class="cb">☐</span> Utstyr</div>
  <div class="check-item"><span class="cb">☐</span> Meskevann</div>
  <div class="check-item"><span class="cb">☐</span> Skylling</div>
  <div class="check-item"><span class="cb">☐</span> Kok</div>
  <div class="check-item"><span class="cb">☐</span> Humle</div>
  <div class="check-item"><span class="cb">☐</span> Nedkjølt</div>
  <div class="check-item"><span class="cb">☐</span> Gjær</div>
  <div class="check-item"><span class="cb">☐</span> Gjæring</div>
</div>

<!-- MÅLINGER: 4×2 grid -->
<div class="divider"></div>
<h2>Målinger</h2>
<div class="stats-4">
  {stat_box("Pre-boil SG",  "",                              pre_sg_v)}
  {stat_box("Pre-boil Vol", "",                              pre_vol_v)}
  {stat_box("Post-boil Vol","",                              post_vol_v)}
  {stat_box("OG",           f"Mål: {fmt_og(ctx['og'])}",    og_v)}
  {stat_box("FG",           f"Mål: {fmt_fg(ctx['fg'])}",    fg_v)}
  {stat_box("ABV",          f"Mål: {fmt_abv(ctx['abv'])}",  abv_v)}
  {stat_box("Pitch temp",   "",                              pitch_v)}
  {stat_box("Maskeeff",     "",                              mash_eff_v)}
</div>

<!-- EFFEKTIVITET & BH-EFF -->
<div class="eff-row" style="margin-top:6px;">
  <div class="eff-field">
    <div class="eff-lbl">Brygghuseffektivitet (plan: {ctx['effektivitet']*100:.0f}%)</div>
    {'<div class="eff-val">' + bh_eff_v + '</div>' if bh_eff_v else '<div class="eff-line"></div>'}
  </div>
  <div class="eff-field">
    <div class="eff-lbl">Beregnet ABV</div>
    {'<div class="eff-val">' + abv_v + '</div>' if abv_v else '<div class="eff-line"></div>'}
  </div>
  <div class="eff-field">
    <div class="eff-lbl">Batch til gjæring</div>
    <div class="eff-line"></div>
  </div>
</div>

<!-- NOTATER -->
<div class="notes-section">
  <div class="divider"></div>
  <h2>Notater</h2>
  <div class="note-lines">
    <div></div><div></div><div></div><div></div>
    <div></div><div></div><div></div><div></div>
  </div>
</div>

</div><!-- /page-wrapper -->
</body>
</html>"""
