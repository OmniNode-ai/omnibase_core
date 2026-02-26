# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Trust domain configuration for contract YAML.

Declarative trust domain declarations at the contract level. Allows
contract authors to declare which trust domains are relevant to a node
and map each to a resolution tier with an optional trust root reference.

Example YAML usage::

    trust_domains:
      - domain_id: "local.default"
        tier: "local_exact"
      - domain_id: "org.omninode"
        tier: "org_trusted"
        trust_root_ref: "secrets://keys/org-omninode-trust-root"

.. versionadded:: 0.22.0
    Phase 7 Part 1 of authenticated dependency resolution (OMN-2896).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from omnibase_core.enums.enum_resolution_tier import EnumResolutionTier

__all__ = ["ModelTrustDomainConfig"]


class ModelTrustDomainConfig(BaseModel):
    """Contract-level trust domain declaration.

    Associates a trust domain identifier with a resolution tier and an
    optional reference to the trust root key. Used by the contract loader
    to configure the tiered resolver with domain-specific settings.

    Attributes:
        domain_id: Trust domain identifier (e.g. ``"local.default"``,
            ``"org.omninode"``, ``"fed.partner-a"``).
        tier: Resolution tier associated with this domain.
        trust_root_ref: Optional URI or path referencing the trust root
            key material (e.g. ``"secrets://keys/org-omninode-trust-root"``).
            ``None`` means the trust root is provided by other means
            (e.g. local key store).
    """

    domain_id: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description="Trust domain identifier (e.g. 'local.default', 'org.omninode')",
    )

    tier: EnumResolutionTier = Field(
        ...,
        description="Resolution tier associated with this trust domain",
    )

    trust_root_ref: str | None = Field(
        default=None,
        max_length=1024,
        description="URI or path to trust root key material (None = provided externally)",
    )

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        from_attributes=True,
    )

    @field_validator("domain_id")
    @classmethod
    def validate_domain_id_format(cls, v: str) -> str:
        """Validate domain_id uses dot-notation with valid segments.

        Args:
            v: The domain_id string.

        Returns:
            The validated domain_id.

        Raises:
            ValueError: If format is invalid.
        """
        if not v or not v.strip():
            raise ValueError("domain_id cannot be empty")

        segments = v.split(".")
        for segment in segments:
            if not segment:
                raise ValueError(f"domain_id '{v}' contains empty segment")
            if not segment[0].isalpha():
                raise ValueError(
                    f"domain_id segment '{segment}' must start with a letter"
                )

        return v
