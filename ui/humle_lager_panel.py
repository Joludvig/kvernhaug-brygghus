import streamlit as st
from config import DEMO_MODE
from modules.humle_lager import les_lager, lagre_lager


def render_humle_lager_panel(humle_database: dict) -> None:
    if DEMO_MODE:
        return
    st.write("---")
    with st.expander("📦 Humlelager"):
        st.caption("Registrer din beholdning av humle i gram. Lager trekkes ikke automatisk ved brygging.")

        lager = les_lager()
        endret = False
        to_delete = []

        if lager:
            st.markdown("**Registrert beholdning**")
            hdr_n, hdr_g, hdr_d = st.columns([3, 2, 1])
            with hdr_n: st.caption("Humle")
            with hdr_g: st.caption("Gram på lager")

            for h_id in sorted(lager.keys()):
                gram = lager[h_id]
                h_info = humle_database.get(h_id, {})
                navn = h_info.get("display_name", h_id)

                col_n, col_g, col_d = st.columns([3, 2, 1])
                with col_n:
                    st.write(navn)
                with col_g:
                    ny = st.number_input(
                        "g",
                        min_value=0,
                        value=int(gram),
                        step=10,
                        key=f"lager_input_{h_id}",
                        label_visibility="collapsed",
                    )
                    if ny != gram:
                        lager[h_id] = float(ny)
                        endret = True
                with col_d:
                    if st.button("✕", key=f"lager_slett_{h_id}", help=f"Fjern {navn} fra lager"):
                        to_delete.append(h_id)
        else:
            st.info("Ingen humle registrert ennå. Legg til via skjemaet nedenfor.")

        for h_id in to_delete:
            del lager[h_id]
            endret = True

        if endret:
            lagre_lager(lager)
            st.rerun()

        st.write("")
        st.markdown("**Legg til humle**")

        allerede = set(lager.keys())
        tilgjengelige = [k for k in humle_database if k not in allerede]
        tilgjengelige_navn = {k: humle_database[k].get("display_name", k) for k in tilgjengelige}

        if tilgjengelige:
            col_sel, col_g, col_btn = st.columns([3, 2, 1])
            with col_sel:
                ny_id = st.selectbox(
                    "Humle",
                    options=tilgjengelige,
                    format_func=lambda x: tilgjengelige_navn[x],
                    key="lager_ny_id",
                    label_visibility="collapsed",
                )
            with col_g:
                ny_gram = st.number_input(
                    "Gram",
                    min_value=0,
                    value=100,
                    step=10,
                    key="lager_ny_gram",
                    label_visibility="collapsed",
                )
            with col_btn:
                if st.button("Legg til", key="lager_legg_til_btn", use_container_width=True):
                    lager[ny_id] = float(ny_gram)
                    lagre_lager(lager)
                    st.rerun()
        else:
            st.caption("Alle humler er allerede registrert i lageret.")
