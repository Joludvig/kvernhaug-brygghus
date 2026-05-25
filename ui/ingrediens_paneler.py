# ui/ingrediens_paneler.py
import streamlit as st

def render_malt_panel(malt_database, malt_meny_valg, malt_id_kart, volum):
    st.header("🌾 Meskekaret (Grist)")
    if st.button("➕ Legg til malt"):
        st.session_state.valgt_malt.append({"id": "weyermann_pilsner", "mengde": 0.5})
        st.rerun()

    total_malt_vekt = sum(m["mengde"] for m in st.session_state.valgt_malt if m["id"] in malt_database)
    oppdatert_malt_liste = []
    
    for i, m_item in enumerate(st.session_state.valgt_malt):
        with st.container():
            r_col1, r_col2, r_col3, r_col4, r_col5, r_col6, r_col7 = st.columns([2.8, 1.0, 1.0, 1.0, 1.0, 1.3, 0.5])
            gjeldende_id = m_item["id"]
            gjeldende_visning = "Pilsner Malt (Weyermann / Viking)"
            for visning, m_id in malt_id_kart.items():
                if m_id == gjeldende_id:
                    gjeldende_visning = visning
                    break
            standard_indeks = malt_meny_valg.index(gjeldende_visning) if gjeldende_visning in malt_meny_valg else 1
            with r_col1:
                valgt_visning = st.selectbox(f"Malt #{i+1}", malt_meny_valg, key=f"malt_ui_{i}", index=standard_indeks)
                if valgt_visning.startswith("---"): valgt_visning = "Pilsner Malt (Weyermann)"
                ny_id = malt_id_kart.get(valgt_visning, "weyermann_pilsner")
            with r_col2:
                ny_mengde = st.number_input(f"Kg", min_value=0.0, value=m_item["mengde"], step=0.1, key=f"malt_kg_{i}")
            
            ebc_visning, prosent_visning, og_bidrag_visning, pris_visning, tags_visning = 0.0, "0.0 %", "+0.000", "0.0 kr", ""
            if ny_id in malt_database:
                info = malt_database[ny_id]
                ebc_visning = info["ebc"]
                tags_visning = ", ".join(info["smakstags"])
                prosent_visning = f"{(ny_mengde / total_malt_vekt * 100):.1f} %" if total_malt_vekt > 0 else "0.0 %"
                poeng_alene = (ny_mengde * (info["potensiale"] - 1) * 1000)
                og_alene = (poeng_alene * 0.75) / volum / 1000 if ny_mengde > 0 else 0.0
                og_bidrag_visning = f"+{og_alene:.3f}"
                pris_nokkel = "pris_olbrygging" if st.session_state.global_butikk == "Ølbrygging.no" else "pris_vestbrygg"
                pris_visning = f"{ny_mengde * info[pris_nokkel]:.1f} kr"

            with r_col3: st.text_input("Andel", value=prosent_visning, disabled=True, key=f"malt_pct_{i}")
            with r_col4: st.text_input("Farge", value=f"{ebc_visning:.1f} EBC", disabled=True, key=f"malt_ebc_{i}")
            with r_col5: st.text_input("OG-bidrag", value=og_bidrag_visning, disabled=True, key=f"malt_og_{i}")
            with r_col6: st.text_input("Pris", value=pris_visning, disabled=True, key=f"malt_pris_{i}")
            with r_col7:
                st.write(" ")
                if st.button("❌", key=f"slett_malt_{i}"):
                    st.session_state.valgt_malt.pop(i)
                    st.rerun()
            if tags_visning: st.caption(f"👅 *Smaksprofil:* {tags_visning}")
            st.write("")
            oppdatert_malt_liste.append({"id": ny_id, "mengde": ny_mengde})
    st.session_state.valgt_malt = oppdatert_malt_liste

def render_hop_panel(humle_database, humle_meny_valg, humle_id_kart):
    st.write("---")
    st.header("🌿 Humle-tilsetninger")
    if st.button("➕ Legg til humle"):
        st.session_state.valgt_humle.append({"id": "us_citra", "gram": 20, "tid": 5})
        st.rerun()

    oppdatert_humle_liste = []
    for j, h_item in enumerate(st.session_state.valgt_humle):
        with st.container():
            h_col1, h_col2, h_col3, h_col4, h_col5, h_col6 = st.columns([2.8, 1.0, 1.2, 1.2, 1.3, 0.5])
            gjeldende_h_id = h_item["id"]
            gjeldende_h_visning = "Citra (USA)"
            for visning, h_id in humle_id_kart.items():
                if h_id == gjeldende_h_id:
                    gjeldende_h_visning = visning
                    break
            standard_h_indeks = humle_meny_valg.index(gjeldende_h_visning) if gjeldende_h_visning in humle_meny_valg else 0
            with h_col1:
                valgt_h_visning = st.selectbox(f"Humle #{j+1}", humle_meny_valg, key=f"humle_ui_{j}", index=standard_h_indeks)
                ny_h_id = humle_id_kart.get(valgt_h_visning, "us_citra")
            with h_col2: nytt_gram = st.number_input(f"Gram", min_value=0, value=h_item["gram"], step=5, key=f"humle_gram_{j}")
            with h_col3: ny_tid = st.number_input(f"Tid (Min)", min_value=0, max_value=120, value=h_item["tid"], step=5, key=f"humle_tid_{j}")
            
            h_alfa, h_smak, h_pris = 0.0, "", "0.0 kr"
            if ny_h_id in humle_database:
                h_info = humle_database[ny_h_id]
                h_alfa = h_info["alfa"]
                h_smak = ", ".join(h_info["smakstags"])
                pris_nokkel = "pris_olbrygging" if st.session_state.global_butikk == "Ølbrygging.no" else "pris_vestbrygg"
                h_pris = f"{(nytt_gram * h_info[pris_nokkel] / 100):.1f} kr"
            bruk_type = "Bitter" if ny_tid >= 60 else ("Aroma" if ny_tid > 0 else "Tørrhumle")
            with h_col4: st.text_input("Bruk", value=f"{bruk_type} ({h_alfa}% Alfa)", disabled=True, key=f"humle_type_{j}")
            with h_col5: st.text_input("Pris", value=h_pris, disabled=True, key=f"humle_pris_{j}")
            with h_col6:
                st.write(" ")
                if st.button("❌", key=f"slett_humle_{j}"):
                    st.session_state.valgt_humle.pop(j)
                    st.rerun()
            if h_smak: st.caption(f"👃 *Aromaprofil:* {h_smak}")
            st.write("")
            oppdatert_humle_liste.append({"id": ny_h_id, "gram": nytt_gram, "tid": ny_tid})
    st.session_state.valgt_humle = oppdatert_humle_liste

def render_yeast_panel(gjaer_id_kart, gjaer_meny_valg):
    st.write("---")
    st.header("🧫 Gjærstamme")
    gjeldende_g_visning = "SafAle US-05 (Amerikansk Ale) (Fermentis (Tørr))"
    for visning, g_id in gjaer_id_kart.items():
        if g_id == st.session_state.valgt_gjaer_id:
            gjeldende_g_visning = visning
            break
    g_indeks = gjaer_meny_valg.index(gjeldende_g_visning) if gjeldende_g_visning in gjaer_meny_valg else 0
    valgt_gjaer_visning = st.selectbox("Velg gjær:", gjaer_meny_valg, index=g_indeks)
    st.session_state.valgt_gjaer_id = gjaer_id_kart[valgt_gjaer_visning]
