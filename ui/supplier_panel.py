import streamlit as st
from config import DEMO_MODE

def render_supplier_panel(malt_database, humle_database, gjaer_database):
    if DEMO_MODE:
        st.info("Leverandør-kontroll er deaktivert i demo-modus.")
        return
    st.write("---")
    st.header("🔍 Leverandør-kontroll")
    st.caption("Verifiser om de lokale databasene dine matcher utvalget hos Vestbrygg og Ølbrygging.")
    
    if st.button("🔍 Sjekk sortiment mot butikkene", width="stretch"):
        from modules.store_sync import lag_sortimentrapport
        with st.spinner("Kontakter vestbrygg.no og olbrygging.no..."):
            rapport = lag_sortimentrapport(malt_database, humle_database, gjaer_database)
        if rapport["status"] == "error":
            st.error(rapport["melding"])
        else:
            st.success("Synkronisering fullført!")
            st.subheader("✨ Nye produkter i butikk")
            if rapport["mangler"]:
                for m in rapport["mangler"]: st.markdown(f"➕ **[{m['type']}]** `{m['id']}` — *{m['name']}*")
            else: st.write("*Ingen manglende produkter funnet. Komplett DB!*")
            
            st.subheader("💰 Prisendringer")
            if rapport["prisavvik"]:
                for p in rapport["prisavvik"]: st.markdown(f"⚠️ **{p['name']}** avviker. Butikk: `{p['butikk_pris']:.1f} kr`")
            else: st.write("*Alle priser i databasen stemmer.*")
