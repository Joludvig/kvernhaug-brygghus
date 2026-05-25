import streamlit as st
from modules.recipe_storage import hent_alle_oppskrifter
from modules.recipe_importer import (
    parse_recipe_text,
    match_imported_ingredients,
    apply_import_to_session_state,
)

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

    st.sidebar.write("---")
    with st.sidebar.expander("📥 Importer oppskrift fra tekst"):
        st.caption(
            "Lim inn ingredienser, én per linje:\n\n"
            "`5 kg Maris Otter`\n"
            "`300 g CaraMunich`\n"
            "`20 g Magnum 60 min`\n"
            "`Wyeast 1318 London Ale III`"
        )
        import_tekst = st.text_area("Oppskrift:", height=160, key="import_tekst_input", label_visibility="collapsed")

        if st.button("🔍 Analyser", key="import_analyser_btn", use_container_width=True):
            if import_tekst.strip():
                parsed = parse_recipe_text(import_tekst)
                resultat = match_imported_ingredients(parsed, malt_database, humle_database, gjaer_database)
                st.session_state["import_preview"] = resultat
            else:
                st.warning("Lim inn ingredienser først.")

        preview = st.session_state.get("import_preview")
        if preview:
            matched = preview["matched"]
            unmatched = preview["unmatched"]

            st.markdown("**Matchet:**")
            noe_matchet = False
            for m in matched["malt"]:
                st.success(f"Malt: {m['navn']} → `{m['id']}` ({m['mengde']} kg)")
                noe_matchet = True
            for h in matched["humle"]:
                st.success(f"Humle: {h['navn']} → `{h['id']}` ({h['gram']}g, {h['tid']} min)")
                noe_matchet = True
            if matched["gjaer"]:
                g = matched["gjaer"]
                st.success(f"Gjær: {g['navn']} → `{g['id']}`")
                noe_matchet = True
            if not noe_matchet:
                st.info("Ingen ingredienser ble gjenkjent.")

            if unmatched:
                st.markdown("**Ikke gjenkjent:**")
                for u in unmatched:
                    st.error(f"{u['kategori'].capitalize()}: {u['navn']}")

            if noe_matchet:
                if st.button("✅ Importer oppskrift", key="import_bekreft_btn", use_container_width=True):
                    apply_import_to_session_state(preview)
                    del st.session_state["import_preview"]
                    st.rerun()
