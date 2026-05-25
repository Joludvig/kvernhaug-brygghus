import streamlit as st

def render_yeast_panel(gjaer_database):
    st.header("🧫 Gjærstamme")
    gjaer_id_kart, gjaer_meny_valg = {}, []
    for g_id, info in gjaer_database.items():
        if info:
            visnings_navn = f"{info.get('display_name', 'Ukjent')} ({info.get('produsent', 'Ukjent')})"
            gjaer_id_kart[visnings_navn] = g_id
            gjaer_meny_valg.append(visnings_navn)

    # SKUDDSIKKER FALLBACK: Hvis gjærdatabasen er tom, legger vi inn et standard testvalg
    # slik at selectboxen ikke blir tom (noe som forårsaker None-krasj)
    if not gjaer_meny_valg:
        gjaer_meny_valg = ["SafAle US-05 (Amerikansk Ale) (Fermentis (Tørr))"]
        gjaer_id_kart["SafAle US-05 (Amerikansk Ale) (Fermentis (Tørr))"] = "fermentis_us05"

    gjeldende_g_visning = "SafAle US-05 (Amerikansk Ale) (Fermentis (Tørr))"
    for visning, g_id in gjaer_id_kart.items():
        if g_id == st.session_state.valgt_gjaer_id:
            gjeldende_g_visning = visning
            break
            
    g_indeks = gjaer_meny_valg.index(gjeldende_g_visning) if gjeldende_g_visning in gjaer_meny_valg else 0
    valgt_gjaer_visning = st.selectbox("Velg gjær:", gjaer_meny_valg, index=g_indeks)
    
    # FIKSET: Sjekker at vi faktisk har en gyldig verdi i kartet før vi lagrer til session state
    if valgt_gjaer_visning and valgt_gjaer_visning in gjaer_id_kart:
        st.session_state.valgt_gjaer_id = gjaer_id_kart[valgt_gjaer_visning]
    else:
        st.session_state.valgt_gjaer_id = "fermentis_us05"
