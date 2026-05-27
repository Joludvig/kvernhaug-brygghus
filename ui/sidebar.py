import json
import streamlit as st
from modules.recipe_storage import hent_alle_oppskrifter
from modules.recipe_importer import (
    parse_recipe_text,
    match_imported_ingredients,
    apply_import_to_session_state,
)

def _last_master_db(filnavn):
    try:
        with open(f"data/{filnavn}", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def render_sidebar():
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
            st.session_state.batch_volum_input = r_data.get("batch_size", 20.0)
            st.session_state.import_versjon = st.session_state.get("import_versjon", 0) + 1
            st.sidebar.success(f"Laddet: {valgt_lagret_navn}")
            st.rerun()
    else:
        st.sidebar.info("Ingen oppskrifter lagret i mappen ennå.")

    st.sidebar.write("---")
    with st.sidebar.expander("📥 Importer oppskrift fra tekst"):
        st.caption(
            "**Kg-format:**\n\n"
            "`5 kg Maris Otter`\n\n"
            "`300 g CaraMunich`\n\n"
            "**Prosentformat** (krever total maltmengde):\n\n"
            "`Total malt: 6 kg`\n\n"
            "`90% Maris Otter`\n\n"
            "`10% Crystal Malt`\n\n"
            "**Humle og gjær:**\n\n"
            "`20 g Magnum 60 min`\n\n"
            "`Wyeast 1318 London Ale III`\n\n"
            "⚠️ Humle må ha koketid, f.eks. `50 g Magnum 60 min`."
        )
        import_tekst = st.text_area("Oppskrift:", height=160, key="import_tekst_input", label_visibility="collapsed")

        if st.button("🔍 Analyser", key="import_analyser_btn", use_container_width=True):
            if import_tekst.strip():
                parsed = parse_recipe_text(import_tekst)
                master_malt  = _last_master_db("master_malt.json")
                master_humle = _last_master_db("master_humle_v2.json")
                master_gjaer = _last_master_db("master_gjaer_v2.json")
                resultat = match_imported_ingredients(parsed, master_malt, master_humle, master_gjaer)
                resultat["metadata"] = {"navn": parsed.get("navn"), "batch_liter": parsed.get("batch_liter")}
                st.session_state["import_preview"] = resultat
                st.session_state["import_parsed"] = parsed
            else:
                st.warning("Lim inn ingredienser først.")

        preview = st.session_state.get("import_preview")
        if preview:
            parsed_debug = st.session_state.get("import_parsed", {})
            n_malt  = len(parsed_debug.get("malt", []))
            n_humle = len(parsed_debug.get("humle", []))
            n_gjaer = len(parsed_debug.get("gjaer", []))
            st.caption(f"Tolket: {n_malt} malt · {n_humle} humle · {n_gjaer} gjær-linje(r)")
            meta = preview.get("metadata", {})
            if meta.get("navn"):
                st.caption(f"📛 Navn: **{meta['navn']}**")
            if meta.get("batch_liter"):
                st.caption(f"🪣 Batch: **{meta['batch_liter']:.0f} L**")
            for w in parsed_debug.get("warnings", []):
                st.warning(w)

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
                    del st.session_state["import_parsed"]
                    st.rerun()
