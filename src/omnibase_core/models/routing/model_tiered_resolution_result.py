# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tiered resolution result model for authenticated dependency resolution.

Wraps the base ``ModelResolutionResult`` with tiered resolution metadata:
the route plan, tier progression, final tier, and structured failure code.
The ``fail_closed`` flag enforces that resolution never downgrades across
trust boundaries.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.bindings.model_resolution_result import ModelResolutionResult
from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt

__all__ = ["ModelTieredResolutionResult"]


class ModelTieredResolutionResult(BaseModel):
    """Complete result of a tiered dependency resolution attempt.

    Extends the base resolution result with tiered resolution context:
    the route plan (if successful), tier progression audit trail, and
    structured failure information. The ``fail_closed`` flag is always
    ``True`` to enforce that resolution never downgrades across trust
    boundaries.

    Attributes:
        route_plan: The resolved route plan, or None if resolution failed.
        base_resolution: The underlying flat resolution result from
            ``ServiceCapabilityResolver``.
        tier_progression: Ordered record of all tier attempts made.
        final_tier: The tier at which resolution concluded (success or
            final failure). None if no tiers were attempted.
        fail_closed: Always True. Enforces that resolution never silently
            downgrades across trust boundaries.
        structured_failure: Structured failure code if resolution failed.
            None on success.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    route_plan: ModelRoutePlan | None = Field(
        default=None,
        description="The resolved route plan, or None if resolution failed",
    )

    base_resolution: ModelResolutionResult = Field(
        ...,
        description="The underlying flat resolution result",
    )

    tier_progression: list[ModelTierAttempt] = Field(
        default_factory=list,
        description="Ordered record of all tier attempts made",
    )

    final_tier: EnumResolutionTier | None = Field(
        default=None,
        description="The tier at which resolution concluded",
    )

    fail_closed: bool = Field(
        default=True,
        description="Always True: resolution never downgrades across trust boundaries",
    )

    structured_failure: EnumResolutionFailureCode | None = Field(
        default=None,
        description="Structured failure code if resolution failed",
    )
