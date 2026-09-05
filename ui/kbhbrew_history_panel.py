# ui/kbhbrew_history_panel.py
"""
V2-1A (issue #83) -- Brygghistorikk/Brew History-UI, koblet til den
allerede merged/testede PRI 3B1-motoren (modules/kbhbrew.py) og
lagringen (modules/kbhbrew_storage.py). Kilde er UTELUKKENDE
hent_alle_brews() (den NYE Core V1-butikken) -- rører ALDRI
recipes/_logs/ (legacy, uendret via modules/recipe_storage.py), samme
prinsipp som render_kbhbrew_export_panel() i ui/kbhbrew_panel.py.

Ett smalt, eksplisitt skriveinngangspunkt: "💾 Lagre målte verdier"
oppdaterer KUN de eksisterende V1 mutable feltene
(actuals.og/fg/volumeL/notes, brewedAt, status) på det VALGTE brygget,
via modules/kbhbrew_storage.py::oppdater_brew_lag() -- ALDRI en ny
skrivevei, ALDRI snapshotet. Rendring/rerendring/utvalg/typing alene
skriver INGENTING -- skrivingen kan kun nås inne i
`if st.button(...)`-blokken, samme garanti som
ui/kbhbrew_panel.py::render_kbhbrew_create_panel().

Widget-nøklene for selve actuals-skjemaet er BEVISST suffikset med
`brew_id` (samme mønster som ui/brewday_panel.py sin
`bd_bekreft_humletid_avvik::{signatur}`-nøkkel): uten dette ville
Streamlit sin egen widget-state for en ellers uendret nøkkel overlevd
et brukervalg av et ANNET brygg i selectboxen, og latt forrige brygges
utypede/upubliserte tekst late som om den hørte til det nye valget.

Tekstfeltene for OG/FG/volum starter TOMME hvis ingen tidligere målt
verdi finnes, og forhåndsutfylles ellers med den EKSAKTE, allerede
lagrede verdien (aldri en gjettet default som 1.050) -- nøyaktig samme
"fabriker aldri en måling"-prinsipp som modules/kbhbrew_ui.py sin
predicted-bygging. Selve tallparsingen/toleransen ved lagring skjer i
modules/kbhbrew.py::normaliser_actuals_lag() (kalt via
oppdater_brew_lag()) -- denne modulen sender kun de rå tekststrengene
videre, ingen egen validering/parsing dupliseres her.

Rene formaterings-/uttrekkshjelpere (planlagt sammendrag,
planlagt-vs-faktisk) er i modules/kbhbrew_history_ui.py, slik at de kan
enhetstestes uten en Streamlit-kontekst (se
tests/test_kbhbrew_history_ui_helpers.py).
"""
import streamlit as st

from config import DEMO_MODE
from modules.export_format import fmt_abv, fmt_fg, fmt_og, fmt_vol
from modules.kbhbrew_history_ui import bygg_planlagt_sammendrag, bygg_planlagt_vs_faktisk
from modules.kbhbrew_storage import hent_alle_brews, oppdater_brew_lag
from modules.kbhbrew_ui import sorter_brews_for_eksport
from ui.i18n import t

_STATUS_VALG = ("active", "done", "discarded")

# UI-presentasjonsterskel for når high-gravity-ABV-estimatet vises i
# tillegg til standardestimatet -- SAMME verdi/begrunnelse som
# ui/abv_calculator_panel.py sin _HOY_GRAVITET_TERSKEL_OG (issue #77,
# docs/development/CORE_CALCULATION_CONTRACT.md "Measured-gravity ABV")
# -- en presentasjonskonstant, ikke en del av selve ABV-formelen, derfor
# en bevisst egen kopi i stedet for en import fra en modul-privat
# konstant i et annet panel.
_HOY_GRAVITET_TERSKEL_OG = 1.070


def _fmt_eller_strek(verdi, formatter):
    return formatter(verdi) if verdi is not None else t("brew_history.ikke_malt")


def _render_planlagt_sammendrag(brew):
    sammendrag = bygg_planlagt_sammendrag(brew)
    st.markdown(f"**{sammendrag['navn']}**")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric(t("brew_history.planlagt_og"), _fmt_eller_strek(sammendrag["planlagt_og"], fmt_og))
    p2.metric(t("brew_history.planlagt_fg"), _fmt_eller_strek(sammendrag["planlagt_fg"], fmt_fg))
    p3.metric(t("brew_history.planlagt_abv"), _fmt_eller_strek(sammendrag["planlagt_abv"], fmt_abv))
    p4.metric(t("brew_history.planlagt_volum"), _fmt_eller_strek(sammendrag["planlagt_volum"], fmt_vol))

    status_nokkel = f"brew_history.status.{sammendrag['status']}"
    linje = f"{t('brew_history.opprettet')}: {sammendrag['opprettet_dato'] or '—'}"
    if sammendrag["brygget_dato"]:
        linje += f"  ·  {t('brew_history.brygget')}: {sammendrag['brygget_dato']}"
    linje += f"  ·  {t('brew_history.status_label')}: **{t(status_nokkel)}**"
    st.caption(linje)


def _render_actuals_skjema(brew_id, brew):
    """Renderer det editerbare actuals-/status-/dato-skjemaet. Returnerer
    det FERSKESTE kjente brew-objektet -- den nettopp lagrede versjonen
    fra oppdater_brew_lag() hvis "Lagre"-knappen ble trykket DENNE
    kjøringen, ellers uendret `brew` -- slik at planlagt-vs-faktisk-
    sammenligningen under aldri viser ett rerun gammel actuals-data rett
    etter et lagre-klikk."""
    st.markdown(f"**{t('brew_history.actuals_tittel')}**")
    actuals = brew.get("actuals") or {}

    a1, a2, a3 = st.columns(3)
    with a1:
        og_tekst = st.text_input(
            t("brew_history.actual_og_label"),
            value="" if actuals.get("og") is None else str(actuals["og"]),
            key=f"kbhbrew_hist_og::{brew_id}",
        )
    with a2:
        fg_tekst = st.text_input(
            t("brew_history.actual_fg_label"),
            value="" if actuals.get("fg") is None else str(actuals["fg"]),
            key=f"kbhbrew_hist_fg::{brew_id}",
        )
    with a3:
        volum_tekst = st.text_input(
            t("brew_history.actual_volum_label"),
            value="" if actuals.get("volumeL") is None else str(actuals["volumeL"]),
            key=f"kbhbrew_hist_volum::{brew_id}",
        )

    s1, s2 = st.columns(2)
    with s1:
        brygget_tekst = st.text_input(
            t("brew_history.brygget_dato_label"),
            value=brew.get("brewedAt") or "",
            key=f"kbhbrew_hist_brygget_dato::{brew_id}",
        )
    with s2:
        status_naa = brew.get("status") if brew.get("status") in _STATUS_VALG else "active"
        status_valgt = st.selectbox(
            t("brew_history.status_label"),
            options=list(_STATUS_VALG),
            index=_STATUS_VALG.index(status_naa),
            format_func=lambda s: t(f"brew_history.status.{s}"),
            key=f"kbhbrew_hist_status::{brew_id}",
        )

    notat_tekst = st.text_area(
        t("brew_history.notes_label"),
        value=actuals.get("notes") or "",
        key=f"kbhbrew_hist_notes::{brew_id}",
    )

    if st.button(t("brew_history.lagre_btn"), key=f"kbhbrew_hist_lagre_btn::{brew_id}"):
        oppdatert_brew = oppdater_brew_lag(
            brew_id,
            actuals={"og": og_tekst, "fg": fg_tekst, "volumeL": volum_tekst, "notes": notat_tekst},
            status=status_valgt,
            brewed_at=brygget_tekst.strip(),
        )
        st.success(t("brew_history.lagret_ok"))
        if oppdatert_brew is not None:
            return oppdatert_brew
    return brew


def _render_sammenligning(brew):
    sammenligning = bygg_planlagt_vs_faktisk(brew)
    if not sammenligning:
        return
    st.markdown(f"**{t('brew_history.sammenligning_tittel')}**")

    if "og" in sammenligning:
        c1, c2 = st.columns(2)
        c1.metric(f"{t('brew_history.rad_og')} — {t('brew_history.planlagt_og')}",
                  _fmt_eller_strek(sammenligning["og"]["planlagt"], fmt_og))
        c2.metric(f"{t('brew_history.rad_og')} — {t('brew_history.actual_og_label')}",
                  _fmt_eller_strek(sammenligning["og"]["faktisk"], fmt_og))

    if "fg" in sammenligning:
        c1, c2 = st.columns(2)
        c1.metric(f"{t('brew_history.rad_fg')} — {t('brew_history.planlagt_fg')}",
                  _fmt_eller_strek(sammenligning["fg"]["planlagt"], fmt_fg))
        c2.metric(f"{t('brew_history.rad_fg')} — {t('brew_history.actual_fg_label')}",
                  _fmt_eller_strek(sammenligning["fg"]["faktisk"], fmt_fg))

    if "volum" in sammenligning:
        c1, c2 = st.columns(2)
        c1.metric(f"{t('brew_history.rad_volum')} — {t('brew_history.planlagt_volum')}",
                  _fmt_eller_strek(sammenligning["volum"]["planlagt"], fmt_vol))
        c2.metric(f"{t('brew_history.rad_volum')} — {t('brew_history.actual_volum_label')}",
                  _fmt_eller_strek(sammenligning["volum"]["faktisk"], fmt_vol))

    if "abv" in sammenligning:
        rad = sammenligning["abv"]
        c1, c2 = st.columns(2)
        c1.metric(f"{t('brew_history.rad_abv')} — {t('brew_history.planlagt_abv')}",
                  _fmt_eller_strek(rad["planlagt"], fmt_abv))
        faktisk = rad["faktisk"]
        if faktisk is None:
            c2.metric(f"{t('brew_history.rad_abv')} — {t('abv_calc.resultat_label')}", t("brew_history.ikke_malt"))
        elif rad["faktisk_og"] is not None and rad["faktisk_og"] >= _HOY_GRAVITET_TERSKEL_OG:
            c2.metric(f"{t('brew_history.rad_abv')} — {t('abv_calc.standard_label')}", fmt_abv(faktisk["standard"]))
            st.metric(f"{t('brew_history.rad_abv')} — {t('abv_calc.high_gravity_label')}",
                      fmt_abv(faktisk["high_gravity"]))
            st.caption(t("abv_calc.high_gravity_forklaring"))
        else:
            c2.metric(f"{t('brew_history.rad_abv')} — {t('abv_calc.standard_label')}", fmt_abv(faktisk["standard"]))


def render_kbhbrew_history_panel():
    """Toppnivå-inngangspunkt kalt fra ui/brewday_panel.py. Skjules helt i
    DEMO_MODE (persistent skriving), samme mønster som
    render_kbhbrew_create_panel()/render_kbhbrew_import_panel()."""
    if DEMO_MODE:
        st.write("---")
        st.subheader(t("brew_history.tittel"))
        st.info(t("brew_history.demo_deaktivert"))
        return

    st.write("---")
    st.subheader(t("brew_history.tittel"))

    brews = hent_alle_brews()
    if not brews:
        st.caption(t("brew_history.tom"))
        return

    valg = sorter_brews_for_eksport(brews)
    etiketter = dict(valg)
    brew_id = st.selectbox(
        t("brew_history.velg_label"),
        options=[bid for bid, _ in valg],
        format_func=lambda bid: etiketter[bid],
        key="kbhbrew_historikk_valgt_id",
    )
    brew = brews.get(brew_id)
    if brew is None:
        return

    st.caption(t("brew_history.planlagt_tittel"))
    _render_planlagt_sammendrag(brew)
    st.write("")
    brew = _render_actuals_skjema(brew_id, brew)
    st.write("")
    _render_sammenligning(brew)
