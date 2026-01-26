"""
Topic suffix validator for ONEX naming convention.

This module provides validation utilities for ONEX topic suffixes following
the canonical naming convention: onex.{kind}.{producer}.{event-name}.v{n}

Validation Rules:
    1. Must be entirely lowercase (no normalization - rejected if not lowercase)
    2. Must start with 'onex.'
    3. Must have exactly 5 dot-separated segments
    4. Segment 2 (kind) must be one of: cmd, evt, dlq, intent, snapshot
    5. Segments 3-4 (producer, event-name) must be kebab-case
    6. Segment 5 must match v{int} pattern (e.g., v1, v2)
    7. Must NOT start with environment prefix (dev., staging., prod.)

Example:
    >>> from omnibase_core.validation.validator_topic_suffix import (
    ...     validate_topic_suffix,
    ...     parse_topic_suffix,
    ...     compose_full_topic,
    ... )
    >>> result = validate_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
    >>> result.is_valid
    True
    >>> result.parsed.producer
    'omnimemory'

    >>> # Invalid: has environment prefix
    >>> result = validate_topic_suffix("dev.onex.evt.omnimemory.intent-stored.v1")
    >>> result.is_valid
    False

    >>> # Invalid: not lowercase (no normalization)
    >>> result = validate_topic_suffix("ONEX.EVT.SERVICE.EVENT.V1")
    >>> result.is_valid
    False

Thread Safety:
    All functions in this module are stateless and thread-safe.
    They can be called concurrently without synchronization.

See Also:
    - ModelTopicSuffixParts: Parsed suffix parts model
    - ModelTopicValidationResult: Validation result model
    - constants_topic_taxonomy: Topic taxonomy constants
"""

from __future__ import annotations

import re
from typing import Final

from omnibase_core.models.validation.model_topic_suffix_parts import (
    VALID_TOPIC_KINDS,
    ModelTopicSuffixParts,
)
from omnibase_core.models.validation.model_topic_validation_result import (
    ModelTopicValidationResult,
)

# ==============================================================================
# Constants
# ==============================================================================

# Required prefix for all ONEX topic suffixes
TOPIC_PREFIX: Final[str] = "onex"

# Environment prefixes that must NOT appear in suffixes
# Suffixes should not include these - they are added separately when composing full topics
ENV_PREFIXES: Final[frozenset[str]] = frozenset(
    {"dev", "staging", "prod", "test", "local"}
)

# Pattern for validating topic suffix format
# Format: onex.{kind}.{producer}.{event-name}.v{n}
# - onex: literal prefix
# - kind: cmd|evt|dlq|intent|snapshot
# - producer: kebab-case (lowercase letters, numbers, hyphens, starts with letter)
# - event-name: kebab-case (lowercase letters, numbers, hyphens, starts with letter)
# - version: v followed by one or more digits
TOPIC_SUFFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^onex\.(cmd|evt|dlq|intent|snapshot)\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.v(\d+)$"
)

# Pattern for validating strict kebab-case identifiers
# Rules:
#   - Must start with lowercase letter
#   - Must end with lowercase letter or digit (no trailing hyphen)
#   - No consecutive hyphens allowed
#   - Hyphens must be followed by letter/digit
# Used for both external/API validation and internal producer/event-name validation
KEBAB_CASE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[a-z]([a-z0-9]*(-[a-z0-9]+)*)?$"
)

# Control characters that are invalid in topic suffixes
# Includes: newline, carriage return, tab, null, vertical tab, form feed
_CONTROL_CHARS: Final[str] = "\n\r\t\x00\x0b\x0c"

# Pattern for validating version segment
VERSION_PATTERN: Final[re.Pattern[str]] = re.compile(r"^v(\d+)$")

# Expected number of segments in a valid suffix
EXPECTED_SEGMENT_COUNT: Final[int] = 5


# ==============================================================================
# Validation Functions
# ==============================================================================


def validate_topic_suffix(suffix: str) -> ModelTopicValidationResult:
    """
    Validate a topic suffix against ONEX naming convention.

    Validates that the suffix follows the canonical format:
    onex.{kind}.{producer}.{event-name}.v{n}

    Validation Rules:
        1. Must be entirely lowercase (no normalization - rejected if not lowercase)
        2. Must start with 'onex.'
        3. Must have exactly 5 dot-separated segments
        4. Segment 2 (kind) must be one of: cmd, evt, dlq, intent, snapshot
        5. Segments 3-4 (producer, event-name) must be kebab-case
        6. Segment 5 must match v{int} pattern
        7. Must NOT start with environment prefix (dev., staging., prod., etc.)
        8. Must not contain control characters (newlines, tabs, etc.)

    Args:
        suffix: The topic suffix to validate (e.g., "onex.evt.omnimemory.intent-stored.v1")

    Returns:
        ModelTopicValidationResult with is_valid=True and parsed parts if valid,
        or is_valid=False with error message if invalid.

    Example:
        >>> result = validate_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        >>> result.is_valid
        True
        >>> result.parsed.kind
        'evt'

        >>> result = validate_topic_suffix("dev.onex.evt.omnimemory.intent-stored.v1")
        >>> result.is_valid
        False
        >>> "environment prefix" in result.error.lower()
        True

        >>> result = validate_topic_suffix("ONEX.EVT.SERVICE.EVENT.V1")
        >>> result.is_valid
        False
        >>> "lowercase" in result.error.lower()
        True
    """
    # Check for control characters (newlines, tabs, null, etc.) before any processing
    # These should never be in a valid topic suffix
    if any(c in suffix for c in _CONTROL_CHARS):
        return ModelTopicValidationResult.failure(
            suffix,
            "Suffix contains invalid control characters (newline, tab, etc.)",
        )

    # Strip leading/trailing whitespace (spaces only at edges)
    stripped = suffix.strip()

    # Check for empty input
    if not stripped:
        return ModelTopicValidationResult.failure(suffix, "Suffix cannot be empty")

    # Strict lowercase validation - no normalization
    # Input must already be lowercase; uppercase or mixed case is rejected
    if stripped != stripped.lower():
        return ModelTopicValidationResult.failure(
            suffix,
            "Suffix must be lowercase. Use lowercase topic suffixes "
            "(e.g., 'onex.evt.service.event.v1')",
        )

    # Split into segments for validation (input is already lowercase)
    segments = stripped.split(".")
    first_segment = segments[0]

    # Check for environment prefix FIRST (must NOT be present in suffix)
    # This check comes before segment count to give a more specific error message
    # when an env prefix is detected (e.g., "dev.onex.evt.xxx.xxx.v1")
    if first_segment in ENV_PREFIXES:
        return ModelTopicValidationResult.failure(
            suffix,
            f"Suffix must not start with environment prefix '{first_segment}.'. "
            "Environment prefix should be added separately when composing full topic.",
        )

    # Check segment count
    if len(segments) != EXPECTED_SEGMENT_COUNT:
        return ModelTopicValidationResult.failure(
            suffix,
            f"Suffix must have exactly {EXPECTED_SEGMENT_COUNT} segments "
            f"(onex.kind.producer.event-name.version). Got {len(segments)} segments.",
        )

    # Check that suffix starts with 'onex.'
    if first_segment != TOPIC_PREFIX:
        return ModelTopicValidationResult.failure(
            suffix,
            f"Suffix must start with '{TOPIC_PREFIX}.' prefix. Got: '{first_segment}.'",
        )

    # Extract segments
    # segments[0] = "onex" (already validated)
    kind = segments[1]
    producer = segments[2]
    event_name = segments[3]
    version_str = segments[4]

    # Validate kind token
    if kind not in VALID_TOPIC_KINDS:
        valid_kinds = ", ".join(sorted(VALID_TOPIC_KINDS))
        return ModelTopicValidationResult.failure(
            suffix,
            f"Kind must be one of: {valid_kinds}. Got: '{kind}'",
        )

    # Validate producer (kebab-case)
    if not KEBAB_CASE_PATTERN.match(producer):
        return ModelTopicValidationResult.failure(
            suffix,
            f"Producer must be kebab-case (lowercase letters, digits, hyphens, "
            f"starting with letter). Got: '{producer}'",
        )

    # Validate event-name (kebab-case)
    if not KEBAB_CASE_PATTERN.match(event_name):
        return ModelTopicValidationResult.failure(
            suffix,
            f"Event name must be kebab-case (lowercase letters, digits, hyphens, "
            f"starting with letter). Got: '{event_name}'",
        )

    # Validate version format
    version_match = VERSION_PATTERN.match(version_str)
    if not version_match:
        return ModelTopicValidationResult.failure(
            suffix,
            f"Version must match 'v{{int}}' pattern (e.g., v1, v2). Got: '{version_str}'",
        )

    version = int(version_match.group(1))
    if version < 1:
        return ModelTopicValidationResult.failure(
            suffix,
            f"Version number must be >= 1. Got: v{version}",
        )

    # All validations passed - create parsed parts
    parsed = ModelTopicSuffixParts(
        kind=kind,
        producer=producer,
        event_name=event_name,
        version=version,
        raw_suffix=stripped,
    )

    return ModelTopicValidationResult.success(suffix=stripped, parsed=parsed)


def parse_topic_suffix(suffix: str) -> ModelTopicSuffixParts:
    """
    Parse a valid topic suffix into structured parts.

    This function validates the suffix and returns the parsed parts.
    If the suffix is invalid, it raises ValueError with details.

    Args:
        suffix: The topic suffix to parse (e.g., "onex.evt.omnimemory.intent-stored.v1")

    Returns:
        ModelTopicSuffixParts with the extracted components

    Raises:
        ValueError: If the suffix is invalid (includes the validation error message)

    Example:
        >>> parts = parse_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        >>> parts.kind
        'evt'
        >>> parts.producer
        'omnimemory'
        >>> parts.event_name
        'intent-stored'
        >>> parts.version
        1
    """
    result = validate_topic_suffix(suffix)
    if not result.is_valid:
        # error-ok: ValueError is standard Python convention for parsing functions
        raise ValueError(f"Invalid topic suffix '{suffix}': {result.error}")

    # result.parsed is guaranteed to be non-None when is_valid is True
    if result.parsed is None:
        # This should never happen due to validation invariants, but guard for safety
        # error-ok: internal consistency check for parse function contract
        raise ValueError(
            f"Validation succeeded but parsed result is None for: {suffix}"
        )

    return result.parsed


def compose_full_topic(env_prefix: str, suffix: str) -> str:
    """
    Compose a full topic name from environment prefix and suffix.

    Combines an environment prefix with a validated suffix to create
    the complete topic name: {env_prefix}.{suffix}

    Args:
        env_prefix: Environment prefix (dev, staging, prod, test, local)
        suffix: Valid ONEX topic suffix (e.g., "onex.evt.omnimemory.intent-stored.v1")

    Returns:
        Full topic name (e.g., "dev.onex.evt.omnimemory.intent-stored.v1")

    Raises:
        ValueError: If env_prefix is invalid or suffix fails validation

    Example:
        >>> compose_full_topic("dev", "onex.evt.omnimemory.intent-stored.v1")
        'dev.onex.evt.omnimemory.intent-stored.v1'

        >>> compose_full_topic("prod", "onex.cmd.user-service.create-account.v2")
        'prod.onex.cmd.user-service.create-account.v2'
    """
    # Normalize environment prefix
    env_normalized = env_prefix.strip().lower()

    # Validate environment prefix
    if not env_normalized:
        # error-ok: ValueError is standard Python convention for composition functions
        raise ValueError("Environment prefix cannot be empty")

    if env_normalized not in ENV_PREFIXES:
        valid_envs = ", ".join(sorted(ENV_PREFIXES))
        # error-ok: ValueError is standard Python convention for composition functions
        raise ValueError(
            f"Environment prefix must be one of: {valid_envs}. Got: '{env_prefix}'"
        )

    # Validate suffix (this raises ValueError if invalid)
    parsed = parse_topic_suffix(suffix)

    # Compose full topic using the normalized suffix from parsed result
    return f"{env_normalized}.{parsed.raw_suffix}"


def is_valid_topic_suffix(suffix: str) -> bool:
    """
    Check if a topic suffix is valid without returning details.

    Convenience function for simple validation checks where you only
    need a boolean result and don't need error details or parsed parts.

    Args:
        suffix: The topic suffix to validate

    Returns:
        True if the suffix is valid, False otherwise

    Example:
        >>> is_valid_topic_suffix("onex.evt.omnimemory.intent-stored.v1")
        True
        >>> is_valid_topic_suffix("dev.onex.evt.omnimemory.intent-stored.v1")
        False
        >>> is_valid_topic_suffix("onex.events.omnimemory.intent-stored.v1")
        False
    """
    return validate_topic_suffix(suffix).is_valid


__all__ = [
    "ENV_PREFIXES",
    "EXPECTED_SEGMENT_COUNT",
    "KEBAB_CASE_PATTERN",
    "TOPIC_PREFIX",
    "TOPIC_SUFFIX_PATTERN",
    "VERSION_PATTERN",
    "compose_full_topic",
    "is_valid_topic_suffix",
    "parse_topic_suffix",
    "validate_topic_suffix",
]
