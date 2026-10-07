"""
Test-only seed for the stage UI progress browser smoke
(playwright.bryggeskole-stage-progress.config.js).

Writes one small, known learner history into the mastery-state file under
KVERNHAUG_BRYGGESKOLE_STATE_DIR, so the progress smoke always starts from
the same state, on its own web server, without sharing a state file with
any other browser spec:

- every Foundation question of Råvarer answered correctly (Råvarer
  Foundation worked through);
- the first Foundation question of Gjæring answered correctly (Gjæring
  Foundation in progress);
- nothing else (every other module not started).

The questions come from the canonical stage map and the pilots' own
files, and the answers go through the production mastery API
(apply_answer + write_mastery_state). Nothing is hand-written into the
schema, and no product code changes.

Fail-closed: refuses to run without KVERNHAUG_BRYGGESKOLE_STATE_DIR, when
it points at the repository's own data/ directory, or when a state file
already exists there. The real data/bryggeskole_mastery_state.json can
therefore never be written by this script.

    KVERNHAUG_BRYGGESKOLE_STATE_DIR=<fresh dir> python tests/playwright_streamlit/seed_stage_progress_state.py
"""
import importlib
import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from bryggeskole import course_stage  # noqa: E402
from bryggeskole.mastery import apply_answer  # noqa: E402
from bryggeskole.mastery_store import (  # noqa: E402
    _STATE_DIR_ENV,
    default_state_path,
    neutral_state_document,
    write_mastery_state,
)

# (module, how many of its Foundation questions to answer correctly;
# None = all of them)
SEED = (("raavarer", None), ("gjaring", 1))

# A fixed timestamp keeps the seeded document identical on every run.
SEED_TIME = "2026-01-01T00:00:00+00:00"


class SeedError(Exception):
    pass


def _check_target():
    state_dir = os.environ.get(_STATE_DIR_ENV)
    if not state_dir:
        raise SeedError(f"{_STATE_DIR_ENV} is not set; refusing to seed the default data/ directory.")
    if os.path.normcase(os.path.realpath(state_dir)) == os.path.normcase(os.path.realpath(os.path.join(_REPO_ROOT, "data"))):
        raise SeedError(f"{_STATE_DIR_ENV} points at the repository's data/ directory; refusing.")
    path = default_state_path()
    if os.path.exists(path):
        raise SeedError(f"{path} already exists; the seed only writes into a fresh state directory.")
    return path


def seeded_document():
    stage_map = course_stage.load_stage_map()
    pilot_modules = dict(course_stage.MODULE_PILOTS)
    document = neutral_state_document()
    for module_id, count in SEED:
        pilot = importlib.import_module(pilot_modules[module_id]).read_pilot_file()
        questions = course_stage.items_for_stage(stage_map, module_id, pilot, "foundation")["questions"]
        for question in questions[:count]:
            document = apply_answer(document, question, True, now=SEED_TIME)
    return document


def main():
    try:
        path = _check_target()
    except SeedError as exc:
        print(f"seed_stage_progress_state: {exc}", file=sys.stderr)
        return 2
    os.makedirs(os.path.dirname(path), exist_ok=True)
    write_mastery_state(seeded_document(), path=path)
    print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
