# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-topic-literal: per-event topic SoT declaration (OMN-13944)

"""
Topic suffix validator for ONEX naming convention.

Validation utilities for ONEX topic suffixes following
the canonical naming convention: onex.{kind}.{producer}.{event-name}.v{n}

Validation Rules:
    1. Must be entirely lowercase (no normalization - rejected if not lowercase)
    2. Must start with 'onex.'
    3. Must have exactly 5 dot-separated segments
    4. Segment 2 (kind) must be one of: cmd, evt, dlq, intent, snapshot
    5. Segments 3-4 (producer, event-name) must be kebab-case
    6. Segment 5 must match v{int} pattern (e.g., v1, v2)
    7. Must NOT start with environment prefix (dev., staging., prod.)

The pure, model-free parsing/validation logic lives in
:mod:`omnibase_core.utils.util_topic_suffix` (OMN-14331); this module wraps it to
produce the public ``ModelTopicValidationResult`` / ``ModelTopicSuffixParts``
return types. The topic-format constants (``TOPIC_PREFIX``, ``ENV_PREFIXES``,
``TOPIC_SUFFIX_PATTERN``, ``KEBAB_CASE_PATTERN``, ``VERSION_PATTERN``,
``EXPECTED_SEGMENT_COUNT``) are re-exported from the util for backwards
compatibility of this module's public surface.

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
    - util_topic_suffix: pure, model-free topic-suffix checker
    - constants_topic_taxonomy: Topic taxonomy constants
"""

from __future__ import annotations

import warnings

from omnibase_core.models.validation.model_topic_suffix_parts import (
    ModelTopicSuffixParts,
)
from omnibase_core.models.validation.model_topic_validation_result import (
    ModelTopicValidationResult,
)

# Re-export the topic-format constants from the pure checker so this module's
# historical public surface (and omnibase_core.validation.__init__) is unchanged.
from omnibase_core.utils.util_topic_suffix import (
    ENV_PREFIXES,
    EXPECTED_SEGMENT_COUNT,
    KEBAB_CASE_PATTERN,
    TOPIC_PREFIX,
    TOPIC_SUFFIX_PATTERN,
    VERSION_PATTERN,
    check_topic_suffix,
)

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
        suffix: The topic suffix to validate (e.g. ``onex.evt.omnimemory.intent-stored.v1``)

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
    check = check_topic_suffix(suffix)
    if (
        not check.is_valid
        or check.kind is None
        or check.producer is None
        or check.event_name is None
        or check.version is None
        or check.normalized_suffix is None
    ):
        # check.error is always populated when is_valid is False.
        return ModelTopicValidationResult.failure(
            suffix, check.error or "Invalid topic suffix"
        )

    parsed = ModelTopicSuffixParts(
        kind=check.kind,
        producer=check.producer,
        event_name=check.event_name,
        version=check.version,
        raw_suffix=check.normalized_suffix,
    )
    return ModelTopicValidationResult.success(
        suffix=check.normalized_suffix, parsed=parsed
    )


def parse_topic_suffix(suffix: str) -> ModelTopicSuffixParts:
    """
    Parse a valid topic suffix into structured parts.

    This function validates the suffix and returns the parsed parts.
    If the suffix is invalid, it raises ValueError with details.

    Args:
        suffix: The topic suffix to parse (e.g. ``onex.evt.omnimemory.intent-stored.v1``)

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
        suffix: Valid ONEX topic suffix (e.g. ``onex.evt.omnimemory.intent-stored.v1``)

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
    warnings.warn(
        "compose_full_topic is deprecated; use bare ONEX topic names "
        "without environment prefix",
        DeprecationWarning,
        stacklevel=2,
    )

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
    return check_topic_suffix(suffix).is_valid


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
