import streamlit as st

FORETRUKKET_GRUPPE_REKKEFØLGE = [
    "PALE / PILSNER",
    "MUNICH / VIENNA",
    "HVETE / RUG",
    "KARAMELL / CRYSTAL",
    "RØSTET / MØRK",
    "SPESIALMALT",
    "FLAKES / UMALTET",
    "NORSK MALT",
    "EKSTRAKT / SPRAYMALT",
]

KATEGORI_TIL_GRUPPE = {
    "Basemalt": "PALE / PILSNER",
    "Hvete- / Rugmalt": "HVETE / RUG",
    "Karamell- / Krystallmalt": "KARAMELL / CRYSTAL",
    "Spesialmalt (Røstet / Andre)": "RØSTET / MØRK",
    "Flakes / Korn": "FLAKES / UMALTET",
    "Spraymalt": "EKSTRAKT / SPRAYMALT",
    "Norsk Malt": "NORSK MALT",
}

def _malt_gruppe(info):
    return info.get("display_group") or KATEGORI_TIL_GRUPPE.get(info.get("kategori", ""), "SPESIALMALT")

def render_malt_panel(malt_database):
    st.header("🌾 Meskekaret (Grist)")
    if st.button("➕ Legg til malt", key="add_malt_btn"):
        st.session_state.valgt_malt.append({"id": "weyermann_pilsner", "mengde": 0.5})
        st.rerun()

    total_malt_vekt = sum(m["mengde"] for m in st.session_state.valgt_malt if m["id"] in malt_database)

    alle_db_grupper = {_malt_gruppe(info) for info in malt_database.values() if info}
    malt_grupper = [g for g in FORETRUKKET_GRUPPE_REKKEFØLGE if g in alle_db_grupper]
    malt_grupper += sorted(g for g in alle_db_grupper if g not in FORETRUKKET_GRUPPE_REKKEFØLGE)

    malt_id_kart, malt_meny_valg = {}, []
    for gruppe in malt_grupper:
        har_varer = False
        midlertidig_liste = []
        for m_id, info in malt_database.items():
            if _malt_gruppe(info) == gruppe:
                visnings_navn = f"{info['display_name']} ({info['produsent']})"
                malt_id_kart[visnings_navn] = m_id
                midlertidig_liste.append(visnings_navn)
                har_varer = True
        if har_varer:
            malt_meny_valg.append(f"--- {gruppe} ---")
            malt_meny_valg.extend(midlertidig_liste)

    # SKUDDSIKKER FALLBACK: Hvis databasen er tom, legger vi inn et standard testvalg
    # slik at selectboxen ikke blir tom (noe som forårsaker None-krasj)
    if not malt_meny_valg:
        malt_meny_valg = ["Pilsner Malt (Weyermann)"]
        malt_id_kart["Pilsner Malt (Weyermann)"] = "weyermann_pilsner"

    _v = st.session_state.get("import_versjon", 0)
    oppdatert_malt_liste = []
    for i, m_item in enumerate(st.session_state.valgt_malt):
        with st.container():
            r_col1, r_col2, r_col3, r_col4, r_col5, r_col6, r_col7 = st.columns([2.8, 1.0, 1.0, 1.0, 1.0, 1.3, 0.5])

            gjeldende_id = m_item["id"]
            gjeldende_visning = next((v for v, mid in malt_id_kart.items() if mid == gjeldende_id), None)
            if not gjeldende_visning or gjeldende_visning not in malt_meny_valg:
                gjeldende_visning = next((v for v in malt_meny_valg if not v.startswith("---")), malt_meny_valg[0])
            standard_indeks = malt_meny_valg.index(gjeldende_visning)

            with r_col1:
                valgt_visning = st.selectbox(f"Malt #{i+1}", malt_meny_valg, key=f"malt_ui_{i}_v{_v}", index=standard_indeks)
                if valgt_visning and valgt_visning.startswith("---"):
                    valgt_visning = next((v for v in malt_meny_valg if not v.startswith("---")), valgt_visning)
                ny_id = malt_id_kart.get(valgt_visning, next(iter(malt_id_kart.values()), ""))
            with r_col2:
                ny_mengde = st.number_input(f"Kg", min_value=0.0, value=m_item["mengde"], step=0.1, key=f"malt_kg_{i}_v{_v}")
            
            ebc_visning, prosent_visning, og_bidrag_visning, pris_visning, tags_visning = 0.0, "0.0 %", "+0.000", "0.0 kr", ""
            if ny_id in malt_database:
                info = malt_database[ny_id]
                ebc_visning = info.get("ebc", 4.0)
                tags_visning = ", ".join(info.get("smakstags", ["maltet"]))
                prosent_visning = f"{(ny_mengde / total_malt_vekt * 100):.1f} %" if total_malt_vekt > 0 else "0.0 %"
                poeng_alene = (ny_mengde * (info.get("potensiale", 1.036) - 1) * 1000)
                og_alene = (poeng_alene * 0.75) / 20.0 / 1000 if ny_mengde > 0 else 0.0
                og_bidrag_visning = f"+{og_alene:.3f}"
                butikk_navn = st.session_state.get("global_butikk", "Ølbrygging.no")
                pris_nokkel = "pris_olbrygging" if butikk_navn == "Ølbrygging.no" else "pris_vestbrygg"
                pris_visning = f"{ny_mengde * info.get(pris_nokkel, 35.0):.1f} kr"
            else:
                # Fallback verdier for visning hvis id ikke finnes i databasen ennå
                prosent_visning = f"{(ny_mengde / total_malt_vekt * 100):.1f} %" if total_malt_vekt > 0 else "0.0 %"
                pris_visning = f"{ny_mengde * 35.0:.1f} kr"

            with r_col3: st.text_input("Andel", value=prosent_visning, disabled=True, key=f"malt_pct_{i}_v{_v}")
            with r_col4: st.text_input("Farge", value=f"{ebc_visning:.1f} EBC", disabled=True, key=f"malt_ebc_{i}_v{_v}")
            with r_col5: st.text_input("OG-bidrag", value=og_bidrag_visning, disabled=True, key=f"malt_og_{i}_v{_v}")
            with r_col6: st.text_input("Pris", value=pris_visning, disabled=True, key=f"malt_pris_{i}_v{_v}")
            with r_col7:
                st.write(" ")
                if st.button("❌", key=f"slett_malt_{i}_v{_v}"):
                    st.session_state.valgt_malt.pop(i)
                    st.rerun()
            if tags_visning: st.caption(f"👅 *Smaksprofil:* {tags_visning}")
            st.write("")
            oppdatert_malt_liste.append({"id": ny_id, "mengde": ny_mengde})
    st.session_state.valgt_malt = oppdatert_malt_liste
