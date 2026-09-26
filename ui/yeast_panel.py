import streamlit as st

from bryggeskole import pilot_fermentation as _pilot_gjaring
from ui.i18n import gjeldende_sprak, t

# De tre eksisterende, verifiserte Gjæring-læringsbolkene denne Learn ->
# Plan-broen viser (V2.2 G3K, issue #384) -- nøyaktig disse tre, i denne
# rekkefølgen, per docs/development/
# v22_g3j_fermentation_learn_plan_contract.md §3/§4. Ingen ny
# undervisningstekst forfattes her; broen gjenbruker
# bryggeskole.pilot_fermentation sin egen read_pilot_file()/render_chunk()
# uendret, akkurat som ui/process_panel.py allerede gjør for Mesking.
_LAER_BRO_CHUNK_IDER = ("CHUNK-FERM-A", "CHUNK-FERM-B", "CHUNK-FERM-C")


def _render_laer_bro(sprak):
    """Kontekstuell Learn -> Plan-bro (V2.2 G3K, issue #384): en
    kollapset expander rett under smak/utgjæring-captionen som viser
    CHUNK-FERM-A/B/C fra den eksisterende, verifiserte
    Gjæring-piloten -- read-only, ingen mastery-kall
    (evaluate_answer/apply_answer), ingen ny lagringstilstand. Ugyldig
    pilotinnhold (PilotContentError) skal aldri krasje Oppskrift-fanen,
    samme mønster som ui/process_panel.py/ui/bryggeskole_panel.py."""
    with st.expander(t("gjaering.laer_bro.tittel"), expanded=False):
        try:
            pilot = _pilot_gjaring.read_pilot_file()
        except _pilot_gjaring.PilotContentError:
            st.error(t("bryggeskole.feil.innhold_ugyldig"))
            return
        chunker = {c["id"]: c for c in pilot["chunks"]}
        for chunk_id in _LAER_BRO_CHUNK_IDER:
            st.markdown(_pilot_gjaring.render_chunk(chunker[chunk_id], sprak)["text"])
        st.caption(t("gjaering.laer_bro.footer"))


def render_yeast_panel(gjaer_database):
    # issue #400, rotårsak A -- samme avgrensede fiks som
    # ui/hop_panel.py sin header/knapp: disse to var ALDRI koblet til
    # i18n-laget, mens _render_laer_bro() lenger ned allerede var det.
    st.header(t("gjaering.gjaer_panel.header"))
    with st.expander("ℹ️ Gjærstarter og gjærhelse (kort intro)"):
        st.markdown(
            "- **Gjærstarter** — en liten mengde steril vørter du tilsetter gjær i på "
            "forhånd, slik at den rekker å formere seg før bryggedagen. Særlig aktuelt "
            "for flytende gjær, lav cellemengde eller en sterk vørter. Ikke en universell "
            "nødvendighet — tørrgjær håndteres ofte annerledes, følg produsentens råd.\n"
            "- **Gjærmengde og temperatur** — for lite gjær eller feil temperatur kan gi "
            "en treg/stresset gjæring og uønskede smaker. Produsentens temperaturområde "
            "er et utgangspunkt, ikke ett fasittall som passer alle øl."
        )
    gjaer_id_kart, gjaer_meny_valg = {}, []
    for g_id, info in gjaer_database.items():
        if info:
            visnings_navn = f"{info.get('display_name', 'Ukjent')} ({info.get('produsent', 'Ukjent')})"
            gjaer_id_kart[visnings_navn] = g_id
            gjaer_meny_valg.append(visnings_navn)

    # SKUDDSIKKER FALLBACK: Hvis gjærdatabasen er tom, legger vi inn et standard testvalg
    # slik at selectboxen ikke blir tom (noe som forårsaker None-krasj)
    if not gjaer_meny_valg:
        gjaer_meny_valg = ["SafAle US-05 (Fermentis)"]
        gjaer_id_kart["SafAle US-05 (Fermentis)"] = "safale_us_05"

    gjeldende_g_visning = "SafAle US-05 (Fermentis)"
    for visning, g_id in gjaer_id_kart.items():
        if g_id == st.session_state.valgt_gjaer_id:
            gjeldende_g_visning = visning
            break
            
    g_indeks = gjaer_meny_valg.index(gjeldende_g_visning) if gjeldende_g_visning in gjaer_meny_valg else 0
    valgt_gjaer_visning = st.selectbox(t("gjaering.gjaer_panel.velg_label"), gjaer_meny_valg, index=g_indeks)

    # FIKSET: Sjekker at vi faktisk har en gyldig verdi i kartet før vi lagrer til session state
    if valgt_gjaer_visning and valgt_gjaer_visning in gjaer_id_kart:
        st.session_state.valgt_gjaer_id = gjaer_id_kart[valgt_gjaer_visning]
    else:
        st.session_state.valgt_gjaer_id = "safale_us_05"

    g_id = st.session_state.valgt_gjaer_id
    if g_id in gjaer_database:
        g_info = gjaer_database[g_id]
        smakstags = g_info.get("smakstags") or []
        att_pst = int(round(g_info.get("attenuation", 0.75) * 100))
        att_str = f"{att_pst}% gjæring"
        if smakstags:
            st.caption(f"🧪 *Smak:* {', '.join(smakstags)} · {att_str}")
        else:
            st.caption(f"🧪 {att_str}")

    sprak = gjeldende_sprak()
    _render_laer_bro(sprak)

    # Planlagt gjæringstemperatur (V2.2 G3K, issue #384) -- widget-bundet
    # DIREKTE til st.session_state["gjaering_temp_maal_c"] (samme mønster
    # som "batch_volum_input"/"gjeldende_navn" i ui/recipe_card.py: verdien
    # settes ALLTID i session_state FØR denne widgeten instansieres --
    # se app.py/ui/sidebar.py -- så INGEN eksplisitt `value=` gis her).
    # Bevisst INGEN min_value/max_value: en bryggefaglig grenseverdi ville
    # kunne leses som Kvernhaug-godkjent gjærveiledning, som §5/§8 i
    # kontrakten eksplisitt forbyr. Unset (None) rendres da som et tomt
    # felt, aldri et forhåndsutfylt tall.
    st.number_input(
        t("gjaering.temp_maal.label"),
        step=0.5,
        key="gjaering_temp_maal_c",
        help=t("gjaering.temp_maal.hjelp"),
    )
