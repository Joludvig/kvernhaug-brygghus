"""
Bryggeskole fermentation-temperature pilot -- V2-3A interactive content +
questions (issue #95), the first small end-to-end Bryggeskole learning
slice, built on top of the Course Fact Registry's trusted, verified-only
consumer API (bryggeskole/course_fact_registry.py, issue #91).

Scope, stated plainly (mirrors the governing issue):
- one bounded pilot topic -- fermentation temperature fundamentals --
  consuming only FACT-BREW-0001..0003;
- three bilingual (NO/EN) learning chunks, plus at least one concept-check
  and one scenario/application question, each declaring source_claims
  that must resolve to a *verified* Course Fact Registry record;
- a pure, fail-closed content validator plus pure renderer/view-model
  helpers only -- no Streamlit/HTML/web dependency, no persistent mastery
  state, no adaptive scheduling, and no raw-score UX (evaluate_answer()
  below returns per-question correctness/feedback, never an aggregate
  score);
- no new factual claims: every source_claims id is checked against the
  registry's verified-only API (get_verified_record), never the raw
  reader -- a missing claim id and an id that exists but is not verified
  are deliberately indistinguishable here too, mirroring
  course_fact_registry.py's own trusted-boundary semantics.

This module is deliberately stdlib-only and side-effect-free: no network
access, no database, no caching across calls -- every read re-validates
both the pilot content file and the registry file it points at.

`validate_pilot_content()` never raises for a malformed *pilot content*
shape -- it always returns a list of human-readable error strings (empty
list == valid). It does propagate CourseFactRegistryError if the
registry file itself is malformed, since claim resolution has no
meaningful fallback in that case -- a distinct failure category from a
pilot-content shape problem. `read_pilot_file()` is the fail-closed
convenience wrapper: it raises PilotContentError, carrying that same
error list, on anything invalid.
"""
import json
import os
import re

from bryggeskole.course_fact_registry import get_verified_record

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PILOT_PATH = os.path.join(_HERE, "data", "pilot_fermentation_temperature.json")
DEFAULT_REGISTRY_PATH = os.path.join(_HERE, "data", "course_fact_registry.json")

PILOT_SCHEMA_VERSION = 1

LANGUAGES = ("no", "en")

DIFFICULTIES = ("beginner", "intermediate", "advanced")

QUESTION_TYPES = ("concept_check", "scenario")

TOPIC_ID_PATTERN = re.compile(r"^PILOT-[A-Z0-9]+(-[A-Z0-9]+)*$")
CHUNK_ID_PATTERN = re.compile(r"^CHUNK-[A-Z0-9]+-[A-Z]$")
QUESTION_ID_PATTERN = re.compile(r"^Q-[A-Z0-9]+-\d{3}$")
OPTION_ID_PATTERN = re.compile(r"^[a-z0-9]+$")

_DOCUMENT_ALLOWED_FIELDS = frozenset({"schema_version", "topic_id", "chunks", "questions"})

_CHUNK_ALLOWED_FIELDS = frozenset({"id", "source_claims", "text"})

_QUESTION_ALLOWED_FIELDS = frozenset({
    "id", "type", "concepts", "difficulty", "source_claims", "prompt",
    "options", "feedback_correct", "feedback_incorrect",
})

_OPTION_ALLOWED_FIELDS = frozenset({"id", "text", "correct"})

_MIN_OPTIONS_PER_QUESTION = 2


class PilotContentError(ValueError):
    """Raised by read_pilot_file() when the pilot content document fails
    validation. `.errors` carries the complete list of problems found
    (never just the first one), so a caller can report everything wrong
    in one pass instead of fixing issues one at a time."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid pilot content document")


def _is_non_empty_string(value):
    return isinstance(value, str) and value.strip() != ""


def _validate_bilingual_text(value, path, errors):
    """A bilingual text field must be an object with exactly the 'no' and
    'en' keys, each a non-empty string -- NO/EN must exist together from
    the start, never as a later translation pass."""
    if not isinstance(value, dict):
        errors.append(f"{path}: must be an object with 'no' and 'en' keys.")
        return
    unknown = sorted(set(value) - set(LANGUAGES))
    if unknown:
        errors.append(f"{path}: unknown language key(s) {unknown}.")
    for lang in LANGUAGES:
        if not _is_non_empty_string(value.get(lang)):
            errors.append(f"{path}: missing or empty '{lang}' text.")


def _validate_source_claims(value, path, errors, registry_path):
    if not isinstance(value, list) or not value:
        errors.append(f"{path}: 'source_claims' must be a non-empty list.")
        return
    seen = set()
    for i, claim_id in enumerate(value):
        item_path = f"{path}.source_claims[{i}]"
        if not _is_non_empty_string(claim_id):
            errors.append(f"{item_path}: must be a non-empty string.")
            continue
        if claim_id in seen:
            errors.append(f"{item_path}: duplicate claim id {claim_id!r}.")
            continue
        seen.add(claim_id)
        if get_verified_record(registry_path, claim_id) is None:
            errors.append(
                f"{item_path}: claim id {claim_id!r} is not a verified Course Fact "
                f"Registry record (missing or not verified -- these are deliberately "
                f"indistinguishable through the trusted verified-only boundary)."
            )


def _validate_concepts(value, path, errors):
    if not isinstance(value, list) or not value:
        errors.append(f"{path}: 'concepts' must be a non-empty list.")
        return
    seen = set()
    for i, concept in enumerate(value):
        item_path = f"{path}.concepts[{i}]"
        if not _is_non_empty_string(concept):
            errors.append(f"{item_path}: must be a non-empty string.")
            continue
        if concept in seen:
            errors.append(f"{item_path}: duplicate concept {concept!r}.")
            continue
        seen.add(concept)


def _validate_chunk(chunk, index, errors, seen_ids, registry_path):
    path = f"chunks[{index}]"
    if not isinstance(chunk, dict):
        errors.append(f"{path}: chunk must be an object, got {type(chunk).__name__}.")
        return

    unknown = sorted(set(chunk) - _CHUNK_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")

    for field in sorted(_CHUNK_ALLOWED_FIELDS):
        if field not in chunk:
            errors.append(f"{path}: missing required field '{field}'.")

    if "id" in chunk:
        chunk_id = chunk["id"]
        if not isinstance(chunk_id, str) or not CHUNK_ID_PATTERN.match(chunk_id):
            errors.append(f"{path}: invalid id {chunk_id!r} (must match {CHUNK_ID_PATTERN.pattern!r}).")
        elif chunk_id in seen_ids:
            errors.append(f"{path}: duplicate id {chunk_id!r}.")
        else:
            seen_ids.add(chunk_id)

    if "source_claims" in chunk:
        _validate_source_claims(chunk["source_claims"], path, errors, registry_path)

    if "text" in chunk:
        _validate_bilingual_text(chunk["text"], f"{path}.text", errors)


def _validate_option(option, path, errors):
    if not isinstance(option, dict):
        errors.append(f"{path}: option must be an object, got {type(option).__name__}.")
        return None

    unknown = sorted(set(option) - _OPTION_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")

    for field in sorted(_OPTION_ALLOWED_FIELDS):
        if field not in option:
            errors.append(f"{path}: missing required field '{field}'.")

    option_id = option.get("id")
    if "id" in option and (not isinstance(option_id, str) or not OPTION_ID_PATTERN.match(option_id)):
        errors.append(f"{path}: invalid option id {option_id!r} (must match {OPTION_ID_PATTERN.pattern!r}).")

    if "text" in option:
        _validate_bilingual_text(option["text"], f"{path}.text", errors)

    if "correct" in option and not isinstance(option["correct"], bool):
        errors.append(f"{path}: 'correct' must be a boolean.")
        return None

    return option


def _validate_options(value, path, errors):
    if not isinstance(value, list) or len(value) < _MIN_OPTIONS_PER_QUESTION:
        errors.append(f"{path}: 'options' must be a list with at least {_MIN_OPTIONS_PER_QUESTION} entries.")
        return

    seen_ids = set()
    correct_count = 0
    for i, option in enumerate(value):
        option_path = f"{path}.options[{i}]"
        validated = _validate_option(option, option_path, errors)
        if validated is None:
            continue
        option_id = validated.get("id")
        if option_id in seen_ids:
            errors.append(f"{option_path}: duplicate option id {option_id!r}.")
        else:
            seen_ids.add(option_id)
        if validated.get("correct") is True:
            correct_count += 1

    if correct_count != 1:
        errors.append(
            f"{path}: exactly one option must have 'correct': true, found {correct_count}."
        )


def _validate_question(question, index, errors, seen_ids, registry_path):
    path = f"questions[{index}]"
    if not isinstance(question, dict):
        errors.append(f"{path}: question must be an object, got {type(question).__name__}.")
        return

    unknown = sorted(set(question) - _QUESTION_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")

    for field in sorted(_QUESTION_ALLOWED_FIELDS):
        if field not in question:
            errors.append(f"{path}: missing required field '{field}'.")

    if "id" in question:
        question_id = question["id"]
        if not isinstance(question_id, str) or not QUESTION_ID_PATTERN.match(question_id):
            errors.append(f"{path}: invalid id {question_id!r} (must match {QUESTION_ID_PATTERN.pattern!r}).")
        elif question_id in seen_ids:
            errors.append(f"{path}: duplicate id {question_id!r}.")
        else:
            seen_ids.add(question_id)

    if "type" in question and question["type"] not in QUESTION_TYPES:
        errors.append(f"{path}: invalid type {question['type']!r} (must be one of {QUESTION_TYPES}).")

    if "difficulty" in question and question["difficulty"] not in DIFFICULTIES:
        errors.append(f"{path}: invalid difficulty {question['difficulty']!r} (must be one of {DIFFICULTIES}).")

    if "concepts" in question:
        _validate_concepts(question["concepts"], path, errors)

    if "source_claims" in question:
        _validate_source_claims(question["source_claims"], path, errors, registry_path)

    if "prompt" in question:
        _validate_bilingual_text(question["prompt"], f"{path}.prompt", errors)

    if "options" in question:
        _validate_options(question["options"], path, errors)

    if "feedback_correct" in question:
        _validate_bilingual_text(question["feedback_correct"], f"{path}.feedback_correct", errors)

    if "feedback_incorrect" in question:
        _validate_bilingual_text(question["feedback_incorrect"], f"{path}.feedback_incorrect", errors)


def validate_pilot_content(data, registry_path=DEFAULT_REGISTRY_PATH):
    """Validates a parsed pilot content document (the Python object
    `json.load` would produce). Returns a list of human-readable error
    strings -- empty means valid. Never raises for a malformed pilot
    content shape; every problem is collected and reported instead of
    stopping at the first one.

    Every `source_claims` entry (chunk or question) is checked against
    the Course Fact Registry's trusted, verified-only API
    (get_verified_record) at `registry_path` -- never the raw reader --
    so a missing claim id and an id that exists but is not verified both
    fail identically (§18.3 of BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md).
    If the registry file itself is malformed, CourseFactRegistryError
    propagates from here rather than being downgraded to a pilot-content
    error string, since there is no meaningful pilot-content verdict
    without a valid registry to check claims against."""
    errors = []
    if not isinstance(data, dict):
        return [f"Pilot content document must be a JSON object, got {type(data).__name__}."]

    unknown = sorted(set(data) - _DOCUMENT_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"Unknown top-level field(s) {unknown}.")

    if data.get("schema_version") != PILOT_SCHEMA_VERSION:
        errors.append(
            f"'schema_version' must be {PILOT_SCHEMA_VERSION}, got {data.get('schema_version')!r}."
        )

    topic_id = data.get("topic_id")
    if not isinstance(topic_id, str) or not TOPIC_ID_PATTERN.match(topic_id):
        errors.append(f"'topic_id' must match {TOPIC_ID_PATTERN.pattern!r}, got {topic_id!r}.")

    chunks = data.get("chunks")
    if not isinstance(chunks, list):
        errors.append("'chunks' must be a list.")
    else:
        seen_chunk_ids = set()
        for index, chunk in enumerate(chunks):
            _validate_chunk(chunk, index, errors, seen_chunk_ids, registry_path)

    questions = data.get("questions")
    if not isinstance(questions, list):
        errors.append("'questions' must be a list.")
    else:
        seen_question_ids = set()
        for index, question in enumerate(questions):
            _validate_question(question, index, errors, seen_question_ids, registry_path)

    return errors


def read_pilot_file(path=DEFAULT_PILOT_PATH, registry_path=DEFAULT_REGISTRY_PATH):
    """Loads and validates the pilot content JSON file at `path` against
    the Course Fact Registry at `registry_path`. Returns the parsed
    document on success. Raises PilotContentError (fail-closed) on
    invalid JSON or any pilot-content validation failure -- never
    repairs, guesses, or silently drops a bad chunk/question."""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise PilotContentError([f"Invalid JSON: {exc}"]) from exc

    errors = validate_pilot_content(data, registry_path=registry_path)
    if errors:
        raise PilotContentError(errors)
    return data


# ---------------------------------------------------------------------------
# Pure renderer/view-model helpers.
#
# No Streamlit/HTML dependency, no persistence, no scoring/mastery state --
# these only reshape an already-validated pilot document into the smallest
# language-selected shape a future UI surface (Streamlit or web) would need
# to display it. Each function operates on a single already-validated
# chunk/question dict (e.g. from read_pilot_file()) and raises ValueError
# for an unsupported language, rather than silently falling back to one.


def _require_language(language):
    if language not in LANGUAGES:
        raise ValueError(f"Unsupported language {language!r}; must be one of {LANGUAGES}.")


def render_chunk(chunk, language):
    """Returns the given learning chunk as a plain dict with its bilingual
    `text` resolved to a single string for `language`."""
    _require_language(language)
    return {
        "id": chunk["id"],
        "text": chunk["text"][language],
        "source_claims": list(chunk["source_claims"]),
    }


def render_question(question, language):
    """Returns the given question as a plain dict with its bilingual
    `prompt` and option `text` resolved to `language`. Deliberately omits
    `feedback_correct`/`feedback_incorrect` and which option is `correct`
    -- that is revealed only by evaluate_answer() after an answer is
    submitted, not up front alongside the question."""
    _require_language(language)
    return {
        "id": question["id"],
        "type": question["type"],
        "concepts": list(question["concepts"]),
        "difficulty": question["difficulty"],
        "source_claims": list(question["source_claims"]),
        "prompt": question["prompt"][language],
        "options": [
            {"id": option["id"], "text": option["text"][language]}
            for option in question["options"]
        ],
    }


def evaluate_answer(question, selected_option_id, language):
    """Pure feedback helper: given a question (as loaded from the pilot
    content, not the rendered view-model) and a learner's selected option
    id, returns whether it was correct and the matching explanatory
    feedback text in `language`. Returns per-question correctness/
    feedback only -- never an aggregate numeric score; any score/progress
    UX is a later round's decision, out of scope here."""
    _require_language(language)
    options_by_id = {option["id"]: option for option in question["options"]}
    if selected_option_id not in options_by_id:
        raise ValueError(f"Unknown option id {selected_option_id!r} for question {question['id']!r}.")

    is_correct = bool(options_by_id[selected_option_id]["correct"])
    feedback_key = "feedback_correct" if is_correct else "feedback_incorrect"
    return {
        "question_id": question["id"],
        "correct": is_correct,
        "feedback": question[feedback_key][language],
    }
