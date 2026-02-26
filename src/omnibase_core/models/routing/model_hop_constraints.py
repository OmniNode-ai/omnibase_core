# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Hop constraints model for tiered authenticated dependency resolution.

Defines per-hop constraints applied to individual route hops, including
TTL, encryption requirements, data classification, and redaction policy.

.. versionadded:: 0.21.0
    Phase 1 of authenticated dependency resolution (OMN-2890).
"""

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelHopConstraints"]


class ModelHopConstraints(BaseModel):
    """Per-hop constraints for a route in tiered resolution.

    Each hop in a route plan can carry constraints that govern how data
    flows through that segment of the resolution path.

    Attributes:
        ttl_ms: Per-hop time-to-live in milliseconds. None means no TTL limit.
        require_encryption: Whether encryption is required for this hop.
        classification: Data classification level for this hop
            (e.g., ``"public"``, ``"internal"``, ``"confidential"``,
            ``"restricted"``). None means unclassified.
        redaction_policy: Redaction policy identifier for this hop
            (e.g., ``"pii_masked"``, ``"none"``). None means no redaction.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    ttl_ms: int | None = Field(
        default=None,
        description="Per-hop time-to-live in milliseconds",
        ge=0,
    )

    require_encryption: bool = Field(
        default=False,
        description="Whether encryption is required for this hop",
    )

    classification: str | None = Field(
        default=None,
        description="Data classification level (e.g., 'public', 'internal')",
    )

    redaction_policy: str | None = Field(
        default=None,
        description="Redaction policy identifier (e.g., 'pii_masked', 'none')",
    )
