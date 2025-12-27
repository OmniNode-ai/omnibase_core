"""
Shared validators package for common patterns.

This package provides reusable Pydantic validators for common data patterns:
- ISO 8601 duration strings
- BCP 47 locale tags
- UUID strings
- Semantic version strings (SemVer 2.0.0)

Usage:
    # Direct validation
    from omnibase_core.validation.validators import (
        validate_duration,
        validate_bcp47_locale,
        validate_uuid,
        validate_semantic_version,
    )

    # Pydantic Annotated types
    from omnibase_core.validation.validators import (
        Duration,
        BCP47Locale,
        UUID,
        SemanticVersion,
    )

    class MyModel(BaseModel):
        timeout: Duration
        locale: BCP47Locale
        id: UUID
        version: SemanticVersion

Ticket: OMN-1054
"""

from omnibase_core.validation.validators.common_validators import (
    UUID,
    # Pydantic Annotated types
    BCP47Locale,
    Duration,
    SemanticVersion,
    # Enum normalizer factory
    create_enum_normalizer,
    # Validator functions
    validate_bcp47_locale,
    validate_duration,
    validate_semantic_version,
    validate_uuid,
)

__all__ = [
    # Validator functions
    "validate_duration",
    "validate_bcp47_locale",
    "validate_uuid",
    "validate_semantic_version",
    # Enum normalizer factory
    "create_enum_normalizer",
    # Pydantic Annotated types
    "Duration",
    "BCP47Locale",
    "UUID",
    "SemanticVersion",
]
