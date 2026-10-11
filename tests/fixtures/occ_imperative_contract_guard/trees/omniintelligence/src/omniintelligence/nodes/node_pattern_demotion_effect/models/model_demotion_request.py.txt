# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Input models for pattern_demotion_effect.

This module defines the request models for the pattern demotion effect node,
which checks and demotes validated patterns to deprecated status when they
fail to meet performance criteria.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelDemotionCheckRequest(BaseModel):
    """Request to check and demote failing patterns.

    This model triggers a scan of all validated patterns to identify those
    failing the demotion criteria based on rolling window success rates,
    failure streaks, and cooldown periods.
    """

    model_config = ConfigDict(frozen=True)

    dry_run: bool = Field(
        default=False,
        description="If True, return what WOULD be demoted without mutating",
    )
    max_success_rate: float = Field(
        default=0.4,
        ge=0.10,
        le=0.60,
        description="Patterns with success rate below this threshold are eligible "
        "for demotion. Bounded 0.10..0.60 to prevent overly aggressive or lenient thresholds.",
    )
    min_failure_streak: int = Field(
        default=5,
        ge=3,
        le=20,
        description="Minimum consecutive failures required to trigger demotion. "
        "Bounded 3..20 to ensure patterns have meaningful failure history.",
    )
    min_injection_count: int = Field(
        default=10,
        ge=1,
        description="Minimum injection_count_rolling_20 required for demotion eligibility. "
        "Ensures sufficient data before making demotion decisions.",
    )
    cooldown_hours: int = Field(
        default=24,
        ge=0,
        description="Minimum hours since promotion before demotion is allowed. "
        "Prevents rapid oscillation between validated and deprecated states.",
    )
    allow_threshold_override: bool = Field(
        default=False,
        description="Must be True to use non-default threshold values. "
        "Safety mechanism to prevent accidental aggressive demotion.",
    )
    correlation_id: UUID | None = Field(
        default=None,
        description="Optional correlation ID for tracing",
    )


__all__ = ["ModelDemotionCheckRequest"]
