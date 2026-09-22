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

V2.2 G2B (issue #355) legger til `learning.hypothesis` -- ETT nytt,
valgfritt fritekstfelt, plassert BEVISST mellom whatChanged og nextTime
(evidens-rekkefølgen: evidens -> tolkning -> hypotese -> neste-gang-
beslutning). Rendres/lagres/tømmes med nøyaktig samme mønster som de tre
eksisterende learning-feltene over -- ingen egen skrivevei, INGEN
automatisk utledet/foreslått hypotese (aldri utledet fra et annet brygg,
f.eks. Sommerglød), og en synlig bildetekst gjør eksplisitt at dette er
en MULIG forklaring, ikke en fastslått årsak (CORE_KBHBREW_V1.md §5.9).
Den read-only planlagt-vs-faktisk-sammenligningen (_render_sammenligning)
er flyttet til å rendres RETT ETTER actuals-skjemaet (i stedet for
nederst) slik at den faktiske evidensen vises før sensorikk/
tolkning/hypotese/neste-gang-skjemaet under -- ren rekkefølge-endring,
ingen ny skrivevei, ingen endring av noen av de to eksisterende
lagreknappenes omfang.
"""
import streamlit as st

from config import DEMO_MODE
from modules.export_format import fmt_abv, fmt_fg, fmt_og, fmt_vol
from modules.kbh_import import UgyldigKbhrecipeForImport
from modules.kbh_import_apply import NESTE_VARIANT_SEED_PENDING_NOKKEL
from modules.kbhbrew import bygg_neste_variant_seed
from modules.kbhbrew_history_ui import (
    bygg_planlagt_sammendrag,
    bygg_planlagt_vs_faktisk,
    parse_actual_tallfelt,
)
from modules.kbhbrew_storage import hent_alle_brews, oppdater_brew_lag
from modules.kbhbrew_ui import sorter_brews_for_eksport
from modules.recipe_storage import hent_alle_oppskrifter
from ui.i18n import t
from ui.kbhbrew_panel import aktiv_brew_id, sett_aktiv_brew_id

# App A1 (issue #170) "Identity safety": et privat, per-modul sentinel-
# objekt (ALDRI en streng/None som i teorien kunne vært en ekte,
# lagret verdi) brukt til å skille "denne nøkkelen er ALDRI satt før"
# fra "nøkkelen er satt, men til None/en tidligere kjent verdi" i de to
# små synk-sjekkene under -- samme "unngå en falsk None==None-treff ved
# aller første rendring"-forsiktighet issue #170 krever.
_UKJENT_SENTINEL = object()

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
    hypothesis/nextTime, via modules/kbhbrew_storage.py::
    oppdater_brew_lag() -- ALDRI en ny skrivevei, ALDRI
    actuals/snapshot/status/brewedAt.

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
    hypothesis_tekst = st.text_area(
        t("brew_history.learning_hypothesis_label"),
        value=learning.get("hypothesis") or "",
        key=f"kbhbrew_hist_learning_hypothesis::{brew_id}",
    )
    st.caption(t("brew_history.learning_hypothesis_caption"))
    next_tekst = st.text_area(
        t("brew_history.learning_next_time_label"),
        value=learning.get("nextTime") or "",
        key=f"kbhbrew_hist_learning_next::{brew_id}",
    )

    if st.button(t("brew_history.sensing_learning_lagre_btn"), key=f"kbhbrew_hist_sensing_learning_lagre_btn::{brew_id}"):
        oppdatert_brew = oppdater_brew_lag(
            brew_id,
            sensing={"judgment": judgment_valgt, "notes": sensing_notat_tekst},
            learning={
                "whatWorked": worked_tekst,
                "whatChanged": changed_tekst,
                "hypothesis": hypothesis_tekst,
                "nextTime": next_tekst,
            },
        )
        st.success(t("brew_history.sensing_learning_lagret_ok"))
        if oppdatert_brew is not None:
            return oppdatert_brew
    return brew


# Stabil, språknøytral sentinel for "ingen kobling valgt" i
# neste-variant-lenke-selectboksen -- samme "aldri den oversatte
# visningsteksten selv"-prinsipp som ui/sidebar.py sin
# _INGEN_OPPSKRIFT_VALGT.
_NESTE_VARIANT_INGEN_LENKE = "__ingen_neste_variant_lenke__"


def _render_neste_variant_seksjon(brew_id, brew, malt_db, humle_db, gjaer_db):
    """V2.2 G2D (issue #363) -- de to ATSKILTE, eksplisitte trinnene
    kontrakten (docs/development/v22_g2c_next_variant_linkage_contract.md
    §3/§4) krever, ETT eget lagre-klikk hver, samme
    "rendring/utvalg/typing skriver ingenting"-garanti som resten av
    dette panelet:

      1. "🌱 Opprett neste variant" seeder et FERSKT, ULAGRET
         oppskriftutkast i session_state fra brew.snapshot.recipe --
         ALDRI den mulig avdriftede live-oppskriften (§3 spørsmål 2),
         ALDRI en automatisk utledet endring fra hypothesis/nextTime.
         Kun aktivert når `learning.nextTime` faktisk er fylt ut (den
         beslutningsteksten dette utkastet skal operasjonalisere).
         Rører KUN session_state -- det lagrede brygget er uendret helt
         til brukeren selv trykker en lagreknapp i Oppskrift-fanen
         (ui/recipe_card.py). Ingen automatisk fanebytte finnes i denne
         App-en (§2.6 -- ingen eksisterende mekanisme for det); brukeren
         bytter selv til fanen «Oppskrift» for å se/redigere utkastet,
         nøyaktig samme mønster som en ferdig .kbhrecipe-import
         (ui/sidebar.py).
      2. En SEPARAT lenke-bekreftelse skriver
         `learning.nextRecipeOriginId` til en ALLEREDE lagret
         oppskrifts `originRecipeId` -- ALDRI auto-koblet på navn eller
         hvilken fane som er aktiv. En kobling som peker på en
         oppskrift som senere er omdøpt/slettet lokalt vises tydelig som
         "ikke funnet", ALDRI en feil/krasj (§3 spørsmål 5)."""
    learning = brew.get("learning") or {}
    st.markdown(f"**{t('brew_history.neste_variant_tittel')}**")

    if not (learning.get("nextTime") or "").strip():
        st.caption(t("brew_history.neste_variant_krever_next_time"))
    elif st.button(t("brew_history.neste_variant_knapp"), key=f"kbhbrew_hist_neste_variant_btn::{brew_id}"):
        try:
            seed = bygg_neste_variant_seed(brew, malt_db, humle_db, gjaer_db)
        except (ValueError, UgyldigKbhrecipeForImport) as e:
            st.error(t("brew_history.neste_variant_feil", feil=str(e)))
        else:
            # Kan IKKE hydrere session_state direkte her: denne knappen
            # rendres fra Bryggdag-fanen, som i app.py sin
            # scriptrekkefølge kjøres ETTER Oppskrift-fanen -- widgeten
            # `gjeldende_navn` m.fl. er derfor ALLEREDE instansiert denne
            # kjøringen (StreamlitWidgetAlreadyInstantiatedError). Lagrer
            # derfor kun det rå seed-resultatet og lar
            # ui/sidebar.py::render_sidebar() (kjører FØR alle
            # fane-widgets, hver eneste rerun) konsumere det på neste
            # kjøring -- se NESTE_VARIANT_SEED_PENDING_NOKKEL sin egen
            # kommentar (modules/kbh_import_apply.py).
            st.session_state[NESTE_VARIANT_SEED_PENDING_NOKKEL] = seed["import_resultat"]
            st.success(t("brew_history.neste_variant_ok"))
            st.rerun()

    st.markdown(f"**{t('brew_history.neste_variant_lenke_tittel')}**")
    kandidater = {
        navn: data.get("originRecipeId")
        for navn, data in hent_alle_oppskrifter().items()
        if isinstance(data.get("originRecipeId"), str) and data["originRecipeId"].strip()
    }

    gjeldende_lenke = learning.get("nextRecipeOriginId")
    _matchende_navn = next((navn for navn, oid in kandidater.items() if oid == gjeldende_lenke), None)
    if gjeldende_lenke:
        if _matchende_navn:
            st.caption(t("brew_history.neste_variant_lenke_gjeldende", navn=_matchende_navn))
        else:
            st.caption(t("brew_history.neste_variant_lenke_ikke_funnet", id=gjeldende_lenke))

    if not kandidater:
        st.caption(t("brew_history.neste_variant_lenke_ingen_kandidater"))
        return brew

    valg = [_NESTE_VARIANT_INGEN_LENKE] + sorted(kandidater.keys())
    _forvalgt = _matchende_navn if _matchende_navn is not None else _NESTE_VARIANT_INGEN_LENKE
    valgt_navn = st.selectbox(
        t("brew_history.neste_variant_lenke_velg_label"),
        options=valg,
        index=valg.index(_forvalgt),
        format_func=lambda v: t("brew_history.neste_variant_lenke_ingen") if v == _NESTE_VARIANT_INGEN_LENKE else v,
        key=f"kbhbrew_hist_neste_variant_lenke::{brew_id}",
    )

    if st.button(t("brew_history.neste_variant_lenke_knapp"), key=f"kbhbrew_hist_neste_variant_lenke_btn::{brew_id}"):
        ny_verdi = "" if valgt_navn == _NESTE_VARIANT_INGEN_LENKE else kandidater[valgt_navn]
        oppdatert_brew = oppdater_brew_lag(brew_id, learning={"nextRecipeOriginId": ny_verdi})
        st.success(t("brew_history.neste_variant_lenke_lagret_ok"))
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


def render_kbhbrew_history_panel(malt_db=None, humle_db=None, gjaer_db=None):
    """Toppnivå-inngangspunkt kalt fra ui/brewday_panel.py. Skjules helt i
    DEMO_MODE (persistent skriving), samme mønster som
    render_kbhbrew_create_panel()/render_kbhbrew_import_panel().

    App A1 (issue #170) "Identity safety": denne selectboksen og
    Bryggdag Steg 4/5 sitt målefelt-mål (ui/kbhbrew_panel.py sin
    `_AKTIV_BREW_ID_NOKKEL`) skal ALDRI stille være uenige om hvilket
    brygg som er målet. To små, retningsbestemte synk-sjekker (under)
    håndhever dette begge veier, uten å innføre noe nytt state-mønster
    utover de allerede etablerte shadow-/pending-nøkkel-idiomene
    (docs/development/PROJECT_MAP.md):

      1. Endres det aktive målet et ANNET sted (nytt brygg opprettet,
         eller ugyldiggjort av et oppskriftsbytte) -- FØR selectboksen
         under instansieres denne kjøringen -- forvelges/låses den til
         det nye aktive målet (kun hvis det faktisk finnes i den
         nåværende brygg-listen).
      2. Ellers, hvis brukeren selv nettopp endret DENNE selectboksens
         egen verdi (sammenlignet mot forrige kjente verdi -- ALDRI mot
         hva forvalget over nettopp kan ha tvunget den til, som ville
         gitt en falsk "brukervalg"-deteksjon), oppdateres det delte
         aktive målet til å matche.

    `malt_db`/`humle_db`/`gjaer_db` (issue #363, V2.2 G2D) -- de samme
    master-databasene app.py allerede laster inn og sender videre til
    ui/brewday_panel.py, brukt UTELUKKENDE av
    _render_neste_variant_seksjon() sin "🌱 Opprett neste variant"-
    handling (samme ingrediens-ID-validering en ekte .kbhrecipe-import
    allerede gjør, se modules/kbhbrew.py::bygg_neste_variant_seed())."""
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

    _aktiv = aktiv_brew_id()
    _sist_kjent_aktiv = st.session_state.get("_kbhbrew_hist_sist_kjente_aktiv", _UKJENT_SENTINEL)
    _tvang_forvalg = False
    if _aktiv != _sist_kjent_aktiv:
        if _aktiv in brews:
            st.session_state["kbhbrew_historikk_valgt_id"] = _aktiv
            _tvang_forvalg = True
        st.session_state["_kbhbrew_hist_sist_kjente_aktiv"] = _aktiv

    brew_id = st.selectbox(
        t("brew_history.velg_label"),
        options=[bid for bid, _ in valg],
        format_func=lambda bid: etiketter[bid],
        key="kbhbrew_historikk_valgt_id",
    )

    _sist_valgt = st.session_state.get("_kbhbrew_hist_sist_valgt_id", _UKJENT_SENTINEL)
    if not _tvang_forvalg and _sist_valgt is not _UKJENT_SENTINEL and brew_id != _sist_valgt:
        sett_aktiv_brew_id(brew_id)
    st.session_state["_kbhbrew_hist_sist_valgt_id"] = brew_id

    brew = brews.get(brew_id)
    if brew is None:
        return

    st.caption(t("brew_history.planlagt_tittel"))
    _render_planlagt_sammendrag(brew)
    st.write("")
    brew = _render_actuals_skjema(brew_id, brew)
    st.write("")
    _render_sammenligning(brew)
    st.write("")
    brew = _render_sensing_learning_skjema(brew_id, brew)
    st.write("")
    _render_neste_variant_seksjon(brew_id, brew, malt_db, humle_db, gjaer_db)
