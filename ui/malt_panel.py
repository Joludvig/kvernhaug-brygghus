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

    # _v must be known before any widget is created so key names are consistent
    _v = st.session_state.get("import_versjon", 0)

    # --- PRE-RENDER SYNC ---
    # When a pct edit redistributed kg values last run, we seed all widget keys here —
    # before any number_input is instantiated — to avoid StreamlitAPIException.
    if st.session_state.get("_malt_pct_pending_sync"):
        st.session_state["_malt_pct_pending_sync"] = False
        _sync_total = sum(m["mengde"] for m in st.session_state.valgt_malt)
        for _j, _m in enumerate(st.session_state.valgt_malt):
            _new_pct = round(_m["mengde"] / _sync_total * 100, 1) if _sync_total > 0 else 0.0
            st.session_state[f"malt_kg_{_j}_v{_v}"] = _m["mengde"]
            st.session_state[f"malt_pct_{_j}_v{_v}"] = _new_pct

    if st.button("➕ Legg til malt", key="add_malt_btn"):
        st.session_state.valgt_malt.append({"id": "weyermann_pilsner", "mengde": 0.5})
        st.rerun()

    # Canonical total captured before any widget changes this render
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

    if not malt_meny_valg:
        malt_meny_valg = ["Pilsner Malt (Weyermann)"]
        malt_id_kart["Pilsner Malt (Weyermann)"] = "weyermann_pilsner"

    oppdatert_malt_liste = []
    needs_rerun = False
    # Track if a pct field was edited this render (only one widget can change per rerun)
    pct_edit_row = None
    pct_edit_new_kg = None
    pct_edit_stored_kg = None

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

            stored_kg = m_item["mengde"]
            old_pct = round(stored_kg / total_malt_vekt * 100, 1) if total_malt_vekt > 0 else 0.0
            kg_key = f"malt_kg_{i}_v{_v}"
            pct_key = f"malt_pct_{i}_v{_v}"

            with r_col2:
                ny_kg = st.number_input("Kg", min_value=0.0, value=stored_kg, step=0.1, key=kg_key)

            kg_changed = abs(ny_kg - stored_kg) > 0.001

            if kg_changed:
                # Kg edited — pre-seed pct widget for this row and schedule full sync
                new_total = total_malt_vekt - stored_kg + ny_kg
                st.session_state[pct_key] = round(ny_kg / new_total * 100, 1) if new_total > 0 else 0.0
                needs_rerun = True

            with r_col3:
                ny_pct = st.number_input("Andel %", min_value=0.0, max_value=100.0, value=old_pct, step=0.5, key=pct_key, format="%.1f")

            pct_changed = not kg_changed and total_malt_vekt > 0 and abs(ny_pct - old_pct) > 0.05

            if pct_changed:
                final_kg = round(ny_pct / 100.0 * total_malt_vekt, 3)
                pct_edit_row = i
                pct_edit_new_kg = final_kg
                pct_edit_stored_kg = stored_kg
                needs_rerun = True
            else:
                final_kg = ny_kg

            ebc_visning, og_bidrag_visning, pris_visning, tags_visning = 0.0, "+0.000", "0.0 kr", ""
            if ny_id in malt_database:
                info = malt_database[ny_id]
                ebc_visning = info.get("ebc", 4.0)
                tags_visning = ", ".join(info.get("smakstags", ["maltet"]))
                poeng_alene = final_kg * (info.get("potensiale", 1.036) - 1) * 1000
                og_alene = (poeng_alene * 0.75) / 20.0 / 1000 if final_kg > 0 else 0.0
                og_bidrag_visning = f"+{og_alene:.3f}"
                butikk_navn = st.session_state.get("global_butikk", "Ølbrygging.no")
                pris_nokkel = "pris_olbrygging" if butikk_navn == "Ølbrygging.no" else "pris_vestbrygg"
                pris_visning = f"{final_kg * info.get(pris_nokkel, 35.0):.1f} kr"
            else:
                pris_visning = f"{final_kg * 35.0:.1f} kr"

            with r_col4: st.text_input("Farge", value=f"{ebc_visning:.1f} EBC", disabled=True, key=f"malt_ebc_{i}_v{_v}")
            with r_col5: st.text_input("OG-bidrag", value=og_bidrag_visning, disabled=True, key=f"malt_og_{i}_v{_v}")
            with r_col6: st.text_input("Pris", value=pris_visning, disabled=True, key=f"malt_pris_{i}_v{_v}")
            with r_col7:
                st.write(" ")
                if st.button("❌", key=f"slett_malt_{i}_v{_v}"):
                    st.session_state.valgt_malt.pop(i)
                    st.rerun()
            if tags_visning:
                st.caption(f"👅 *Smaksprofil:* {tags_visning}")
            st.write("")
            oppdatert_malt_liste.append({"id": ny_id, "mengde": final_kg})

    st.session_state.valgt_malt = oppdatert_malt_liste

    # Redistribute other malts proportionally when pct was edited, keeping total fixed.
    # Widget keys are NOT updated here — that happens at the top of the next render
    # via _malt_pct_pending_sync to avoid StreamlitAPIException.
    if pct_edit_row is not None and total_malt_vekt > 0:
        old_other_total = total_malt_vekt - pct_edit_stored_kg
        remaining_kg = total_malt_vekt - pct_edit_new_kg

        if old_other_total <= 0:
            # Single malt or all others were 0 — cancel the change
            st.session_state.valgt_malt[pct_edit_row]["mengde"] = pct_edit_stored_kg
        else:
            for j, m in enumerate(st.session_state.valgt_malt):
                if j != pct_edit_row:
                    m["mengde"] = round(m["mengde"] * remaining_kg / old_other_total, 3)

    if needs_rerun:
        st.session_state["_malt_pct_pending_sync"] = True
        st.rerun()
