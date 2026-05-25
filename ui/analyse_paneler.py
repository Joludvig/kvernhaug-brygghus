# ui/analyse_paneler.py
import streamlit as st

def render_style_analysis(context):
    """Viser BJCP-matching og smaksadvarsler i høyre kolonne."""
    analyse = context["style_analysis"]
    recipe = context["recipe"]
    konflikter = context["conflicts"]

    st.header("🧠 Kvernhaug AI: Stil- & Balanse")
    st.subheader(f"Nærmeste stil: *{analyse['stil']}*")
    st.write(f"📊 **Bitterhetsindeks (BU:GU):** `{analyse['bu_gu']:.2f}`")
    for note in analyse['balanse']: st.write(note)
    for problem in analyse['problemer']: st.warning(problem)

    st.write("---")
    st.subheader("🎯 BJCP Stil-matching (Prosentvis):")
    for s_item in analyse["stil_liste"]:
        st.write(f"🔹 **{s_item['stil']}:** `{s_item['score']}% match`")
        if s_item["mangler"] and s_item["score"] > 20:
            with st.expander(f"Se hva som mangler for {s_item['stil']}"):
                for mangel in s_item["mangler"]: st.caption(f"❌ {mangel}")

    if konflikter:
        st.write("---")
        st.subheader("⚠️ Sensoriske konflikter registrert:")
        for konflikt in konflikter: st.error(konflikt)

def render_supplier_sync(malt_database, humle_database, gjaer_database):
    """Viser leverandørkontrollen i høyre kolonne."""
    st.write("---")
    st.header("🔍 Leverandør-kontroll")
    st.caption("Verifiser om de lokale databasene dine matcher utvalget hos Vestbrygg og Ølbrygging.")
    
    if st.button("🔍 Sjekk sortiment mot butikkene", use_container_width=True):
        from modules.store_sync import lag_sortimentrapport
        with st.spinner("Kontakter vestbrygg.no and olbrygging.no..."):
            rapport = lag_sortimentrapport(malt_database, humle_database, gjaer_database)
        if rapport["status"] == "error":
            st.error(rapport["melding"])
        else:
            st.success("Synkronisering fullført! Her er avvikene som ble oppdaget:")
            st.subheader("✨ Nye produkter i butikk (Mangler i Kvernhaug DB)")
            if rapport["mangler"]:
                for m in rapport["mangler"]: st.markdown(f"➕ **[{m['type']}]** `{m['id']}` — *{m['name']}* (Butikkpris: {m['pris']:.1f} kr)")
            else: st.write("*Ingen manglende produkter funnet. Databasen din er komplett!*")
            st.write(" ")
            st.subheader("💰 Registrerte prisendringer i butikk")
            if rapport["prisavvik"]:
                for p in rapport["prisavvik"]: st.markdown(f"⚠️ **{p['name']}** avviker. Butikk: `{p['butikk_pris']:.1f} kr` | Din DB: OB=`{p['db_pris_ob']:.1f} kr`, VB=`{p['db_pris_vb']:.1f} kr`")
            else: st.write("*Alle priser i databasen stemmer overens med butikkene.*")
