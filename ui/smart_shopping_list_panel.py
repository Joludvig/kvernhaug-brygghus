import streamlit as st
from modules import pantry
from modules.smart_shopping_list import beregn_handleliste, oppsummer_handleliste

_STATUS_VISNING = {
    "kjop": "🔴 Kjøp",
    "nok": "✅ Nok",
    "ukjent_match": "⚪ Kan ikke matches sikkert",
}
_TYPE_VISNING = {"malt": "🌾 Malt", "humle": "🌿 Humle", "gjaer": "🧫 Gjær"}
_TABELL_KOLONNER = [2.2, 1.1, 1.2, 1.1, 1.5, 1.1, 1.6]
_TABELL_OVERSKRIFTER = ["Ingrediens", "Trenger", "På lager", "Mangler", "Foreslått kjøp", "Rest", "Status"]


def _fmt(verdi, enhet):
    if verdi is None:
        return "–"
    if enhet == "pakke":
        return f"{verdi:g} pakke(r)"
    return f"{verdi:g} {enhet}"


def _fmt_kjop(rad):
    if rad["status"] != "kjop" or not rad["suggested_purchase_quantity"]:
        return "–"
    merke = "" if rad.get("package_size_known") else " _(eksakt, ukjent pakning)_"
    return f"{rad['suggested_purchase_quantity']:g} {rad['purchase_unit']}{merke}"


def render_smart_shopping_list_panel(ctx, malt_database, humle_database, gjaer_database):
    st.write("---")
    st.subheader("🧠 Smart Handleliste")
    st.caption(
        "Bruker 📦 Lager (Pantry) som eneste sannhetskilde for lagerbeholdning. "
        "Det gamle humlelageret nedenfor påvirker IKKE denne listen."
    )

    recipe = (ctx or {}).get("recipe") if ctx else None
    if not recipe:
        st.caption("Ingen aktiv oppskrift å beregne handleliste for.")
        return

    try:
        pantry_data = pantry.last_pantry()
    except pantry.PantryCorruptError as e:
        st.error(
            "📦 Lagerfilen (data/pantry.json) kunne ikke leses fordi innholdet er ugyldig JSON — "
            f"Smart Handleliste kan derfor ikke beregnes. Detaljer: {e}"
        )
        return

    butikk = st.session_state.get("global_butikk", "Ølbrygging.no")
    handleliste = beregn_handleliste(
        recipe, pantry_data, malt_database, humle_database, gjaer_database, butikk=butikk,
    )
    sammendrag = oppsummer_handleliste(handleliste)

    st.markdown(f"**Aktiv oppskrift:** {recipe.get('name', '(uten navn)')} — {(ctx.get('volum') or 0):.0f} L")

    vis_alt = st.checkbox("Vis også det jeg har nok av", key="smart_handleliste_vis_alt")

    noe_vist = False
    for ingredient_type in ("malt", "humle", "gjaer"):
        rader = [r for r in handleliste if r["ingredient_type"] == ingredient_type]
        if not vis_alt:
            rader = [r for r in rader if r["status"] != "nok"]
        if not rader:
            continue

        noe_vist = True
        st.markdown(f"**{_TYPE_VISNING[ingredient_type]}**")
        hdr_cols = st.columns(_TABELL_KOLONNER)
        for col, tekst in zip(hdr_cols, _TABELL_OVERSKRIFTER):
            col.caption(tekst)

        for rad in rader:
            cols = st.columns(_TABELL_KOLONNER)
            cols[0].write(rad["name"])
            cols[1].write(_fmt(rad["required_base"], rad["base_unit"]))
            cols[2].write(_fmt(rad["available_base"], rad["base_unit"]))
            cols[3].write(_fmt(rad["missing_base"], rad["base_unit"]))
            cols[4].write(_fmt_kjop(rad))
            cols[5].write(_fmt(rad["expected_remainder_base"], rad["base_unit"]))
            cols[6].write(_STATUS_VISNING[rad["status"]])

    if not noe_vist:
        st.caption(
            "Ingen ingredienser å vise — alt dekkes av lageret."
            if not vis_alt else "Ingen ingredienser i oppskriften ennå."
        )

    st.write("")
    c1, c2, c3 = st.columns(3)
    c1.metric("Må kjøpes", sammendrag["antall_ma_kjopes"])
    c2.metric("Usikre matcher", sammendrag["antall_usikre_matcher"])
    kost_tekst = f"{sammendrag['estimert_totalkostnad']:.0f} kr"
    if sammendrag["totalkostnad_er_estimat"]:
        kost_tekst += " (estimert)"
    c3.metric("Estimert kostnad", kost_tekst)
