"""
Bryggeskole -- Kvernhaug's teaching domain (see
docs/development/KBH_CORE_CONTRACT.md Section 1: Bryggeskole is its own
domain, distinct from Core/App-Web/Brew Lab/Soti). This package holds
the Course Fact Registry V1 foundation: a stable-identity, fail-closed
knowledge substrate that later course content, questions and mastery
logic can point back to, plus a narrower, verified-only consumer API
(read_verified_records/get_verified_record/find_verified_records) that
future course code must use for any teaching-facing consumption of
factual content -- see
docs/development/BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md for the full
contract. It also holds the first small interactive learning slice built
on top of that registry, the fermentation-temperature pilot (V2-3A,
issue #95): bilingual (NO/EN) learning chunks and questions whose
source_claims are checked against the registry's verified-only API, plus
pure renderer/view-model helpers -- no course UI, no mastery model, no
adaptive scheduling.
"""
from bryggeskole.course_fact_registry import (
    CLASSIFICATIONS,
    REGISTRY_SCHEMA_VERSION,
    SOURCE_TIERS,
    STATUSES,
    CourseFactRegistryError,
    find_verified_records,
    get_verified_record,
    read_registry_file,
    read_verified_records,
    validate_registry,
)
from bryggeskole.pilot_fermentation import (
    DEFAULT_PILOT_PATH,
    DEFAULT_REGISTRY_PATH,
    DIFFICULTIES,
    PILOT_SCHEMA_VERSION,
    QUESTION_TYPES,
    PilotContentError,
    evaluate_answer,
    read_pilot_file,
    render_chunk,
    render_question,
    validate_pilot_content,
)

__all__ = [
    "CLASSIFICATIONS",
    "REGISTRY_SCHEMA_VERSION",
    "SOURCE_TIERS",
    "STATUSES",
    "CourseFactRegistryError",
    "find_verified_records",
    "get_verified_record",
    "read_registry_file",
    "read_verified_records",
    "validate_registry",
    "DEFAULT_PILOT_PATH",
    "DEFAULT_REGISTRY_PATH",
    "DIFFICULTIES",
    "PILOT_SCHEMA_VERSION",
    "QUESTION_TYPES",
    "PilotContentError",
    "evaluate_answer",
    "read_pilot_file",
    "render_chunk",
    "render_question",
    "validate_pilot_content",
]
