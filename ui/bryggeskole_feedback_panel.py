# ui/bryggeskole_feedback_panel.py
"""
Bryggeskole representative-user feedback form (issue #542).

A short, voluntary, anonymous acceptance survey, opened from the school
overview or from a module summary. It is deliberately separate from the
course engine:
- it reads and writes no mastery, progress, completion or learner state, and
  it never changes bs_aktiv_modul -- closing the form returns the learner to
  exactly where they were;
- its own session keys all start with "bs_feedback_" / "bs_fb_";
- nothing is written to local disk, in DEMO_MODE or out of it. Sending is a
  server-side HTTPS POST to the owner-configured webhook
  (bryggeskole/feedback.py); without that configuration the form says
  calmly that sending is not available and pretends nothing.

State:
- bs_feedback_apen: the form view is open;
- bs_feedback_kontekst: (environment, stage, module) where it was opened;
- bs_feedback_id: random id of the current submission (new per new form);
- bs_feedback_status: last outcome (feedback.SENT / FAILED / None);
- bs_feedback_sendt_id: the id already sent, so the same submission can
  never be sent twice;
- bs_feedback_utkast: the answers of the last submit attempt, written back
  into the widgets so a failed send keeps everything the person typed.
"""
import datetime

import streamlit as st

from bryggeskole import feedback as _feedback
from config import DEMO_MODE
from ui.i18n import gjeldende_sprak, t

_APEN_KEY = "bs_feedback_apen"
_KONTEKST_KEY = "bs_feedback_kontekst"
_ID_KEY = "bs_feedback_id"
_STATUS_KEY = "bs_feedback_status"
_SENDT_ID_KEY = "bs_feedback_sendt_id"
_UTKAST_KEY = "bs_feedback_utkast"

# (answer key, i18n stem, optional free-text field shown under it)
_LUKKEDE = (
    ("start_clarity", None),
    ("stage_difference", None),
    ("unknown_terms", "unknown_terms_text"),
    ("unsure_next_step", "unsure_next_step_text"),
    ("text_amount", None),
    ("questions_quality", "questions_quality_text"),
    ("explanation_helped", None),
    ("learned_for_real_brew", "learned_for_real_brew_text"),
    ("would_continue", None),
)


def _widget_key(svar_nokkel):
    return f"bs_fb_{svar_nokkel}"


def apne_tilbakemelding(miljo=None, trinn=None, modul=None):
    """on_click for every entry button. Starts a new submission unless the
    current one is still unsent (then it is simply reopened)."""
    st.session_state[_APEN_KEY] = True
    st.session_state[_KONTEKST_KEY] = {"environment": miljo, "stage": trinn, "module": modul}
    if st.session_state.get(_ID_KEY) is None or st.session_state.get(_SENDT_ID_KEY) == st.session_state.get(_ID_KEY):
        _ny_innsending()


def _ny_innsending():
    st.session_state[_ID_KEY] = _feedback.new_feedback_id()
    st.session_state[_STATUS_KEY] = None
    st.session_state.pop(_UTKAST_KEY, None)
    for svar_nokkel in list(_feedback.CLOSED_QUESTIONS) + list(_feedback.TEXT_FIELDS):
        st.session_state.pop(_widget_key(svar_nokkel), None)


def _lukk():
    st.session_state[_APEN_KEY] = False


def tilbakemelding_er_apen():
    return bool(st.session_state.get(_APEN_KEY))


def render_inngang(knapp_key, miljo, trinn=None, modul=None, forklaring_nokkel="bryggeskole.feedback.inngang_forklaring"):
    """The small, voluntary entry: one caption line and one button. It
    never blocks or replaces any course navigation."""
    with st.container(key=f"{knapp_key}_inngang"):
        st.caption(t(forklaring_nokkel))
        st.button(
            t("bryggeskole.feedback.inngang"), key=knapp_key, width="content",
            on_click=apne_tilbakemelding, args=(miljo, trinn, modul),
        )


def _gjenopprett_utkast():
    """Streamlit drops widget state in runs where a widget is not drawn.
    Writing the last submitted answers back before the widgets exist keeps a
    failed or unsent submission intact (the documented carry-over pattern,
    as in bryggeskole_panel._init_state)."""
    utkast = st.session_state.get(_UTKAST_KEY) or {}
    for svar_nokkel, verdi in utkast.items():
        key = _widget_key(svar_nokkel)
        if key not in st.session_state:
            st.session_state[key] = verdi


def _les_svar():
    svar = {}
    for svar_nokkel in list(_feedback.CLOSED_QUESTIONS) + list(_feedback.TEXT_FIELDS):
        verdi = st.session_state.get(_widget_key(svar_nokkel))
        if verdi not in (None, ""):
            svar[svar_nokkel] = verdi
    return svar


def _send(module_ids):
    svar = _les_svar()
    st.session_state[_UTKAST_KEY] = dict(svar)
    if not _feedback.has_content(svar):
        st.session_state[_STATUS_KEY] = "tom"
        return
    if st.session_state.get(_SENDT_ID_KEY) == st.session_state[_ID_KEY]:
        st.session_state[_STATUS_KEY] = _feedback.SENT
        return
    payload = _feedback.build_payload(
        svar,
        language=gjeldende_sprak(),
        context=st.session_state.get(_KONTEKST_KEY),
        feedback_id=st.session_state[_ID_KEY],
        submitted_at=datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        demo_mode=DEMO_MODE,
        module_ids=module_ids,
    )
    resultat = _feedback.send_feedback(payload)
    st.session_state[_STATUS_KEY] = resultat
    if resultat == _feedback.SENT:
        st.session_state[_SENDT_ID_KEY] = st.session_state[_ID_KEY]


def _alternativ_tekst(svar_nokkel):
    return lambda alternativ: t(f"bryggeskole.feedback.{svar_nokkel}.{alternativ}")


def render_tilbakemelding(module_ids):
    """The form view. `module_ids` are the course's module ids, used only to
    validate the context the form was opened in."""
    st.subheader(t("bryggeskole.feedback.heading"))
    st.button(t("bryggeskole.feedback.lukk"), key="bs_feedback_lukk_btn", on_click=_lukk)

    if not _feedback.is_configured():
        # Honest and calm: nothing can be sent, so nothing is collected.
        st.info(t("bryggeskole.feedback.ikke_konfigurert"))
        return

    status = st.session_state.get(_STATUS_KEY)
    if status == _feedback.SENT and st.session_state.get(_SENDT_ID_KEY) == st.session_state.get(_ID_KEY):
        st.success(t("bryggeskole.feedback.sendt"))
        st.button(t("bryggeskole.feedback.ny"), key="bs_feedback_ny_btn", on_click=_ny_innsending)
        return

    st.caption(t("bryggeskole.feedback.intro"))
    _gjenopprett_utkast()
    with st.form("bs_feedback_skjema", clear_on_submit=False, border=True):
        for svar_nokkel, tekstfelt in _LUKKEDE:
            key = _widget_key(svar_nokkel)
            # No preselected answer. `index` only when the value is not
            # already in Session State (restored draft), or Streamlit warns
            # about a default set twice.
            standard = {} if key in st.session_state else {"index": None}
            st.radio(
                t(f"bryggeskole.feedback.{svar_nokkel}.sporsmal"),
                options=list(_feedback.CLOSED_QUESTIONS[svar_nokkel]),
                format_func=_alternativ_tekst(svar_nokkel),
                horizontal=True,
                key=key,
                **standard,
            )
            if tekstfelt is not None:
                st.text_area(
                    t(f"bryggeskole.feedback.{tekstfelt}"), key=_widget_key(tekstfelt),
                    max_chars=_feedback.TEXT_MAX_CHARS, height=68,
                )
        st.text_area(
            t("bryggeskole.feedback.other_comments"), key=_widget_key("other_comments"),
            max_chars=_feedback.TEXT_MAX_CHARS, height=100,
        )
        sendt = st.form_submit_button(t("bryggeskole.feedback.send"))

    if sendt:
        _send(module_ids)
        status = st.session_state.get(_STATUS_KEY)
        if status == _feedback.SENT:
            st.rerun()
    if status == "tom":
        st.warning(t("bryggeskole.feedback.tom"))
    elif status == _feedback.FAILED:
        st.error(t("bryggeskole.feedback.feilet"))
    elif status == _feedback.NOT_CONFIGURED:
        st.info(t("bryggeskole.feedback.ikke_konfigurert"))
