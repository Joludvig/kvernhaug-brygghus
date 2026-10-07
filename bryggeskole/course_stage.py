"""
Bryggeskole course stage map -- S1 of the course stage UI contract
(docs/development/v22_course_stage_ui_contract.md §6, §15; offline, no
GitHub issue yet). Metadata, validation and pure lookups; the Bryggeskole
panel is its only runtime consumer (stage UI S2/S3).

Scope, stated plainly:
- one canonical stage map, bryggeskole/data/course_stage_map.json, that
  places every chunk id and every question id of the 11 canonical
  Bryggeskole modules in exactly one course stage -- instead of a `stage`
  field in eleven lesson files, and instead of chunk-letter lists in UI
  code. The allocation itself comes from the stage allocation contract
  (docs/development/v22_course_stage_allocation_contract.md §C/§D); this
  module only carries and checks it;
- a closed stage set, STAGES = ("foundation", "kompetent"), for the main
  App (curriculum map §6.2.8). Bryggemester and Bryggeri / profesjonell
  are NOT stage values here. A later stage would be added by extending
  STAGES and the map, without changing the API;
- course stage is NOT question `difficulty` (recipe contract §27.2) and
  NOT the legacy Hjemmebrygger/Bryggeri environment (curriculum map
  §6.2.4). The map carries no learner progress and no development
  completeness: those are separate (stage UI contract §7.4).

Fail-closed, like the pilots and the Course Fact Registry:
validate_stage_map() never raises for a malformed map -- it returns the
complete list of human-readable errors (empty list == valid).
load_stage_map() raises StageMapError carrying that list. Nothing is
repaired, guessed or silently dropped. The lookup helpers raise for an
unknown module, item or stage instead of returning a default.

Pure and side-effect free: stdlib only, no Streamlit, no mastery state,
no session state, no file writes. Validation is against pilot documents
the caller passes in (validate_stage_map(data, pilots)); the only file
reads are load_stage_map()'s own map file and, through
load_production_pilots(), the pilots' own read_pilot_file().
"""
import importlib
import json
import os

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_STAGE_MAP_PATH = os.path.join(_HERE, "data", "course_stage_map.json")

STAGE_MAP_SCHEMA_VERSION = 1

# Closed, ordered set for the main App (Foundation -> Kompetent hjemmebrygger).
STAGES = ("foundation", "kompetent")

# The canonical 11 modules in canonical order (curriculum map §6.2.8), with
# the pilot module that owns each one's content. The ids are the same module
# ids ui/bryggeskole_panel.py uses.
MODULE_PILOTS = (
    ("raavarer", "bryggeskole.pilot_raw_materials"),
    ("rengjoring", "bryggeskole.pilot_cleaning_safety"),
    ("metodevalg", "bryggeskole.pilot_method_context"),
    ("mesking", "bryggeskole.pilot_mashing"),
    ("koking", "bryggeskole.pilot_boil_hop"),
    ("kjoling", "bryggeskole.pilot_cool_transfer"),
    ("gjaring", "bryggeskole.pilot_fermentation"),
    ("pakking", "bryggeskole.pilot_package"),
    ("maaling", "bryggeskole.pilot_measurement"),
    ("oppskrift", "bryggeskole.pilot_recipe"),
    ("smak", "bryggeskole.pilot_sensory"),
)
MODULE_ORDER = tuple(module_id for module_id, _ in MODULE_PILOTS)

_DOCUMENT_FIELDS = frozenset({"schema_version", "modules", "notes"})
_MODULE_REQUIRED_FIELDS = frozenset({"module", "topic_id"}) | frozenset(STAGES)
_MODULE_OPTIONAL_FIELDS = frozenset({"notes"})
_STAGE_FIELDS = frozenset({"chunks", "questions"})
_ITEM_KINDS = ("chunks", "questions")


class StageMapError(ValueError):
    """Raised by load_stage_map() when the stage map fails validation.
    `.errors` carries the complete list of problems found."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid course stage map")


def _require_stage(stage):
    if stage not in STAGES:
        raise ValueError(f"Unknown course stage {stage!r}; must be one of {STAGES}.")


def load_production_pilots():
    """Returns {module_id: pilot document} for the 11 canonical modules,
    each read through its own pilot module's read_pilot_file() (which
    validates the content against the Course Fact Registry)."""
    return {
        module_id: importlib.import_module(pilot_module).read_pilot_file()
        for module_id, pilot_module in MODULE_PILOTS
    }


def _validate_module_entry(entry, index, pilots, errors, seen_modules):
    path = f"modules[{index}]"
    if not isinstance(entry, dict):
        errors.append(f"{path}: must be an object, got {type(entry).__name__}.")
        return
    unknown = sorted(set(entry) - _MODULE_REQUIRED_FIELDS - _MODULE_OPTIONAL_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown} (allowed stages: {list(STAGES)}).")
    missing = sorted(_MODULE_REQUIRED_FIELDS - set(entry))
    if missing:
        errors.append(f"{path}: missing field(s) {missing}.")

    module_id = entry.get("module")
    if module_id not in MODULE_ORDER:
        errors.append(f"{path}: unknown module {module_id!r} (must be one of {list(MODULE_ORDER)}).")
        return
    if module_id in seen_modules:
        errors.append(f"{path}: duplicate module {module_id!r}.")
        return
    seen_modules.add(module_id)
    path = f"modules[{index}] ({module_id})"

    pilot = pilots.get(module_id)
    if pilot is None:
        errors.append(f"{path}: no pilot content was given for this module.")
        return
    if entry.get("topic_id") != pilot.get("topic_id"):
        errors.append(
            f"{path}: topic_id {entry.get('topic_id')!r} does not match the pilot's {pilot.get('topic_id')!r}."
        )

    real = {
        "chunks": [c["id"] for c in pilot.get("chunks", [])],
        "questions": [q["id"] for q in pilot.get("questions", [])],
    }
    placed = {kind: {} for kind in _ITEM_KINDS}  # item id -> stage
    for stage in STAGES:
        block = entry.get(stage)
        if block is None:
            continue
        stage_path = f"{path}.{stage}"
        if not isinstance(block, dict):
            errors.append(f"{stage_path}: must be an object with 'chunks' and 'questions'.")
            continue
        bad_fields = sorted(set(block) ^ _STAGE_FIELDS)
        if bad_fields:
            errors.append(f"{stage_path}: must have exactly the fields {sorted(_STAGE_FIELDS)}, got {sorted(block)}.")
        for kind in _ITEM_KINDS:
            ids = block.get(kind)
            if ids is None:
                continue
            if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                errors.append(f"{stage_path}.{kind}: must be a list of id strings.")
                continue
            for item_id in ids:
                if item_id not in real[kind]:
                    errors.append(f"{stage_path}.{kind}: unknown {kind[:-1]} id {item_id!r}.")
                elif item_id in placed[kind]:
                    first = placed[kind][item_id]
                    if first == stage:
                        errors.append(f"{stage_path}.{kind}: duplicate mapping of {item_id!r}.")
                    else:
                        errors.append(f"{path}: {item_id!r} is mapped to both {first!r} and {stage!r}.")
                else:
                    placed[kind][item_id] = stage

    for kind in _ITEM_KINDS:
        for item_id in real[kind]:
            if item_id not in placed[kind]:
                errors.append(f"{path}: {kind[:-1]} {item_id!r} is not mapped to any stage.")


def validate_stage_map(data, pilots):
    """Validates a parsed stage map against `pilots` ({module_id: pilot
    document}). Returns a list of error strings; empty means valid. Never
    raises for a malformed map."""
    if not isinstance(data, dict):
        return [f"Stage map must be a JSON object, got {type(data).__name__}."]
    errors = []
    unknown = sorted(set(data) - _DOCUMENT_FIELDS)
    if unknown:
        errors.append(f"Unknown top-level field(s) {unknown}.")
    if data.get("schema_version") != STAGE_MAP_SCHEMA_VERSION:
        errors.append(f"'schema_version' must be {STAGE_MAP_SCHEMA_VERSION}, got {data.get('schema_version')!r}.")
    modules = data.get("modules")
    if not isinstance(modules, list):
        errors.append("'modules' must be a list.")
        return errors
    seen_modules = set()
    for index, entry in enumerate(modules):
        _validate_module_entry(entry, index, pilots, errors, seen_modules)
    for module_id in MODULE_ORDER:
        if module_id not in seen_modules:
            errors.append(f"Module {module_id!r} is missing from the stage map.")
    order = [e.get("module") for e in modules if isinstance(e, dict)]
    if not errors and order != list(MODULE_ORDER):
        errors.append(f"Modules must be in canonical order {list(MODULE_ORDER)}, got {order}.")
    return errors


def load_stage_map(path=DEFAULT_STAGE_MAP_PATH, pilots=None):
    """Loads and validates the stage map. `pilots` defaults to the
    production pilots (load_production_pilots()). Raises StageMapError
    (fail-closed) on invalid JSON or any validation error."""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise StageMapError([f"Invalid JSON: {exc}"]) from exc
    if pilots is None:
        pilots = load_production_pilots()
    errors = validate_stage_map(data, pilots)
    if errors:
        raise StageMapError(errors)
    return data


# ---------------------------------------------------------------------------
# Lookups on an already-validated map. They raise instead of guessing.


def _module_entry(stage_map, module_id):
    for entry in stage_map["modules"]:
        if entry["module"] == module_id:
            return entry
    raise KeyError(f"Unknown module {module_id!r}.")


def _stage_of(stage_map, module_id, kind, item_id):
    entry = _module_entry(stage_map, module_id)
    for stage in STAGES:
        if item_id in entry[stage][kind]:
            return stage
    raise KeyError(f"{kind[:-1].capitalize()} {item_id!r} is not in the stage map for module {module_id!r}.")


def stage_for_chunk(stage_map, module_id, chunk_id):
    return _stage_of(stage_map, module_id, "chunks", chunk_id)


def stage_for_question(stage_map, module_id, question_id):
    return _stage_of(stage_map, module_id, "questions", question_id)


def module_has_stage(stage_map, module_id, stage):
    """True if the module has at least one chunk or question in `stage`."""
    _require_stage(stage)
    entry = _module_entry(stage_map, module_id)
    return bool(entry[stage]["chunks"] or entry[stage]["questions"])


def items_for_stage(stage_map, module_id, pilot, stage):
    """Returns {"chunks": [...], "questions": [...]}: the pilot's own chunk
    and question dicts that belong to `stage`, in the pilot's order."""
    _require_stage(stage)
    entry = _module_entry(stage_map, module_id)
    chunk_ids = set(entry[stage]["chunks"])
    question_ids = set(entry[stage]["questions"])
    return {
        "chunks": [c for c in pilot["chunks"] if c["id"] in chunk_ids],
        "questions": [q for q in pilot["questions"] if q["id"] in question_ids],
    }


# ---------------------------------------------------------------------------
# Learner progress per (module, stage), derived read-only from a mastery
# document's existing `answered_questions` (stage UI contract §7.2). Pure:
# the caller passes the answered_questions dict in; nothing here reads or
# writes mastery state. Stage UI S3 uses stage_worked_through() for the
# default lens and the "Ready for Stage 2?" guidance; S4 will reuse
# module_stage_status() for its per-card status.

STATUS_NOT_STARTED = "not_started"
STATUS_IN_PROGRESS = "in_progress"
STATUS_WORKED_THROUGH = "worked_through"


def module_stage_status(stage_map, module_id, stage, answered_questions):
    """None when the module has no questions in `stage` (no status there),
    otherwise one of the STATUS_* values:
    - not started: no stage question has an attempt;
    - worked through: every stage question has an attempt and its latest
      recorded answer was correct;
    - in progress: anything in between."""
    _require_stage(stage)
    question_ids = _module_entry(stage_map, module_id)[stage]["questions"]
    if not question_ids:
        return None
    answered_questions = answered_questions or {}
    tried = [qid for qid in question_ids if (answered_questions.get(qid) or {}).get("attempts", 0) > 0]
    if not tried:
        return STATUS_NOT_STARTED
    if len(tried) == len(question_ids) and all(answered_questions[qid].get("last_correct") is True
                                               for qid in question_ids):
        return STATUS_WORKED_THROUGH
    return STATUS_IN_PROGRESS


def stage_worked_through(stage_map, stage, answered_questions):
    """True when every module that has questions in `stage` is worked
    through. Learner guidance only -- never a qualification, and never
    about development completeness (stage UI contract §7.3, §7.4)."""
    statuses = [module_stage_status(stage_map, module_id, stage, answered_questions)
                for module_id in MODULE_ORDER]
    statuses = [status for status in statuses if status is not None]
    return bool(statuses) and all(status == STATUS_WORKED_THROUGH for status in statuses)
