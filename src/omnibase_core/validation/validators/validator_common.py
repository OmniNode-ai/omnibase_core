"""
Shared validators for common patterns.

This module provides reusable Pydantic validators for common data patterns:
- ISO 8601 duration strings (e.g., "PT1H30M", "P1D")
- BCP 47 locale tags (e.g., "en-US", "fr-FR", "zh-Hans-CN") - simplified validator
- UUID strings (with or without hyphens)
- Semantic version strings (SemVer 2.0.0)

Usage:
    # Direct validation
    from omnibase_core.validation.validators import (
        validate_duration,
        validate_bcp47_locale,
        validate_uuid,
        validate_semantic_version,
    )

    duration = validate_duration("PT1H30M")  # Returns "PT1H30M"
    locale = validate_bcp47_locale("en-US")  # Returns "en-US"

    # With Pydantic models (recommended)
    from omnibase_core.validation.validators import (
        Duration,
        BCP47Locale,
        UUIDString,
        SemanticVersion,
    )

    class MyModel(BaseModel):
        timeout: Duration
        locale: BCP47Locale
        id: UUIDString
        version: SemanticVersion

Note:
    The BCP 47 locale validator is simplified and does NOT support:
    - Private use subtags (x-private, en-x-custom)
    - Extension subtags (en-US-u-ca-gregory, zh-Hant-t-...)
    - Grandfathered irregular tags (i-default, i-ami)
    - Multiple variant subtags
    For full BCP 47 compliance, consider using a dedicated library like `langcodes`.

Ticket: OMN-1054
"""

import re
from typing import Annotated

from pydantic import AfterValidator

# Re-export for module API (commonly used with validators)
from omnibase_core.constants.constants_error import ERROR_CODE_PATTERN
from omnibase_core.utils.util_enum_normalizer import create_enum_normalizer

# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Validator functions
    "validate_duration",
    "validate_bcp47_locale",
    "validate_uuid",
    "validate_semantic_version",
    "validate_error_code",
    # Compiled regex patterns (re-exported from constants_error)
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

# =============================================================================
# ISO 8601 Duration Validator
# =============================================================================

# ISO 8601 duration pattern
# Format: P[n]Y[n]M[n]W[n]DT[n]H[n]M[n]S
# - P is the duration designator (required)
# - Y = years, M = months, W = weeks, D = days
# - T separates date from time components (required if time components present)
# - H = hours, M = minutes, S = seconds (can have decimal)
# Examples: PT1H30M, P1D, PT30S, P1Y2M3DT4H5M6S, PT0.5S, P1W
_ISO8601_DURATION_PATTERN = re.compile(
    r"^P"  # Start with P
    r"(?:(\d+)Y)?"  # Optional years
    r"(?:(\d+)M)?"  # Optional months
    r"(?:(\d+)W)?"  # Optional weeks
    r"(?:(\d+)D)?"  # Optional days
    r"(?:T"  # Time designator (required if time components present)
    r"(?:(\d+)H)?"  # Optional hours
    r"(?:(\d+)M)?"  # Optional minutes
    r"(?:(\d+(?:\.\d+)?)S)?"  # Optional seconds (can have decimal)
    r")?$"  # End of time section
)


def validate_duration(value: str) -> str:
    """Validate ISO 8601 duration string.

    Validates that the input string conforms to ISO 8601 duration format.
    Supported formats include:
    - PT1H30M (1 hour 30 minutes)
    - P1D (1 day)
    - PT30S (30 seconds)
    - P1Y2M3DT4H5M6S (full format)
    - PT0.5S (fractional seconds)
    - P1W (1 week)

    Note: Per ISO 8601, weeks (W) are an alternative representation and cannot
    be combined with other date/time components. Valid: P1W, P2W.
    Invalid: P1WT1H, P1Y1W, P1W1D.

    Args:
        value: Duration string to validate

    Returns:
        The validated duration string (unchanged if valid)

    Raises:
        ValueError: If the format is invalid, the duration is empty (P or PT only),
            or weeks are combined with other components

    Examples:
        >>> validate_duration("PT1H30M")
        'PT1H30M'
        >>> validate_duration("P1D")
        'P1D'
        >>> validate_duration("P1W")
        'P1W'
        >>> validate_duration("invalid")  # Raises ValueError
        >>> validate_duration("P1WT1H")  # Raises ValueError (weeks cannot combine)
    """
    if not value:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError("Duration cannot be empty")

    match = _ISO8601_DURATION_PATTERN.match(value)
    if not match:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(f"Invalid ISO 8601 duration format: '{value}'")

    # Check that at least one component is present (not just "P" or "PT")
    groups = match.groups()
    if not any(groups):
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(
            f"Duration must specify at least one time component: '{value}'"
        )

    # Per ISO 8601, weeks cannot be combined with other date/time components
    # groups: (years, months, weeks, days, hours, minutes, seconds)
    weeks = groups[2]
    has_other_date = any(groups[0:2]) or groups[3]  # years, months, days
    has_time = any(groups[4:7])  # hours, minutes, seconds

    if weeks and (has_other_date or has_time):
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(
            f"Invalid ISO 8601 duration '{value}': weeks (W) cannot be combined with other components"
        )

    return value


# =============================================================================
# BCP 47 Locale Validator
# =============================================================================

# BCP 47 language tag pattern (simplified)
# Format: language[-script][-region][-variant]
# - Language: 2-3 letter ISO 639 code (required)
# - Script: 4 letter ISO 15924 code (optional)
# - Region: 2 letter ISO 3166-1 or 3 digit UN M.49 code (optional)
# - Variant: 5-8 alphanumeric characters (optional)
# Examples: en, en-US, zh-Hans, zh-Hans-CN, en-GB-oed
_BCP47_LOCALE_PATTERN = re.compile(
    r"^"
    r"(?P<language>[a-zA-Z]{2,3})"  # Language code (2-3 letters)
    r"(?:-(?P<script>[a-zA-Z]{4}))?"  # Optional script (4 letters)
    r"(?:-(?P<region>[a-zA-Z]{2}|\d{3}))?"  # Optional region (2 letters or 3 digits)
    r"(?:-(?P<variant>[a-zA-Z0-9]{5,8}))?"  # Optional variant (5-8 alphanumeric)
    r"$"
)


def validate_bcp47_locale(value: str) -> str:
    """Validate BCP 47 locale tag.

    This is a simplified validator covering most common use cases.

    Limitations:
        - Does NOT support private use subtags (x-private, en-x-custom)
        - Does NOT support extension subtags (en-US-u-ca-gregory, zh-Hant-t-...)
        - Does NOT support grandfathered irregular tags (i-default, i-ami, etc.)
        - Does NOT support multiple variant subtags
        - Only validates pattern format, not semantic validity of codes

    Supported formats:
        - Language only: "en", "fr", "zh"
        - Language + region: "en-US", "fr-FR", "pt-BR"
        - Language + script: "zh-Hans", "zh-Hant"
        - Language + script + region: "zh-Hans-CN", "zh-Hant-TW"
        - Language + region + variant: "en-GB-oed"

    For full BCP 47 compliance, consider using a dedicated library like `langcodes`.

    Args:
        value: Locale tag string to validate

    Returns:
        The validated locale tag string (unchanged if valid)

    Raises:
        ValueError: If the format is invalid

    Examples:
        >>> validate_bcp47_locale("en-US")
        'en-US'
        >>> validate_bcp47_locale("zh-Hans-CN")
        'zh-Hans-CN'
        >>> validate_bcp47_locale("invalid_locale")  # Raises ValueError
    """
    if not value:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError("Locale cannot be empty")

    match = _BCP47_LOCALE_PATTERN.match(value)
    if not match:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(f"Invalid BCP 47 locale format: '{value}'")

    return value


# =============================================================================
# UUID Validator
# =============================================================================

# UUID pattern (with or without hyphens)
# Format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx or xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
# Supports UUID v1-v5 (32 hex digits, optionally with 4 hyphens)
_UUID_PATTERN = re.compile(
    r"^"
    r"([0-9a-fA-F]{8})-?"
    r"([0-9a-fA-F]{4})-?"
    r"([0-9a-fA-F]{4})-?"
    r"([0-9a-fA-F]{4})-?"
    r"([0-9a-fA-F]{12})"
    r"$"
)


def validate_uuid(value: str) -> str:
    """Validate UUID format string.

    Validates that the input string is a valid UUID (v1-v5).
    Accepts UUIDs with or without hyphens and returns a normalized
    UUID string with hyphens in standard format.

    Args:
        value: UUID string to validate (with or without hyphens)

    Returns:
        Normalized UUID string with hyphens (lowercase)

    Raises:
        ValueError: If the format is invalid

    Examples:
        >>> validate_uuid("550e8400-e29b-41d4-a716-446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> validate_uuid("550E8400E29B41D4A716446655440000")
        '550e8400-e29b-41d4-a716-446655440000'
        >>> validate_uuid("invalid-uuid")  # Raises ValueError
    """
    if not value:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError("UUID cannot be empty")

    match = _UUID_PATTERN.match(value)
    if not match:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(f"Invalid UUID format: '{value}'")

    # Normalize to lowercase with hyphens
    groups = match.groups()
    normalized = f"{groups[0]}-{groups[1]}-{groups[2]}-{groups[3]}-{groups[4]}"
    return normalized.lower()


# =============================================================================
# Semantic Version Validator
# =============================================================================

# SemVer 2.0.0 pattern
# Format: MAJOR.MINOR.PATCH[-PRERELEASE][+BUILD]
# - MAJOR, MINOR, PATCH: non-negative integers without leading zeros (except 0)
# - PRERELEASE: dot-separated identifiers (alphanumeric + hyphen)
# - BUILD: dot-separated identifiers (alphanumeric + hyphen)
# Examples: 1.0.0, 2.1.3-beta.1, 1.0.0+build.123, 2.0.0-rc.1+build.456
_SEMVER_PATTERN = re.compile(
    r"^(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
    r"(?:-(?P<prerelease>(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)"
    r"(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+(?P<build>[0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)


def validate_semantic_version(value: str) -> str:
    """Validate SemVer 2.0.0 version string.

    Validates that the input string conforms to Semantic Versioning 2.0.0
    specification (https://semver.org/).

    Supported formats include:
    - Basic: "1.0.0", "0.1.0", "2.10.3"
    - With prerelease: "1.0.0-alpha", "2.0.0-beta.1", "1.0.0-rc.1"
    - With build metadata: "1.0.0+build.123", "1.0.0+20230101"
    - Full format: "1.0.0-beta.1+build.123"

    Note: For structured SemVer handling with comparison operators,
    use `omnibase_core.models.primitives.ModelSemVer` instead.

    Args:
        value: Version string to validate

    Returns:
        The validated version string (unchanged if valid)

    Raises:
        ValueError: If the format is invalid

    Examples:
        >>> validate_semantic_version("1.0.0")
        '1.0.0'
        >>> validate_semantic_version("2.1.3-beta.1+build.123")
        '2.1.3-beta.1+build.123'
        >>> validate_semantic_version("1.0")  # Raises ValueError (missing patch)
        >>> validate_semantic_version("01.0.0")  # Raises ValueError (leading zero)
    """
    if not value:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError("Version cannot be empty")

    match = _SEMVER_PATTERN.match(value)
    if not match:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(f"Invalid semantic version format: '{value}'")

    return value


# =============================================================================
# Error Code Validator
# =============================================================================

# Error Code Pattern Design Decision (OMN-1054):
#
# ONEX uses TWO distinct error code formats for different purposes:
#
# 1. STRUCTURED ERROR CODES (validated here): CATEGORY_NNN
#    Pattern: ^[A-Z][A-Z0-9_]*_\d{1,4}$
#    Examples: AUTH_001, VALIDATION_123, NETWORK_TIMEOUT_001, SYSTEM_01
#    Use case: API errors, model validation errors, structured error tracking
#    - Multi-character category prefixes ARE supported (AUTH, VALIDATION, NETWORK_TIMEOUT)
#    - Underscore separator is REQUIRED before the numeric suffix
#    - 1-4 digits allowed for the numeric suffix
#
# 2. LINT-STYLE SHORT CODES (NOT validated here): XNNN
#    Pattern: ^[A-Z]\d{3}$
#    Examples: W001, E001, I001
#    Use case: Workflow linting, static analysis warnings (see checker_workflow_linter.py)
#    - Single-character category prefix (W=warning, E=error, I=info)
#    - No underscore separator
#    - Fixed 3-digit suffix
#
# Why keep them separate?
# - Structured codes prioritize readability and self-documentation (AUTH_001 is clearer than A001)
# - Lint-style codes prioritize brevity for dense warning lists
# - Different validation requirements and use cases
#
# If you need lint-style short codes (W001, E001), use a separate validator or
# the checker_workflow_linter module directly. This validator enforces structured codes.
#
# The ERROR_CODE_PATTERN is imported from omnibase_core.constants.constants_error
# which provides the single source of truth for error code validation across:
# - omnibase_core.models.context.model_operational_error_context
# - omnibase_core.models.context.model_retry_error_context
# - omnibase_core.validation.validators.validator_common (this module)


def validate_error_code(value: str) -> str:
    """Validate structured error code format (CATEGORY_NNN).

    Validates that the input string follows the ONEX structured error code
    format: CATEGORY_NNN where:
    - CATEGORY: One or more uppercase letters, digits, or underscores,
      starting with an uppercase letter (e.g., AUTH, VALIDATION, NETWORK_TIMEOUT)
    - Underscore separator (required)
    - NNN: 1-4 digit numeric suffix (e.g., 001, 123, 1234)

    Note: This validator does NOT support lint-style short codes (W001, E001).
    Those follow a different pattern (single letter + 3 digits, no underscore)
    used in workflow linting. See module docstring for design rationale.

    Args:
        value: Error code string to validate

    Returns:
        The validated error code string (unchanged if valid)

    Raises:
        ValueError: If the format is invalid

    Examples:
        >>> validate_error_code("AUTH_001")
        'AUTH_001'
        >>> validate_error_code("VALIDATION_123")
        'VALIDATION_123'
        >>> validate_error_code("NETWORK_TIMEOUT_001")
        'NETWORK_TIMEOUT_001'
        >>> validate_error_code("E001")  # Raises ValueError (lint-style not supported)
        >>> validate_error_code("auth_001")  # Raises ValueError (must be uppercase)
    """
    if not value:
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError("Error code cannot be empty")

    if not ERROR_CODE_PATTERN.match(value):
        # error-ok: Pydantic validators require ValueError for proper error aggregation
        raise ValueError(
            f"Invalid error code format: '{value}'. "
            "Expected CATEGORY_NNN pattern (e.g., AUTH_001, VALIDATION_123). "
            "For lint-style short codes (W001, E001), use checker_workflow_linter module."
        )

    return value


ErrorCode = Annotated[str, AfterValidator(validate_error_code)]
"""Annotated type for structured error codes (CATEGORY_NNN format).

Use this type in Pydantic models for automatic validation:

    class ErrorReport(BaseModel):
        code: ErrorCode  # Validated as CATEGORY_NNN

Examples of valid values: "AUTH_001", "VALIDATION_123", "NETWORK_TIMEOUT_001"

Note: Does NOT support lint-style short codes (W001, E001).
For those, see the checker_workflow_linter module.
"""


# =============================================================================
# Pydantic Annotated Types
# =============================================================================

# These types can be used directly in Pydantic models for automatic validation

Duration = Annotated[str, AfterValidator(validate_duration)]
"""Annotated type for ISO 8601 duration strings.

Use this type in Pydantic models for automatic validation:

    class Config(BaseModel):
        timeout: Duration  # Validated as ISO 8601 duration

Examples of valid values: "PT1H30M", "P1D", "PT30S"
"""

BCP47Locale = Annotated[str, AfterValidator(validate_bcp47_locale)]
"""Annotated type for BCP 47 locale tags.

Use this type in Pydantic models for automatic validation:

    class UserPreferences(BaseModel):
        locale: BCP47Locale  # Validated as BCP 47 locale

Examples of valid values: "en-US", "fr-FR", "zh-Hans-CN"

Note:
    This is a simplified validator. It does NOT support private use subtags
    (x-...), extension subtags (u-..., t-...), or grandfathered tags (i-...).
    For full BCP 47 compliance, consider using a dedicated library like `langcodes`.
"""

UUIDString = Annotated[str, AfterValidator(validate_uuid)]
"""Annotated type for UUID strings.

Use this type in Pydantic models for automatic validation:

    class Entity(BaseModel):
        id: UUIDString  # Validated and normalized UUID

Examples of valid values: "550e8400-e29b-41d4-a716-446655440000"
Note: UUIDs are normalized to lowercase with hyphens.

Note: Named UUIDString (not UUID) to avoid shadowing Python's built-in uuid module.
"""

SemanticVersion = Annotated[str, AfterValidator(validate_semantic_version)]
"""Annotated type for SemVer 2.0.0 version strings.

Use this type in Pydantic models for automatic validation:

    class Package(BaseModel):
        version: SemanticVersion  # Validated as SemVer 2.0.0

Examples of valid values: "1.0.0", "2.1.3-beta.1+build.123"

Note: For structured version handling with comparison operators,
use `ModelSemVer` from `omnibase_core.models.primitives` instead.
"""
