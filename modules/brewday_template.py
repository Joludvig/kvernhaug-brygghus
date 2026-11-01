from modules.brewday_calc import (
    bryggedag_noter, fermenteringstemp_linjer, maskeplan_label_visning, tilsetning_visning,
)
from modules.i18n import SPRAK_DEFAULT, t
from modules.process_profiles import profilnavn_visning
from modules.water_chemistry import SALTER, maalprofil_tekst, salt_navn, syre_navn
from modules.export_format import (
    fmt_kg, fmt_gram, fmt_ibu_bid,
    fmt_og, fmt_fg, fmt_abv,
    stats_linje, logo_img_tag, esc,
)


def render_brewday_html(ctx: dict, plan: dict, log: dict = None, water: dict = None,
                        sprak: str = SPRAK_DEFAULT) -> str:
    log = log or {}
    water = water or {}
    w   = plan["vann"]

    def _t(nokkel, **params):
        return t(nokkel, sprak, **params)

    logo_img = logo_img_tag(24)

    # ── Malt list ─────────────────────────────────────────────────────────
    malt_li = "".join(
        f"<li><span class='cb'>☐</span><span class='m-kg'>{fmt_kg(m['mengde'])}</span>{esc(m['navn'])}</li>"
        for m in plan["malt_liste"]
    ) or f"<li>{_t('bx.ingen_malt')}</li>"

    # ── Maskeplan ─────────────────────────────────────────────────────────
    maskeplan_li = "".join(
        f"<li><span class='cb'>☐</span> {s['temp_c']}°C – {s['varighet_min']} min <em>({esc(maskeplan_label_visning(s, (plan.get('prosess_profil') or {}).get('process_id'), sprak))})</em></li>"
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
        f"<tr><td colspan='5'>{_t('bx.ingen_humle')}</td></tr>" + humle_tomme_rows
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
            "<li>" + _t(
                "bx.avvik.rad", navn=esc(h['navn']), tid=h['tid'], koketid=plan['koketid_min'],
            ) + "</li>"
            for h in plan["humle_over_koketid"]
        )
        humle_avvik_html = f"""
    <div class="ibu-avvik">
      <p class="ibu-avvik-tittel">{_t('bx.avvik.tittel')}</p>
      <ul>{avvik_li}</ul>
      <div class="ibu-avvik-sammenligning">
        <div><span class="ibu-avvik-lbl">{_t('bx.avvik.planlagt')}</span><span class="ibu-avvik-val">{fmt_ibu_bid(plan['ibu_planlagt'])}</span></div>
        <div><span class="ibu-avvik-lbl">{_t('bx.avvik.faktisk')}</span><span class="ibu-avvik-val">{fmt_ibu_bid(plan['ibu_faktisk_prosess'])}</span></div>
      </div>
    </div>"""

    # ── Vannbehandling (se modules/water_chemistry.py) ───────────────────────
    vann_kilde      = water.get("kilde")
    vann_maal       = water.get("maal")
    vann_behandling = water.get("behandling") or {}
    vann_maalinger  = water.get("maalinger") or {}
    vann_salter     = vann_behandling.get("salter") or []

    # Appens egne plassholdernavn for «ingen kilde valgt» lagres på norsk i
    # snapshotten; de vises i valgt språk. En brukerdefinert kildes navn
    # beholdes alltid uendret.
    def _kildenavn(kilde):
        if kilde.get("water_id") == "__ukjent__":
            return _t("bx.ukjent_kilde")
        if kilde.get("water_id") == "__ny_kilde__":
            return _t("bx.ny_kilde")
        return kilde["name"]

    vannkilde_li = (
        "<li><span class='cb'>☐</span> "
        + _t("bx.vannkilde", navn=esc(_kildenavn(vann_kilde))) + "</li>"
        if vann_kilde and vann_kilde.get("name") else ""
    )
    # Navnet hentes fra profilens EGEN "name" — aldri target_id — og fra
    # den FROSNE snapshotten som fulgte med denne oppskriften (water_target_
    # profile), ikke fra det gjeldende biblioteket i data/water_targets.json.
    # Et senere redigert/omdøpt bibliotek skal derfor ALDRI kunne endre
    # navnet en allerede lagret oppskrift viser fram.
    maalprofil_navn = maalprofil_tekst(vann_maal, "name", sprak) if vann_maal else None
    maalprofil_li = "<li>" + _t("bx.maalprofil", navn=esc(maalprofil_navn or _t("bx.ikke_valgt"))) + "</li>"

    def _saltnavn(s):
        return salt_navn(s["salt_id"], sprak) if s.get("salt_id") in SALTER else s["navn"]

    salter_mesk_li = "".join(
        "<li><span class='cb'>☐</span> " + _t(
            "bx.salt_mesk", navn=esc(_saltnavn(s)), form=esc(s['kjemisk_form']), g=f"{s['gram_mesk']:.2f}",
        ) + "</li>"
        for s in vann_salter if s.get("gram_mesk", 0) > 0.005
    )
    salter_skyll_li = "".join(
        "<li><span class='cb'>☐</span> " + _t(
            "bx.salt_skyll", navn=esc(_saltnavn(s)), form=esc(s['kjemisk_form']), g=f"{s['gram_skyll']:.2f}",
        ) + "</li>"
        for s in vann_salter if s.get("gram_skyll", 0) > 0.005
    )
    mash_ph_maal_li = (
        "<li>" + _t("bx.maal_ph", x=f"{vann_maal['mash_ph_min']:.2f}–{vann_maal['mash_ph_max']:.2f}") + "</li>"
        if vann_maal and vann_maal.get("mash_ph_min") is not None else ""
    )
    faktisk_ph = vann_maalinger.get("maalt_mash_ph")
    faktisk_ph_val = f"{faktisk_ph:.2f}" if faktisk_ph else ""
    maaletemp_val = _t("bx.romtemp") if vann_maalinger.get("malt_ved_romtemperatur") else ""
    syrer_tilsatt_val = ", ".join(
        f"{esc(syre_navn(s['syre_id'], sprak) if s.get('syre_id') in ('melkesyre', 'fosforsyre') else s['navn'])} {s['mengde_ml']:.1f} mL"
        + (f" ({s['prosent']:.0f}%)" if s.get("prosent") else _t("bx.syre_ukjent_konsentrasjon"))
        for s in (vann_maalinger.get("syrer") or [])
    )

    # ── Prosessprofil / bryggemåte ──────────────────────────────────────────
    prosess_profil = plan.get("prosess_profil")
    prosess_line = (
        "<p class='recipe-stil'>" + _t("bx.bryggemaate", navn=esc(profilnavn_visning(prosess_profil['navn'], sprak, prosess_profil.get('process_id')))) + "</p>"
        if prosess_profil else ""
    )
    dekoksjon_li = ""
    if plan.get("dekoksjon"):
        d = plan["dekoksjon"]
        dekoksjon_li = "<li class='note'>" + _t(
            "bx.dekoksjon", uttak=f"{d['uttak_liter']:.2f}", fra=d['fra_temp_c'],
            min=d['koketid_min'], til=d['til_temp_c'],
        ) + "</li>"
    reiterated_li = ""
    if plan.get("reiterated_mash_flyt"):
        r = plan["reiterated_mash_flyt"]
        reiterated_li = "<li class='note'>" + _t(
            "bx.dobbelmesk", m1=f"{r['malt_1_kg']:.2f}", v1=f"{r['vann_mesk_1_l']:.1f}",
            w1=f"{r['vort_1_l']:.1f}", m2=f"{r['malt_2_kg']:.2f}", w2=f"{r['vort_2_l']:.1f}",
        ) + "</li>"

    # ── Brewing additions ─────────────────────────────────────────────────
    tilsetninger = plan.get("tilsetninger", [])
    tilsetninger_html = ""
    if tilsetninger:
        rows_t = "".join(
            f"<tr><td>{esc(v['navn'])}</td><td>{esc(v['dose'])}</td><td>{esc(v['timing'])}</td></tr>"
            for v in (tilsetning_visning(x, sprak) for x in tilsetninger)
        )
        tilsetninger_html = f"""
    <h2>{_t('bx.tils_tittel')}</h2>
    <table class="humle">
      <tr><th>{_t('bx.th.tilsetning')}</th><th>{_t('bx.th.dose')}</th><th>{_t('bx.th.tidspunkt')}</th></tr>
      {rows_t}
    </table>"""

    # ── Gjær notes ────────────────────────────────────────────────────────
    temp_li = "".join(
        f"<li>{esc(linje)}</li>"
        for linje in fermenteringstemp_linjer(plan, (ctx.get("recipe") or {}).get("fermentation_temp_target_c"), sprak)
    )
    noter_li = "".join(f"<li class='note'>ℹ️ {esc(n)}</li>" for n in bryggedag_noter(plan, sprak))
    dms_note = (
        "<li class='note'>" + _t("bd.kok.pilsner_anbefalt_ark") + "</li>"
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
      <div class="stat-faktisk-lbl">{_t('bx.faktisk_lbl') if maal else _t('bx.malt_lbl')}</div>
      {fakt_val}{fakt_line}
    </div>"""

    return f"""<!DOCTYPE html>
<html lang="{sprak if sprak in ('no', 'en') else 'no'}">
<head>
<meta charset="utf-8">
<title>{_t('bx.tittel', navn=esc(ctx['name']))}</title>
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
    break-inside: avoid;
    page-break-inside: avoid;
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

  /* ── MÅLINGER-BLOKK (Brewday Print Pagination Fix V1): overskrift +
     4×2-målebokser (.stats-4) + effektivitetsrad (.eff-row) holdes ALLTID
     samlet ved sideskift under utskrift. Uten en regel på DENNE
     wrapper-nivået kan nettleseren splitte selve CSS-gridet midt mellom
     rad 1 og rad 2 (ingen grid-/flex-barn har i seg selv noen
     fragmenteringsregel som hindrer det) -- det er nettopp det som gjorde
     at "andre rad" og effektivitetsraden havnet visuelt komprimert/
     overlappende rundt sideskiftet. Med regelen her flyttes i stedet HELE
     blokken samlet til neste side dersom den ikke får plass på
     gjenværende del av forrige side. ── */
  .maalinger-block {{
    break-inside: avoid;
    page-break-inside: avoid;
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
<p class="stats-bar">{stats_linje(ctx, html=True, effektivitet_label=_t('bx.effektivitet'))}</p>

<!-- BATCH-INFO -->
<div class="batch-info">
  <div class="bi-field"><div class="lbl">{_t('bx.batchnr')}</div><div class="bi-line"></div></div>
  <div class="bi-field"><div class="lbl">{_t('bx.dato')}</div><div class="bi-line"></div></div>
  <div class="bi-field"><div class="lbl">{_t('bx.brygger')}</div><div class="bi-line"></div></div>
</div>

<div class="divider"></div>

<!-- HOVED: TO KOLONNER -->
<div class="main">

  <!-- VENSTRE: Malt · Vann · Mesking · Kok -->
  <div>
    <h2>{_t('bx.malt_tittel', kg=fmt_kg(plan['total_korn_kg']))}</h2>
    <ul class="malt-list">{malt_li}</ul>

    <h2>{_t('bx.vann_tittel')}</h2>
    <ul class="cb-list">
      {vannkilde_li}
      {maalprofil_li}
      <li><span class="cb">☐</span> {_t('bx.meskevann', l=f"{w['mash_vann_l']:.1f}")}</li>
      <li><span class="cb">☐</span> {_t('bx.skyllevann', l=f"{w['sparge_vann_l']:.1f}")}</li>
      <li><span class="cb">☐</span> {_t('bx.preboil', l=f"{w['pre_boil_l']:.1f}")}
          &nbsp;<em style="font-size:9pt;color:#777;">{_t('bx.preboil_maks')}</em></li>
      {salter_mesk_li}{salter_skyll_li}{mash_ph_maal_li}
    </ul>
    <div class="ferm-grid" style="margin-top:2px;">
      <div>
        <div class="field-lbl">{_t('bx.faktisk_ph')}</div>
        <div class="field-line">{faktisk_ph_val}</div>
      </div>
      <div>
        <div class="field-lbl">{_t('bx.maaletemp')}</div>
        <div class="field-line">{maaletemp_val}</div>
      </div>
    </div>
    <div style="margin-top:2px;">
      <div class="field-lbl">{_t('bx.syre_tilsatt')}</div>
      <div class="field-line">{syrer_tilsatt_val}</div>
    </div>

    <h2>{_t('bx.mesking_tittel')}</h2>
    <ul class="cb-list">{maskeplan_li}{dekoksjon_li}{reiterated_li}</ul>

    <h2>{_t('bx.koking_tittel')}</h2>
    <ul class="cb-list">
      <li><span class="cb">☐</span> {_t('bx.kok_linje', min=plan['koketid_min'])}
          &nbsp;·&nbsp; {_t('bx.koketap', l=f"{plan['estimert_koketap_l']:.1f}")}</li>
      {dms_note}
    </ul>
  </div>

  <!-- HØYRE: Humle · Tilsetninger · Gjær -->
  <div>
    <h2>{_t('bx.humle_tittel')}</h2>
    <table class="humle">
      <tr><th>{_t('bx.th.tid_igjen')}</th><th>{_t('bx.th.tilsatt_etter')}</th><th>{_t('bx.th.humle')}</th><th>{_t('bx.th.gram')}</th><th>IBU</th></tr>
      {humle_rows}
    </table>
    {humle_avvik_html}

    {tilsetninger_html}

    <h2>{_t('bx.gjaer_tittel')}</h2>
    <ul class="cb-list">
      <li><span class="cb">☐</span> <strong>{esc(plan['gjaer_navn'])}</strong></li>
      <li><span class="cb">☐</span> {_t('bx.pakker', n=plan['pakker'])}</li>
      {temp_li}
      {noter_li}
    </ul>
    <div class="ferm-grid">
      <div>
        <div class="field-lbl">{_t('bx.gjaering_start')}</div>
        <div class="field-line"></div>
      </div>
      <div>
        <div class="field-lbl">{_t('bx.coldcrash')}</div>
        <div class="field-line"></div>
      </div>
    </div>
  </div>

</div><!-- /main -->

<!-- SJEKKLISTE -->
<div class="divider"></div>
<h2>{_t('bx.sjekkliste_tittel')}</h2>
<div class="checklist">
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.0')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.1')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.2')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.3')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.4')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.5')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.6')}</div>
  <div class="check-item"><span class="cb">☐</span> {_t('bx.sjekk.7')}</div>
</div>

<!-- MÅLINGER: 4×2 grid + effektivitet -- samlet i én wrapper
     (.maalinger-block) slik at hele blokken holdes sammen ved
     sideskift under utskrift, se .maalinger-block i <style>. -->
<div class="divider"></div>
<div class="maalinger-block">
<h2>{_t('bx.maalinger_tittel')}</h2>
<div class="stats-4">
  {stat_box(_t("bx.stat.preboil_sg"),  "",                                          pre_sg_v)}
  {stat_box(_t("bx.stat.preboil_vol"), "",                                          pre_vol_v)}
  {stat_box(_t("bx.stat.postboil_vol"),"",                                          post_vol_v)}
  {stat_box("OG",           _t("bx.maal_lbl", x=fmt_og(ctx['og'])),                 og_v)}
  {stat_box("FG",           _t("bx.maal_lbl", x=fmt_fg(ctx['fg'])),                 fg_v)}
  {stat_box("ABV",          _t("bx.maal_lbl", x=fmt_abv(ctx['abv'])),               abv_v)}
  {stat_box(_t("bx.stat.pitch"),   "",                                              pitch_v)}
  {stat_box(_t("bx.stat.maskeeff"),"",                                              mash_eff_v)}
</div>

<!-- EFFEKTIVITET & BH-EFF -->
<div class="eff-row" style="margin-top:6px;">
  <div class="eff-field">
    <div class="eff-lbl">{_t('bx.eff_bryggeri', x=f"{ctx['effektivitet']*100:.0f}")}</div>
    {'<div class="eff-val">' + bh_eff_v + '</div>' if bh_eff_v else '<div class="eff-line"></div>'}
  </div>
  <div class="eff-field">
    <div class="eff-lbl">{_t('bx.eff_abv')}</div>
    {'<div class="eff-val">' + abv_v + '</div>' if abv_v else '<div class="eff-line"></div>'}
  </div>
  <div class="eff-field">
    <div class="eff-lbl">{_t('bx.batch_til_gjaering')}</div>
    <div class="eff-line"></div>
  </div>
</div>
</div><!-- /maalinger-block -->

<!-- NOTATER -->
<div class="notes-section">
  <div class="divider"></div>
  <h2>{_t('bx.notater')}</h2>
  <div class="note-lines">
    <div></div><div></div><div></div><div></div>
    <div></div><div></div><div></div><div></div>
  </div>
</div>

</div><!-- /page-wrapper -->
</body>
</html>"""
