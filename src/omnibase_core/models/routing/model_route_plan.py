# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Route plan model for tiered authenticated dependency resolution.

A route plan is the complete output of a successful tiered resolution,
containing the ordered hops, capability resolved, tier progression audit
trail, and determinism inputs (registry/policy/trust-graph hashes).

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.routing.model_resolution_route_hop import (
    ModelResolutionRouteHop,
)
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt

__all__ = ["ModelRoutePlan"]


class ModelRoutePlan(BaseModel):
    """Complete route plan produced by tiered resolution.

    A route plan captures the resolved hops, the capability that was
    resolved, and all determinism inputs needed to reproduce the exact
    same resolution given the same registry/policy/trust-graph state.

    Attributes:
        plan_id: Unique identifier for this route plan.
        hops: Ordered list of route hops (at least one).
        source_capability: The capability identifier that was resolved.
        resolved_at: Timestamp when resolution completed.
        resolution_tier_used: The tier at which resolution succeeded.
        tier_progression: Ordered record of all tier attempts made.
        registry_snapshot_hash: BLAKE3 hash of the provider registry
            snapshot used during resolution.
        policy_bundle_hash: SHA-256 hash of the policy bundle applied.
        trust_graph_hash: SHA-256 hash of the trust domain graph used.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    plan_id: UUID = Field(
        ...,
        description="Unique identifier for this route plan",
    )

    hops: list[ModelResolutionRouteHop] = Field(
        ...,
        description="Ordered list of route hops",
        min_length=1,
    )

    source_capability: str = Field(
        ...,
        description="The capability identifier that was resolved",
        min_length=1,
    )

    resolved_at: datetime = Field(
        ...,
        description="Timestamp when resolution completed",
    )

    resolution_tier_used: EnumResolutionTier = Field(
        ...,
        description="The tier at which resolution succeeded",
    )

    tier_progression: list[ModelTierAttempt] = Field(
        default_factory=list,
        description="Ordered record of all tier attempts made during resolution",
    )

    registry_snapshot_hash: str = Field(
        ...,
        description="BLAKE3 hash of the provider registry snapshot",
        min_length=1,
    )

    policy_bundle_hash: str = Field(
        ...,
        description="SHA-256 hash of the policy bundle applied",
        min_length=1,
    )

    trust_graph_hash: str = Field(
        ...,
        description="SHA-256 hash of the trust domain graph used",
        min_length=1,
    )
