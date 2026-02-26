# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Tiered resolution configuration for contract YAML dependencies.

Declarative per-dependency configuration for tiered resolution behavior.
Allows contract authors to specify resolution tier bounds, required proofs,
and data classification constraints directly in YAML contracts.

All fields are optional with sensible defaults, ensuring existing contracts
parse without changes.

Example YAML usage::

    dependencies:
      - alias: "db"
        capability: "database.relational"
        tiered_resolution:
          min_tier: "local_exact"
          max_tier: "org_trusted"
          require_proofs: ["node_identity", "capability_attested"]
          classification: "internal"

.. versionadded:: 0.22.0
    Phase 7 Part 1 of authenticated dependency resolution (OMN-2896).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier

__all__ = ["ModelTieredResolutionConfig"]


class ModelTieredResolutionConfig(BaseModel):
    """Per-dependency tiered resolution configuration.

    Constrains how the tiered resolver handles a particular capability
    dependency. When present on a ``ModelCapabilityDependency``, the
    resolver will only attempt tiers within ``[min_tier, max_tier]`` and
    will require the listed proof types before accepting a match.

    Attributes:
        min_tier: Lowest tier the resolver should attempt. ``None`` means
            start from the lowest configured tier (typically ``local_exact``).
        max_tier: Highest tier the resolver should attempt. ``None`` means
            no upper bound (up to ``quarantine``).
        require_proofs: Proof type identifiers that must be satisfied for
            a resolution match at any tier. Empty list means no additional
            proof requirements beyond the tier defaults.
        classification: Data classification label (e.g. ``"public"``,
            ``"internal"``, ``"confidential"``, ``"restricted"``). When set,
            the resolver checks classification gates before each tier attempt.
    """

    min_tier: EnumResolutionTier | None = Field(
        default=None,
        description="Lowest resolution tier to attempt (None = start from lowest configured)",
    )

    max_tier: EnumResolutionTier | None = Field(
        default=None,
        description="Highest resolution tier to attempt (None = no upper bound)",
    )

    require_proofs: list[str] = Field(
        default_factory=list,
        description="Proof type identifiers required for resolution match",
    )

    classification: str | None = Field(
        default=None,
        description="Data classification label for classification gate checks",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )
