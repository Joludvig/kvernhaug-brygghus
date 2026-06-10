import json
import streamlit as st

_MALT_FALLBACK_KR_KG   = 35.0
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
    butikk  = st.session_state.get("global_butikk", "Ølbrygging.no")
    bm_key, pris_flat = _butikk_nokkel(butikk)
    master_malt = _last_master_malt()

    malt_items, humle_items = [], []

    for m in st.session_state.get("valgt_malt", []):
        m_id   = m["id"]
        m_info = malt_database.get(m_id, {})
        navn   = m_info.get("display_name", m_id)
        mengde = m["mengde"]

        pris_kg   = m_info.get(pris_flat) or _MALT_FALLBACK_KR_KG
        er_estimat = not (m_info.get(pris_flat))
        total = round(mengde * pris_kg, 1)

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

        bm         = h_info.get("butikk_match", {}).get(bm_key, {})
        pris_pakke  = bm.get("pris") or _HUMLE_FALLBACK_KR_100G
        pakke_gram  = bm.get("pakke_gram") or 100.0
        er_estimat  = not bm.get("pris")
        total       = round(pris_pakke * gram / pakke_gram, 1)
        url         = bm.get("url")

        humle_items.append({
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


def _generer_tekst(malt_items, humle_items, gjaer_item, recipe_name, volum, butikk):
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
    for h in humle_items:
        est = " (estimert)" if h["er_estimat"] else ""
        linjer.append(f"- {h['navn']}: {h['gram']}g ({h['tid']} min) — ca {h['total']:.0f} kr{est}")
        linjer.append(f"  {h['url']}" if h["url"] else "  (mangler butikklenke)")

    if gjaer_item:
        g = gjaer_item
        est = " (estimert)" if g["er_estimat"] else ""
        linjer += ["", "GJÆR"]
        linjer.append(f"- {g['navn']}: 1 pakke — ca {g['pris']:.0f} kr{est}")
        linjer.append(f"  {g['url']}" if g["url"] else "  (mangler butikklenke)")

    total = (
        sum(m["total"] for m in malt_items)
        + sum(h["total"] for h in humle_items)
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


def render_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database):
    st.write("---")
    with st.expander("🛒 Handleliste"):
        malt_items, humle_items, gjaer_item, butikk = _bygg_handleliste(
            malt_database, humle_database, gjaer_database
        )
        recipe_name = ctx["name"]
        volum       = ctx["volum"]

        st.subheader(f"{recipe_name} — {volum:.0f} L")
        st.caption(f"Valgt butikk: **{butikk}**")

        total_sum = 0.0

        st.markdown("**🌾 Malt**")
        for m in malt_items:
            _rad(m["navn"], f"{m['mengde']:.2f} kg", m["total"], m["er_estimat"], m["url"])
            total_sum += m["total"]

        st.write("")
        st.markdown("**🌿 Humle**")
        for h in humle_items:
            _rad(h["navn"], f"{h['gram']}g ({h['tid']} min)", h["total"], h["er_estimat"], h["url"])
            total_sum += h["total"]

        if gjaer_item:
            g = gjaer_item
            st.write("")
            st.markdown("**🧫 Gjær**")
            _rad(g["navn"], "1 pakke", g["pris"], g["er_estimat"], g["url"])
            total_sum += g["pris"]

        st.write("---")
        st.markdown(f"**TOTAL: ca {total_sum:.0f} kr**")

        st.write("")
        st.markdown("**📋 Kopier / last ned handleliste**")
        tekst = _generer_tekst(malt_items, humle_items, gjaer_item, recipe_name, volum, butikk)
        st.code(tekst, language=None)
        fil_navn = recipe_name.replace(" ", "_").replace("/", "-").lower() + "_handleliste.txt"
        st.download_button(
            label="📥 Last ned handleliste (.txt)",
            data=tekst,
            file_name=fil_navn,
            mime="text/plain",
            use_container_width=True,
            key="handleliste_download_btn",
        )
