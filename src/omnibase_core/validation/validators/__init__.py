"""
Shared validators package for common patterns.

This package provides reusable Pydantic validators for common data patterns:
- ISO 8601 duration strings
- BCP 47 locale tags
- UUID strings
- Semantic version strings (SemVer 2.0.0)
- Structured error codes (CATEGORY_NNN format)

Usage:
    # Direct validation
    from omnibase_core.validation.validators import (
        validate_duration,
        validate_bcp47_locale,
        validate_uuid,
        validate_semantic_version,
        validate_error_code,
    )

    # Compiled regex patterns (cached at module level for performance)
    from omnibase_core.validation.validators import ERROR_CODE_PATTERN

    # Pydantic Annotated types
    from omnibase_core.validation.validators import (
        Duration,
        BCP47Locale,
        UUIDString,
        SemanticVersion,
        ErrorCode,
    )

    class MyModel(BaseModel):
        timeout: Duration
        locale: BCP47Locale
        id: UUIDString
        version: SemanticVersion
        code: ErrorCode

Ticket: OMN-1054
"""

# Compiled regex patterns, Pydantic Annotated types, enum normalizer, and validators
from omnibase_core.validation.validators.validator_common import (
    ERROR_CODE_PATTERN,
    BCP47Locale,
    Duration,
    ErrorCode,
    SemanticVersion,
    UUIDString,
    create_enum_normalizer,
    validate_bcp47_locale,
    validate_duration,
    validate_error_code,
    validate_semantic_version,
    validate_uuid,
)

__all__ = [
    # Validator functions
    "validate_duration",
    "validate_bcp47_locale",
    "validate_uuid",
    "validate_semantic_version",
    "validate_error_code",
    # Compiled regex patterns (cached at module level)
    "ERROR_CODE_PATTERN",
    # Enum normalizer factory
    "create_enum_normalizer",
    # Pydantic Annotated types
    "Duration",
    "BCP47Locale",
    "UUIDString",
    "SemanticVersion",
    "ErrorCode",
]
