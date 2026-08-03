# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed view of the pinned MSK IAM consumer-group pattern mirror.

Backs ``omnibase_core/contracts/consumer_group_iam_patterns.yaml``. Modelling it
rather than reading a raw mapping means a malformed or truncated mirror fails at load
with a Pydantic error instead of degrading into a silently-empty authorized set — an
empty set would make every authorization check fail open or closed by accident rather
than by contract.

.. versionadded:: OMN-15639
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.event_bus.model_consumer_group_iam_source import (
    ModelConsumerGroupIamSource,
)


class ModelConsumerGroupIamPatterns(BaseModel):
    """The pinned authorized-pattern set plus its provenance and drift digest."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    source: ModelConsumerGroupIamSource = Field(
        ..., description="Provenance of the mirrored terraform variable."
    )
    pattern_set_sha256: str = Field(
        ...,
        min_length=64,
        max_length=64,
        description=(
            "sha256 of authorized_patterns joined by newline with no trailing "
            "newline; recomputed at load time and rejected on mismatch."
        ),
    )
    authorized_patterns: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description="MSK IAM consumer-group globs, verbatim and in source order.",
    )
    managed_environments: tuple[str, ...] = Field(
        ...,
        min_length=1,
        description=(
            "Environment tokens whose brokers are MSK and therefore IAM-gated."
        ),
    )


__all__ = ["ModelConsumerGroupIamPatterns"]
