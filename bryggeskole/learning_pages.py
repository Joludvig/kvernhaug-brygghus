"""
Bryggeskole learning pages -- the learner-facing presentation unit of a
stage lesson (owner acceptance #508; docs/development/
v22_course_stage_ui_contract.md §5.1).

Two separate concepts, stated plainly:
- the authored CHUNK stays the content and provenance unit: its id, text,
  source_claims and basis live in the pilot, and its course stage lives in
  bryggeskole/data/course_stage_map.json. Nothing here changes either;
- the learning PAGE is what one lesson screen shows: one or more ADJACENT
  chunks of one (module, stage), with one real bilingual page title. The
  grouping is reviewable data in bryggeskole/data/course_learning_pages.json,
  never UI code. It carries no fact, stage, question or mastery truth.

Fail-closed, like the stage map: validate_learning_pages() never raises for
a malformed map -- it returns the complete list of human-readable errors
(empty list == valid). load_learning_pages() raises LearningPagesError
carrying that list. Nothing is repaired, regrouped or silently dropped.
The panel falls back to one chunk per screen when loading fails; the
production-map test keeps that fallback from hiding stale data.

Headings: split_heading() lifts an authored leading «**Heading.**» prefix
out of a chunk body; page_sections() then suppresses it when it equals the
page title and otherwise turns it into a subheading. Only a chunk without
such a prefix may get an explicit map subheading. No heading is guessed.

Pure and side-effect free: stdlib only, no Streamlit, no session or mastery
state, no file writes. The only file reads are load_learning_pages()'s own
map file and, when the caller passes none, the production stage map and
pilots through bryggeskole.course_stage.
"""
import json
import os
import re

from bryggeskole import course_stage

_HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEARNING_PAGES_PATH = os.path.join(_HERE, "data", "course_learning_pages.json")

LEARNING_PAGES_SCHEMA_VERSION = 1
LANGUAGES = ("no", "en")

_DOCUMENT_FIELDS = frozenset({"schema_version", "notes", "pages"})
_PAGE_REQUIRED_FIELDS = frozenset({"id", "module", "stage", "title", "chunks"})
_PAGE_OPTIONAL_FIELDS = frozenset({"subheadings"})

# An authored chunk heading: a bold run at the very start of the text.
_HEADING_PREFIX = re.compile(r"^\*\*(.+?)\*\*\s*")


class LearningPagesError(ValueError):
    """Raised by load_learning_pages() when the page map fails validation.
    `.errors` carries the complete list of problems found."""

    def __init__(self, errors):
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) if self.errors else "invalid learning page map")


# ---------------------------------------------------------------------------
# Headings


def split_heading(text):
    """(heading, body) for an authored chunk text. `heading` is the leading
    «**…**» prefix without its trailing full stop, or None when the text has
    no such prefix (then `body` is the text unchanged)."""
    match = _HEADING_PREFIX.match(text)
    if match is None:
        return None, text
    return _clean_heading(match.group(1)), text[match.end():]


def _clean_heading(heading):
    return heading.strip().rstrip(".").strip()


def same_heading(a, b):
    """True when two headings say the same thing (case, surrounding space
    and a trailing full stop ignored; «?» and wording are significant)."""
    return _clean_heading(a).casefold() == _clean_heading(b).casefold()


def page_sections(page, texts, language):
    """The body of one page, in chunk order: a list of (chunk_id, subheading
    or None, body). `texts` maps each chunk id on the page to its text in
    `language`. A chunk's authored heading that equals the page title is
    dropped (the title already shows it); any other authored heading becomes
    the chunk's subheading; a chunk without one may take the map's explicit
    subheading."""
    title = page["title"][language]
    explicit = page.get("subheadings") or {}
    sections = []
    for chunk_id in page["chunks"]:
        heading, body = split_heading(texts[chunk_id])
        if heading is not None:
            subheading = None if same_heading(heading, title) else heading
        else:
            subheading = (explicit.get(chunk_id) or {}).get(language)
        sections.append((chunk_id, subheading, body))
    return sections


# ---------------------------------------------------------------------------
# Validation


def _is_text(value):
    return isinstance(value, str) and value.strip() != ""


def _bilingual_errors(value, path):
    if not isinstance(value, dict) or set(value) != set(LANGUAGES):
        return [f"{path}: must be an object with exactly {list(LANGUAGES)}."]
    return [f"{path}.{lang}: must be a non-empty string." for lang in LANGUAGES if not _is_text(value[lang])]


def _chunk_index(pilots):
    """chunk id -> (module id, chunk dict) and the set of every question id."""
    chunks, questions = {}, set()
    for module_id, pilot in pilots.items():
        for chunk in pilot.get("chunks", []):
            chunks[chunk["id"]] = (module_id, chunk)
        questions.update(q["id"] for q in pilot.get("questions", []))
    return chunks, questions


def _validate_page(page, index, stage_chunks, chunk_index, question_ids, errors):
    """Field-level checks of one page. Returns (module, stage) when both are
    valid, else None. Coverage and order are checked per stage afterwards."""
    path = f"pages[{index}]"
    if not isinstance(page, dict):
        errors.append(f"{path}: must be an object, got {type(page).__name__}.")
        return None
    if _is_text(page.get("id")):
        path = f"pages[{index}] ({page['id']})"
    unknown = sorted(set(page) - _PAGE_REQUIRED_FIELDS - _PAGE_OPTIONAL_FIELDS)
    if unknown:
        errors.append(f"{path}: unknown field(s) {unknown}.")
    missing = sorted(_PAGE_REQUIRED_FIELDS - set(page))
    if missing:
        errors.append(f"{path}: missing field(s) {missing}.")

    module_id, stage = page.get("module"), page.get("stage")
    key = None
    if module_id not in course_stage.MODULE_ORDER:
        errors.append(f"{path}: unknown module {module_id!r}.")
    elif stage not in course_stage.STAGES:
        errors.append(f"{path}: unknown stage {stage!r} (must be one of {list(course_stage.STAGES)}).")
    elif not stage_chunks[(module_id, stage)]:
        errors.append(f"{path}: {module_id!r} has no chunks in stage {stage!r}; a page there would be invented.")
    else:
        key = (module_id, stage)

    if "title" in page:
        errors.extend(_bilingual_errors(page["title"], f"{path}.title"))
    title_ok = "title" in page and not _bilingual_errors(page["title"], "")

    chunk_ids = page.get("chunks")
    if not isinstance(chunk_ids, list) or not chunk_ids or not all(_is_text(c) for c in chunk_ids):
        if "chunks" in page:
            errors.append(f"{path}.chunks: must be a non-empty list of chunk id strings.")
        return key
    for position, chunk_id in enumerate(chunk_ids):
        if chunk_id in question_ids:
            errors.append(f"{path}.chunks: {chunk_id!r} is a question id; pages hold chunks only.")
            continue
        if chunk_id not in chunk_index:
            errors.append(f"{path}.chunks: unknown chunk id {chunk_id!r}.")
            continue
        owner, chunk = chunk_index[chunk_id]
        if key is not None and owner != module_id:
            errors.append(f"{path}.chunks: {chunk_id!r} belongs to module {owner!r}, not {module_id!r}.")
            continue
        if key is not None:
            chunk_stage = next(s for s in course_stage.STAGES if chunk_id in stage_chunks[(owner, s)])
            if chunk_stage != stage:
                errors.append(f"{path}.chunks: {chunk_id!r} is a {chunk_stage!r} chunk; no cross-stage grouping.")
        headings = {lang: split_heading(chunk["text"][lang])[0] for lang in LANGUAGES}
        if (headings["no"] is None) != (headings["en"] is None):
            errors.append(f"{path}.chunks: {chunk_id!r} has an authored heading in only one language.")
        elif title_ok and headings["no"] is not None:
            equal = [same_heading(headings[lang], page["title"][lang]) for lang in LANGUAGES]
            if equal[0] != equal[1]:
                errors.append(f"{path}: the heading of {chunk_id!r} equals the page title in only one language.")
            elif equal[0] and position != 0:
                errors.append(f"{path}: {chunk_id!r} repeats the page title but is not the page's first chunk.")

    subheadings = page.get("subheadings")
    if subheadings is not None:
        if not isinstance(subheadings, dict) or not subheadings:
            errors.append(f"{path}.subheadings: must be a non-empty object keyed by chunk id.")
        else:
            for chunk_id, value in subheadings.items():
                sub_path = f"{path}.subheadings.{chunk_id}"
                if chunk_id not in chunk_ids:
                    errors.append(f"{sub_path}: not a chunk on this page.")
                    continue
                errors.extend(_bilingual_errors(value, sub_path))
                if chunk_id in chunk_index and split_heading(chunk_index[chunk_id][1]["text"]["no"])[0] is not None:
                    errors.append(f"{sub_path}: the chunk already has an authored heading; no double heading.")
    return key


def validate_learning_pages(data, stage_map, pilots):
    """Validates a parsed page map against a VALID stage map and `pilots`
    ({module_id: pilot document}). Returns a list of error strings; empty
    means valid. Never raises for a malformed map."""
    if not isinstance(data, dict):
        return [f"Learning page map must be a JSON object, got {type(data).__name__}."]
    errors = []
    unknown = sorted(set(data) - _DOCUMENT_FIELDS)
    if unknown:
        errors.append(f"Unknown top-level field(s) {unknown}.")
    if data.get("schema_version") != LEARNING_PAGES_SCHEMA_VERSION:
        errors.append(f"'schema_version' must be {LEARNING_PAGES_SCHEMA_VERSION}, got {data.get('schema_version')!r}.")
    pages = data.get("pages")
    if not isinstance(pages, list):
        errors.append("'pages' must be a list.")
        return errors

    chunk_index, question_ids = _chunk_index(pilots)
    stage_chunks = {(entry["module"], stage): entry[stage]["chunks"]
                    for entry in stage_map["modules"] for stage in course_stage.STAGES}
    keys = []  # (module, stage) per page, None where invalid
    seen_ids = set()
    for index, page in enumerate(pages):
        keys.append(_validate_page(page, index, stage_chunks, chunk_index, question_ids, errors))
        page_id = page.get("id") if isinstance(page, dict) else None
        if isinstance(page_id, str):
            if page_id in seen_ids:
                errors.append(f"pages[{index}]: duplicate page id {page_id!r}.")
            seen_ids.add(page_id)

    # Deterministic order: stages appear as contiguous runs, in canonical
    # module order and Foundation before Kompetent, and page ids number
    # each run 1..n.
    expected_keys = [(m, s) for m in course_stage.MODULE_ORDER for s in course_stage.STAGES
                     if stage_chunks[(m, s)]]
    runs = []
    for key in keys:
        if key is not None and (not runs or runs[-1] != key):
            runs.append(key)
    for key in expected_keys:
        if key not in runs:
            errors.append(f"No pages for {key[0]!r} / {key[1]!r}, which has chunks in that stage.")
    if len(set(runs)) != len(runs):
        errors.append("Each (module, stage) must be one contiguous run of pages.")
    elif [k for k in expected_keys if k in runs] != runs:
        errors.append(f"Pages must follow canonical module and stage order {expected_keys}.")

    for module_id, stage in expected_keys:
        stage_pages = [p for p, k in zip(pages, keys) if k == (module_id, stage)]
        if not stage_pages:
            continue
        for n, page in enumerate(stage_pages, 1):
            if page.get("id") != f"{module_id}.{stage}.{n}":
                errors.append(f"Page {page.get('id')!r}: expected id {module_id}.{stage}.{n!s} (position in its stage).")
        mapped = [c for p in stage_pages if isinstance(p.get("chunks"), list) for c in p["chunks"]]
        canonical = [c["id"] for c in course_stage.items_for_stage(stage_map, module_id, pilots[module_id], stage)["chunks"]]
        if mapped != canonical:
            missing = [c for c in canonical if c not in mapped]
            duplicate = sorted({c for c in mapped if mapped.count(c) > 1})
            errors.append(
                f"{module_id!r} / {stage!r}: pages must concatenate to the stage chunks exactly, in order; "
                f"expected {canonical}, got {mapped} (missing {missing}, duplicate {duplicate})."
            )
    return errors


def load_learning_pages(path=DEFAULT_LEARNING_PAGES_PATH, stage_map=None, pilots=None):
    """Loads and validates the page map. `pilots` defaults to the production
    pilots and `stage_map` to the production stage map (loaded with those
    pilots). Raises LearningPagesError (fail-closed) on invalid JSON or any
    validation error, and the stage map's own StageMapError for a bad map."""
    with open(path, "r", encoding="utf-8") as fh:
        try:
            data = json.load(fh)
        except json.JSONDecodeError as exc:
            raise LearningPagesError([f"Invalid JSON: {exc}"]) from exc
    if pilots is None:
        pilots = course_stage.load_production_pilots()
    if stage_map is None:
        stage_map = course_stage.load_stage_map(pilots=pilots)
    errors = validate_learning_pages(data, stage_map, pilots)
    if errors:
        raise LearningPagesError(errors)
    return data


def pages_for_stage(learning_pages, module_id, stage):
    """The pages of one (module, stage) of an already-validated map, in
    order; an empty list for a stage without chunks."""
    if stage not in course_stage.STAGES:
        raise ValueError(f"Unknown course stage {stage!r}; must be one of {course_stage.STAGES}.")
    return [p for p in learning_pages["pages"] if p["module"] == module_id and p["stage"] == stage]
