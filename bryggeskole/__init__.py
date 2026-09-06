"""
Bryggeskole -- Kvernhaug's teaching domain (see
docs/development/KBH_CORE_CONTRACT.md Section 1: Bryggeskole is its own
domain, distinct from Core/App-Web/Brew Lab/Soti). This package holds
the Course Fact Registry V1 foundation only: a stable-identity,
fail-closed knowledge substrate that later course content, questions
and mastery logic can point back to. It contains no course UI, no
question engine, no mastery model and no course content itself -- see
docs/development/BRYGGESKOLE_COURSE_FACT_REGISTRY_V1.md for the full
contract.
"""
from bryggeskole.course_fact_registry import (
    CLASSIFICATIONS,
    REGISTRY_SCHEMA_VERSION,
    SOURCE_TIERS,
    STATUSES,
    CourseFactRegistryError,
    read_registry_file,
    validate_registry,
)

__all__ = [
    "CLASSIFICATIONS",
    "REGISTRY_SCHEMA_VERSION",
    "SOURCE_TIERS",
    "STATUSES",
    "CourseFactRegistryError",
    "read_registry_file",
    "validate_registry",
]
