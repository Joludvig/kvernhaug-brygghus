import streamlit as st
from modules.recipe_storage import hent_alle_oppskrifter

def render_sidebar(malt_database, humle_database, gjaer_database):
    st.sidebar.header("📁 Lagrede oppskrifter")
    lagrede_brygg = hent_alle_oppskrifter()
    if lagrede_brygg:
        valgt_lagret_navn = st.sidebar.selectbox("Velg et brygg fra harddisken:", ["-- Velg oppskrift --"] + list(lagrede_brygg.keys()))
        if valgt_lagret_navn != "-- Velg oppskrift --":
            r_data = lagrede_brygg[valgt_lagret_navn]
            st.session_state.valgt_malt = r_data["malts"]
            st.session_state.valgt_humle = r_data["hops"]
            st.session_state.valgt_gjaer_id = r_data["yeast"] if isinstance(r_data["yeast"], str) else r_data["yeast"].get("id", "fermentis_us05")
            st.session_state.gjeldende_navn = r_data["name"]
            st.sidebar.success(f"Laddet: {valgt_lagret_navn}")
            st.rerun()
    else:
        st.sidebar.info("Ingen oppskrifter lagret i mappen ennå.")
