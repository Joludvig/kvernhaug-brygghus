/**
 * Kvernhaug Bryggeskole -- feedback receiver (issue #542). SAMPLE.
 *
 * A Google Apps Script Web App bound to one Google Sheet. It receives the
 * anonymous feedback JSON that bryggeskole/feedback.py POSTs and appends
 * one response as one row. Contract and owner setup:
 * docs/development/BRYGGESKOLE_FEEDBACK.md.
 *
 * Replies are always JSON: {"ok": true} or {"ok": false, "error": "..."}.
 * The app shows "sent" only on {"ok": true}.
 *
 * Optional shared secret: set the Script Property FEEDBACK_TOKEN to the same
 * value as the Streamlit secret BRYGGESKOLE_FEEDBACK_TOKEN. When it is set,
 * a request without the matching "token" field is refused.
 */

var SCHEMA = 'kbh.bryggeskole.feedback';
var SCHEMA_VERSION = 1;
var SHEET_NAME = 'Feedback';
var TEXT_MAX = 1000;

// Answer keys in column order; must match bryggeskole/feedback.py.
var CLOSED = {
  start_clarity: ['easy', 'ok', 'hard'],
  stage_difference: ['clear', 'partly', 'unclear', 'not_noticed'],
  unknown_terms: ['no', 'yes'],
  unsure_next_step: ['no', 'yes'],
  text_amount: ['too_little', 'about_right', 'too_much'],
  questions_quality: ['clear', 'some_unclear', 'some_tricky'],
  explanation_helped: ['yes', 'partly', 'no', 'no_wrong_answers'],
  learned_for_real_brew: ['yes', 'a_little', 'no'],
  would_continue: ['yes', 'maybe', 'no']
};
var TEXT = ['unknown_terms_text', 'unsure_next_step_text', 'questions_quality_text',
            'learned_for_real_brew_text', 'other_comments'];

var HEADER = ['received_at', 'submitted_at', 'feedback_id', 'schema_version', 'language', 'demo_mode',
              'environment', 'stage', 'module']
  .concat(Object.keys(CLOSED)).concat(TEXT);

function doPost(e) {
  try {
    var body = JSON.parse((e && e.postData && e.postData.contents) || '');
    var error = validate_(body);
    if (error) return reply_({ ok: false, error: error });

    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    try {
      var sheet = sheet_();
      if (alreadyStored_(sheet, body.feedback_id)) {
        // A retry of a submission that already arrived: idempotent success.
        return reply_({ ok: true, duplicate: true });
      }
      sheet.appendRow(row_(body));
    } finally {
      lock.releaseLock();
    }
    return reply_({ ok: true });
  } catch (err) {
    return reply_({ ok: false, error: 'invalid request' });
  }
}

function validate_(body) {
  if (!body || typeof body !== 'object') return 'not an object';
  if (body.schema !== SCHEMA || body.schema_version !== SCHEMA_VERSION) return 'unknown schema';
  if (!/^[0-9a-f]{32}$/.test(String(body.feedback_id || ''))) return 'bad feedback_id';
  if (!body.answers || typeof body.answers !== 'object') return 'missing answers';
  var token = PropertiesService.getScriptProperties().getProperty('FEEDBACK_TOKEN');
  if (token && body.token !== token) return 'unauthorized';
  return null;
}

function sheet_() {
  var book = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = book.getSheetByName(SHEET_NAME) || book.insertSheet(SHEET_NAME);
  if (sheet.getLastRow() === 0) sheet.appendRow(HEADER);
  return sheet;
}

function alreadyStored_(sheet, id) {
  var col = HEADER.indexOf('feedback_id') + 1;
  if (sheet.getLastRow() < 2) return false;
  return !!sheet.getRange(2, col, sheet.getLastRow() - 1, 1)
    .createTextFinder(id).matchEntireCell(true).findNext();
}

// Free text must never become a formula in the Sheet.
function safe_(value) {
  var text = String(value == null ? '' : value).slice(0, TEXT_MAX);
  return /^[=+\-@]/.test(text) ? "'" + text : text;
}

function row_(body) {
  var a = body.answers || {};
  var c = body.context || {};
  var row = [new Date().toISOString(), safe_(body.submitted_at), body.feedback_id, body.schema_version,
             safe_(body.language), body.demo_mode === true, safe_(c.environment), safe_(c.stage), safe_(c.module)];
  Object.keys(CLOSED).forEach(function (key) {
    row.push(CLOSED[key].indexOf(a[key]) >= 0 ? a[key] : '');
  });
  TEXT.forEach(function (key) { row.push(safe_(a[key])); });
  return row;
}

function reply_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
