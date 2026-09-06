"""
Course Fact Registry V1 -- pure validator/reader for Bryggeskole's
knowledge substrate. Normative contract:
docs/development/BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md. Machine
policy mirrored here only as code, not restated as data -- there is no
separate machine-readable policy file for this round (unlike
core/status_provenance.json), since the registry document itself
(bryggeskole/data/course_fact_registry.json) already IS the
machine-readable artifact this contract governs.

This module is deliberately stdlib-only and side-effect-free:
- no network access, no database, no vector store, no RAG;
- no automatic fact-checking, no source-tier inference;
- never promotes a record between statuses (draft/reviewed/verified/
  deprecated) -- that remains an explicit, external editorial decision;
- never repairs, guesses, or silently drops a malformed record --
  every problem found is reported, and the caller decides what to do.

`validate_registry()` never raises for a malformed *document* shape
(wrong types, missing keys, wrong JSON) -- it always returns a list of
human-readable error strings describing everything that is wrong
(empty list == valid). `read_registry_file()` is the fail-closed
convenience wrapper: it raises CourseFactRegistryError, carrying that
same full error list, on anything invalid.
"""
import json
import re
import unicodedata

REGISTRY_SCHEMA_VERSION = 1

# FACT-<DOMAIN>-<4 digits>, e.g. FACT-BREW-0001, FACT-TEST-0001. DOMAIN
# is free-form uppercase A-Z/0-9 (not an enumerated list in V1) so a
# future domain does not require a validator change -- only the ID
# grammar itself is enforced here, never uniqueness of "which domains
# exist". "TEST" is the reserved-by-convention domain for synthetic
# fixtures (documented in BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md), not
# a rule this module enforces.
ID_PATTERN = re.compile(r"^FACT-[A-Z0-9]+-\d{4}$")

# The #65 knowledge classifications -- what KIND of statement a record
# is. Deliberately a separate value set from STATUSES below (see
# "Required distinction: classification != verification status" in the
# governing issue) and deliberately NOT reusing Core's own, differently
# shaped claim_evidence_types from core/status_provenance.json: the two
# vocabularies belong to different domains (Core masterdata vs.
# Bryggeskole course knowledge) and are not harmonized in this round,
# mirroring the precedent already documented in
# docs/development/CORE_STATUS_PROVENANCE.md Section 3.1 for the Vault
# Canon model.
CLASSIFICATIONS = (
    "documented_fact",
    "professional_interpretation",
    "practical_experience",
    "hypothesis",
)

# Separate lifecycle/review status axis.
STATUSES = ("draft", "reviewed", "verified", "deprecated")

# The existing #65 source hierarchy. The registry never infers a tier;
# every source must declare one explicitly.
SOURCE_TIERS = ("A", "B", "C", "D")

_DOCUMENT_ALLOWED_FIELDS = frozenset({"schema_version", "records"})

_RECORD_REQUIRED_FIELDS = frozenset({"id", "claim", "classification", "status"})
_RECORD_OPTIONAL_FIELDS = frozenset({"sources", "verified_at", "notes", "concepts", "modules"})
_RECORD_ALLOWED_FIELDS = _RECORD_REQUIRED_FIELDS | _RECORD_OPTIONAL_FIELDS

_SOURCE_REQUIRED_FIELDS = frozenset({"tier", "type"})
_SOURCE_OPTIONAL_FIELDS = frozenset({"ref", "note"})
_SOURCE_ALLOWED_FIELDS = _SOURCE_REQUIRED_FIELDS | _SOURCE_OPTIONAL_FIELDS

# ISO 8601 timestamp, requiring an explicit UTC offset (Z or +HH:MM) --
# "verified at some unspecified local time" is not good enough for a
# claim that is supposed to be independently checkable.
_TIMESTAMP_PATTERN = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

# Heuristic denylist: an AI/model name must never be presented as a
# source. This is intentionally a fixed, documented word/phrase list,
# not an automatic classifier -- see
# BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md for the documented limitation
# that a real-world proper noun colliding with one of these words (e.g.
# a person literally named "Claude") is a known, accepted false-positive
# risk in V1, not a validator bug.
_AI_SOURCE_DENYLIST = (
    "artificial intelligence",
    "large language model",
    "language model",
    "chatgpt",
    "anthropic",
    "openai",
    "claude",
    "gemini",
    "copilot",
    "mistral",
    "llama",
    "bard",
    "soti",
    "llm",
    "gpt",
    "ai",
)

_AI_SOURCE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(term) for term in _AI_SOURCE_DENYLIST) + r")\b"
)


class CourseFactRegistryError(ValueError):
    """Raised by read_registry_file() when a registry document fails
    validation. `.errors` carries the complete list of problems found
    (never just the first one), so a caller can report everything wrong
    in one pass instead of fixing issues one at a time."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid registry document")


def _is_non_empty_string(value):
    return isinstance(value, str) and value.strip() != ""


def _fold_diacritics(value):
    decomposed = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def _looks_like_ai_source(value):
    if not isinstance(value, str):
        return False
    normalized = _fold_diacritics(value).lower()
    return bool(_AI_SOURCE_PATTERN.search(normalized))


def _is_valid_timestamp(value):
    return isinstance(value, str) and bool(_TIMESTAMP_PATTERN.match(value))


def _validate_source(source, path, errors):
    if not isinstance(source, dict):
        errors.append(f"{path}: source must be an object, got {type(source).__name__}.")
        return

    unknown = sorted(set(source) - _SOURCE_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown source field(s) {unknown}.")

    for field in sorted(_SOURCE_REQUIRED_FIELDS):
        if field not in source:
            errors.append(f"{path}: missing required source field '{field}'.")

    if "tier" in source and source["tier"] not in SOURCE_TIERS:
        errors.append(f"{path}: invalid source tier {source['tier']!r} (must be one of {SOURCE_TIERS}).")

    if "type" in source:
        source_type = source["type"]
        if not _is_non_empty_string(source_type):
            errors.append(f"{path}: source 'type' must be a non-empty string.")
        elif _looks_like_ai_source(source_type):
            errors.append(f"{path}: AI/model name {source_type!r} cannot be declared as a source type.")

    if "ref" in source and source["ref"] is not None:
        ref = source["ref"]
        if not _is_non_empty_string(ref):
            errors.append(f"{path}: source 'ref' must be a non-empty string or omitted.")
        elif _looks_like_ai_source(ref):
            errors.append(f"{path}: AI/model name {ref!r} cannot be declared as a source ref.")

    if "note" in source and source["note"] is not None and not isinstance(source["note"], str):
        errors.append(f"{path}: source 'note' must be a string.")


def _validate_reference_collection(value, field_name, path, errors):
    if value is None:
        return
    if not isinstance(value, list):
        errors.append(f"{path}: '{field_name}' must be a list.")
        return
    seen = set()
    for i, item in enumerate(value):
        item_path = f"{path}.{field_name}[{i}]"
        if not _is_non_empty_string(item):
            errors.append(f"{item_path}: must be a non-empty string.")
            continue
        if item in seen:
            errors.append(f"{item_path}: duplicate value {item!r} in '{field_name}'.")
        seen.add(item)


def _validate_record(record, index, errors, seen_ids):
    path = f"records[{index}]"
    if not isinstance(record, dict):
        errors.append(f"{path}: record must be an object, got {type(record).__name__}.")
        return

    unknown = sorted(set(record) - _RECORD_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")

    for field in sorted(_RECORD_REQUIRED_FIELDS):
        if field not in record:
            errors.append(f"{path}: missing required field '{field}'.")

    if "id" in record:
        record_id = record["id"]
        if not isinstance(record_id, str) or not ID_PATTERN.match(record_id):
            errors.append(f"{path}: invalid id {record_id!r} (must match {ID_PATTERN.pattern!r}).")
        elif record_id in seen_ids:
            errors.append(f"{path}: duplicate id {record_id!r}.")
        else:
            seen_ids.add(record_id)

    if "claim" in record and not _is_non_empty_string(record["claim"]):
        errors.append(f"{path}: 'claim' must be a non-empty string.")

    if "classification" in record and record["classification"] not in CLASSIFICATIONS:
        errors.append(
            f"{path}: invalid classification {record['classification']!r} "
            f"(must be one of {CLASSIFICATIONS})."
        )

    status = record.get("status")
    if "status" in record and status not in STATUSES:
        errors.append(f"{path}: invalid status {status!r} (must be one of {STATUSES}).")

    sources = record.get("sources")
    if sources is not None:
        if not isinstance(sources, list):
            errors.append(f"{path}: 'sources' must be a list.")
            sources = []
        else:
            for i, source in enumerate(sources):
                _validate_source(source, f"{path}.sources[{i}]", errors)
    else:
        sources = []

    verified_at = record.get("verified_at")
    if verified_at is not None and not _is_valid_timestamp(verified_at):
        errors.append(f"{path}: 'verified_at' must be an ISO 8601 timestamp with an explicit offset, or omitted.")

    if status == "verified":
        if not sources:
            errors.append(f"{path}: status 'verified' requires at least one source.")
        if not _is_valid_timestamp(verified_at):
            errors.append(f"{path}: status 'verified' requires a valid 'verified_at' timestamp.")

    if "notes" in record and record["notes"] is not None and not isinstance(record["notes"], str):
        errors.append(f"{path}: 'notes' must be a string.")

    _validate_reference_collection(record.get("concepts"), "concepts", path, errors)
    _validate_reference_collection(record.get("modules"), "modules", path, errors)


def validate_registry(data):
    """Validates a parsed registry document (the Python object `json.load`
    would produce). Returns a list of human-readable error strings --
    empty means valid. Never raises for a malformed shape; every
    problem is collected and reported instead of stopping at the
    first one."""
    errors = []
    if not isinstance(data, dict):
        return [f"Registry document must be a JSON object, got {type(data).__name__}."]

    unknown = sorted(set(data) - _DOCUMENT_ALLOWED_FIELDS)
    if unknown:
        errors.append(f"Unknown top-level field(s) {unknown}.")

    if data.get("schema_version") != REGISTRY_SCHEMA_VERSION:
        errors.append(
            f"'schema_version' must be {REGISTRY_SCHEMA_VERSION}, got {data.get('schema_version')!r}."
        )

    records = data.get("records")
    if not isinstance(records, list):
        errors.append("'records' must be a list.")
        return errors

    seen_ids = set()
    for index, record in enumerate(records):
        _validate_record(record, index, errors, seen_ids)

    return errors


def read_registry_file(path):
    """Loads and validates a registry JSON file from `path`. Returns the
    parsed document on success. Raises CourseFactRegistryError
    (fail-closed) on invalid JSON or any validation failure -- never
    repairs, guesses, or silently drops a bad record."""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise CourseFactRegistryError([f"Invalid JSON: {exc}"]) from exc

    errors = validate_registry(data)
    if errors:
        raise CourseFactRegistryError(errors)
    return data
