# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tier attempt model for tiered authenticated dependency resolution.

Records the outcome of attempting resolution at a single tier, including
candidate counts before and after trust filtering, failure information,
and timing.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier

__all__ = ["ModelTierAttempt"]


class ModelTierAttempt(BaseModel):
    """Records the outcome of a single tier attempt during resolution.

    Each tier the resolver tries is recorded as a ``ModelTierAttempt``,
    providing full observability into the resolution escalation path.

    Attributes:
        tier: The resolution tier that was attempted.
        attempted_at: Timestamp when this tier attempt started.
        candidates_found: Number of candidate providers found at this tier
            before trust filtering.
        candidates_after_trust_filter: Number of candidates remaining after
            trust filtering was applied.
        failure_code: Structured failure code if this tier attempt failed.
            None if the tier resolved successfully.
        failure_reason: Human-readable explanation of why this tier failed.
            None if the tier resolved successfully.
        duration_ms: Duration of this tier attempt in milliseconds.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    tier: EnumResolutionTier = Field(
        ...,
        description="The resolution tier that was attempted",
    )

    attempted_at: datetime = Field(
        ...,
        description="Timestamp when this tier attempt started",
    )

    candidates_found: int = Field(
        ...,
        description="Number of candidate providers found before trust filtering",
        ge=0,
    )

    candidates_after_trust_filter: int = Field(
        ...,
        description="Number of candidates remaining after trust filtering",
        ge=0,
    )

    failure_code: EnumResolutionFailureCode | None = Field(
        default=None,
        description="Structured failure code if this tier attempt failed",
    )

    failure_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of why this tier failed",
    )

    duration_ms: float = Field(
        ...,
        description="Duration of this tier attempt in milliseconds",
        ge=0.0,
    )
