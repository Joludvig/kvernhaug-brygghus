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
        [s for s in ctx['style_analysis']["stil_liste"] if s["score"] >= 5],
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

    # Blomster-advarsel — vektet floral_score med koketidsfaktor og maskering fra røyk/mørke malter
    _FLORALE_TAGS = {"blomst", "blomster", "floral", "parfyme", "parfymert"}
    batch_liter = max(ctx["volum"], 1.0)
    floral_score = 0.0
    for h in st.session_state.valgt_humle:
        if h["gram"] > 0 and h["id"] in humle_database:
            if any(t in _FLORALE_TAGS for t in humle_database[h["id"]].get("smakstags", [])):
                tid = h.get("tid", 0)
                if tid == 0:
                    tid_faktor = 1.00
                elif tid <= 5:
                    tid_faktor = 0.85
                elif tid <= 15:
                    tid_faktor = 0.35
                else:
                    tid_faktor = 0.05
                floral_score += (h["gram"] / batch_liter) * tid_faktor

    fp = ctx["recipe"]["flavor_profile"]
    mask_score = fp.get("Røyk", 0) + fp.get("Kaffe", 0) * 0.6 + fp.get("Sjokolade", 0) * 0.4

    if floral_score >= 0.30:
        if mask_score >= 4.0:
            st.warning(
                f"🌸 **Blomsterpreg til stede** *(floral {floral_score:.2f}, demping {mask_score:.1f}):* "
                "Humlen bidrar floral karakter, men røyk og mørke malter vil sannsynligvis overdøve dette i det ferdige ølet."
            )
        else:
            st.error(
                f"⚠️ **Sterk blomster-/parfymerisiko** *(floral {floral_score:.2f}):* "
                "Florale humler dominerer smaksprofilen — dette ølet vil sannsynligvis smake parfymert. "
                "Vurder nøytrale sorter (Magnum, Hallertau) eller reduser sene tilsetninger."
            )
    elif floral_score >= 0.10 and mask_score < 3.0:
        st.warning(
            f"🌸 **Mulig blomsterpreg** *(floral {floral_score:.2f}):* "
            "En liten floral komponent er til stede. Trolig ikke dominerende, "
            "men kan merkes av sensitive nese/gane."
        )
