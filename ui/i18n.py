"""Streamlit-eid halvdel av App-i18n-laget: eier
`st.session_state`-nøkkelen for gjeldende visningsspråk og selve
språkvelger-widgeten. Den språknøytrale oppslags-/interpolasjons-logikken
(og selve tekstene) ligger i modules/i18n.py — se den modulens docstring
for konvensjonene (nøkkelnavngiving, `{param}`-interpolasjon,
fallback-/feil-oppførsel). Splitten følger den etablerte
modules-vs-ui-regelen (.claude/rules/desktop.md): modules/** importerer
aldri Streamlit.

Språkvalget er bevisst et rent presentasjonsvalg i denne omgang (kun
`st.session_state`, ikke lagret i oppskriftsfiler eller på tvers av
prosesser) — "lokal preferanse for denne økten", samme avgrensning som
web-varianten sin URL-strategi V1 (web/js/i18n.js). Berører ALDRI
oppskrift-/beregningsdata: se test_app_i18n_foundation.py sin
`test_sprak_endrer_ikke_beregning_eller_lagret_data`.
"""

import streamlit as st

from modules.i18n import SPRAK_DEFAULT, SPRAK_LISTE, t as _t_ren

SPRAK_STATE_KEY = "sprak"


def init_sprak_state() -> None:
    if SPRAK_STATE_KEY not in st.session_state:
        st.session_state[SPRAK_STATE_KEY] = SPRAK_DEFAULT


def gjeldende_sprak() -> str:
    return st.session_state.get(SPRAK_STATE_KEY, SPRAK_DEFAULT)


def t(nokkel: str, **params) -> str:
    """Som modules.i18n.t(), men leser gjeldende språk automatisk fra
    st.session_state i stedet for å kreve det som argument ved hvert
    kall — den praktiske inngangen for alt UI-kode i ui/**/app.py."""
    return _t_ren(nokkel, gjeldende_sprak(), **params)


def render_sprak_valger() -> None:
    """Renderer språkvelgeren i sidebaren. Kalt fra ui/sidebar.py, ikke
    fra app.py direkte — sidebaren er navigasjonsflaten denne
    representative skiven av i18n-migreringen bruker (se issue #58)."""
    init_sprak_state()
    st.sidebar.radio(
        t("sprak.valger.label"),
        options=list(SPRAK_LISTE),
        format_func=lambda kode: t(f"sprak.valger.{kode}"),
        horizontal=True,
        key=SPRAK_STATE_KEY,
    )
