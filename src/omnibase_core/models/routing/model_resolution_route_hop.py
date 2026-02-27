# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Route hop model for tiered authenticated dependency resolution.

A route hop represents a single segment in a resolution route plan,
identifying the adapter, trust domain, tier, required proofs, and
per-hop constraints.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier
from omnibase_core.models.routing.model_hop_constraints import ModelHopConstraints

__all__ = ["ModelResolutionRouteHop"]


class ModelResolutionRouteHop(BaseModel):
    """A single hop in a tiered resolution route plan.

    Each hop identifies a resolved provider/adapter at a specific trust
    domain and tier, along with the proofs required to authorize the hop
    and any per-hop constraints.

    Attributes:
        hop_index: Zero-based position of this hop in the route plan.
        adapter_id: Identifier of the resolved provider or adapter.
        trust_domain: The ``domain_id`` of the trust domain for this hop.
        tier: The resolution tier at which this hop was resolved.
        required_proofs: Proof type identifiers required to authorize
            this hop (e.g., ``["node_identity", "capability_attested"]``).
        constraints: Per-hop constraints (TTL, encryption, classification).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    hop_index: int = Field(
        ...,
        description="Zero-based position of this hop in the route plan",
        ge=0,
    )

    adapter_id: str = Field(
        ...,
        description="Identifier of the resolved provider or adapter",
        min_length=1,
    )

    trust_domain: str = Field(
        ...,
        description="The domain_id of the trust domain for this hop",
        min_length=1,
    )

    tier: EnumResolutionTier = Field(
        ...,
        description="Resolution tier at which this hop was resolved",
    )

    required_proofs: list[str] = Field(
        default_factory=list,
        description="Proof type identifiers required to authorize this hop",
    )

    constraints: ModelHopConstraints = Field(
        default_factory=ModelHopConstraints,
        description="Per-hop constraints (TTL, encryption, classification)",
    )
