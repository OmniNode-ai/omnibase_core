# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
# onex-allow-file-topic-literal: per-event topic SoT declaration (OMN-13944)

"""Pure ONEX topic-suffix checker (no model dependencies).

The parsing/validation logic for ONEX topic suffixes lives here so that domain
MODELS can validate a topic suffix without importing the ``validation``
behavioral layer — the ``models -> validation`` import back-edge the intra-core
import-linter oracle forbids (OMN-14331, epic OMN-3210).

``omnibase_core.validation.validator_topic_suffix`` builds the public
``ModelTopicValidationResult`` / ``ModelTopicSuffixParts`` return types on top of
:func:`check_topic_suffix` here; model-side callers use the model-free
:class:`UtilTopicSuffixCheck` result directly.

Canonical topic-suffix format::

    onex.{kind}.{producer}.{event-name}.v{n}

Thread Safety:
    All functions in this module are stateless and thread-safe.
"""

from __future__ import annotations

import re
from typing import Final, NamedTuple

# ==============================================================================
# Constants
# ==============================================================================

# Required prefix for all ONEX topic suffixes
TOPIC_PREFIX: Final[str] = "onex"

# Environment prefixes that must NOT appear in suffixes.
# Suffixes should not include these — they are added separately when composing
# full topics.
ENV_PREFIXES: Final[frozenset[str]] = frozenset(
    {"dev", "staging", "prod", "test", "local"}
)

# Valid topic kind tokens. These mirror ``VALID_TOPIC_KINDS`` in
# ``omnibase_core.models.validation.model_topic_suffix_parts`` (the model layer
# cannot be imported here without re-introducing the models -> validation
# back-edge, so the frozen taxonomy is declared locally). Kept in sync with the
# ``(cmd|evt|dlq|intent|snapshot)`` group in ``TOPIC_SUFFIX_PATTERN`` below.
VALID_TOPIC_KINDS: Final[frozenset[str]] = frozenset(
    {"cmd", "evt", "dlq", "intent", "snapshot"}
)

# Pattern for validating topic suffix format:
#   onex.{kind}.{producer}.{event-name}.v{n}
TOPIC_SUFFIX_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^onex\.(cmd|evt|dlq|intent|snapshot)\.[a-z][a-z0-9-]*\.[a-z][a-z0-9-]*\.v(\d+)$"
)

# Pattern for validating strict kebab-case identifiers:
#   - Must start with lowercase letter
#   - Must end with lowercase letter or digit (no trailing hyphen)
#   - No consecutive hyphens allowed
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


class UtilTopicSuffixCheck(NamedTuple):
    """Model-free result of :func:`check_topic_suffix`.

    ``is_valid`` is True only when every rule passes, in which case the parsed
    component fields (``kind``, ``producer``, ``event_name``, ``version``,
    ``normalized_suffix``) are populated and ``error`` is None. On failure,
    ``error`` carries the human-readable reason and the component fields are None.
    """

    is_valid: bool
    error: str | None = None
    kind: str | None = None
    producer: str | None = None
    event_name: str | None = None
    version: int | None = None
    normalized_suffix: str | None = None


def check_topic_suffix(suffix: str) -> UtilTopicSuffixCheck:
    """Validate a topic suffix against the ONEX naming convention.

    Pure, model-free counterpart of
    ``omnibase_core.validation.validator_topic_suffix.validate_topic_suffix``.
    Applies the same rules, in the same order, with the same error messages.

    Validation Rules:
        1. Must not contain control characters (newlines, tabs, etc.).
        2. Must not be empty (after stripping edge whitespace).
        3. Must NOT start with an environment prefix (dev., staging., prod., etc.).
        4. Must have exactly 5 dot-separated segments.
        5. Must start with the ``onex.`` prefix.
        6. Segment 2 (kind) must be one of: cmd, evt, dlq, intent, snapshot.
        7. Segments 3-4 (producer, event-name) must be kebab-case.
        8. Segment 5 must match ``v{int}`` with version >= 1.

    Args:
        suffix: The topic suffix to validate.

    Returns:
        A :class:`UtilTopicSuffixCheck`. On success ``is_valid`` is True and the
        parsed component fields are populated; on failure ``error`` explains why.
    """
    # Check for control characters (newlines, tabs, null, etc.) before processing.
    if any(c in suffix for c in _CONTROL_CHARS):
        return UtilTopicSuffixCheck(
            is_valid=False,
            error="Suffix contains invalid control characters (newline, tab, etc.)",
        )

    # Strip leading/trailing whitespace (spaces only at edges)
    stripped = suffix.strip()

    # Check for empty input
    if not stripped:
        return UtilTopicSuffixCheck(is_valid=False, error="Suffix cannot be empty")

    # Strict lowercase validation — no normalization.
    if stripped != stripped.lower():
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                "Suffix must be lowercase. Use lowercase topic suffixes "
                "(e.g., 'onex.evt.service.event.v1')"
            ),
        )

    # Split into segments for validation (input is already lowercase)
    segments = stripped.split(".")
    first_segment = segments[0]

    # Check for environment prefix FIRST (must NOT be present in suffix).
    if first_segment in ENV_PREFIXES:
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                f"Suffix must not start with environment prefix '{first_segment}.'. "
                "Environment prefix should be added separately when composing full topic."
            ),
        )

    # Check segment count
    if len(segments) != EXPECTED_SEGMENT_COUNT:
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                f"Suffix must have exactly {EXPECTED_SEGMENT_COUNT} segments "
                f"(onex.kind.producer.event-name.version). Got {len(segments)} segments."
            ),
        )

    # Check that suffix starts with 'onex.'
    if first_segment != TOPIC_PREFIX:
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                f"Suffix must start with '{TOPIC_PREFIX}.' prefix. "
                f"Got: '{first_segment}.'"
            ),
        )

    # Extract segments (segments[0] == "onex", already validated)
    kind = segments[1]
    producer = segments[2]
    event_name = segments[3]
    version_str = segments[4]

    # Validate kind token
    if kind not in VALID_TOPIC_KINDS:
        valid_kinds = ", ".join(sorted(VALID_TOPIC_KINDS))
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=f"Kind must be one of: {valid_kinds}. Got: '{kind}'",
        )

    # Validate producer (kebab-case)
    if not KEBAB_CASE_PATTERN.match(producer):
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                f"Producer must be kebab-case (lowercase letters, digits, hyphens, "
                f"starting with letter). Got: '{producer}'"
            ),
        )

    # Validate event-name (kebab-case)
    if not KEBAB_CASE_PATTERN.match(event_name):
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                f"Event name must be kebab-case (lowercase letters, digits, hyphens, "
                f"starting with letter). Got: '{event_name}'"
            ),
        )

    # Validate version format
    version_match = VERSION_PATTERN.match(version_str)
    if not version_match:
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=(
                f"Version must match 'v{{int}}' pattern (e.g., v1, v2). "
                f"Got: '{version_str}'"
            ),
        )

    version = int(version_match.group(1))
    if version < 1:
        return UtilTopicSuffixCheck(
            is_valid=False,
            error=f"Version number must be >= 1. Got: v{version}",
        )

    # All validations passed
    return UtilTopicSuffixCheck(
        is_valid=True,
        kind=kind,
        producer=producer,
        event_name=event_name,
        version=version,
        normalized_suffix=stripped,
    )


def is_valid_topic_suffix(suffix: str) -> bool:
    """Return True if ``suffix`` is a valid ONEX topic suffix, else False.

    Convenience wrapper over :func:`check_topic_suffix` for callers that only
    need a boolean result.
    """
    return check_topic_suffix(suffix).is_valid


__all__ = [
    "ENV_PREFIXES",
    "EXPECTED_SEGMENT_COUNT",
    "KEBAB_CASE_PATTERN",
    "TOPIC_PREFIX",
    "TOPIC_SUFFIX_PATTERN",
    "VALID_TOPIC_KINDS",
    "VERSION_PATTERN",
    "UtilTopicSuffixCheck",
    "check_topic_suffix",
    "is_valid_topic_suffix",
]
