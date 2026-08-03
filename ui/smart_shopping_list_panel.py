import streamlit as st
from config import DEMO_MODE
from modules import pantry
from modules.smart_shopping_list import beregn_handleliste, oppsummer_handleliste
from modules.malt_packaging import (
    MALTFORM_KNUST, MALTFORM_HEL, MALTFORM_BILLIGST, MALTFORM_INGEN_PREFERANSE,
    PRIORITET_BILLIGST, PRIORITET_MINST_OVERKJOP, PRIORITET_BALANSERT,
)
from ui import demo_state

_STATUS_VISNING = {
    "kjop": "🔴 Kjøp",
    "nok": "✅ Nok",
    "ukjent_match": "⚪ Kan ikke matches sikkert",
}
_TYPE_VISNING = {"malt": "🌾 Malt", "humle": "🌿 Humle", "gjaer": "🧫 Gjær"}
_TABELL_KOLONNER = [2.2, 1.1, 1.2, 1.1, 1.5, 1.1, 1.6]
_TABELL_OVERSKRIFTER = ["Ingrediens", "Trenger", "På lager", "Mangler", "Foreslått kjøp", "Rest", "Status"]

_MALTFORM_VISNING = {
    MALTFORM_INGEN_PREFERANSE: "Ingen preferanse",
    MALTFORM_KNUST: "Knust",
    MALTFORM_HEL: "Hel",
    MALTFORM_BILLIGST: "Billigste tilgjengelige",
}
_PRIORITET_VISNING = {
    PRIORITET_BALANSERT: "Balansert",
    PRIORITET_BILLIGST: "Billigst totalt",
    PRIORITET_MINST_OVERKJOP: "Minst overkjøp",
}


def _fmt_pakninger(antall_pakninger):
    delar = []
    for p in antall_pakninger:
        storrelse = p["pakningsstorrelse_gram"]
        enhet = f"{storrelse / 1000.0:g} kg" if storrelse >= 1000 else f"{storrelse:g} g"
        delar.append(f"{p['antall']} × {enhet}")
    return " + ".join(delar)


def _render_malt_pakningsforslag(forslag):
    if not forslag:
        return
    anbefalt = forslag["anbefalt_kombinasjon"]
    st.markdown(
        f"　　**Anbefalt:** {_fmt_pakninger(anbefalt['antall_pakninger'])} "
        f"({anbefalt['total_gram']:g} g, {anbefalt['malttype']}) — "
        f"rest {anbefalt['overkjop_gram']:g} g, ca. {anbefalt['total_pris']:.0f} kr"
    )
    for alt in forslag["alternative_kombinasjoner"]:
        st.caption(
            f"　　Alternativ: {_fmt_pakninger(alt['antall_pakninger'])} "
            f"({alt['total_gram']:g} g, {alt['malttype']}) — "
            f"rest {alt['overkjop_gram']:g} g, ca. {alt['total_pris']:.0f} kr"
        )
    if forslag.get("advarsel"):
        st.caption(f"　　⚠️ {forslag['advarsel']}")
    _render_eksakt_mal_instruks(forslag.get("kjopsresultat"))


def _render_eksakt_mal_instruks(kjopsresultat):
    """Vises KUN når kjøpsresultatet faktisk kommer fra eksakt-mål-modus
    (Steg F3) — gjenkjennes på at "bestilling" er et strukturert objekt
    med "eksakt_onsket_mengde_gram", ikke den vanlige, flate SKU-listen
    (se modules/malt_packaging.py::_kjopsresultat_eksakt_mal()). For alle
    andre kjøpsresultater (normalmodus, Ølbrygging, hel malt osv.) er
    "bestilling" fortsatt en vanlig liste, og denne funksjonen gjør ingenting."""
    if not kjopsresultat:
        return
    bestilling = kjopsresultat.get("bestilling")
    if not isinstance(bestilling, dict):
        return
    eksakt_gram = bestilling.get("eksakt_onsket_mengde_gram")
    if eksakt_gram is None:
        return
    pakninger = bestilling.get("pakninger") or []
    eksakt_kg = eksakt_gram / 1000.0
    st.markdown(
        f"　　🎯 **Eksakt mål (Vestbrygg, knust):** Legg {_fmt_pakninger(pakninger)} i handlekurven "
        f"og oppgi i meldingsfeltet: «Ønsket eksakt mengde: {eksakt_kg:g} kg»."
    )
    st.caption(
        "　　Vestbrygg opplyser at knust malt kan bestilles til eksakte mål via melding til "
        "salgsavdelingen — dette er ikke en garantert, automatisert tjeneste."
    )


def _render_liten_mangel_alternativ(alt):
    if not alt:
        return
    st.caption(f"　　💡 {alt['advarsel']}: {alt['tekst']}. Oppskriften endres ikke automatisk.")


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


def _status_tekst(rad):
    # Pantry sitt "knapp"-signal skal ikke drukne i en udifferensiert
    # "✅ Nok" — vises kun i denne mer presise formen når raden faktisk
    # rendres (dvs. når "Vis også det jeg har nok av" er aktivert, se
    # rendringsløkken under). Raden teller uansett IKKE med blant "må
    # kjøpes" og bidrar ikke til estimert kostnad.
    if rad["status"] == "nok" and rad.get("pantry_status") == "knapp":
        return "✅ Nok – knapp margin"
    return _STATUS_VISNING[rad["status"]]


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
        pantry_data = demo_state.hent_pantry() if DEMO_MODE else pantry.last_pantry()
    except pantry.PantryCorruptError as e:
        st.error(
            "📦 Lagerfilen (data/pantry.json) kunne ikke leses fordi innholdet er ugyldig JSON — "
            f"Smart Handleliste kan derfor ikke beregnes. Detaljer: {e}"
        )
        return

    butikk = st.session_state.get("global_butikk", "Ølbrygging.no")

    with st.expander("⚙️ Malt-innstillinger (pakningsforslag)", expanded=False):
        maltform_valg = st.selectbox(
            "Maltform", options=list(_MALTFORM_VISNING), format_func=lambda k: _MALTFORM_VISNING[k],
            key="smart_handleliste_maltform",
            help="Styrer kun hvilken maltype (hel/knust) pakningsforslag hentes fra. "
                 "Ett forslag blander aldri hel og knust malt.",
        )
        malt_prioritet_valg = st.selectbox(
            "Prioritet for pakningsforslag", options=list(_PRIORITET_VISNING), format_func=lambda k: _PRIORITET_VISNING[k],
            key="smart_handleliste_malt_prioritet",
        )

        eksakt_mal_knust_valg = False
        if maltform_valg == MALTFORM_KNUST:
            eksakt_mal_knust_valg = st.checkbox(
                "Vestbrygg: bestill knust malt til eksakt mål",
                key="smart_handleliste_eksakt_mal_knust",
                help=(
                    "Kun for Vestbrygg og knust malt. Du betaler fortsatt for avrundede "
                    "1 kg-/100 g-SKU-er, men oppgir ønsket eksakt mengde i meldingsfeltet til "
                    "salgsavdelingen ved bestilling. Forventet rest i Pantry regnes da ut fra "
                    "det eksakte behovet i stedet for SKU-summen."
                ),
            )
            if eksakt_mal_knust_valg:
                st.caption(
                    "Vestbrygg opplyser at knust malt kan bestilles til eksakte mål via "
                    "melding til salgsavdelingen — dette er ikke en garantert, automatisert "
                    "tjeneste, og gjelder kun når du faktisk handler hos Vestbrygg."
                )

    handleliste = beregn_handleliste(
        recipe, pantry_data, malt_database, humle_database, gjaer_database, butikk=butikk,
        maltform=maltform_valg, malt_prioritet=malt_prioritet_valg,
        eksakt_mal_knust=eksakt_mal_knust_valg,
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
            cols[6].write(_status_tekst(rad))
            # Advisory vises alltid for "kjop"-rader (f.eks. Steg F3 sitt
            # "ingen kjøpbar variant akkurat nå" -- en kritisk pris-/
            # tilgjengelighetsadvarsel skal aldri gjemmes bak "vis alt", som
            # kun er ment for å avsløre den mindre kritiske "knapp margin"-
            # advisoryen på "nok"-rader).
            if rad.get("advisory") and (vis_alt or rad["status"] == "kjop"):
                st.caption(f"　　💡 {rad['advisory']}")
            if ingredient_type == "malt" and rad["status"] == "kjop":
                _render_malt_pakningsforslag(rad.get("malt_pakningsforslag"))
            if ingredient_type == "humle" and rad["status"] == "kjop":
                _render_liten_mangel_alternativ(rad.get("liten_mangel_alternativ"))

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
