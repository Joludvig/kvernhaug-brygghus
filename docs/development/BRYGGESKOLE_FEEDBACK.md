# Bryggeskole — representative-user feedback (issue #542)

*Del av KBDP. Se [../../CLAUDE.md](../../CLAUDE.md) for oversikt over hele dokumentsystemet.*

This is a short, voluntary, anonymous feedback form inside the Bryggeskole. It is used for representative-user acceptance (#540), not for analytics or user profiling.

Answers go from the app, with a server-side HTTPS POST, to an owner-configured webhook. The planned receiver is a Google Apps Script Web App that adds one row to a Google Sheet.

**Status at merge:** the app side is implemented. Live storage is **not** active until the owner has completed the setup below and confirmed that a test row arrived. Until then the form says "Innsending av tilbakemelding er ikke tilgjengelig akkurat nå", and nothing is sent or saved.

## Separation from the course

- Feedback is **not** learning data. The form reads and writes no mastery, progress, completion or other learner state, and its payload contains none of it.
- Opening, sending or closing the form never changes the open module (`bs_aktiv_modul`). The learner comes back to exactly where they were.
- It has its own session keys: `bs_feedback_*` and widget keys `bs_fb_*`.

## UX

| Where | What |
|---|---|
| Below the module grid on the Bryggeskole overview | One caption line and the button «💬 Gi tilbakemelding på Bryggeskolen» / "💬 Give feedback on the Brew School" |
| Under a module's summary, after the «Prøv igjen» / «Tilbake til oversikten» row | The same button, with the line «Gi gjerne en kort tilbakemelding – den er frivillig og påvirker ikke fremgangen din.» |

How the form behaves:
- It opens as its own view with «← Tilbake».
- It is voluntary and anonymous. Every question can be skipped, and the person is asked not to write their name or contact details.
- It has 9 short closed questions, with no option selected in advance and **no overall 1–10 score**. Four of them have an optional free-text "Hvis ja: hvilke/hvor? / Hva?" field.
- It ends with one optional free-text field: "Er det noe annet du vil si om Bryggeskolen?"

Outcomes:

| Situation | What the person sees |
|---|---|
| **Sent** | «Takk! Tilbakemeldingen din er sendt.» The form disappears, so the same submission cannot be sent twice. «Skriv en ny tilbakemelding» starts a new submission with a new id. |
| **Failed** (HTTP error, network error, timeout, no JSON, or `{"ok": false}`) | «Tilbakemeldingen ble ikke sendt. Svarene dine er tatt vare på – prøv igjen om litt.» Every answer stays, even after closing and reopening. A retry reuses the same `feedback_id`. |
| **Empty form** | «Svar på minst ett spørsmål før du sender.» Nothing is sent. |
| **Not configured** | A calm info message and no form. Nothing is collected or pretended. |

NO/EN parity: all text is under `bryggeskole.feedback.*` in `modules/i18n.py`.

## Payload contract (schema `kbh.bryggeskole.feedback`, version 1)

Built only by `bryggeskole/feedback.py::build_payload()`. Every field is listed below, and nothing else can reach the receiver.

```json
{
  "schema": "kbh.bryggeskole.feedback",
  "schema_version": 1,
  "feedback_id": "32 hex chars, random per submission (UUID4)",
  "submitted_at": "2026-10-16T12:00:00+00:00",
  "language": "no | en",
  "demo_mode": true,
  "context": {
    "environment": "hjemmebrygger | bryggeri | null",
    "stage": "foundation | kompetent | null",
    "module": "<module id> | null"
  },
  "answers": {
    "start_clarity": "easy | ok | hard",
    "stage_difference": "clear | partly | unclear | not_noticed",
    "unknown_terms": "no | yes",
    "unknown_terms_text": "free text",
    "unsure_next_step": "no | yes",
    "unsure_next_step_text": "free text",
    "text_amount": "too_little | about_right | too_much",
    "questions_quality": "clear | some_unclear | some_tricky",
    "questions_quality_text": "free text",
    "explanation_helped": "yes | partly | no | no_wrong_answers",
    "learned_for_real_brew": "yes | a_little | no",
    "learned_for_real_brew_text": "free text",
    "would_continue": "yes | maybe | no",
    "other_comments": "free text"
  },
  "token": "only if BRYGGESKOLE_FEEDBACK_TOKEN is set"
}
```

- **Answers.** Unanswered questions are left out. A closed answer must be one of its option ids (language-neutral; the UI owns the labels). Free text is stripped and capped at 1000 characters.
- **Context.** This is where the form was opened. Unknown values become `null`. Opened from the overview, `module` is `null`.
- **Never sent:** name, e-mail, IP, user agent, a persistent user or learner id, mastery, progress, session state. `feedback_id` identifies one submission, never a person. It is random, is made when a new form opens in one browser session, and is not stored anywhere by the app.
- **Free text.** People can still type something identifying. The form asks them not to, and the owner should treat the Sheet as possibly containing it (keep it private, delete rows on request).

### Transport

- `send_feedback()` POSTs `application/json; charset=utf-8` with a 10 s timeout, server-side from the Streamlit process. The browser never talks to the endpoint, and the URL is never sent to the browser.
- It returns `sent` **only** for HTTP 2xx with a JSON body `{"ok": true}`, and `not_configured` when no valid https URL is set (no request is made). Every other outcome is `failed`; it never raises.
- Google Apps Script answers a POST with a 302 redirect to `script.googleusercontent.com`. Python's `urllib` follows it with a GET and reads the JSON reply; no extra handling is needed.
- Stdlib only (`urllib`), with no new dependency.

### DEMO_MODE

- The public demo (`DEMO_MODE=1`) **may** send feedback. This is an explicit, owner-approved exception to Demo Mode's no-network habit (see [DEMO_MODE.md](DEMO_MODE.md)).
- Nothing is written to local disk, in demo or not. There is no feedback file, no outbox and no log of answers.
- The payload marks `demo_mode: true`. No mastery or user data goes with it.

## Configuration (environment / Streamlit secrets)

| Name | Required | Meaning |
|---|---|---|
| `BRYGGESKOLE_FEEDBACK_WEBHOOK_URL` | yes, to enable sending | The Web App URL, `https://script.google.com/macros/s/<id>/exec`. Anything that is not an `https://` URL counts as not configured. |
| `BRYGGESKOLE_FEEDBACK_TOKEN` | optional | A shared secret. It is sent in the JSON body, because an Apps Script Web App cannot read request headers. It must equal the Script Property `FEEDBACK_TOKEN`. Recommended, so that only this app can add rows. |

Never commit either value. On Streamlit Community Cloud, root-level entries in the app's **Secrets** are also exposed as environment variables, which is what the app reads.

## Receiver: Google Apps Script

The sample is [bryggeskole_feedback_receiver.gs](bryggeskole_feedback_receiver.gs). It:
- parses the JSON body;
- checks the schema/version, the `feedback_id` format and `answers`;
- checks the token if `FEEDBACK_TOKEN` is set;
- under a script lock, appends **one row per response** to the sheet `Feedback`, creating the header row on first use;
- treats a repeated `feedback_id` as already stored and replies `{"ok": true, "duplicate": true}`, so a retry after a lost reply never duplicates a row;
- writes closed answers only if they are known option ids;
- prefixes free text that starts with `= + - @` with `'`, so it can never become a spreadsheet formula;
- replies `{"ok": true}` or `{"ok": false, "error": "..."}`.

Columns: `received_at, submitted_at, feedback_id, schema_version, language, demo_mode, environment, stage, module`, the 9 closed answers, then the 5 text fields. The order is pinned to `bryggeskole/feedback.py` by `tests/test_bryggeskole_feedback.py`.

## Owner setup after merge

Nothing here is done by the implementation. The owner does it once:

1. **Create the Sheet.** In Google Drive, create a new, private Google Sheet, e.g. «KBH Bryggeskole feedback (#540)». Do not share it publicly.
2. **Add the Apps Script.**
   - In the Sheet: *Extensions → Apps Script*.
   - Replace `Code.gs` with the content of `docs/development/bryggeskole_feedback_receiver.gs` and save.
   - Optional but recommended: *Project Settings → Script Properties → Add*, `FEEDBACK_TOKEN` = a long random string.
3. **Deploy as a Web App.**
   - *Deploy → New deployment → type: Web app*.
   - *Execute as:* **Me**. *Who has access:* **Anyone**. The Streamlit server is not signed in to Google.
   - *Deploy*, authorise the requested Sheet access, and copy the **Web app URL** (ends in `/exec`).
   - After any later script change, use *Manage deployments → Edit → New version*, so the same URL keeps working.
4. **Add the secrets in Streamlit Cloud.**
   - *App → Settings → Secrets*, at root level:
     ```toml
     BRYGGESKOLE_FEEDBACK_WEBHOOK_URL = "https://script.google.com/macros/s/<id>/exec"
     BRYGGESKOLE_FEEDBACK_TOKEN = "<same value as FEEDBACK_TOKEN, or omit both>"
     ```
   - Save. The app restarts.
5. **Send one test response.** Open https://kvernhaug-brygghus.streamlit.app → Bryggeskole → «💬 Gi tilbakemelding på Bryggeskolen». Answer one question and write «TEST – owner setup» in the last field, then *Send*. The app must show «Takk! Tilbakemeldingen din er sendt.»
6. **Confirm that the row arrived.** In the Sheet, tab `Feedback`:
   - a header row plus exactly one new row;
   - `demo_mode` is `TRUE`;
   - `other_comments` contains «TEST – owner setup».
   - Delete the test row (keep the header) before inviting participants.

If step 5 shows «Tilbakemeldingen ble ikke sendt», the app reached no `{"ok": true}`. Check, in order:
1. the URL ends in `/exec` (not `/dev`);
2. *Who has access* is **Anyone**;
3. the token matches on both sides;
4. the latest version is deployed.

Live persistence counts as active only after steps 5–6 have passed.

## Tests

- `tests/test_bryggeskole_feedback.py`: the payload schema and whitelist; no personal or learner data; option validation; text cap; endpoint config; success, HTTP error, network error, timeout, non-JSON and `ok:false` handling; token handling; no disk I/O; receiver column contract.
- `tests/test_ui_bryggeskole_feedback.py`, with AppTest:
  - the entries and NO/EN parity;
  - not configured: no form, nothing sent;
  - success: one POST, honest confirmation, no double send, new submission gets a new id;
  - failure: answers kept, retry with the same id;
  - an empty form is never sent;
  - mastery, progress and the open module are unchanged;
  - DEMO_MODE sends and writes nothing to disk (separate process).
