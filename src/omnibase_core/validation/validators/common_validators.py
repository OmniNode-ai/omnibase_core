"""
Shared validators for common patterns.

This module provides reusable Pydantic validators for common data patterns:
- ISO 8601 duration strings (e.g., "PT1H30M", "P1D")
- BCP 47 locale tags (e.g., "en-US", "fr-FR", "zh-Hans-CN")
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

import re
from typing import Annotated

from pydantic import AfterValidator

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

    Args:
        value: Duration string to validate

    Returns:
        The validated duration string (unchanged if valid)

    Raises:
        ValueError: If the format is invalid or the duration is empty (P or PT only)

    Examples:
        >>> validate_duration("PT1H30M")
        'PT1H30M'
        >>> validate_duration("P1D")
        'P1D'
        >>> validate_duration("invalid")  # Raises ValueError
    """
    if not value:
        msg = "Duration cannot be empty"
        raise ValueError(msg)

    match = _ISO8601_DURATION_PATTERN.match(value)
    if not match:
        msg = f"Invalid ISO 8601 duration format: '{value}'"
        raise ValueError(msg)

    # Check that at least one component is present (not just "P" or "PT")
    groups = match.groups()
    if not any(groups):
        msg = f"Duration must specify at least one time component: '{value}'"
        raise ValueError(msg)

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

    Validates that the input string is a valid BCP 47 language tag.
    Supported formats include:
    - Language only: "en", "fr", "zh"
    - Language + region: "en-US", "fr-FR", "pt-BR"
    - Language + script: "zh-Hans", "zh-Hant"
    - Language + script + region: "zh-Hans-CN", "zh-Hant-TW"
    - Language + region + variant: "en-GB-oed"

    Note: This is a simplified validator that covers most common use cases.
    For full BCP 47 compliance including extensions and private use tags,
    consider using a dedicated library like `langcodes`.

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
        msg = "Locale cannot be empty"
        raise ValueError(msg)

    match = _BCP47_LOCALE_PATTERN.match(value)
    if not match:
        msg = f"Invalid BCP 47 locale format: '{value}'"
        raise ValueError(msg)

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
        msg = "UUID cannot be empty"
        raise ValueError(msg)

    match = _UUID_PATTERN.match(value)
    if not match:
        msg = f"Invalid UUID format: '{value}'"
        raise ValueError(msg)

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
        msg = "Version cannot be empty"
        raise ValueError(msg)

    match = _SEMVER_PATTERN.match(value)
    if not match:
        msg = f"Invalid semantic version format: '{value}'"
        raise ValueError(msg)

    return value


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
"""

UUID = Annotated[str, AfterValidator(validate_uuid)]
"""Annotated type for UUID strings.

Use this type in Pydantic models for automatic validation:

    class Entity(BaseModel):
        id: UUID  # Validated and normalized UUID

Examples of valid values: "550e8400-e29b-41d4-a716-446655440000"
Note: UUIDs are normalized to lowercase with hyphens.
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


# =============================================================================
# Module Exports
# =============================================================================

__all__ = [
    # Validator functions
    "validate_duration",
    "validate_bcp47_locale",
    "validate_uuid",
    "validate_semantic_version",
    # Pydantic Annotated types
    "Duration",
    "BCP47Locale",
    "UUID",
    "SemanticVersion",
]
