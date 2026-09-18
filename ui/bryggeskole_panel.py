# ui/bryggeskole_panel.py
"""
Kvernhaug Bryggeskole -- første integrerte lærings-UI (issue #327,
BRYGGESKOLE V2-3C). Renderes som sin egen topplinje-fane i app.py, ikke
gjemt under Verktøy.

Ett Bryggeskole -> to visuelle miljøer (Hjemmebrygger / Bryggeri) -> delt
verifisert kunnskap + delt mastery. De to miljøene er bevisst kun
navigasjon/presentasjon: begge går inn i NØYAKTIG samme
gjæringstemperatur-pilot og oppdaterer NØYAKTIG samme mastery-tilstand --
ingen nye kursfakta/påstander oppstår her.

Gjenbruker den eksisterende læringsmotoren uendret, per issue #327 sitt
eksplisitte krav ("Reuse existing learning engine as-is"):
    bryggeskole.pilot_fermentation.{read_pilot_file, render_chunk,
        render_question, evaluate_answer}
    bryggeskole.mastery.{apply_answer, mastery_label}
    bryggeskole.mastery_store.{read_mastery_state, write_mastery_state,
        neutral_state_document}
Ingen av disse fire modulene er endret for denne skiven.

Kun gjæringstemperatur-modulen er aktiv i denne skiven -- alle andre
prosess-stadier vises kun til orientering (aldri klikkbare/leksjoner),
per issue #327 sitt "no new course claims / no second module".

DEMO_MODE-grensen (avgjørelsen issue #327 selv ber om å bli dokumentert):
en PANEL-NIVÅ vakt her i stedet for en ny modules/bryggeskole_state.py-
adapter. ui/demo_state.py er dokumentert som avgrenset til fire
eksisterende domener (pantry, vannkjemi, utstyr, gammelt humlelager) --
å utvide DEN modulen for et femte, urelatert domene ville bare utvidet
dens kontrakt uten noen delt fordel, siden
bryggeskole/mastery_store.py allerede er sin egen rene, allerede isolerte
lese/skrive-grense. Denne panelet speiler i stedet SAMME mønster
(session-scoped overlay i DEMO_MODE, ekte fillesing/-skriving utenfor)
lokalt, nøyaktig som ui/equipment_panel.py sine egne
_hent_equipment()/_lagre_equipment() gjør for sitt domene.
"""
import datetime

import streamlit as st

from config import DEMO_MODE
from bryggeskole.mastery import apply_answer, mastery_label
from bryggeskole.mastery_store import (
    neutral_state_document,
    read_mastery_state,
    write_mastery_state,
)
from bryggeskole.pilot_fermentation import (
    PilotContentError,
    evaluate_answer,
    read_pilot_file,
    render_chunk,
    render_question,
)
from ui.i18n import gjeldende_sprak, t

_ENV_HJEMMEBRYGGER = "hjemmebrygger"
_ENV_BRYGGERI = "bryggeri"

# Seks representative prosess-stadier (malt/maling -> mesk -> koking ->
# kjøling -> gjæring -> pakking) i to miljø-varianter, per issue #327 sitt
# krav om "malt/milling → mash → boil → cooling → fermentation →
# packaging". Bevisst lokale bilingual-dicts (samme mønster som
# bryggeskole/pilot_fermentation.py sitt eget "no"/"en"-format) i stedet
# for modules/i18n.py-nøkler, for å holde i18n-tillegget der til et
# minimum -- disse er navigasjons-/presentasjonstekst, ikke lærings-
# innhold, og teksten er identisk begge steder uansett miljøvalg.
_PROSESS_STADIER = {
    _ENV_HJEMMEBRYGGER: [
        {"no": "Maling av malt", "en": "Milling the malt"},
        {"no": "Mesking (kjele/BIAB)", "en": "Mashing (kettle/BIAB)"},
        {"no": "Koking", "en": "Boil"},
        {"no": "Kjøling", "en": "Cooling"},
        {"no": "Gjæring (bøtte/FermZilla)", "en": "Fermentation (bucket/FermZilla)"},
        {"no": "Tapping/flasking", "en": "Kegging/bottling"},
    ],
    _ENV_BRYGGERI: [
        {"no": "Mølle", "en": "Mill"},
        {"no": "Mesk/lauter", "en": "Mash/lauter"},
        {"no": "Kokekar/whirlpool", "en": "Kettle/whirlpool"},
        {"no": "Varmeveksler", "en": "Heat exchanger"},
        {"no": "Konisk gjæringstank", "en": "Conical fermenter"},
        {"no": "Pakking/CIP", "en": "Packaging/CIP"},
    ],
}

# Samme indeks i begge miljøer -- gjæring er det eneste aktive steget
# denne omgangen; resten er ren orientering.
_GJARINGSSTADIUM_INDEKS = 4

# Menneskelesbare visningsnavn for pilotens konsept-id-er -- aldri de
# rå id-strengene selv i oppsummeringen (issue #327: læreren skal aldri
# se "fermentation.temperature" som tekst).
_KONSEPT_LABELS = {
    "fermentation.temperature": {"no": "Gjæringstemperatur", "en": "Fermentation temperature"},
    "fermentation.yeast_activity": {"no": "Gjæraktivitet", "en": "Yeast activity"},
    "fermentation.flavor": {"no": "Smak og aroma", "en": "Flavor and aroma"},
    "fermentation.yeast_strain": {"no": "Gjærstamme-avhengighet", "en": "Yeast strain dependence"},
}

_DEMO_TILSTAND_NOKKEL = "_demo_bryggeskole_mastery_tilstand"


def _konsept_label(konsept_id, sprak):
    return _KONSEPT_LABELS.get(konsept_id, {}).get(sprak, konsept_id)


def _les_tilstand():
    if DEMO_MODE:
        if _DEMO_TILSTAND_NOKKEL not in st.session_state:
            st.session_state[_DEMO_TILSTAND_NOKKEL] = neutral_state_document()
        return st.session_state[_DEMO_TILSTAND_NOKKEL]
    return read_mastery_state()


def _skriv_tilstand(dokument):
    if DEMO_MODE:
        st.session_state[_DEMO_TILSTAND_NOKKEL] = dokument
        return
    write_mastery_state(dokument)


def _utc_now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _init_state():
    st.session_state.setdefault("bs_miljo", None)
    st.session_state.setdefault("bs_modul_startet", False)
    st.session_state.setdefault("bs_fase", "leksjon")
    st.session_state.setdefault("bs_sporsmal_idx", 0)
    st.session_state.setdefault("bs_runde", 0)
    st.session_state.setdefault("bs_siste_feedback", None)


def _velg_miljo(miljo):
    st.session_state["bs_miljo"] = miljo
    st.session_state["bs_modul_startet"] = False
    st.session_state["bs_fase"] = "leksjon"
    st.session_state["bs_sporsmal_idx"] = 0
    st.session_state["bs_siste_feedback"] = None


def _bytt_miljo():
    st.session_state["bs_miljo"] = None
    st.session_state["bs_modul_startet"] = False
    st.session_state["bs_fase"] = "leksjon"
    st.session_state["bs_sporsmal_idx"] = 0
    st.session_state["bs_siste_feedback"] = None


def _start_modul():
    st.session_state["bs_modul_startet"] = True
    st.session_state["bs_fase"] = "leksjon"


def _start_sporsmal_runde():
    """Starter (eller re-starter, ved «Prøv igjen») spørsmålsrunden fra
    første spørsmål. Øker ALLTID bs_runde, slik at hvert
    spørsmål-widget-key blir garantert unikt for denne runden -- uten
    dette ville et gjenbrukt key ha fått Streamlit til å vise en gammel,
    lagret radioverdi fra en tidligere runde. `apply_answer()`s egen
    `first_attempt`-logikk leser fortsatt den PERSISTERTE mastery-
    tilstanden uendret -- «Prøv igjen» resetter aldri selve
    mastery-tilstanden, kun denne UI-runden."""
    st.session_state["bs_runde"] += 1
    st.session_state["bs_fase"] = "sporsmal"
    st.session_state["bs_sporsmal_idx"] = 0
    st.session_state["bs_siste_feedback"] = None


def _sjekk_svar(sporsmal, sprak, widget_key, runde):
    valgt_id = st.session_state.get(widget_key)
    resultat = evaluate_answer(sporsmal, valgt_id, sprak)
    tilstand = _les_tilstand()
    nytt_tilstand = apply_answer(tilstand, sporsmal, resultat["correct"], now=_utc_now_iso())
    _skriv_tilstand(nytt_tilstand)
    st.session_state["bs_siste_feedback"] = {
        "question_id": resultat["question_id"],
        "runde": runde,
        "correct": resultat["correct"],
        "feedback": resultat["feedback"],
    }


def _neste_sporsmal(totalt):
    ny_idx = st.session_state["bs_sporsmal_idx"] + 1
    st.session_state["bs_sporsmal_idx"] = ny_idx
    st.session_state["bs_siste_feedback"] = None
    st.session_state["bs_fase"] = "oppsummering" if ny_idx >= totalt else "sporsmal"


def _render_miljovalg():
    st.subheader(t("bryggeskole.velg_miljo_heading"))
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown(f"### {t('bryggeskole.miljo.hjemmebrygger')}")
            st.caption(t("bryggeskole.miljo.hjemmebrygger_beskrivelse"))
            st.button(
                t("bryggeskole.miljo.velg_knapp"), key="bs_velg_hjemmebrygger_btn",
                width="stretch", on_click=_velg_miljo, args=(_ENV_HJEMMEBRYGGER,),
            )
    with col2:
        with st.container(border=True):
            st.markdown(f"### {t('bryggeskole.miljo.bryggeri')}")
            st.caption(t("bryggeskole.miljo.bryggeri_beskrivelse"))
            st.button(
                t("bryggeskole.miljo.velg_knapp"), key="bs_velg_bryggeri_btn",
                width="stretch", on_click=_velg_miljo, args=(_ENV_BRYGGERI,),
            )


def _render_prosessoversikt(miljo, sprak):
    if st.session_state["bs_modul_startet"]:
        # Kompakt visning mens leksjon/spørsmål/oppsummering pågår -- fullt
        # skjema er kun nyttig FØR modulen starter (jf. designprinsippet
        # "clear focus", ikke en tekstvegg samtidig med spørsmålet).
        st.caption(t("bryggeskole.prosess.kompakt", miljo=t(f"bryggeskole.miljo.{miljo}")))
        return

    st.subheader(t(f"bryggeskole.miljo.{miljo}"))
    stadier = _PROSESS_STADIER[miljo]
    cols = st.columns(len(stadier))
    for i, (col, stadium) in enumerate(zip(cols, stadier)):
        with col, st.container(border=True):
            st.markdown(f"**{stadium[sprak]}**")
            if i == _GJARINGSSTADIUM_INDEKS:
                st.caption(t("bryggeskole.prosess.aktiv_badge"))
            else:
                st.caption(t("bryggeskole.prosess.kommer_badge"))

    st.button(
        t("bryggeskole.start_leksjon"), key="bs_start_modul_btn",
        width="stretch", on_click=_start_modul,
    )


def _render_leksjon(pilot, sprak):
    st.write("---")
    st.subheader(t("bryggeskole.leksjon.heading"))
    for chunk in pilot["chunks"]:
        st.markdown(render_chunk(chunk, sprak)["text"])
    st.button(
        t("bryggeskole.leksjon.start_sporsmal"), key="bs_start_sporsmal_btn",
        width="stretch", on_click=_start_sporsmal_runde,
    )


def _render_sporsmal(pilot, sprak):
    st.write("---")
    sporsmal_liste = pilot["questions"]
    totalt = len(sporsmal_liste)
    idx = st.session_state["bs_sporsmal_idx"]
    if idx >= totalt:
        # Forsvarslinje -- normal flyt går alltid via _neste_sporsmal(),
        # som selv setter fasen til "oppsummering" når siste spørsmål er
        # besvart, så dette skal aldri inntreffe i praksis.
        st.session_state["bs_fase"] = "oppsummering"
        return

    sporsmal = sporsmal_liste[idx]
    rendret = render_question(sporsmal, sprak)
    runde = st.session_state["bs_runde"]
    widget_key = f"bs_valg_r{runde}_q{idx}"

    siste = st.session_state["bs_siste_feedback"]
    besvart = bool(
        siste
        and siste["question_id"] == sporsmal["id"]
        and siste["runde"] == runde
    )

    st.caption(t("bryggeskole.sporsmal.fremdrift", n=idx + 1, totalt=totalt))
    st.markdown(f"**{rendret['prompt']}**")

    alternativer = rendret["options"]
    st.radio(
        t("bryggeskole.sporsmal.velg_svar"),
        options=[o["id"] for o in alternativer],
        format_func=lambda oid: next(o["text"] for o in alternativer if o["id"] == oid),
        key=widget_key,
        label_visibility="collapsed",
        disabled=besvart,
    )

    if not besvart:
        st.button(
            t("bryggeskole.sporsmal.svar_knapp"), key=f"bs_svar_btn_r{runde}_q{idx}",
            width="stretch", on_click=_sjekk_svar, args=(sporsmal, sprak, widget_key, runde),
        )
    else:
        (st.success if siste["correct"] else st.error)(siste["feedback"])
        st.button(
            t("bryggeskole.sporsmal.fortsett"), key=f"bs_fortsett_btn_r{runde}_q{idx}",
            width="stretch", on_click=_neste_sporsmal, args=(totalt,),
        )


def _render_oppsummering(pilot, sprak):
    st.write("---")
    st.subheader(t("bryggeskole.oppsummering.heading"))
    tilstand = _les_tilstand()
    konsepter = sorted({konsept for sporsmal in pilot["questions"] for konsept in sporsmal["concepts"]})
    for konsept_id in konsepter:
        konsept_tilstand = tilstand["concepts"].get(konsept_id)
        if konsept_tilstand is None:
            continue
        st.markdown(f"- **{_konsept_label(konsept_id, sprak)}:** {mastery_label(konsept_tilstand, sprak)}")

    st.button(
        t("bryggeskole.oppsummering.prov_igjen"), key="bs_prov_igjen_btn",
        width="stretch", on_click=_start_sporsmal_runde,
    )


def render_bryggeskole_panel():
    _init_state()
    sprak = gjeldende_sprak()

    st.header(t("bryggeskole.heading"))
    st.caption(t("bryggeskole.tagline"))

    miljo = st.session_state["bs_miljo"]
    if miljo is None:
        _render_miljovalg()
        return

    st.button(t("bryggeskole.bytt_miljo"), key="bs_bytt_miljo_btn", on_click=_bytt_miljo)
    _render_prosessoversikt(miljo, sprak)

    if not st.session_state["bs_modul_startet"]:
        return

    try:
        pilot = read_pilot_file()
    except PilotContentError:
        st.error(t("bryggeskole.feil.innhold_ugyldig"))
        return

    fase = st.session_state["bs_fase"]
    if fase == "leksjon":
        _render_leksjon(pilot, sprak)
    elif fase == "sporsmal":
        _render_sporsmal(pilot, sprak)
    else:
        _render_oppsummering(pilot, sprak)
