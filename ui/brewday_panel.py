import streamlit as st
from modules.brewday_calc import lag_brewday_plan


def render_brewday_panel(ctx, humle_database, gjaer_database):
    st.write("---")
    with st.expander("🍺 Bryggeplan"):
        gjaer_id   = st.session_state.get("valgt_gjaer_id", "")
        gjaer_info = gjaer_database.get(gjaer_id, {})

        plan = lag_brewday_plan(
            malt_valg     = st.session_state.get("valgt_malt", []),
            humle_valg    = st.session_state.get("valgt_humle", []),
            gjaer_id      = gjaer_id,
            gjaer_info    = gjaer_info,
            og            = ctx["og"],
            batch_volum_l = ctx["volum"],
            humle_database= humle_database,
        )

        st.subheader(ctx["name"])
        st.caption(f"Batch: {ctx['volum']:.0f} L  ·  Totalt korn: {plan['total_korn_kg']:.2f} kg")

        # ── VANN ──────────────────────────────────────────
        st.markdown("**💧 Vann**")
        w = plan["vann"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Maskevatn",  f"{w['mash_vann_l']:.1f} L")
        c2.metric("Spargevatn", f"{w['sparge_vann_l']:.1f} L")
        c3.metric("Pre-boil",   f"{w['pre_boil_l']:.1f} L")

        # ── MESKING ───────────────────────────────────────
        st.write("")
        st.markdown("**🌡️ Mesking**")
        for steg in plan["maskeplan"]:
            st.write(f"- {steg['temp_c']}°C i {steg['varighet_min']} min — *{steg['label']}*")

        # ── KOKING ────────────────────────────────────────
        st.write("")
        st.markdown("**🔥 Koking**")
        st.write(f"- {plan['koketid_min']} min")
        if plan["koketid_min"] == 90:
            st.caption("90 min anbefalt for Pilsnermalt — reduserer DMS-forstadie.")

        # ── HUMLETILSETNINGER ─────────────────────────────
        st.write("")
        st.markdown("**🌿 Humletilsetninger**")
        if plan["humleplan"]:
            for h in plan["humleplan"]:
                st.write(f"- {h['gram']}g {h['navn']} @{h['tid']} min")
        else:
            st.caption("Ingen humle i oppskriften.")

        # ── GJÆR ──────────────────────────────────────────
        st.write("")
        st.markdown("**🧫 Gjær**")
        st.write(f"- {plan['gjaer_navn']}")
        st.write(f"- Anbefalt: **{plan['pakker']} pakke(r)**")
        st.write(f"- Fermenteringstemperatur: **{plan['temp_min']}–{plan['temp_maks']}°C**")
        for note in plan["noter"]:
            st.info(note)

        # ── UTSTYRSNOTAT ──────────────────────────────────
        st.write("")
        st.caption(
            "Beregnet med standard BrewZilla 35L-verdier: "
            "3,2 L/kg maskeforhold · 1,0 L/kg kornabsorpsjon · "
            "4,0 L/t fordampning · 2,0 L dead volume."
        )
