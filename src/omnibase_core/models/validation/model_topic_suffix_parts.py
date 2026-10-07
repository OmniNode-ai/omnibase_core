# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Parsed topic suffix parts model for ONEX topic naming validation.

ModelTopicSuffixParts, an immutable Pydantic model that
represents the parsed components of a valid ONEX topic suffix.

Topic Suffix Format:
    onex.{kind}.{producer}.{event-name}.v{n}

Where:
    - kind: Topic type token (cmd, evt, dlq, intent, snapshot)
    - producer: Service/producer name in kebab-case
    - event-name: Event name in kebab-case
    - v{n}: Version number (e.g., v1, v2)

Example:
    >>> from omnibase_core.models.validation.model_topic_suffix_parts import (
    ...     ModelTopicSuffixParts,
    ... )
    >>> parts = ModelTopicSuffixParts(
    ...     kind="evt",
    ...     producer="omnimemory",
    ...     event_name="intent-stored",
    ...     version=1,
    ...     raw_suffix="onex.evt.omnimemory.intent-stored.v1",  # onex-topic-doc-example
    ... )
    >>> parts.kind
    'evt'

Thread Safety:
    ModelTopicSuffixParts is immutable (frozen=True) and thread-safe.
    Instances can be safely shared across threads.

See Also:
    - validator_topic_suffix: Validation utilities for topic suffixes
    - ModelTopicValidationResult: Result model for suffix validation
"""

# Cross-reference: For semantic topic type constants (TAXONOMY_TYPE_COMMANDS, etc.),
# see omnibase_core.constants.constants_topic_taxonomy.
# This module defines KIND_ABBR_* tokens used in topic suffix strings,
# while constants_topic_taxonomy defines TAXONOMY_TYPE_* semantic values.

from pydantic import BaseModel, ConfigDict, Field

# Topic kind tokens used in ONEX naming convention (short forms)
# These are the abbreviated tokens used in topic suffixes, not the full type names
KIND_ABBR_CMD = "cmd"
KIND_ABBR_EVT = "evt"
KIND_ABBR_DLQ = "dlq"
KIND_ABBR_INTENT = "intent"
KIND_ABBR_SNAPSHOT = "snapshot"

# Valid topic kind tokens for validation
VALID_TOPIC_KINDS: frozenset[str] = frozenset(
    {
        KIND_ABBR_CMD,
        KIND_ABBR_DLQ,
        KIND_ABBR_EVT,
        KIND_ABBR_INTENT,
        KIND_ABBR_SNAPSHOT,
    }
)


class ModelTopicSuffixParts(BaseModel):
    """
    Immutable model representing parsed components of an ONEX topic suffix.

    This model stores the structured parts extracted from a valid topic suffix
    following the ONEX naming convention: onex.{kind}.{producer}.{event-name}.v{n}

    Attributes:
        kind: Topic type token (cmd, evt, dlq, intent, snapshot)
        producer: Service/producer name in kebab-case (e.g., "omnimemory")
        event_name: Event name in kebab-case (e.g., "intent-stored")
        version: Version number as integer (extracted from v{n} format)
        raw_suffix: The canonical lowercase suffix for consistent comparison (normalized from input)

    Example:
        >>> parts = ModelTopicSuffixParts(
        ...     kind="evt",
        ...     producer="user-service",
        ...     event_name="account-created",
        ...     version=1,
        ...     raw_suffix="onex.evt.user-service.account-created.v1",  # onex-topic-doc-example
        ... )
        >>> parts.producer
        'user-service'
        >>> parts.version
        1
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: str = Field(
        ...,
        description="Topic type token (cmd, evt, dlq, intent, snapshot)",
    )

    producer: str = Field(
        ...,
        description="Service/producer name in kebab-case",
    )

    event_name: str = Field(
        ...,
        description="Event name in kebab-case",
    )

    version: int = Field(
        ...,
        description="Version number (e.g., 1 for v1)",
        ge=1,
    )

    raw_suffix: str = Field(
        ...,
        description="Canonical normalized suffix (lowercase form used for comparison)",
    )


__all__ = [
    "ModelTopicSuffixParts",
    "KIND_ABBR_CMD",
    "KIND_ABBR_DLQ",
    "KIND_ABBR_EVT",
    "KIND_ABBR_INTENT",
    "KIND_ABBR_SNAPSHOT",
    "VALID_TOPIC_KINDS",
]
