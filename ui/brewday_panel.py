import streamlit as st
from modules.brewday_calc import lag_brewday_plan
from modules.export_format import fmt_og, fmt_fg, fmt_abv, stats_linje
from modules.brewday_template import render_brewday_html

_SJEKKLISTE = [
    "Utstyr rent", "Meskevann varmt", "Skylling ferdig", "Kok startet",
    "Humle tilsatt", "Nedkjøling ferdig", "Gjær tilsatt", "Gjæring startet",
]


def render_brewday_panel(ctx, humle_database, gjaer_database, malt_database=None):
    st.write("---")
    with st.expander("🍺 Bryggeplan"):
        gjaer_id   = st.session_state.get("valgt_gjaer_id", "")
        gjaer_info = gjaer_database.get(gjaer_id, {})

        plan = lag_brewday_plan(
            malt_valg      = st.session_state.get("valgt_malt", []),
            humle_valg     = st.session_state.get("valgt_humle", []),
            gjaer_id       = gjaer_id,
            gjaer_info     = gjaer_info,
            og             = ctx["og"],
            batch_volum_l  = ctx["volum"],
            humle_database = humle_database,
            malt_database  = malt_database,
        )

        # ── HEADER ──────────────────────────────────────────
        st.subheader(ctx["name"])
        if ctx.get("brygger_stil"):
            st.caption(ctx["brygger_stil"])
        st.caption(stats_linje(ctx))

        # ── BATCH-INFO ──────────────────────────────────────
        bi1, bi2, bi3 = st.columns(3)
        with bi1:
            st.text_input("Batchnummer", placeholder="f.eks. 2026-001", key="bd_batchnr")
        with bi2:
            st.date_input("Bryggedato", key="bd_dato")
        with bi3:
            st.text_input("Brygger", placeholder="Navn", key="bd_brygger")

        st.write("---")

        # ── VENSTRE / HØYRE ─────────────────────────────────
        bd_left, bd_right = st.columns(2)

        with bd_left:
            st.markdown(f"**🌾 Malt — {plan['total_korn_kg']:.2f} kg**")
            for i, m in enumerate(plan["malt_liste"]):
                st.checkbox(f"{m['mengde']:.2f} kg — {m['navn']}", key=f"bd_malt_{i}")

            st.write("")
            st.markdown("**💧 Vann**")
            w = plan["vann"]
            c1, c2, c3 = st.columns(3)
            c1.metric("Meskevann",  f"{w['mash_vann_l']:.1f} L")
            c2.metric("Skyllevann", f"{w['sparge_vann_l']:.1f} L")
            c3.metric("Pre-boil",   f"{w['pre_boil_l']:.1f} L")

            st.write("")
            st.markdown("**🌡️ Mesking**")
            for steg in plan["maskeplan"]:
                st.write(f"- {steg['temp_c']}°C  ·  {steg['varighet_min']} min  —  *{steg['label']}*")

            st.write("")
            st.markdown("**🔥 Koking**")
            st.write(f"- {plan['koketid_min']} min")
            if plan["koketid_min"] == 90:
                st.caption("90 min anbefalt for Pilsnermalt.")

        with bd_right:
            st.markdown("**🌿 Humletilsetninger**")
            if plan["humleplan"]:
                header = "| Tid | Humle | Gram | IBU |\n|-----|-------|------|-----|"
                rows = "\n".join(
                    f"| {h['tid']} min | {h['navn']} | {h['gram']:.0f} g | {h['ibu_bidrag']:.1f} |"
                    for h in plan["humleplan"]
                )
                st.markdown(f"{header}\n{rows}")
            else:
                st.caption("Ingen humle i oppskriften.")

            st.write("")
            st.markdown("**🧫 Gjær & Fermentering**")
            st.write(f"- **{plan['gjaer_navn']}** — {plan['pakker']} pakke(r)")
            st.write(f"- Temp: **{plan['temp_min']}–{plan['temp_maks']}°C**")
            for note in plan["noter"]:
                st.info(note)
            ferm1, ferm2 = st.columns(2)
            with ferm1:
                st.date_input("Gjæringsstart", key="bd_ferm_start")
            with ferm2:
                st.date_input("Cold crash / tapping", key="bd_ferm_slutt")

        # ── SJEKKLISTE ──────────────────────────────────────
        st.write("---")
        st.markdown("**✅ Bryggedags-sjekkliste**")
        chk_cols = st.columns(4)
        for i, item in enumerate(_SJEKKLISTE):
            chk_cols[i % 4].checkbox(item, key=f"bd_chk_{i}")

        # ── MÅLINGER ────────────────────────────────────────
        st.write("---")
        st.markdown("**📐 Målinger**")
        og_col, fg_col, abv_col = st.columns(3)
        with og_col:
            st.text_input(f"OG (mål: {fmt_og(ctx['og'])})", placeholder="Faktisk", key="bd_og")
        with fg_col:
            st.text_input(f"FG (mål: {fmt_fg(ctx['fg'])})", placeholder="Faktisk", key="bd_fg")
        with abv_col:
            st.text_input(f"ABV (mål: {fmt_abv(ctx['abv'])})", placeholder="Faktisk", key="bd_abv")

        st.caption("Vannberegning basert på aktiv utstyrsprofil.")

        # ── PRINT-ARK ───────────────────────────────────────
        st.write("")
        if st.button("🖨️ Generer Bryggedagsark", use_container_width=True, key="brewday_print_btn"):
            html = render_brewday_html(ctx, plan)
            fil_navn = ctx["name"].replace(" ", "_").replace("/", "-") + "_bryggedag.html"
            st.download_button(
                label="📥 Last ned bryggedagsark",
                data=html,
                file_name=fil_navn,
                mime="text/html",
                use_container_width=True,
                key="brewday_download_btn",
            )
            st.info("💡 Åpne filen i nettleseren og trykk **Ctrl + P** for å skrive ut.")
