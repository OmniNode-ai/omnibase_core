# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Resolution event ledger model for audit, replay, and intelligence.

A resolution event captures the complete audit trail of a single
dependency resolution decision, including the dependency requested,
determinism inputs (registry/policy/trust-graph hashes), the resulting
route plan (if successful), all tier attempts, all proofs attempted,
and structured failure information.

These events are published to ``onex.evt.platform.resolution-decided.v1``
and form the resolution event ledger used for compliance auditing,
deterministic replay, and intelligence-driven pattern analysis.

.. versionadded:: 0.21.0
    Phase 6 of authenticated dependency resolution (OMN-2895).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_failure_code import EnumResolutionFailureCode
from omnibase_core.models.capabilities.model_capability_dependency import (
    ModelCapabilityDependency,
)
from omnibase_core.models.routing.model_resolution_proof import ModelResolutionProof
from omnibase_core.models.routing.model_route_plan import ModelRoutePlan
from omnibase_core.models.routing.model_tier_attempt import ModelTierAttempt

__all__ = ["ModelResolutionEvent"]


class ModelResolutionEvent(BaseModel):
    """Complete audit record of a single dependency resolution decision.

    Every invocation of the tiered resolver produces one of these events,
    regardless of whether resolution succeeded or failed. Together they
    form an append-only ledger that supports:

    - **Compliance auditing**: who resolved what, when, with which proofs.
    - **Deterministic replay**: given the same hashes, the same decision
      is reproducible.
    - **Intelligence analysis**: pattern detection across resolution
      outcomes (e.g., frequent failures at a specific tier).

    Attributes:
        event_id: Unique identifier for this resolution event.
        timestamp: When the resolution decision was made (UTC).
        dependency: The capability dependency that was being resolved.
        registry_snapshot_hash: BLAKE3 hash of the provider registry
            snapshot at the time of resolution.
        policy_bundle_hash: SHA-256 hash of the policy bundle in effect.
        trust_graph_hash: SHA-256 hash of the trust domain graph used.
        route_plan: The resulting route plan if resolution succeeded.
            None when resolution failed.
        tier_progression: Ordered record of all tier attempts made
            during resolution escalation.
        proofs_attempted: All proof verifications performed during
            resolution, regardless of outcome.
        success: Whether resolution produced a valid route plan.
        failure_code: Structured failure code when resolution failed.
            None when resolution succeeded.
        failure_reason: Human-readable explanation of the failure.
            None when resolution succeeded.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    event_id: UUID = Field(
        ...,
        description="Unique identifier for this resolution event",
    )

    timestamp: datetime = Field(
        ...,
        description="When the resolution decision was made (UTC)",
    )

    dependency: ModelCapabilityDependency = Field(
        ...,
        description="The capability dependency that was being resolved",
    )

    registry_snapshot_hash: str = Field(
        ...,
        description="BLAKE3 hash of the provider registry snapshot",
        min_length=1,
    )

    policy_bundle_hash: str = Field(
        ...,
        description="SHA-256 hash of the policy bundle in effect",
        min_length=1,
    )

    trust_graph_hash: str = Field(
        ...,
        description="SHA-256 hash of the trust domain graph used",
        min_length=1,
    )

    route_plan: ModelRoutePlan | None = Field(
        default=None,
        description="Resulting route plan if resolution succeeded",
    )

    tier_progression: list[ModelTierAttempt] = Field(
        default_factory=list,
        description="Ordered record of all tier attempts made",
    )

    proofs_attempted: list[ModelResolutionProof] = Field(
        default_factory=list,
        description="All proof verifications performed during resolution",
    )

    success: bool = Field(
        ...,
        description="Whether resolution produced a valid route plan",
    )

    failure_code: EnumResolutionFailureCode | None = Field(
        default=None,
        description="Structured failure code when resolution failed",
    )

    failure_reason: str | None = Field(
        default=None,
        description="Human-readable explanation of the failure",
    )
