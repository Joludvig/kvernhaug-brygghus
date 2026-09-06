"""
Bryggeskole -- Kvernhaug's teaching domain (see
docs/development/KBH_CORE_CONTRACT.md Section 1: Bryggeskole is its own
domain, distinct from Core/App-Web/Brew Lab/Soti). This package holds
the Course Fact Registry V1 foundation: a stable-identity, fail-closed
knowledge substrate that later course content, questions and mastery
logic can point back to, plus a narrower, verified-only consumer API
(read_verified_records/get_verified_record/find_verified_records) that
future course code must use for any teaching-facing consumption of
factual content. It contains no course UI, no question engine, no
mastery model and no course content itself -- see
docs/development/BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md for the full
contract.
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
]
