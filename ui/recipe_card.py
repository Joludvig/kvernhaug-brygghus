# ui/recipe_card.py
import streamlit as st
from modules.recipe_storage import lagre_oppskrift, slett_oppskrift_fil
from modules.recipe import bygg_recipe_object

def render_recipe_card(ctx, malt_database, humle_database, gjaer_database):
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
                st.session_state.valgt_gjaer_id = "fermentis_us05"
                st.session_state.gjeldende_navn = "Kvernhaug Spesial"
                st.rerun()

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

    if st.button("🖨️ Generer utskriftsvennlig ark (A4)", use_container_width=True):
        st.markdown("<script>window.print();</script>", unsafe_allow_html=True)
        st.info("💡 **Tips:** Trykk **Ctrl + P** hvis vinduet ikke åpnet seg.")
