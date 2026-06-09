import os
import streamlit as st
from modules.brewday_calc import lag_brewday_plan
from ui.branding import _logo_base64

_LOGO_PATH = os.path.join("assets", "branding", "master_v1_transparent.png")

_SJEKKLISTE = [
    "Utstyr rent", "Meskevann varmt", "Skylling ferdig", "Kok startet",
    "Humle tilsatt", "Nedkjøling ferdig", "Gjær tilsatt", "Gjæring startet",
]


def render_brewday_panel(ctx, humle_database, gjaer_database, malt_database=None):
    st.write("---")
    with st.expander("🍺 Bryggeplan"):
        gjaer_id   = st.session_state.get("valgt_gjaer_id", "")
        gjaer_info = gjaer_database.get(gjaer_id, {})

        plan = lag_brewday_plan(
            malt_valg      = st.session_state.get("valgt_malt", []),
            humle_valg     = st.session_state.get("valgt_humle", []),
            gjaer_id       = gjaer_id,
            gjaer_info     = gjaer_info,
            og             = ctx["og"],
            batch_volum_l  = ctx["volum"],
            humle_database = humle_database,
            malt_database  = malt_database,
        )

        # ── HEADER ──────────────────────────────────────────
        st.subheader(ctx["name"])
        if ctx.get("brygger_stil"):
            st.caption(ctx["brygger_stil"])
        st.caption(
            f"{ctx['volum']:.0f} L  ·  OG {ctx['og']:.3f}  ·  FG {ctx['fg']:.3f}  ·  "
            f"ABV {ctx['abv']:.1f}%  ·  IBU {ctx['ibu']:.0f}  ·  EBC {ctx['ebc']:.0f}"
        )

        # ── BATCH-INFO ──────────────────────────────────────
        bi1, bi2, bi3 = st.columns(3)
        with bi1:
            st.text_input("Batchnummer", placeholder="f.eks. 42", key="bd_batchnr")
        with bi2:
            st.date_input("Bryggedato", key="bd_dato")
        with bi3:
            st.text_input("Brygger", placeholder="Navn", key="bd_brygger")

        st.write("---")

        # ── VENSTRE / HØYRE ─────────────────────────────────
        bd_left, bd_right = st.columns(2)

        with bd_left:
            # MALT
            st.markdown(f"**🌾 Malt — {plan['total_korn_kg']:.2f} kg**")
            for i, m in enumerate(plan["malt_liste"]):
                st.checkbox(f"{m['mengde']:.2f} kg — {m['navn']}", key=f"bd_malt_{i}")

            # VANN
            st.write("")
            st.markdown("**💧 Vann**")
            w = plan["vann"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Meskevann",  f"{w['mash_vann_l']:.1f} L")
            c2.metric("Skyllevann", f"{w['sparge_vann_l']:.1f} L")
            c3.metric("Pre-boil",   f"{w['pre_boil_l']:.1f} L")

            # MESKING
            st.write("")
            st.markdown("**🌡️ Mesking**")
            for steg in plan["maskeplan"]:
                st.write(f"- {steg['temp_c']}°C  ·  {steg['varighet_min']} min  —  *{steg['label']}*")

            # KOK
            st.write("")
            st.markdown("**🔥 Koking**")
            st.write(f"- {plan['koketid_min']} min")
            if plan["koketid_min"] == 90:
                st.caption("90 min anbefalt for Pilsnermalt — reduserer DMS-forstadie.")

        with bd_right:
            # HUMLE
            st.markdown("**🌿 Humletilsetninger**")
            if plan["humleplan"]:
                header = "| Tid | Humle | Gram | IBU |\n|-----|-------|------|-----|"
                rows = "\n".join(
                    f"| {h['tid']} min | {h['navn']} | {h['gram']:.0f} g | {h['ibu_bidrag']:.1f} |"
                    for h in plan["humleplan"]
                )
                st.markdown(f"{header}\n{rows}")
            else:
                st.caption("Ingen humle i oppskriften.")

            # GJÆR
            st.write("")
            st.markdown("**🧫 Gjær**")
            st.write(f"- **{plan['gjaer_navn']}** — {plan['pakker']} pakke(r)")
            st.write(f"- Temp: **{plan['temp_min']}–{plan['temp_maks']}°C**")
            for note in plan["noter"]:
                st.info(note)

            # FERMENTERING
            st.write("")
            st.markdown("**🌡️ Fermentering**")
            ferm1, ferm2 = st.columns(2)
            with ferm1:
                st.date_input("Gjæringsstart", key="bd_ferm_start")
            with ferm2:
                st.date_input("Cold crash / tapping", key="bd_ferm_slutt")

        # ── SJEKKLISTE ──────────────────────────────────────
        st.write("---")
        st.markdown("**✅ Bryggedags-sjekkliste**")
        chk_cols = st.columns(4)
        for i, item in enumerate(_SJEKKLISTE):
            chk_cols[i % 4].checkbox(item, key=f"bd_chk_{i}")

        # ── MÅLINGER ────────────────────────────────────────
        st.write("---")
        st.markdown("**📐 Målinger**")
        og_col, fg_col, abv_col = st.columns(3)
        with og_col:
            st.text_input(f"OG (mål: {ctx['og']:.3f})", placeholder="Faktisk", key="bd_og")
        with fg_col:
            st.text_input(f"FG (mål: {ctx['fg']:.3f})", placeholder="Faktisk", key="bd_fg")
        with abv_col:
            st.text_input(f"ABV (mål: {ctx['abv']:.1f}%)", placeholder="Faktisk", key="bd_abv")

        st.caption("Vannberegning basert på aktiv utstyrsprofil.")

        # ── PRINT-ARK ───────────────────────────────────────
        st.write("")
        if st.button("🖨️ Generer Bryggedagsark", use_container_width=True, key="brewday_print_btn"):
            html = _bygg_brewday_html(ctx, plan)
            fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + "_bryggedag.html"
            st.download_button(
                label="📥 Last ned bryggedagsark",
                data=html,
                file_name=fil_navn,
                mime="text/html",
                use_container_width=True,
                key="brewday_download_btn",
            )
            st.info("💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.")


def _bygg_brewday_html(ctx, plan):
    w = plan["vann"]

    logo_b64 = _logo_base64() if os.path.exists(_LOGO_PATH) else None
    logo_img = (
        f'<img src="data:image/png;base64,{logo_b64}" alt="KBH">'
        if logo_b64 else ""
    )

    malt_li = "".join(
        f"<li><span class='cb'>☐</span> <strong>{m['mengde']:.2f} kg</strong> — {m['navn']}</li>"
        for m in plan["malt_liste"]
    ) or "<li>Ingen malt registrert.</li>"

    maskeplan_li = "".join(
        f"<li><span class='cb'>☐</span> {s['temp_c']}°C – {s['varighet_min']} min <em>({s['label']})</em></li>"
        for s in plan["maskeplan"]
    )

    humle_rows = "".join(
        f"<tr><td>{h['tid']} min</td><td>{h['navn']}</td>"
        f"<td>{h['gram']:.0f} g</td><td>{h['ibu_bidrag']:.1f}</td></tr>"
        for h in plan["humleplan"]
    ) or "<tr><td colspan='4'>Ingen humle i oppskriften.</td></tr>"

    noter_li = "".join(f"<li class='note'>ℹ️ {n}</li>" for n in plan["noter"])
    dms_note = "<li class='note'>90 min anbefalt for Pilsnermalt</li>" if plan["koketid_min"] == 90 else ""
    stil_line = f"<p class='recipe-stil'>{ctx['brygger_stil']}</p>" if ctx.get("brygger_stil") else ""

    return f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Bryggedagsark — {ctx['name']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 9pt;
          color: #111; background: #fff; padding: 8mm 10mm 6mm 10mm; }}
  .header {{ display: flex; align-items: center; gap: 6mm;
             border-bottom: 2px solid #222; padding-bottom: 4px; margin-bottom: 4px; }}
  .header img {{ height: 30px; }}
  .header-text h1 {{ font-size: 13pt; font-weight: bold; letter-spacing: 0.04em; }}
  .header-text p {{ font-size: 7.5pt; color: #555; }}
  .recipe-title {{ font-size: 11pt; font-weight: bold; margin: 3px 0 0 0; }}
  .recipe-stil {{ font-size: 8pt; color: #555; font-style: italic; margin: 1px 0; }}
  .stats-bar {{ font-size: 8pt; color: #333; padding-bottom: 3px;
                border-bottom: 1px solid #bbb; margin-bottom: 3px; }}
  .batch-info {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 3mm;
                 margin: 3px 0 4px 0; padding-bottom: 3px; border-bottom: 1px solid #bbb; }}
  .bi-field .lbl {{ font-size: 7pt; color: #555; }}
  .bi-line {{ border-bottom: 1px solid #888; height: 13px; margin-top: 1px; }}
  h2 {{ font-size: 7.5pt; font-weight: bold; text-transform: uppercase;
        letter-spacing: 0.06em; border-bottom: 1px solid #aaa;
        padding-bottom: 1px; margin: 5px 0 2px 0; }}
  .main {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 8mm; }}
  ul {{ list-style: none; margin: 0; padding: 0; }}
  li {{ margin: 1.5px 0; font-size: 8.5pt; line-height: 1.25; }}
  .cb {{ font-size: 9.5pt; margin-right: 3px; }}
  .note {{ font-size: 7.5pt; color: #555; font-style: italic; }}
  table.humle {{ width: 100%; border-collapse: collapse; font-size: 8pt; margin-top: 1px; }}
  table.humle th {{ background: #f0f0f0; padding: 2px 4px; text-align: left;
                    font-size: 7pt; text-transform: uppercase; border-bottom: 1px solid #999; }}
  table.humle td {{ padding: 2px 4px; border-bottom: 1px dotted #ccc; }}
  .ferm-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 1px 5mm; margin-top: 2px; }}
  .field-lbl {{ font-size: 7pt; color: #555; margin-top: 3px; }}
  .field-line {{ border-bottom: 1px solid #aaa; height: 13px; }}
  .divider {{ border-top: 1.5px solid #333; margin: 5px 0 3px 0; }}
  .checklist {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 2px 2mm; margin: 2px 0; }}
  .check-item {{ font-size: 8.5pt; }}
  .bottom {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 8mm; }}
  .stats-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 2px; }}
  .stat-box {{ border: 1px solid #bbb; border-radius: 2px; padding: 2px 4px; }}
  .slbl {{ font-size: 7pt; color: #666; text-transform: uppercase; }}
  .sline {{ border-bottom: 1px solid #bbb; height: 13px; margin-top: 2px; }}
  .note-lines div {{ border-bottom: 1px solid #ccc; height: 16px; margin: 3px 0; }}
  @media print {{
    @page {{ size: A4; margin: 0; }}
    body {{ padding: 7mm 9mm 5mm 9mm; }}
  }}
</style>
</head>
<body>

<div class="header">
  {logo_img}
  <div class="header-text">
    <h1>KVERNHAUG BRYGGHUS</h1>
    <p>Ved Dalelva i Åsane</p>
  </div>
</div>

<p class="recipe-title">{ctx['name']}</p>
{stil_line}
<p class="stats-bar">{ctx['volum']:.0f} L &nbsp;·&nbsp; OG {ctx['og']:.3f} &nbsp;·&nbsp; FG {ctx['fg']:.3f} &nbsp;·&nbsp; ABV {ctx['abv']:.1f}% &nbsp;·&nbsp; IBU {ctx['ibu']:.0f} &nbsp;·&nbsp; EBC {ctx['ebc']:.0f} &nbsp;·&nbsp; Effektivitet {ctx['effektivitet']*100:.0f}%</p>

<div class="batch-info">
  <div class="bi-field"><div class="lbl">Batchnummer</div><div class="bi-line"></div></div>
  <div class="bi-field"><div class="lbl">Bryggedato</div><div class="bi-line"></div></div>
  <div class="bi-field"><div class="lbl">Brygger</div><div class="bi-line"></div></div>
</div>

<div class="main">
  <div>
    <h2>Malt — {plan['total_korn_kg']:.2f} kg</h2>
    <ul>{malt_li}</ul>

    <h2>Vann</h2>
    <ul>
      <li><span class="cb">☐</span> Meskevann: <strong>{w['mash_vann_l']:.1f} L</strong></li>
      <li><span class="cb">☐</span> Skyllevann: <strong>{w['sparge_vann_l']:.1f} L</strong></li>
      <li><span class="cb">☐</span> Pre-boil: <strong>{w['pre_boil_l']:.1f} L</strong></li>
    </ul>

    <h2>Mesking</h2>
    <ul>{maskeplan_li}</ul>

    <h2>Koking</h2>
    <ul>
      <li><span class="cb">☐</span> {plan['koketid_min']} min kok</li>
      {dms_note}
    </ul>
  </div>

  <div>
    <h2>Humle</h2>
    <table class="humle">
      <tr><th>Tid</th><th>Humle</th><th>Gram</th><th>IBU</th></tr>
      {humle_rows}
    </table>

    <h2>Gjær</h2>
    <ul>
      <li><span class="cb">☐</span> <strong>{plan['gjaer_navn']}</strong></li>
      <li><span class="cb">☐</span> {plan['pakker']} pakke(r) anbefalt</li>
      <li>Fermenterer {plan['temp_min']}–{plan['temp_maks']}°C</li>
      {noter_li}
    </ul>

    <h2>Fermentering</h2>
    <div class="ferm-grid">
      <div><div class="field-lbl">Gjæringsstart</div><div class="field-line"></div></div>
      <div><div class="field-lbl">Cold crash</div><div class="field-line"></div></div>
      <div><div class="field-lbl">Tapping</div><div class="field-line"></div></div>
      <div><div class="field-lbl">Kullsyre / Spunding</div><div class="field-line"></div></div>
    </div>
  </div>
</div>

<div class="divider"></div>
<h2>Bryggedags-sjekkliste</h2>
<div class="checklist">
  <div class="check-item"><span class="cb">☐</span> Utstyr rent</div>
  <div class="check-item"><span class="cb">☐</span> Meskevann varmt</div>
  <div class="check-item"><span class="cb">☐</span> Skylling ferdig</div>
  <div class="check-item"><span class="cb">☐</span> Kok startet</div>
  <div class="check-item"><span class="cb">☐</span> Humle tilsatt</div>
  <div class="check-item"><span class="cb">☐</span> Nedkjøling ferdig</div>
  <div class="check-item"><span class="cb">☐</span> Gjær tilsatt</div>
  <div class="check-item"><span class="cb">☐</span> Gjæring startet</div>
</div>

<div class="divider"></div>
<div class="bottom">
  <div>
    <h2>Målinger</h2>
    <div class="stats-3">
      <div class="stat-box"><div class="slbl">OG (mål: {ctx['og']:.3f})</div><div class="sline"></div></div>
      <div class="stat-box"><div class="slbl">FG (mål: {ctx['fg']:.3f})</div><div class="sline"></div></div>
      <div class="stat-box"><div class="slbl">ABV (mål: {ctx['abv']:.1f}%)</div><div class="sline"></div></div>
    </div>
  </div>
  <div>
    <h2>Notater</h2>
    <div class="note-lines">
      <div></div><div></div><div></div>
    </div>
  </div>
</div>

</body>
</html>"""
