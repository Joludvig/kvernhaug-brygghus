"""
Bryggeskole -- hidden per-concept mastery state, V2-3B (issue #97), built on
top of the V2-3A fermentation pilot (bryggeskole/pilot_fermentation.py,
issue #95). Adds the smallest hidden learner-state layer needed to remember
concept mastery signals across answered questions, without turning the
pilot into a score-first quiz system.

Scope, stated plainly (mirrors the governing issue):
- one V1 mastery model per concept id: mastery, confidence, attempts,
  last_tested -- a small, explicit, documented representation, not a
  general-purpose learner-modelling framework;
- a pure, deterministic update function (update_concept_state()) plus a
  pure orchestrator (apply_answer()) that updates every concept a given
  question declares -- no hidden wall-clock dependency, no randomness, no
  persistence, no Streamlit/HTML/web dependency;
- a pure helper (mastery_label()) mapping hidden state to simple NO/EN
  learner-facing labels -- never a raw x/100 score or a grade;
- no adaptive repetition scheduling, no spaced-repetition engine, no
  aggregate course grade -- all explicitly out of scope for this round.

Identity: concept state is keyed by the same concept id strings pilot
questions already declare in their `concepts` list
(bryggeskole/pilot_fermentation.py's `_validate_concepts()`) -- no second
concept namespace is invented here. Question ids (bryggeskole/
pilot_fermentation.py's `QUESTION_ID_PATTERN`) are reused as the key for
per-question first-attempt tracking in `answered_questions`.

This module is deliberately stdlib-only and side-effect-free, exactly like
its siblings: no network access, no database, no file I/O (that lives in
bryggeskole/mastery_store.py), no caching across calls.
"""
import re

MASTERY_STATE_SCHEMA_VERSION = 1

LANGUAGES = ("no", "en")

MASTERY_MIN, MASTERY_MAX = 0.0, 1.0
CONFIDENCE_MIN, CONFIDENCE_MAX = 0.0, 1.0

NEUTRAL_MASTERY = 0.0
NEUTRAL_CONFIDENCE = 0.0

# Update weights (V1). Deliberately simple and documented rather than
# pseudo-scientifically precise:
#
# - A correct answer moves mastery/confidence a fixed *fraction of the
#   remaining headroom* towards the upper bound (never an additive raw
#   point), so repeated correct answers have naturally diminishing
#   returns without a separate, second cap rule.
# - A first-attempt correct answer uses a larger fraction
#   (MASTERY_GAIN_FIRST_ATTEMPT) than a correct answer that follows an
#   earlier miss on the same question (MASTERY_GAIN_RECOVERY) -- i.e.
#   recovery always improves mastery less strongly than a clean first
#   attempt, for any starting mastery value, because the fraction itself
#   is smaller.
# - An incorrect answer never increases mastery (left unchanged) -- it
#   only reduces confidence, reflecting reduced certainty in the
#   concept without erasing prior demonstrated understanding.
MASTERY_GAIN_FIRST_ATTEMPT = 0.35
MASTERY_GAIN_RECOVERY = 0.15
CONFIDENCE_GAIN_CORRECT = 0.30
CONFIDENCE_LOSS_INCORRECT = 0.25

_ROUND_NDIGITS = 4

# Same grammar as bryggeskole/course_fact_registry.py's own
# `_TIMESTAMP_PATTERN` (ISO 8601, explicit offset or literal 'Z' required)
# -- duplicated rather than imported, matching this codebase's established
# per-module independence convention (see e.g. .github/scripts/
# chief_retry_signal.py duplicating chief_ready_signal.py's marker
# construction).
_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

_CONCEPT_ALLOWED_FIELDS = frozenset({"mastery", "confidence", "attempts", "last_tested"})
_QUESTION_ATTEMPT_ALLOWED_FIELDS = frozenset({"attempts", "last_correct", "last_tested"})
_DOCUMENT_ALLOWED_FIELDS = frozenset({"schema_version", "concepts", "answered_questions"})

# Learner-facing NO/EN labels (issue #97's own example wording). Exact
# thresholds/wording are an implementation choice; what is fixed is that
# they are deterministic, tested, and never a raw x/100 score or a grade.
# Ordered highest-threshold-first; the first threshold `mastery` meets or
# exceeds wins.
LABEL_THRESHOLDS = (
    (0.75, {"no": "Sterkt område", "en": "Strong area"}),
    (0.5, {"no": "God forståelse", "en": "Good understanding"}),
    (0.25, {"no": "På god vei", "en": "On the way"}),
)
LABEL_FALLBACK = {"no": "Bør repeteres", "en": "Should repeat"}


class MasteryStateError(ValueError):
    """Raised by bryggeskole.mastery_store.read_mastery_state() when a
    stored mastery state document fails validation. `.errors` carries the
    complete list of problems found (never just the first one), mirroring
    bryggeskole.pilot_fermentation.PilotContentError and
    bryggeskole.course_fact_registry.CourseFactRegistryError."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid mastery state document")


def _is_non_empty_string(value):
    return isinstance(value, str) and value.strip() != ""


def _is_valid_timestamp(value):
    return isinstance(value, str) and bool(_TIMESTAMP_PATTERN.match(value))


def _is_bounded_number(value, lo, hi):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and lo <= value <= hi


def _is_non_negative_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _clamp(value, lo, hi):
    return max(lo, min(hi, value))


def _require_language(language):
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}; must be one of {LANGUAGES}.")


def neutral_concept_state():
    """The explicit neutral baseline a concept is created from the first
    time it is ever referenced by an answered question -- never a guessed
    or partially-informed starting point."""
    return {
        "mastery": NEUTRAL_MASTERY,
        "confidence": NEUTRAL_CONFIDENCE,
        "attempts": 0,
        "last_tested": None,
    }


def update_concept_state(previous, correct, first_attempt, now):
    """Pure, deterministic per-concept update. `previous` is either an
    existing concept-state dict (mastery/confidence/attempts/last_tested)
    or None (unknown concept -- created safely from neutral_concept_state()).
    `now` is the caller-supplied current timestamp (ISO 8601, explicit
    offset) -- this function never reads the wall clock itself, so it stays
    trivially pure/testable.

    Required behavior (issue #97):
    - a correct first-attempt answer increases mastery/confidence;
    - an incorrect answer never increases mastery;
    - a correct answer after an earlier miss on the same question may
      recover mastery, but less strongly than a first-attempt correct
      answer (MASTERY_GAIN_RECOVERY < MASTERY_GAIN_FIRST_ATTEMPT);
    - attempts increments by exactly 1;
    - last_tested is set to the supplied `now`;
    - mastery/confidence remain within [MASTERY_MIN, MASTERY_MAX] /
      [CONFIDENCE_MIN, CONFIDENCE_MAX].
    """
    if not _is_valid_timestamp(now):
        raise ValueError(f"'now' must be an ISO 8601 timestamp with explicit offset, got {now!r}.")

    base = previous if previous is not None else neutral_concept_state()
    mastery = base["mastery"]
    confidence = base["confidence"]
    attempts = base["attempts"]

    if correct:
        gain = MASTERY_GAIN_FIRST_ATTEMPT if first_attempt else MASTERY_GAIN_RECOVERY
        mastery = mastery + gain * (MASTERY_MAX - mastery)
        confidence = confidence + CONFIDENCE_GAIN_CORRECT * (CONFIDENCE_MAX - confidence)
    else:
        confidence = confidence - CONFIDENCE_LOSS_INCORRECT * (confidence - CONFIDENCE_MIN)
        # mastery is deliberately left unchanged here -- an incorrect
        # answer never increases it, and this V1 model does not decay it
        # either (no "forgetting" model yet -- that would be an adaptive-
        # scheduling concern, explicitly out of scope for this round).

    mastery = round(_clamp(mastery, MASTERY_MIN, MASTERY_MAX), _ROUND_NDIGITS)
    confidence = round(_clamp(confidence, CONFIDENCE_MIN, CONFIDENCE_MAX), _ROUND_NDIGITS)

    return {
        "mastery": mastery,
        "confidence": confidence,
        "attempts": attempts + 1,
        "last_tested": now,
    }


def apply_answer(state_document, question, correct, now):
    """Pure orchestrator: given a previous whole mastery-state document
    (schema_version/concepts/answered_questions -- typically loaded via
    bryggeskole.mastery_store.read_mastery_state()), a pilot `question`
    dict (must carry a non-empty 'id' and non-empty 'concepts' list, e.g.
    from bryggeskole.pilot_fermentation), whether the learner's answer was
    `correct`, and the caller-supplied `now` timestamp, returns a NEW
    document with every concept the question declares updated via
    update_concept_state() -- never mutates `state_document` in place.

    `first_attempt` for update_concept_state() is derived here, purely
    from whether `question['id']` already appears in
    `state_document['answered_questions']` -- reusing the pilot's own
    stable question id rather than inventing a second identity namespace.
    """
    question_id = question["id"]
    if not _is_non_empty_string(question_id):
        raise ValueError(f"question 'id' must be a non-empty string, got {question_id!r}.")

    concepts = question.get("concepts")
    if not isinstance(concepts, list) or not concepts:
        raise ValueError(f"question {question_id!r} must declare a non-empty 'concepts' list.")

    answered_questions = dict(state_document.get("answered_questions") or {})
    first_attempt = question_id not in answered_questions

    concept_states = dict(state_document.get("concepts") or {})
    for concept_id in concepts:
        concept_states[concept_id] = update_concept_state(
            concept_states.get(concept_id), correct=correct, first_attempt=first_attempt, now=now,
        )

    previous_attempt = answered_questions.get(question_id, {"attempts": 0})
    answered_questions[question_id] = {
        "attempts": previous_attempt.get("attempts", 0) + 1,
        "last_correct": bool(correct),
        "last_tested": now,
    }

    return {
        "schema_version": state_document.get("schema_version", MASTERY_STATE_SCHEMA_VERSION),
        "concepts": concept_states,
        "answered_questions": answered_questions,
    }


def mastery_label(concept_state, language):
    """Pure helper mapping a hidden concept-state dict to a simple,
    deterministic NO/EN learner-facing label -- never the raw `mastery`/
    `confidence` numbers, a raw x/100 score, or a grade like F/3 of 10."""
    _require_language(language)
    mastery = concept_state["mastery"]
    for threshold, labels in LABEL_THRESHOLDS:
        if mastery >= threshold:
            return labels[language]
    return LABEL_FALLBACK[language]


def _validate_concept_entry(concept_id, entry, errors):
    path = f"concepts[{concept_id!r}]"
    if not _is_non_empty_string(concept_id):
        errors.append(f"concepts: invalid concept id {concept_id!r} (must be a non-empty string).")

    if not isinstance(entry, dict):
        errors.append(f"{path}: entry must be an object, got {type(entry).__name__}.")
        return

    unknown = sorted(set(entry) - _CONCEPT_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")

    for field in sorted(_CONCEPT_ALLOWED_FIELDS):
        if field not in entry:
            errors.append(f"{path}: missing required field '{field}'.")

    if "mastery" in entry and not _is_bounded_number(entry["mastery"], MASTERY_MIN, MASTERY_MAX):
        errors.append(f"{path}: 'mastery' must be a number in [{MASTERY_MIN}, {MASTERY_MAX}], got {entry['mastery']!r}.")

    if "confidence" in entry and not _is_bounded_number(entry["confidence"], CONFIDENCE_MIN, CONFIDENCE_MAX):
        errors.append(
            f"{path}: 'confidence' must be a number in [{CONFIDENCE_MIN}, {CONFIDENCE_MAX}], got {entry['confidence']!r}."
        )

    attempts_ok = "attempts" in entry and _is_non_negative_int(entry["attempts"])
    if "attempts" in entry and not attempts_ok:
        errors.append(f"{path}: 'attempts' must be a non-negative integer, got {entry['attempts']!r}.")

    if "last_tested" not in entry:
        return
    last_tested = entry["last_tested"]
    if attempts_ok and entry["attempts"] == 0:
        if last_tested is not None:
            errors.append(f"{path}: 'last_tested' must be null when 'attempts' is 0, got {last_tested!r}.")
    elif last_tested is None or not _is_valid_timestamp(last_tested):
        errors.append(
            f"{path}: 'last_tested' must be an ISO 8601 timestamp with explicit offset "
            f"(null only allowed when 'attempts' is 0), got {last_tested!r}."
        )


def _validate_question_attempt_entry(question_id, entry, errors):
    path = f"answered_questions[{question_id!r}]"
    if not _is_non_empty_string(question_id):
        errors.append(f"answered_questions: invalid question id {question_id!r} (must be a non-empty string).")

    if not isinstance(entry, dict):
        errors.append(f"{path}: entry must be an object, got {type(entry).__name__}.")
        return

    unknown = sorted(set(entry) - _QUESTION_ATTEMPT_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")

    for field in sorted(_QUESTION_ATTEMPT_ALLOWED_FIELDS):
        if field not in entry:
            errors.append(f"{path}: missing required field '{field}'.")

    if "attempts" in entry:
        if not _is_non_negative_int(entry["attempts"]) or entry["attempts"] < 1:
            errors.append(f"{path}: 'attempts' must be a positive integer (>= 1) for an answered question, got {entry['attempts']!r}.")

    if "last_correct" in entry and not isinstance(entry["last_correct"], bool):
        errors.append(f"{path}: 'last_correct' must be a boolean, got {entry['last_correct']!r}.")

    if "last_tested" in entry and not _is_valid_timestamp(entry["last_tested"]):
        errors.append(
            f"{path}: 'last_tested' must be an ISO 8601 timestamp with explicit offset, got {entry['last_tested']!r}."
        )


def validate_mastery_state(data):
    """Validates a parsed mastery-state document (the Python object
    `json.load` would produce). Returns a list of human-readable error
    strings -- empty means valid. Never raises; every problem is collected
    and reported instead of stopping at the first one, exactly like
    bryggeskole.pilot_fermentation.validate_pilot_content(). Fail-closed
    V1 policy: any unrecognised top-level, concept-entry, or
    answered_questions-entry field is rejected rather than silently
    ignored."""
    errors = []
    if not isinstance(data, dict):
        return [f"Mastery state document must be a JSON object, got {type(data).__name__}."]

    unknown = sorted(set(data) - _DOCUMENT_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"Unknown top-level field(s) {unknown}.")

    if data.get("schema_version") != MASTERY_STATE_SCHEMA_VERSION:
        errors.append(f"'schema_version' must be {MASTERY_STATE_SCHEMA_VERSION}, got {data.get('schema_version')!r}.")

    concepts = data.get("concepts")
    if not isinstance(concepts, dict):
        errors.append("'concepts' must be an object keyed by concept id.")
    else:
        for concept_id, entry in concepts.items():
            _validate_concept_entry(concept_id, entry, errors)

    if "answered_questions" in data:
        answered_questions = data["answered_questions"]
        if not isinstance(answered_questions, dict):
            errors.append("'answered_questions' must be an object keyed by question id.")
        else:
            for question_id, entry in answered_questions.items():
                _validate_question_attempt_entry(question_id, entry, errors)

    return errors
