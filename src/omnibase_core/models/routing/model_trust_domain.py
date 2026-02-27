# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Trust domain model for tiered authenticated dependency resolution.

A trust domain represents a boundary within which providers share a common
trust root and resolution tier. Domains are identified by a hierarchical ID
(e.g., ``local.default``, ``org.omninode``, ``fed.partner-a``) and scoped
to specific capabilities via glob patterns.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier

__all__ = ["ModelTrustDomain"]


class ModelTrustDomain(BaseModel):
    """Defines a trust boundary for tiered dependency resolution.

    Each trust domain is associated with a resolution tier and a trust root
    public key. Providers within the domain are scoped by capability glob
    patterns, and the domain's policy bundle is identified by its hash.

    Attributes:
        domain_id: Hierarchical identifier for the trust domain
            (e.g., ``local.default``, ``org.omninode``, ``fed.partner-a``).
        tier: The resolution tier associated with this domain.
        trust_root_public_key: Base64-encoded Ed25519 public key for the
            domain's trust root. Used to verify capability attestations
            issued by this domain.
        allowed_capabilities: Glob patterns scoping which capabilities
            this domain can provide (e.g., ``["database.*", "cache.*"]``).
        policy_bundle_hash: SHA-256 hash of the associated policy bundle.
            Used as a determinism input for resolution reproducibility.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    domain_id: str = Field(
        ...,
        description="Hierarchical trust domain identifier (e.g., 'local.default')",
        min_length=1,
        max_length=128,
    )

    tier: EnumResolutionTier = Field(
        ...,
        description="Resolution tier associated with this trust domain",
    )

    trust_root_public_key: str = Field(
        ...,
        description="Base64-encoded Ed25519 public key for the domain trust root",
        min_length=1,
    )

    allowed_capabilities: list[str] = Field(
        default_factory=list,
        description="Glob patterns scoping capabilities this domain can provide",
    )

    policy_bundle_hash: str = Field(
        ...,
        description="SHA-256 hash of the associated policy bundle",
        min_length=1,
    )
