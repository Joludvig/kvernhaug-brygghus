import json
import streamlit as st
from modules.shopping_template import render_shopping_list_html
from modules.humle_lager import les_lager, beregn_status

_MALT_FALLBACK_KR_KG    = 35.0
_HUMLE_FALLBACK_KR_100G = 99.0
_GJAER_FALLBACK_KR      = 59.0


@st.cache_data
def _last_master_malt():
    try:
        with open("data/master_malt.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _butikk_nokkel(global_butikk):
    if global_butikk == "Ølbrygging.no":
        return "olbrygging", "pris_olbrygging"
    return "vestbrygg", "pris_vestbrygg"


def _bygg_handleliste(malt_database, humle_database, gjaer_database):
    butikk     = st.session_state.get("global_butikk", "Ølbrygging.no")
    bm_key, pris_flat = _butikk_nokkel(butikk)
    master_malt = _last_master_malt()

    malt_items, humle_items = [], []

    for m in st.session_state.get("valgt_malt", []):
        m_id   = m["id"]
        m_info = malt_database.get(m_id, {})
        navn   = m_info.get("display_name", m_id)
        mengde = m["mengde"]

        pris_kg    = m_info.get(pris_flat) or _MALT_FALLBACK_KR_KG
        er_estimat = not m_info.get(pris_flat)
        total      = round(mengde * pris_kg, 1)

        url = (master_malt
               .get(m_id, {})
               .get("butikk_match", {})
               .get(bm_key, {})
               .get("url"))

        malt_items.append({
            "navn": navn, "mengde": mengde,
            "pris_kg": pris_kg, "total": total,
            "er_estimat": er_estimat, "url": url,
        })

    for h in st.session_state.get("valgt_humle", []):
        h_id   = h["id"]
        h_info = humle_database.get(h_id, {})
        navn   = h_info.get("display_name", h_id)
        gram   = h["gram"]
        tid    = h["tid"]

        bm          = h_info.get("butikk_match", {}).get(bm_key, {})
        pris_pakke  = bm.get("pris") or _HUMLE_FALLBACK_KR_100G
        pakke_gram  = bm.get("pakke_gram") or 100.0
        er_estimat  = not bm.get("pris")
        total       = round(pris_pakke * gram / pakke_gram, 1)
        url         = bm.get("url")

        humle_items.append({
            "id": h_id,
            "navn": navn, "gram": gram, "tid": tid,
            "pris_pakke": pris_pakke, "pakke_gram": pakke_gram,
            "total": total, "er_estimat": er_estimat, "url": url,
        })

    gjaer_item = None
    gjaer_id   = st.session_state.get("valgt_gjaer_id")
    if gjaer_id:
        g_info = gjaer_database.get(gjaer_id, {})
        navn   = g_info.get("display_name", gjaer_id)
        bm     = g_info.get("butikk_match", {}).get(bm_key, {})
        pris   = bm.get("pris") or _GJAER_FALLBACK_KR
        er_estimat = not bm.get("pris")
        url    = bm.get("url")
        gjaer_item = {
            "navn": navn, "pris": pris,
            "er_estimat": er_estimat, "url": url,
        }

    return malt_items, humle_items, gjaer_item, butikk


def _bygg_humle_gruppert(humle_items, humle_database, butikk):
    """Grupperer humle_items per ID og beregner lagerstatus."""
    bm_key, _ = _butikk_nokkel(butikk)
    lager      = les_lager()
    valgt      = [{"id": h["id"], "gram": h["gram"]} for h in humle_items]
    status     = beregn_status(valgt, lager, humle_database, bm_key)

    # Behold første forekomst per ID for visningsinformasjon
    seen: dict = {}
    for h in humle_items:
        if h["id"] not in seen:
            seen[h["id"]] = h

    gruppert = []
    for h_id, s in status.items():
        h = seen[h_id]
        kjop_kr = 0.0
        if s["kjop"] > 0:
            kjop_kr = round(h["pris_pakke"] * s["kjop"] / h["pakke_gram"], 1)
        gruppert.append({
            "id": h_id,
            "navn": h["navn"],
            "url": h["url"],
            "er_estimat": h["er_estimat"],
            **s,
            "kjop_kr": kjop_kr,
        })

    return gruppert


def _generer_tekst(malt_items, humle_gruppert, gjaer_item, recipe_name, volum, butikk):
    linjer = [
        f"{recipe_name} — {volum:.0f} L",
        f"Butikk: {butikk}",
        "",
        "MALT",
    ]
    for m in malt_items:
        est = " (estimert)" if m["er_estimat"] else ""
        linjer.append(f"- {m['navn']}: {m['mengde']:.2f} kg — ca {m['total']:.0f} kr{est}")
        linjer.append(f"  {m['url']}" if m["url"] else "  (mangler butikklenke)")

    linjer += ["", "HUMLE"]
    for h in humle_gruppert:
        est       = " (estimert)" if h["er_estimat"] else ""
        hjemme_s  = f", hjemme: {int(h['hjemme'])}g" if h["hjemme"] > 0 else ""
        kjop_s    = f", kjøp: {int(h['kjop'])}g ({h['kjop_kr']:.0f} kr)" if h["kjop"] > 0 else ""
        rest_s    = f", rest: {int(h['rest'])}g" if h["rest"] > 0 else ""
        linjer.append(f"- {h['navn']}: {int(h['trenger'])}g{hjemme_s}{kjop_s}{rest_s}{est}")
        linjer.append(f"  {h['url']}" if h["url"] else "  (mangler butikklenke)")

    if gjaer_item:
        g   = gjaer_item
        est = " (estimert)" if g["er_estimat"] else ""
        linjer += ["", "GJÆR"]
        linjer.append(f"- {g['navn']}: 1 pakke — ca {g['pris']:.0f} kr{est}")
        linjer.append(f"  {g['url']}" if g["url"] else "  (mangler butikklenke)")

    total = (
        sum(m["total"] for m in malt_items)
        + sum(h["kjop_kr"] for h in humle_gruppert)
        + (gjaer_item["pris"] if gjaer_item else 0)
    )
    linjer += ["", f"TOTAL: ca {total:.0f} kr"]
    return "\n".join(linjer)


def _rad(navn, mengde_str, total, er_estimat, url):
    col_navn, col_pris = st.columns([3, 1])
    with col_navn:
        if url:
            st.markdown(f"[{navn}]({url}) — {mengde_str}")
        else:
            st.write(f"{navn} — {mengde_str}")
            st.caption("_(mangler butikklenke)_")
    with col_pris:
        est_tag = " _(est.)_" if er_estimat else ""
        st.write(f"ca **{total:.0f} kr**{est_tag}")


def _humle_rad(h: dict) -> None:
    """Rendrer én gruppert humle-rad med lagerstatus (5 kolonner)."""
    col_n, col_t, col_hj, col_k, col_r = st.columns([3, 1, 1, 1.5, 1])

    with col_n:
        if h["url"]:
            st.markdown(f"[{h['navn']}]({h['url']})")
        else:
            st.write(h["navn"])

    with col_t:
        st.write(f"{int(h['trenger'])}g")

    with col_hj:
        st.write(f"{int(h['hjemme'])}g" if h["hjemme"] > 0 else "—")

    with col_k:
        if h["kjop"] > 0:
            est = " _(est.)_" if h["er_estimat"] else ""
            st.markdown(f"**{int(h['kjop'])}g** / {h['kjop_kr']:.0f} kr{est}")
        else:
            st.write("✓")

    with col_r:
        st.write(f"{int(h['rest'])}g")


def render_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database):
    st.write("---")
    with st.expander("🛒 Handleliste"):
        malt_items, humle_items, gjaer_item, butikk = _bygg_handleliste(
            malt_database, humle_database, gjaer_database
        )
        humle_gruppert = _bygg_humle_gruppert(humle_items, humle_database, butikk)
        recipe_name    = ctx["name"]
        volum          = ctx["volum"]

        st.subheader(f"{recipe_name} — {volum:.0f} L")
        st.caption(f"Valgt butikk: **{butikk}**")

        total_sum = 0.0

        st.markdown("**🌾 Malt**")
        for m in malt_items:
            _rad(m["navn"], f"{m['mengde']:.2f} kg", m["total"], m["er_estimat"], m["url"])
            total_sum += m["total"]

        st.write("")
        st.markdown("**🌿 Humle**")

        # Kolonneoverskrifter
        hdr_n, hdr_t, hdr_hj, hdr_k, hdr_r = st.columns([3, 1, 1, 1.5, 1])
        with hdr_n:  st.caption("Humle")
        with hdr_t:  st.caption("Trenger")
        with hdr_hj: st.caption("Hjemme")
        with hdr_k:  st.caption("Kjøp")
        with hdr_r:  st.caption("Rest")

        for h in humle_gruppert:
            _humle_rad(h)
            total_sum += h["kjop_kr"]

        if gjaer_item:
            g = gjaer_item
            st.write("")
            st.markdown("**🧫 Gjær**")
            _rad(g["navn"], "1 pakke", g["pris"], g["er_estimat"], g["url"])
            total_sum += g["pris"]

        st.write("---")
        st.markdown(f"**TOTAL: ca {total_sum:.0f} kr**")
        st.caption("_Humle: kun kostnad for det som kjøpes (runder opp til hel pakke). Lagerbeholdning trekkes ikke._")

        st.write("")
        st.markdown("**📋 Kopier / last ned handleliste**")
        tekst = _generer_tekst(malt_items, humle_gruppert, gjaer_item, recipe_name, volum, butikk)
        st.code(tekst, language=None)
        base_fil = recipe_name.replace(" ", "_").replace("/", "-").lower()
        dl_col1, dl_col2 = st.columns(2)
        with dl_col1:
            st.download_button(
                label="📥 Last ned handleliste (.txt)",
                data=tekst,
                file_name=base_fil + "_handleliste.txt",
                mime="text/plain",
                use_container_width=True,
                key="handleliste_download_btn",
            )
        with dl_col2:
            html_ark = render_shopping_list_html(ctx, malt_items, humle_items, gjaer_item, butikk)
            st.download_button(
                label="📥 Last ned handleliste som HTML",
                data=html_ark,
                file_name=base_fil + "_handleliste.html",
                mime="text/html",
                use_container_width=True,
                key="handleliste_html_btn",
            )
