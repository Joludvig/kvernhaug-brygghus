# ui/recipe_card.py
import re
import streamlit as st
from datetime import date
from modules.recipe_storage import lagre_oppskrift, slett_oppskrift_fil, lagre_logg_entry, hent_logg
from modules.recipe import bygg_recipe_object

def _render_brewday_result_panel(ctx):
    if st.session_state.get("_last_loaded_recipe") != ctx["name"]:
        return

    logg = hent_logg(ctx["name"])

    with st.expander(f"📓 Bryggelogg ({len(logg)} oppføringer)" if logg else "📓 Bryggelogg", expanded=False):
        with st.form("brewday_logg_form"):
            st.markdown("**Nytt brygg**")
            col_og, col_fg = st.columns(2)
            with col_og:
                actual_og = st.number_input(
                    "Faktisk OG",
                    min_value=1.000, max_value=1.200, step=0.001, format="%.3f",
                    value=float(ctx["og"]),
                )
            with col_fg:
                actual_fg = st.number_input(
                    "Faktisk FG (valgfritt)",
                    min_value=1.000, max_value=1.200, step=0.001, format="%.3f",
                    value=float(ctx["fg"]),
                )
            col_dato, col_vol = st.columns(2)
            with col_dato:
                brew_date = st.date_input("Bryggedato", value=date.today())
            with col_vol:
                actual_volume = st.number_input(
                    "Volum til gjæring (L)",
                    min_value=0.0, max_value=200.0, step=0.5,
                    value=float(ctx["volum"]),
                )
            note = st.text_area("Notat", height=68)

            if st.form_submit_button("Legg til loggoppføring", use_container_width=True):
                entry = {
                    "date": brew_date.isoformat(),
                    "actual_volume_l": actual_volume,
                    "actual_og": actual_og,
                    "actual_fg": actual_fg,
                    "actual_abv": round((actual_og - actual_fg) * 131.25, 1),
                    "note": note.strip(),
                }
                lagre_logg_entry(ctx["name"], entry)
                st.toast("Loggoppføring lagret!", icon="📓")
                st.rerun()

        if logg:
            st.write("---")
            for entry in reversed(logg):
                abv_str = f" · ABV {entry['actual_abv']:.1f}%" if entry.get("actual_abv") else ""
                st.markdown(
                    f"**{entry.get('date', '-')}** · "
                    f"{entry.get('actual_volume_l', 0):.1f} L · "
                    f"OG {entry.get('actual_og', 1.0):.3f} · "
                    f"FG {entry.get('actual_fg', 1.0):.3f}"
                    f"{abv_str}"
                )
                if entry.get("note"):
                    st.caption(entry["note"])

def render_recipe_card(ctx, malt_database, humle_database, gjaer_database):
    # Bryggnavn og batchvolum
    navn_col, vol_col = st.columns([3, 1.5])
    with navn_col:
        st.text_input("Bryggnavn", key="gjeldende_navn")
    with vol_col:
        st.number_input("Liter", min_value=1.0, max_value=200.0, step=1.0, key="batch_volum_input")

    # Knapper for å lagre og slette
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("💾 Lagre oppskrift", use_container_width=True):
            ny_recipe = bygg_recipe_object(ctx["name"], ctx["volum"], efficiency=ctx["effektivitet"], malts=st.session_state.valgt_malt, hops=st.session_state.valgt_humle, yeast=st.session_state.valgt_gjaer_id, og=ctx["og"], fg=ctx["fg"], abv=ctx["abv"], ibu=ctx["ibu"], ebc=ctx["ebc"], flavor_profile={})
            lagre_oppskrift(ny_recipe)
            st.toast(f"Oppskriften ble lagret!", icon="💾")
            st.rerun()
    with btn_col2:
        if st.button("🗑️ Slett gjeldende", use_container_width=True):
            if slett_oppskrift_fil(ctx["name"]):
                st.toast(f"Slettet {ctx['name']}", icon="🗑️")
                st.session_state.valgt_malt = [{"id": "weyermann_pilsner", "mengde": 5.0}]
                st.session_state.valgt_humle = [{"id": "magnum_de", "gram": 20, "tid": 60}]
                st.session_state.valgt_gjaer_id = "safale_us_05"
                st.session_state.gjeldende_navn = "Kvernhaug Spesial"
                st.rerun()

    with st.expander("📐 Skaler oppskrift"):
        original = st.session_state.get("_original_batch_size")
        if original and abs(original - ctx["volum"]) > 0.01:
            st.caption(f"Original: {original:.0f} L · Gjeldende: {ctx['volum']:.0f} L")
        maal = st.number_input(
            "Skalér til (L)",
            min_value=1.0, max_value=200.0, step=0.5,
            value=float(ctx["volum"]),
            key="skaler_maal_volum",
        )
        if st.button("Skaler oppskrift", use_container_width=True, key="skaler_btn"):
            if abs(maal - ctx["volum"]) < 0.01:
                st.warning("Mål-volum er allerede lik gjeldende volum.")
            else:
                faktor = maal / ctx["volum"]
                st.session_state.valgt_malt = [
                    {**m, "mengde": round(m["mengde"] * faktor, 3)}
                    for m in st.session_state.valgt_malt
                ]
                st.session_state.valgt_humle = [
                    {**h, "gram": round(h["gram"] * faktor, 1)}
                    for h in st.session_state.valgt_humle
                ]
                st.session_state["_pending_batch_volum"] = maal
                base_navn = re.sub(r' - \d+(?:\.\d+)?L batch$', '', st.session_state.get("gjeldende_navn", ""))
                st.session_state.gjeldende_navn = f"{base_navn} - {maal:g}L batch"
                st.rerun()
        st.caption("💡 Endre navn før lagring for å ikke overskrive originalen.")

    # Formater HTML for malt og humle-linjer til arket
    malt_html = "".join([f"<tr><td style='padding:5px; color:#ffffff;'>{malt_database[m['id']]['display_name']}</td><td style='padding:5px; color:#ffffff;'>{m['mengde']:.2f} kg</td></tr>" for m in st.session_state.valgt_malt if m["id"] in malt_database])
    humle_html = "".join([f"<tr><td style='padding:5px; color:#ffffff;'>{humle_database[h['id']]['display_name']}</td><td style='padding:5px; color:#ffffff;'>{h['gram']}g</td><td style='padding:5px; color:#ffffff;'>{h['tid']} min</td></tr>" for h in st.session_state.valgt_humle if h["id"] in humle_database])

    # Generer det lune HTML-oppskriftskortet
    html_kort = f"""
    <div style="border: 2px solid #b87333; padding: 20px; border-radius: 10px; background-color: #1e140a; color: #f5f5f5; font-family: 'Georgia', serif;">
        <h2 style="color: #b87333; margin-top: 0; font-family: 'Palatino', serif; text-align: center; border-bottom: 1px dashed #b87333; padding-bottom: 10px;">📋 {ctx['name'].upper()}</h2>
        <p style="text-align: center; font-style: italic; color: #dddddd; margin-top: 5px;">Batchvolum: {ctx['volum']:.0f} Liter</p>
        <table style="width: 100%; text-align: center; margin: 15px 0; border-collapse: collapse;">
            <tr style="color: #b87333; font-weight: bold; font-size: 1.1em;">
                <th style="padding: 5px; color: #b87333;">OG</th><th style="padding: 5px; color: #b87333;">FG</th><th style="padding: 5px; color: #b87333;">ABV</th><th style="padding: 5px; color: #b87333;">IBU</th><th style="padding: 5px; color: #b87333;">FARGE</th>
            </tr>
            <tr style="font-size: 1.3em; font-weight: bold; color: #ffffff;">
                <td style="padding: 5px;">{ctx['og']:.3f}</td><td style="padding: 5px;">{ctx['fg']:.3f}</td><td style="padding: 5px;">{ctx['abv']:.1f}%</td><td style="padding: 5px;">{ctx['ibu']:.0f}</td><td style="padding: 5px;">{ctx['ebc']:.0f} EBC</td>
            </tr>
        </table>
        <div style="background-color: #2d1e10; padding: 12px; border-radius: 6px; border-left: 4px solid #b87333; margin-bottom: 15px;">
            <p style="margin: 0; font-size: 0.95em; line-height: 1.4; color: #ffffff;"><b>👅 Smaksprofil:</b> {ctx['summary'].replace('**', '')}</p>
        </div>
        <h3 style="color: #b87333; border-bottom: 1px solid #b87333; margin-top: 15px;">🌾 Meskeplan</h3>
        <table style="width: 100%; text-align: left;">{malt_html}</table>
        <h3 style="color: #b87333; border-bottom: 1px solid #b87333; margin-top: 15px;">🌿 Kokeplan</h3>
        <table style="width: 100%; text-align: left;">{humle_html}</table>
        <p style="margin: 15px 0 0 0; font-size: 0.95em; text-align: right; color: #aaaaaa;">Estimert pris: <b>{ctx['total_pris']:.2f} kr</b></p>
    </div>
    """
    st.components.v1.html(html_kort, height=580, scrolling=True)

    _render_brewday_result_panel(ctx)

    if st.button("🖨️ Generer utskriftsvennlig ark (A4)", use_container_width=True):
        malt_li = "".join(
            f"<li>{malt_database[m['id']]['display_name']}: {m['mengde']:.2f} kg</li>"
            for m in st.session_state.valgt_malt if m["id"] in malt_database
        )
        humle_li = "".join(
            f"<li>{humle_database[h['id']]['display_name']} {h['gram']}g @{h['tid']} min</li>"
            for h in st.session_state.valgt_humle if h["id"] in humle_database
        )
        gjaer_print = gjaer_database.get(st.session_state.valgt_gjaer_id, {}).get(
            "display_name", st.session_state.valgt_gjaer_id
        )
        smak = ctx["summary"].replace("**", "")

        html_dokument = f"""<!DOCTYPE html>
<html lang="no">
<head>
<meta charset="utf-8">
<title>{ctx['name']}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, Helvetica, sans-serif; font-size: 11pt;
          color: #111; background: #fff; padding: 12mm 14mm 10mm 14mm; }}
  h1 {{ font-size: 17pt; margin-bottom: 2px; }}
  .sub {{ font-size: 10.5pt; color: #444; margin-bottom: 10px; }}
  h2 {{ font-size: 10pt; font-weight: bold; text-transform: uppercase;
        letter-spacing: 0.06em; border-bottom: 1px solid #bbb;
        margin: 9px 0 3px 0; padding-bottom: 2px; }}
  ul {{ padding-left: 16px; margin-bottom: 2px; }}
  li {{ margin: 1px 0; line-height: 1.5; }}
  .stats {{ display: grid; grid-template-columns: repeat(5, 1fr);
            gap: 5px; margin: 6px 0 4px 0; }}
  .stat {{ border: 1px solid #ccc; border-radius: 3px;
           text-align: center; padding: 3px 2px; }}
  .slabel {{ font-size: 7.5pt; color: #666; text-transform: uppercase; }}
  .sval {{ font-size: 13pt; font-weight: bold; line-height: 1.3; }}
  .smak {{ font-size: 9pt; color: #555; margin-top: 3px; }}
  .notes {{ margin-top: 10px; border-top: 1px dashed #bbb; padding-top: 7px; }}
  .nline {{ border-bottom: 1px solid #ddd; height: 20px; margin-bottom: 5px; }}
  @media print {{
    @page {{ size: A4; margin: 0; }}
    body {{ padding: 10mm 12mm 8mm 12mm; }}
  }}
</style>
</head>
<body>
  <h1>{ctx['name']}</h1>
  <p class="sub">{ctx['volum']:.0f} L &nbsp;·&nbsp; {ctx['abv']:.1f}% ABV &nbsp;·&nbsp; {ctx['ibu']:.0f} IBU &nbsp;·&nbsp; {ctx['ebc']:.0f} EBC</p>

  <h2>Malt</h2>
  <ul>{malt_li}</ul>

  <h2>Humle</h2>
  <ul>{humle_li}</ul>

  <h2>Gjær</h2>
  <ul><li>{gjaer_print}</li></ul>

  <h2>Statistikk</h2>
  <div class="stats">
    <div class="stat"><div class="slabel">OG</div><div class="sval">{ctx['og']:.3f}</div></div>
    <div class="stat"><div class="slabel">FG</div><div class="sval">{ctx['fg']:.3f}</div></div>
    <div class="stat"><div class="slabel">ABV</div><div class="sval">{ctx['abv']:.1f}%</div></div>
    <div class="stat"><div class="slabel">IBU</div><div class="sval">{ctx['ibu']:.0f}</div></div>
    <div class="stat"><div class="slabel">EBC</div><div class="sval">{ctx['ebc']:.0f}</div></div>
  </div>
  <p class="smak">&#128485; {smak}</p>

  <div class="notes">
    <strong style="font-size:9pt;">Notater:</strong>
    <div class="nline" style="margin-top:5px;"></div>
    <div class="nline"></div>
    <div class="nline"></div>
  </div>
</body>
</html>"""

        fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + ".html"
        st.download_button(
            label="📥 Last ned oppskriftsark",
            data=html_dokument,
            file_name=fil_navn,
            mime="text/html",
            use_container_width=True,
        )
        st.info("💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.")
