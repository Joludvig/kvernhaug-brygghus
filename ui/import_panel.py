# ui/import_panel.py
import streamlit as st
import os
from config import DEMO_MODE
from modules.store_scraper import kjor_full_skanning
from modules.store_matcher import (
    match_store_data_to_master,
    match_store_data_to_master_malt,
    match_store_data_to_master_gjaer,
)
from ui.review_panel import render_review_panel

def render_import_panel():
    if DEMO_MODE:
        st.info("Import og scraping er deaktivert i demo-modus.")
        return
    st.write("---")
    st.header("🧠 Kvernhaug AI: Import- & Sortimentsbygger")
    st.caption(
        "Trål vestbrygg.no og olbrygging.no live og kjør lingvistisk AI-normalisering. "
        "Matchede produkter (pris/URL) skrives DIREKTE til master-databasene appen faktisk "
        "bruker (master_malt.json / master_humle_v2.json / master_gjaer_v2.json) — det finnes "
        "ikke noe eget «importer til runtime»-steg lenger. Umatchede produkter havner i "
        "«📋 Pending Review» under, og blir også synlige i appen med én gang de godkjennes der."
    )

    col1, col2 = st.columns(2)

    # === KNAPP 1: SKANN BUTIKKER ===
    with col1:
        if st.button("🔍 Trål og skann butikker", width="stretch"):
            with st.spinner("Cravler nettbutikker side for side (delay 1s)..."):
                # Slett gamle review-filer ved ny skanning så vi ikke ser gammel info
                for k in ["malt", "humle", "gjaer"]:
                    p = f"raw_data/{k}_review.json"
                    if os.path.exists(p): os.remove(p)
                
                m, h, g = kjor_full_skanning()
                st.success(f"Skanning ferdig! Fant {m} malttyper, {h} humlesorter, og {g} gjærtyper.")
                st.session_state["raw_scanned"] = True
                st.rerun()
                
    # === KNAPP 2: AI NORMALISERING ===
    with col2:
        raw_finnes = os.path.exists("raw_data/malt_raw.json")
        if st.button("🧠 Kjør AI-normalisering", width="stretch", disabled=not raw_finnes):
            status_element = st.empty()
            progress_bar = st.progress(0)

            with st.spinner("AI leser produktbeskrivelser og utleder sensoriske akser..."):
                try:
                    matcher_config = [
                        ("humle", match_store_data_to_master,
                         ["raw_data/humle_raw.json", "data/master_humle_v2.json",
                          "raw_data/matched_hops.json", "raw_data/unmatched_hops.json"]),
                        ("malt", match_store_data_to_master_malt,
                         ["raw_data/malt_raw.json", "data/master_malt.json",
                          "raw_data/unmatched_malt.json"]),
                        ("gjær", match_store_data_to_master_gjaer,
                         ["raw_data/gjaer_raw.json", "data/master_gjaer_v2.json",
                          "raw_data/unmatched_gjaer.json"]),
                    ]
                    for i, (kat, fn, args) in enumerate(matcher_config):
                        status_element.markdown(f"🔍 **Matcher** `{kat}` mot master...")
                        raw_fil = args[0]
                        if os.path.exists(raw_fil):
                            try:
                                matched_n, unmatched_n = fn(*args)
                                if unmatched_n > 0:
                                    st.warning(f"{kat.capitalize()}: {matched_n} matchet, {unmatched_n} til manuell review")
                                else:
                                    st.info(f"{kat.capitalize()}: {matched_n} matchet — ingen umatched")
                            except Exception as e:
                                st.warning(f"{kat.capitalize()}-matching feilet: {e}")
                        progress_bar.progress((i + 1) / len(matcher_config))

                    progress_bar.empty()
                    status_element.empty()

                    st.session_state["vis_ai_suksess"] = True
                    st.toast("Normalisering fullført!", icon="✅")
                    st.rerun()

                except Exception as e:
                    st.error(f"Det skjedde en feil: {e}")

    # Det fantes tidligere en tredje knapp ("📥 Importer til Master DB")
    # her som skrev flatede kopier til de separate, IKKE-brukte
    # legacy-filene data/humle.json, data/malt.json og data/gjaer.json.
    # app.py leser derimot master_malt.json / master_humle_v2.json /
    # master_gjaer_v2.json DIREKTE (se app.py sin last_json_data()) --
    # matching over og review-godkjenning under skriver allerede rett inn
    # i akkurat de filene, så knappen importerte aldri noe appen faktisk
    # brukte. Fjernet i stedet for å beholde en knapp som påsto å
    # importere til runtime uten å gjøre det. De tre legacy-filene selv
    # er IKKE slettet -- se docs/MASTER_DATA_FLOW.md for videre vurdering.

    if st.session_state.get("vis_ai_suksess"):
        st.success("🎉 AI-normalisering fullført! Råvarene er ferdig tolket, fargetestet og klare for review i rapporten under.")

    render_review_panel()
