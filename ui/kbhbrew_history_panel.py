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
predicted-bygging.

Chief review-fiks (PR #84 runde 2, issue #83): OG/FG/volum-teksten
valideres nå STRENGT her (modules/kbhbrew_history_ui.py::
parse_actual_tallfelt()) FØR oppdater_brew_lag() i det hele tatt
kalles. modules/kbhbrew.py::normaliser_actuals_lag() sin
JS-parseFloat-prefiks-toleranse (Core V1 Section 5.16) er riktig for
import/legacy-data, men FEIL for direkte manuell tasting her: uten
denne forhåndsvalideringen ville "1,055" stille blitt lagret som 1.0,
"1.055abc" ville blitt lagret som 1.055 med etterslepet stille
forkastet, og ren søppeltekst ville TØMT et allerede lagret mål mens
UI-en likevel viser "Lagret ok". Ett eneste ugyldig (ikke-blankt)
tallfelt blokkerer nå HELE lagre-klikket -- ingen skriving utføres for
NOEN av feltene -- og viser en synlig feilmelding i stedet. Et
BEVISST blankt felt beholder sin eksisterende "tøm dette feltet"-
oppførsel uendret.

Rene formaterings-/uttrekkshjelpere (planlagt sammendrag,
planlagt-vs-faktisk) er i modules/kbhbrew_history_ui.py, slik at de kan
enhetstestes uten en Streamlit-kontekst (se
tests/test_kbhbrew_history_ui_helpers.py).

V2-1B (issue #87) legger til et EGET, atskilt sensorikk-/lærings-skjema
(_render_sensing_learning_skjema()) under actuals-skjemaet, med sitt
EGET eksplisitte "💾 Lagre sensorikk og læring"-lagre-klikk -- samme
"rendring/utvalg/typing skriver ingenting"-garanti som actuals-skjemaet,
men en helt separat skrivehandling (ett Lagre-klikk her rører ALDRI
actuals/status/brewedAt, og omvendt). Bruker KUN de eksisterende Core V1
sensing.judgment/sensing.notes/learning.whatWorked/whatChanged/nextTime
-- ingen ny .kbhbrew-semantikk, ingen AI-tolkning, ingen automatisk
utledet konklusjon (se issue #87 "Ownership boundary": dette er
fangst-UI, ikke Brew Lab-tolkning). `sensing.judgment` har en BEVISST
tredje "ikke satt"-tilstand (tomstreng) utover de tre ekte
yes/maybe/no-verdiene, slik at et ubesvart brygg aldri fremstår som om
brukeren aktivt har valgt et av de tre svarene.
"""
import streamlit as st

from config import DEMO_MODE
from modules.export_format import fmt_abv, fmt_fg, fmt_og, fmt_vol
from modules.kbhbrew_history_ui import (
    bygg_planlagt_sammendrag,
    bygg_planlagt_vs_faktisk,
    parse_actual_tallfelt,
)
from modules.kbhbrew_storage import hent_alle_brews, oppdater_brew_lag
from modules.kbhbrew_ui import sorter_brews_for_eksport
from ui.i18n import t

_STATUS_VALG = ("active", "done", "discarded")

# Tomstreng er det BEVISST reserverte "ikke satt"-valget (issue #87: "Do
# not infer or auto-fill a judgment") -- ALDRI et gjettet/forhåndsvalgt
# yes/maybe/no. normaliser_sensing_lag() (modules/kbhbrew.py) godtar kun
# de tre ekte verdiene i _GYLDIGE_JUDGMENT_VERDIER, så en lagret tomstreng
# faller automatisk bort igjen fra det lagrede laget (samme "blankt felt
# tømmer feltet"-prinsipp som actuals.notes over).
_SENSING_JUDGMENT_VALG = ("", "yes", "maybe", "no")

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
        og_ok, og_verdi = parse_actual_tallfelt(og_tekst)
        fg_ok, fg_verdi = parse_actual_tallfelt(fg_tekst)
        volum_ok, volum_verdi = parse_actual_tallfelt(volum_tekst)

        ugyldige_felt = []
        if not og_ok:
            ugyldige_felt.append(t("brew_history.actual_og_label"))
        if not fg_ok:
            ugyldige_felt.append(t("brew_history.actual_fg_label"))
        if not volum_ok:
            ugyldige_felt.append(t("brew_history.actual_volum_label"))

        if ugyldige_felt:
            st.error(t("brew_history.ugyldig_tall_feil", felt=", ".join(ugyldige_felt)))
        else:
            oppdatert_brew = oppdater_brew_lag(
                brew_id,
                actuals={
                    "og": "" if og_verdi is None else og_verdi,
                    "fg": "" if fg_verdi is None else fg_verdi,
                    "volumeL": "" if volum_verdi is None else volum_verdi,
                    "notes": notat_tekst,
                },
                status=status_valgt,
                brewed_at=brygget_tekst.strip(),
            )
            st.success(t("brew_history.lagret_ok"))
            if oppdatert_brew is not None:
                return oppdatert_brew
    return brew


def _judgment_etikett(verdi):
    return t("brew_history.sensing_judgment.unset") if verdi == "" else t(f"brew_history.sensing_judgment.{verdi}")


def _render_sensing_learning_skjema(brew_id, brew):
    """Renderer det editerbare sensorikk-/lærings-skjemaet (issue #87,
    V2-1B) -- ATSKILT fra actuals-skjemaet over, med sitt EGET eksplisitte
    lagre-klikk (samme "ingen skriving uten knappetrykk"-garanti som
    _render_actuals_skjema()). Bruker KUN de eksisterende Core V1-feltene
    sensing.judgment/sensing.notes/learning.whatWorked/whatChanged/
    nextTime, via modules/kbhbrew_storage.py::oppdater_brew_lag() -- ALDRI
    en ny skrivevei, ALDRI actuals/snapshot/status/brewedAt.

    Returnerer det FERSKESTE kjente brew-objektet, samme mønster som
    _render_actuals_skjema()."""
    sensing = brew.get("sensing") or {}
    learning = brew.get("learning") or {}

    st.markdown(f"**{t('brew_history.sensing_tittel')}**")
    judgment_naa = sensing.get("judgment")
    if judgment_naa not in _SENSING_JUDGMENT_VALG:
        judgment_naa = ""
    judgment_valgt = st.selectbox(
        t("brew_history.sensing_judgment_label"),
        options=list(_SENSING_JUDGMENT_VALG),
        index=_SENSING_JUDGMENT_VALG.index(judgment_naa),
        format_func=_judgment_etikett,
        key=f"kbhbrew_hist_sensing_judgment::{brew_id}",
    )
    sensing_notat_tekst = st.text_area(
        t("brew_history.sensing_notes_label"),
        value=sensing.get("notes") or "",
        key=f"kbhbrew_hist_sensing_notes::{brew_id}",
    )

    st.markdown(f"**{t('brew_history.learning_tittel')}**")
    worked_tekst = st.text_area(
        t("brew_history.learning_what_worked_label"),
        value=learning.get("whatWorked") or "",
        key=f"kbhbrew_hist_learning_worked::{brew_id}",
    )
    changed_tekst = st.text_area(
        t("brew_history.learning_what_changed_label"),
        value=learning.get("whatChanged") or "",
        key=f"kbhbrew_hist_learning_changed::{brew_id}",
    )
    next_tekst = st.text_area(
        t("brew_history.learning_next_time_label"),
        value=learning.get("nextTime") or "",
        key=f"kbhbrew_hist_learning_next::{brew_id}",
    )

    if st.button(t("brew_history.sensing_learning_lagre_btn"), key=f"kbhbrew_hist_sensing_learning_lagre_btn::{brew_id}"):
        oppdatert_brew = oppdater_brew_lag(
            brew_id,
            sensing={"judgment": judgment_valgt, "notes": sensing_notat_tekst},
            learning={"whatWorked": worked_tekst, "whatChanged": changed_tekst, "nextTime": next_tekst},
        )
        st.success(t("brew_history.sensing_learning_lagret_ok"))
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
    brew = _render_sensing_learning_skjema(brew_id, brew)
    st.write("")
    _render_sammenligning(brew)
