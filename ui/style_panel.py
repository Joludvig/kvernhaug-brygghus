import streamlit as st

def render_style_panel(ctx, humle_database):
    st.plotly_chart(ctx["fig_smak"], use_container_width=True, key="kvernhaug_smakshjul")
    
    st.header("🧠 Kvernhaug AI: Stil- & Balanse")
    st.subheader(f"Nærmeste stil: *{ctx['style_analysis']['stil']}*")
    st.write(f"📊 **Bitterhetsindeks (BU:GU):** `{ctx['style_analysis']['bu_gu']:.2f}`")
    
    for note in ctx['style_analysis']['balanse']: st.write(note)
    for problem in ctx['style_analysis']['problemer']: st.warning(problem)

    st.write("---")
    st.subheader("🎯 BJCP Stil-matching (Prosentvis):")
    relevante_stiler = sorted(
        [s for s in ctx['style_analysis']["stil_liste"] if s["score"] > 0],
        key=lambda x: (-x["score"], x["prio"])
    )
    if not relevante_stiler:
        st.caption("Ingen stiler matcher oppskriften din ennå.")
    for s_item in relevante_stiler:
        st.write(f"🔹 **{s_item['stil']}:** `{s_item['score']}% match`")
        if s_item["mangler"] and s_item["score"] > 20:
            with st.expander(f"Se hva som mangler for {s_item['stil']}"):
                for mangel in s_item["mangler"]: st.caption(f"❌ {mangel}")

    if ctx["conflicts"]:
        st.write("---")
        st.subheader("⚠️ Sensoriske konflikter registrert:")
        for konflikt in ctx["conflicts"]: st.error(konflikt)

    # Blomster-advarsel basert på aktive tags
    _FLORALE_TAGS = {"blomst", "blomster", "floral", "parfyme", "parfymert"}
    aktive_humle_tags = set()
    for h in st.session_state.valgt_humle:
        if h["gram"] > 0 and h["id"] in humle_database:
            aktive_humle_tags.update(humle_database[h["id"]].get("smakstags", []))
    if aktive_humle_tags & _FLORALE_TAGS:
        st.error("⚠️ **ADVARSEL!** Ølet vil få en **parfymert og blomsteraktig smak**.")
