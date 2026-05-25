import streamlit as st

def render_hop_panel(humle_database):
    st.header("🌿 Humle-tilsetninger")
    if st.button("➕ Legg til humle", key="add_hop_btn"):
        st.session_state.valgt_humle.append({"id": "citra", "gram": 20, "tid": 5})
        st.rerun()

    humle_id_kart, humle_meny_valg = {}, []
    for h_id, info in humle_database.items():
        if info:
            opprinnelse = info.get("opprinnelse", "")
            visnings_navn = (
                f"{info.get('display_name', h_id)} ({opprinnelse})"
                if opprinnelse and opprinnelse != "Ukjent"
                else info.get("display_name", h_id)
            )
            humle_id_kart[visnings_navn] = h_id
            humle_meny_valg.append(visnings_navn)

    # SKUDDSIKKER FALLBACK: Hvis humledatabasen er tom, oppretter vi et standardvalg
    if not humle_meny_valg:
        standard_visning = "Citra (USA)"
        humle_meny_valg = [standard_visning]
        humle_id_kart[standard_visning] = "citra"

    _v = st.session_state.get("import_versjon", 0)
    oppdatert_humle_liste = []
    for j, h_item in enumerate(st.session_state.valgt_humle):
        with st.container():
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.8, 1.0, 1.2, 1.2, 1.3, 0.5])
            gjeldende_h_id = h_item["id"]
            gjeldende_h_visning = next((v for v, hid in humle_id_kart.items() if hid == gjeldende_h_id), None)
            if not gjeldende_h_visning or gjeldende_h_visning not in humle_meny_valg:
                gjeldende_h_visning = humle_meny_valg[0] if humle_meny_valg else "Citra (USA)"
            standard_h_indeks = humle_meny_valg.index(gjeldende_h_visning)

            with h_col1:
                valgt_h_visning = st.selectbox(f"Humle #{j+1}", humle_meny_valg, key=f"humle_ui_{j}_v{_v}", index=standard_h_indeks)
                ny_h_id = humle_id_kart.get(valgt_h_visning, next(iter(humle_id_kart.values()), ""))
            with h_col2:
                nytt_gram = st.number_input(f"Gram", min_value=0.0, value=float(h_item["gram"]), step=5.0, key=f"humle_gram_{j}_v{_v}")
            with h_col3:
                ny_tid = st.number_input(f"Tid (Min)", min_value=0, max_value=120, value=h_item["tid"], step=5, key=f"humle_tid_{j}_v{_v}")
            
            h_alfa, h_smak, h_pris = 0.0, "", "0.0 kr"
            if ny_h_id in humle_database:
                h_info = humle_database[ny_h_id]
                h_alfa = h_info.get("alfa_typisk") or h_info.get("alfa", 12.0)
                smakstags_liste = h_info.get("smakstags") or []
                h_smak = ", ".join(smakstags_liste)
                butikk_navn = st.session_state.get("global_butikk", "Ølbrygging.no")
                h_pris_nokkel = "pris_olbrygging" if butikk_navn == "Ølbrygging.no" else "pris_vestbrygg"
                h_pris = f"{(nytt_gram * h_info.get(h_pris_nokkel, 99.0) / 100):.1f} kr"
            else:
                # Fallback hvis ID-en ikke finnes på disk ennå
                h_alfa = 12.0
                h_pris = f"{(nytt_gram * 99.0 / 100):.1f} kr"

            bruk_type = "Bitter" if ny_tid >= 60 else ("Smak" if ny_tid >= 15 else ("Aroma" if ny_tid > 0 else "Tørrhumle"))
            with h_col4: st.text_input("Bruk", value=f"{bruk_type} ({h_alfa}% Alfa)", disabled=True, key=f"humle_type_{j}_v{_v}")
            with h_col5: st.text_input("Pris", value=h_pris, disabled=True, key=f"humle_pris_{j}_v{_v}")
            with h_col6:
                st.write(" ")
                if st.button("❌", key=f"slett_humle_{j}_v{_v}"):
                    st.session_state.valgt_humle.pop(j)
                    st.rerun()
            if h_smak:
                st.caption(f"👃 *Smak:* {h_smak}")
            st.write("")
            oppdatert_humle_liste.append({"id": ny_h_id, "gram": nytt_gram, "tid": ny_tid})
    st.session_state.valgt_humle = oppdatert_humle_liste
