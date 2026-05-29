import streamlit as st
from modules.brewday_calc import lag_brewday_plan


def render_brewday_panel(ctx, humle_database, gjaer_database):
    st.write("---")
    with st.expander("🍺 Bryggeplan"):
        gjaer_id   = st.session_state.get("valgt_gjaer_id", "")
        gjaer_info = gjaer_database.get(gjaer_id, {})

        plan = lag_brewday_plan(
            malt_valg     = st.session_state.get("valgt_malt", []),
            humle_valg    = st.session_state.get("valgt_humle", []),
            gjaer_id      = gjaer_id,
            gjaer_info    = gjaer_info,
            og            = ctx["og"],
            batch_volum_l = ctx["volum"],
            humle_database= humle_database,
        )

        st.subheader(ctx["name"])
        st.caption(f"Batch: {ctx['volum']:.0f} L  ·  Totalt korn: {plan['total_korn_kg']:.2f} kg")

        # ── VANN ──────────────────────────────────────────
        st.markdown("**💧 Vann**")
        w = plan["vann"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Maskevatn",  f"{w['mash_vann_l']:.1f} L")
        c2.metric("Spargevatn", f"{w['sparge_vann_l']:.1f} L")
        c3.metric("Pre-boil",   f"{w['pre_boil_l']:.1f} L")

        # ── MESKING ───────────────────────────────────────
        st.write("")
        st.markdown("**🌡️ Mesking**")
        for steg in plan["maskeplan"]:
            st.write(f"- {steg['temp_c']}°C i {steg['varighet_min']} min — *{steg['label']}*")

        # ── KOKING ────────────────────────────────────────
        st.write("")
        st.markdown("**🔥 Koking**")
        st.write(f"- {plan['koketid_min']} min")
        if plan["koketid_min"] == 90:
            st.caption("90 min anbefalt for Pilsnermalt — reduserer DMS-forstadie.")

        # ── HUMLETILSETNINGER ─────────────────────────────
        st.write("")
        st.markdown("**🌿 Humletilsetninger**")
        if plan["humleplan"]:
            for h in plan["humleplan"]:
                st.write(f"- {h['gram']}g {h['navn']} @{h['tid']} min")
        else:
            st.caption("Ingen humle i oppskriften.")

        # ── GJÆR ──────────────────────────────────────────
        st.write("")
        st.markdown("**🧫 Gjær**")
        st.write(f"- {plan['gjaer_navn']}")
        st.write(f"- Anbefalt: **{plan['pakker']} pakke(r)**")
        st.write(f"- Fermenteringstemperatur: **{plan['temp_min']}–{plan['temp_maks']}°C**")
        for note in plan["noter"]:
            st.info(note)

        # ── UTSTYRSNOTAT ──────────────────────────────────
        st.write("")
        st.caption(
            "Beregnet med standard BrewZilla 35L-verdier: "
            "3,2 L/kg maskeforhold · 1,0 L/kg kornabsorpsjon · "
            "4,0 L/t fordampning · 2,0 L dead volume."
        )

        # ── PRINT-ARK ─────────────────────────────────────
        st.write("")
        if st.button("🖨️ Generer Bryggedagsark", use_container_width=True, key="brewday_print_btn"):
            w = plan["vann"]

            maskeplan_li = "".join(
                f"<li><span class='cb'>☐</span> {s['temp_c']}°C – {s['varighet_min']} min <em>({s['label']})</em></li>"
                for s in plan["maskeplan"]
            )
            humle_li = "".join(
                f"<li><span class='cb'>☐</span> {h['gram']}g {h['navn']} @{h['tid']} min</li>"
                for h in plan["humleplan"]
            ) or "<li>Ingen humle i oppskriften.</li>"

            noter_li = "".join(
                f"<li class='note'>ℹ️ {n}</li>" for n in plan["noter"]
            )

            html = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>Bryggedagsark — {ctx['name']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 9.5pt;
          color: #111; background: #fff; padding: 8mm 10mm 6mm 10mm; }}
  h1 {{ font-size: 13pt; margin-bottom: 1px; }}
  .sub {{ font-size: 8.5pt; color: #444; margin-bottom: 5px;
          padding-bottom: 4px; border-bottom: 1.5px solid #333; }}
  h2 {{ font-size: 8pt; font-weight: bold; text-transform: uppercase;
        letter-spacing: 0.07em; border-bottom: 1px solid #888;
        padding-bottom: 1px; margin: 5px 0 2px 0; }}
  ul {{ list-style: none; margin: 0 0 1px 0; }}
  li {{ margin: 1px 0; display: flex; align-items: baseline;
        gap: 4px; line-height: 1.3; }}
  .cb {{ font-size: 10pt; flex-shrink: 0; }}
  .note {{ font-size: 7.5pt; color: #555; font-style: italic; }}
  .line {{ border-bottom: 1px solid #bbb; height: 15px; margin: 2px 0 4px 0; }}
  .lbl {{ font-size: 7.5pt; color: #555; margin: 3px 0 0 0; }}
  /* Two-column main body */
  .main {{ display: grid; grid-template-columns: 1fr 1fr;
           gap: 0 8mm; margin-bottom: 4px; }}
  /* Fermentation write-in fields: 2×2 grid */
  .ferm-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 6mm; }}
  /* Bottom strip: measurements left, notes right */
  .bottom {{ display: grid; grid-template-columns: 1fr 1fr; gap: 0 8mm;
             border-top: 1.5px solid #333; padding-top: 4px; margin-top: 3px; }}
  .stats-3 {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 3px; }}
  .stat-box {{ border: 1px solid #bbb; border-radius: 2px; padding: 2px 4px; }}
  .slbl {{ font-size: 7pt; color: #666; text-transform: uppercase; }}
  .sline {{ border-bottom: 1px solid #bbb; height: 13px; margin-top: 2px; }}
  @media print {{
    @page {{ size: A4; margin: 0; }}
    body {{ padding: 7mm 9mm 5mm 9mm; }}
  }}
</style>
</head>
<body>
  <h1>{ctx['name']}</h1>
  <p class="sub">{ctx['volum']:.0f} L &nbsp;·&nbsp; OG {ctx['og']:.3f} &nbsp;·&nbsp; FG {ctx['fg']:.3f} &nbsp;·&nbsp; ABV {ctx['abv']:.1f}% &nbsp;·&nbsp; IBU {ctx['ibu']:.0f} &nbsp;·&nbsp; EBC {ctx['ebc']:.0f}</p>

  <div class="main">
    <!-- LEFT: Vann · Mesking · Kok -->
    <div>
      <h2>Vann</h2>
      <ul>
        <li><span class="cb">☐</span> Meskevann: <strong>{w['mash_vann_l']:.1f} L</strong></li>
        <li><span class="cb">☐</span> Skyllevann: <strong>{w['sparge_vann_l']:.1f} L</strong></li>
        <li><span class="cb">☐</span> Pre-boil: <strong>{w['pre_boil_l']:.1f} L</strong></li>
      </ul>

      <h2>Mesking</h2>
      <ul>{maskeplan_li}</ul>

      <h2>Kok</h2>
      <ul><li><span class="cb">☐</span> {plan['koketid_min']} min</li></ul>
    </div>

    <!-- RIGHT: Humle · Gjær · Fermentering -->
    <div>
      <h2>Humle</h2>
      <ul>{humle_li}</ul>

      <h2>Gjær</h2>
      <ul>
        <li><span class="cb">☐</span> {plan['gjaer_navn']}</li>
        <li><span class="cb">☐</span> Anbefalt: <strong>{plan['pakker']} pakke(r)</strong></li>
        {noter_li}
      </ul>

      <h2>Fermentering</h2>
      <div class="ferm-grid">
        <div><p class="lbl">Temperatur ({plan['temp_min']}–{plan['temp_maks']}°C)</p><div class="line"></div></div>
        <div><p class="lbl">Startdato</p><div class="line"></div></div>
        <div><p class="lbl">Sluttdato</p><div class="line"></div></div>
        <div><p class="lbl">Kullsyre / Spunning</p><div class="line"></div></div>
      </div>
    </div>
  </div>

  <!-- BOTTOM: Målinger + Notater -->
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
      <div class="line"></div>
      <div class="line"></div>
      <div class="line"></div>
    </div>
  </div>
</body>
</html>"""

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
