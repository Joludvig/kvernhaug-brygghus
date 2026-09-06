"""
Bryggeskole -- local JSON persistence for hidden per-concept mastery state
(V2-3B, issue #97).

Persistence scope, stated plainly (mirrors the governing issue):
- local-first, deterministic JSON, no cloud/account/backend;
- deliberately separate from the Course Fact Registry
  (bryggeskole/data/course_fact_registry.json) and pilot content
  (bryggeskole/data/pilot_fermentation_temperature.json) -- both of those
  are shared, versioned course content, checked into git; this file is
  private, per-installation learner state and is stored under `data/`
  instead, the repo's existing convention for local, gitignored user
  state (see modules/pantry.py -- `KVERNHAUG_PANTRY_DIR`), not under
  bryggeskole/data/;
- fail-closed: read_mastery_state() never repairs or silently drops a
  malformed stored document -- it raises MasteryStateError, mirroring
  bryggeskole.mastery.validate_mastery_state() and
  bryggeskole.pilot_fermentation.read_pilot_file()'s own convention;
- no write happens as a side effect of reading or rendering -- a missing
  file is a normal, valid "no state yet" case that returns a fresh
  neutral document, not an error and not a file-creation side effect.

Bryggeskole is deliberately framework-independent, exactly like
bryggeskole/pilot_fermentation.py and bryggeskole/course_fact_registry.py
(no Streamlit/config import). This package is not wired into any UI yet,
so there is nothing for a DEMO_MODE guard to guard against yet -- unlike
modules/**, which .claude/rules/desktop.md requires to respect DEMO_MODE
on every disk write. Wiring bryggeskole into the Streamlit app, and
deciding where DEMO_MODE gating belongs for that call site (ui/), is a
later round's concern, not this pure storage module's.
"""
import json
import os
import uuid

from bryggeskole.mastery import MASTERY_STATE_SCHEMA_VERSION, MasteryStateError, validate_mastery_state

_STATE_DIR_ENV = "KVERNHAUG_BRYGGESKOLE_STATE_DIR"
_STATE_FILENAME = "bryggeskole_mastery_state.json"


def _state_dir():
    """Read fresh on every call -- never frozen at import time -- so
    tests can isolate via the env var before touching any real local
    file, exactly like modules/pantry.py::_pantry_mappe()."""
    return os.getenv(_STATE_DIR_ENV, "data")


def default_state_path():
    return os.path.join(_state_dir(), _STATE_FILENAME)


def neutral_state_document():
    """The explicit empty/neutral document for a learner who has not yet
    answered any pilot question."""
    return {
        "schema_version": MASTERY_STATE_SCHEMA_VERSION,
        "concepts": {},
        "answered_questions": {},
    }


def read_mastery_state(path=None):
    """Returns a fresh neutral_state_document() if no state file exists
    yet -- a normal case, not an error, and reading never creates the
    file. Raises MasteryStateError (fail-closed) on invalid JSON or a
    document that fails bryggeskole.mastery.validate_mastery_state()."""
    path = path or default_state_path()
    if not os.path.exists(path):
        return neutral_state_document()

    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise MasteryStateError([f"Invalid JSON: {exc}"]) from exc

    errors = validate_mastery_state(data)
    if errors:
        raise MasteryStateError(errors)
    return data


def write_mastery_state(document, path=None):
    """Explicit, caller-invoked write only -- never called as a side
    effect of reading or rendering. Validates before writing, so an
    invalid document can never be persisted (it would just fail
    read_mastery_state() straight back on the next read). Writes
    atomically: a temp file is written then swapped in with os.replace()
    (atomic on both POSIX and Windows), the same pattern as
    modules/kbhbrew_storage.py::_skriv_json_atomisk() and
    modules/recipe_storage.py."""
    errors = validate_mastery_state(document)
    if errors:
        raise MasteryStateError(errors)

    path = path or default_state_path()
    directory = os.path.dirname(path)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    tmp_path = f"{path}.tmp_{uuid.uuid4().hex[:8]}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(document, fh, ensure_ascii=False, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
