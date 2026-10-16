"""
Bryggeskole representative-user feedback (issue #542) -- schema, payload and
transport. Pure and stdlib-only: no Streamlit, no disk I/O.

The form in ui/bryggeskole_feedback_panel.py collects a short, anonymous
acceptance survey. This module turns those answers into an explicitly
limited JSON payload and POSTs it, server-side, to an owner-configured HTTPS
webhook (planned receiver: a Google Apps Script Web App that appends one row
to a Google Sheet; contract and setup in
docs/development/BRYGGESKOLE_FEEDBACK.md).

Boundaries, stated plainly:
- Feedback is NOT learning data. It never reads or writes mastery, progress,
  completion or any other learner state, and the payload carries none of it.
- Anonymous by default: no name, e-mail, IP, user agent or persistent user
  id. `feedback_id` is a random id made when the form opens in one browser
  session; it identifies one submission, never a learner.
- Only whitelisted answer keys pass. Closed questions accept only their own
  option ids; free text is stripped and capped.
- Nothing is ever written to local disk, in DEMO_MODE or out of it. The one
  side effect is the POST to the configured endpoint (an explicit, owner-
  approved exception to Demo Mode's no-network habit; see DEMO_MODE.md).
- The endpoint comes only from the environment (on Streamlit Community
  Cloud, a root-level secret is exported as an environment variable). It is
  never hardcoded or committed. Without it, send_feedback() reports
  NOT_CONFIGURED and sends nothing.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import uuid

WEBHOOK_URL_ENV = "BRYGGESKOLE_FEEDBACK_WEBHOOK_URL"
# Optional shared secret. A Google Apps Script Web App cannot read request
# headers, so the token travels in the JSON body; it only reaches the
# owner's own endpoint over HTTPS.
TOKEN_ENV = "BRYGGESKOLE_FEEDBACK_TOKEN"

SCHEMA = "kbh.bryggeskole.feedback"
SCHEMA_VERSION = 1

TEXT_MAX_CHARS = 1000
TIMEOUT_SECONDS = 10

# Closed questions: answer key -> allowed option ids (language-neutral; the
# UI owns the NO/EN labels). Order is the form order.
CLOSED_QUESTIONS = {
    "start_clarity": ("easy", "ok", "hard"),
    "stage_difference": ("clear", "partly", "unclear", "not_noticed"),
    "unknown_terms": ("no", "yes"),
    "unsure_next_step": ("no", "yes"),
    "text_amount": ("too_little", "about_right", "too_much"),
    "questions_quality": ("clear", "some_unclear", "some_tricky"),
    "explanation_helped": ("yes", "partly", "no", "no_wrong_answers"),
    "learned_for_real_brew": ("yes", "a_little", "no"),
    "would_continue": ("yes", "maybe", "no"),
}

# Optional free-text answers, each tied to the question it explains.
TEXT_FIELDS = (
    "unknown_terms_text",
    "unsure_next_step_text",
    "questions_quality_text",
    "learned_for_real_brew_text",
    "other_comments",
)

# Where the form was opened. Values are app ids (not personal data); an
# unknown value is dropped rather than passed through.
CONTEXT_FIELDS = ("environment", "stage", "module")
_ENVIRONMENTS = ("hjemmebrygger", "bryggeri")
_STAGES = ("foundation", "kompetent")

LANGUAGES = ("no", "en")

# send_feedback() outcomes.
SENT = "sent"
NOT_CONFIGURED = "not_configured"
FAILED = "failed"


def new_feedback_id():
    """A random, session-scoped submission id (UUID4 hex). Never derived from
    anything about the person or device."""
    return uuid.uuid4().hex


def _clean_text(value):
    if not isinstance(value, str):
        return ""
    return value.strip()[:TEXT_MAX_CHARS]


def clean_answers(answers):
    """Only known keys survive. Closed answers must be one of their option
    ids (anything else is dropped); free text is stripped and capped; empty
    answers are left out."""
    answers = answers if isinstance(answers, dict) else {}
    cleaned = {}
    for key, options in CLOSED_QUESTIONS.items():
        value = answers.get(key)
        if value in options:
            cleaned[key] = value
    for key in TEXT_FIELDS:
        text = _clean_text(answers.get(key))
        if text:
            cleaned[key] = text
    return cleaned


def has_content(answers):
    """True when at least one question is answered. An empty form is never
    sent."""
    return bool(clean_answers(answers))


def clean_context(context, module_ids=()):
    context = context if isinstance(context, dict) else {}
    allowed = {
        "environment": _ENVIRONMENTS,
        "stage": _STAGES,
        "module": tuple(module_ids),
    }
    return {key: (context.get(key) if context.get(key) in allowed[key] else None) for key in CONTEXT_FIELDS}


def build_payload(answers, language, context, feedback_id, submitted_at, demo_mode, module_ids=()):
    """The complete, explicitly limited payload. Every field is listed here;
    nothing else can reach the receiver."""
    return {
        "schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "feedback_id": str(feedback_id),
        "submitted_at": str(submitted_at),
        "language": language if language in LANGUAGES else "no",
        "demo_mode": bool(demo_mode),
        "context": clean_context(context, module_ids),
        "answers": clean_answers(answers),
    }


def webhook_url(environ=None):
    """The configured HTTPS endpoint, or None. Anything that is not an https
    URL with a host counts as not configured."""
    environ = os.environ if environ is None else environ
    url = (environ.get(WEBHOOK_URL_ENV) or "").strip()
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or not parts.netloc:
        return None
    return url


def is_configured(environ=None):
    return webhook_url(environ) is not None


def _default_opener(request, timeout):
    return urllib.request.urlopen(request, timeout=timeout)


def send_feedback(payload, environ=None, opener=None, timeout=TIMEOUT_SECONDS):
    """POST the payload as JSON. Returns SENT only when the endpoint answers
    HTTP 2xx with a JSON body {"ok": true}; NOT_CONFIGURED when no endpoint
    is set (nothing is sent); FAILED for every other outcome (HTTP error,
    network error, timeout, non-JSON or {"ok": false} reply). Never raises
    for a transport problem, and never writes anything locally."""
    environ = os.environ if environ is None else environ
    url = webhook_url(environ)
    if url is None:
        return NOT_CONFIGURED
    body = dict(payload)
    token = (environ.get(TOKEN_ENV) or "").strip()
    if token:
        body["token"] = token
    request = urllib.request.Request(
        url,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    opener = opener or _default_opener
    try:
        with opener(request, timeout) as response:
            status = getattr(response, "status", None) or response.getcode()
            raw = response.read()
    except (urllib.error.URLError, OSError, ValueError):
        return FAILED
    if not 200 <= int(status) < 300:
        return FAILED
    try:
        reply = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return FAILED
    return SENT if isinstance(reply, dict) and reply.get("ok") is True else FAILED
