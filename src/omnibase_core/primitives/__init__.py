"""
Primitive Types Module

Foundational types with minimal dependencies used across the codebase.
These types form the base layer of the import hierarchy:

    primitives/ ← (this module - imports only errors/ and enums/)
        ↓
    types/      ← TypedDict structural definitions
        ↓
    models/     ← Pydantic models with business logic

Primitives should be:
- Self-contained value objects
- Immutable where possible
- Have no dependencies on models/ or types/
- Represent atomic concepts (version, timestamp, ID, etc.)
"""

from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    SemVerField,
    parse_input_state_version,
    parse_semver_from_string,
)

__all__ = [
    "ModelSemVer",
    "SemVerField",
    "parse_semver_from_string",
    "parse_input_state_version",
]
