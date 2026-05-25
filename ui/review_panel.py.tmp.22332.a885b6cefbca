# ui/review_panel.py
import streamlit as st
import json
import os
import re

MASTER_PATHS = {
    "humle": "data/master_humle_v0_1.json",
    "malt":  "data/master_malt.json",
    "gjaer": "data/master_gjaer_v2.json",
}

UNMATCHED_PATHS = {
    "humle": "raw_data/unmatched_hops.json",
    "malt":  "raw_data/unmatched_malt.json",
    "gjaer": "raw_data/unmatched_gjaer.json",
}


def _les_json(sti, default):
    if os.path.exists(sti) and os.path.getsize(sti) > 0:
        try:
            with open(sti, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def _skriv_json(sti, data):
    with open(sti, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _lag_kanonisk_id(navn):
    s = navn.lower()
    s = s.replace("æ", "ae").replace("ø", "o").replace("å", "aa")
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _fjern_fra_unmatched(kat, index):
    sti = UNMATCHED_PATHS[kat]
    items = _les_json(sti, [])
    if 0 <= index < len(items):
        items.pop(index)
        _skriv_json(sti, items)


def _legg_til_alias_og_fjern(kat, master_id, item, index):
    master_sti = MASTER_PATHS[kat]
    master = _les_json(master_sti, {})
    if master_id not in master:
        return
    navn = item.get("navn", "")
    aliaser = master[master_id].setdefault("aliases", [])
    if navn and navn not in aliaser:
        aliaser.append(navn)
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    if butikk:
        bm = master[master_id].setdefault("butikk_match", {})
        if butikk not in bm:
            bm[butikk] = {"pris": None, "url": None}
        if pris:
            bm[butikk]["pris"] = pris
        if url:
            bm[butikk]["url"] = url
    _skriv_json(master_sti, master)
    _fjern_fra_unmatched(kat, index)


def _opprett_og_fjern(kat, ny_id, ny_entry, index):
    master_sti = MASTER_PATHS[kat]
    master = _les_json(master_sti, {})
    master[ny_id] = ny_entry
    _skriv_json(master_sti, master)
    _fjern_fra_unmatched(kat, index)


def _render_match_tab(kat, item, index, master):
    if not master:
        st.info("Master-fil ikke funnet.")
        return
    options = {v.get("display_name", k): k for k, v in master.items()}
    valgt = st.selectbox(
        "Match mot eksisterende entry:",
        sorted(options.keys()),
        key=f"sel_{kat}_{index}",
    )
    st.caption("Produktnavnet legges til som alias, og pris/URL oppdateres i master.")
    if st.button("Legg til alias + oppdater pris", key=f"match_btn_{kat}_{index}", type="primary"):
        _legg_til_alias_og_fjern(kat, options[valgt], item, index)
        st.toast(f"Matchet til «{valgt}»", icon="✅")
        st.rerun()


def _render_avvis_tab(kat, item, index):
    navn = item.get("navn", "Ukjent")
    st.caption(f"«{navn}» fjernes fra pending. Ingenting skrives til master.")
    if st.button("Bekreft avvis", key=f"avvis_{kat}_{index}"):
        _fjern_fra_unmatched(kat, index)
        st.toast(f"«{navn}» avvist", icon="🗑️")
        st.rerun()


def _render_ny_humle(item, index):
    navn = item.get("navn", "")
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    with st.form(key=f"ny_humle_{index}"):
        display_name = st.text_input("Navn", value=navn)
        aliases_tekst = st.text_area("Aliases (én per linje)", value=navn, height=80)
        alfa = st.number_input("Alfa-syre (%)", 0.0, 25.0, 5.0, 0.1)
        kategori = st.selectbox("Kategori", ["Aroma", "Bitterhet", "Dual"])
        smakstags_tekst = st.text_area("Smakstags (én per linje)", height=80)
        origin = st.text_input("Opprinnelse (land)", value="")
        st.caption(f"Auto-ID basert på navn: `{_lag_kanonisk_id(navn)}`")
        if st.form_submit_button("Opprett i master", type="primary"):
            ny_id = _lag_kanonisk_id(display_name)
            aliases = [a.strip() for a in aliases_tekst.splitlines() if a.strip()]
            smakstags = [s.strip() for s in smakstags_tekst.splitlines() if s.strip()]
            entry = {
                "display_name": display_name,
                "kategori": kategori,
                "alfa_typisk": alfa,
                "aliases": aliases,
                "smakstags": smakstags,
                "origin": origin,
                "butikk_match": {butikk: {"pris": pris, "url": url}} if butikk else {},
                "verified": True,
            }
            _opprett_og_fjern("humle", ny_id, entry, index)
            st.toast(f"«{display_name}» opprettet i master!", icon="✅")
            st.rerun()


def _render_ny_malt(item, index):
    navn = item.get("navn", "")
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    ebc_raw = float(item.get("ebc") or 4.0)
    with st.form(key=f"ny_malt_{index}"):
        display_name = st.text_input("Navn", value=navn)
        aliases_tekst = st.text_area("Aliases (én per linje)", value=navn, height=80)
        produsent = st.text_input("Produsent", value=item.get("produsent", ""))
        kategori = st.selectbox("Kategori", ["Basemalt", "Karamell", "Spesialmalt", "Spraymalt", "Røkt"])
        ebc = st.number_input("EBC", 0.0, 2000.0, ebc_raw, 1.0)
        smakstags_tekst = st.text_area("Smakstags (én per linje)", height=80)
        st.caption(f"Auto-ID basert på navn: `{_lag_kanonisk_id(navn)}`")
        if st.form_submit_button("Opprett i master", type="primary"):
            ny_id = _lag_kanonisk_id(display_name)
            aliases = [a.strip() for a in aliases_tekst.splitlines() if a.strip()]
            smakstags = [s.strip() for s in smakstags_tekst.splitlines() if s.strip()]
            entry = {
                "display_name": display_name,
                "produsent": produsent,
                "kategori": kategori,
                "ebc": ebc,
                "aliases": aliases,
                "smakstags": smakstags,
                "butikk_match": {butikk: {"pris": pris, "url": url}} if butikk else {},
                "verified": True,
            }
            _opprett_og_fjern("malt", ny_id, entry, index)
            st.toast(f"«{display_name}» opprettet i master!", icon="✅")
            st.rerun()


def _render_ny_gjaer(item, index):
    navn = item.get("navn", "")
    butikk = item.get("butikk", "")
    pris = item.get("pris", 0)
    url = item.get("url", "")
    with st.form(key=f"ny_gjaer_{index}"):
        display_name = st.text_input("Navn", value=navn)
        aliases_tekst = st.text_area("Aliases (én per linje)", value=navn, height=80)
        produsent = st.text_input("Produsent", value=item.get("produsent", ""))
        kategori = st.selectbox("Kategori", ["Tørrgjær", "Flytende gjær", "Kveik"])
        gjaertype = st.selectbox("Gjærtype", ["Ale", "Lager", "Wheat", "Belgian", "Kveik", "Annet"])
        attenuation = st.number_input("Attenuation", 0.60, 0.90, 0.75, 0.01, format="%.2f")
        smakstags_tekst = st.text_area("Smakstags (én per linje)", height=80)
        st.caption(f"Auto-ID basert på navn: `{_lag_kanonisk_id(navn)}`")
        if st.form_submit_button("Opprett i master", type="primary"):
            ny_id = _lag_kanonisk_id(display_name)
            aliases = [a.strip() for a in aliases_tekst.splitlines() if a.strip()]
            smakstags = [s.strip() for s in smakstags_tekst.splitlines() if s.strip()]
            entry = {
                "display_name": display_name,
                "produsent": produsent,
                "kategori": kategori,
                "gjaertype": gjaertype,
                "attenuation": attenuation,
                "aliases": aliases,
                "smakstags": smakstags,
                "butikk_match": {butikk: {"pris": pris, "url": url}} if butikk else {},
                "verified": True,
            }
            _opprett_og_fjern("gjaer", ny_id, entry, index)
            st.toast(f"«{display_name}» opprettet i master!", icon="✅")
            st.rerun()


_NY_FORM = {
    "humle": _render_ny_humle,
    "malt":  _render_ny_malt,
    "gjaer": _render_ny_gjaer,
}


def _render_kategori(kat, label, emoji):
    unmatched = _les_json(UNMATCHED_PATHS[kat], [])
    master = _les_json(MASTER_PATHS[kat], {})

    if not unmatched:
        st.success(f"✅ Ingen {label} pending review.")
        return

    st.warning(f"⚠️ {len(unmatched)} {label} matchet ikke master")

    for i, item in enumerate(unmatched):
        navn = item.get("navn", "Ukjent")
        butikk = item.get("butikk", "")
        pris = item.get("pris", 0)
        url = item.get("url", "")

        with st.expander(f"{emoji} **{navn}** — {butikk} — {pris} kr"):
            if url:
                st.markdown(f"[Åpne produktside]({url})")

            tab_match, tab_ny, tab_avvis = st.tabs(["🔗 Match eksisterende", "➕ Ny ingrediens", "🚫 Avvis"])

            with tab_match:
                _render_match_tab(kat, item, i, master)
            with tab_ny:
                _NY_FORM[kat](item, i)
            with tab_avvis:
                _render_avvis_tab(kat, item, i)


def render_review_panel():
    st.write("---")
    st.subheader("📋 Pending Review")

    tab_malt, tab_humle, tab_gjaer = st.tabs(["🌾 Malt", "🌿 Humle", "🧫 Gjær"])

    with tab_malt:
        _render_kategori("malt", "malter", "🌾")
    with tab_humle:
        _render_kategori("humle", "humler", "🌿")
    with tab_gjaer:
        _render_kategori("gjaer", "gjærsorter", "🧫")
