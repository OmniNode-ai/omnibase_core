# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation routing configuration wire DTOs.

OMN-8596 owns ModelRoutingDecision; this module only carries routing config.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelTierModel(BaseModel):
    """Model candidate inside a delegation routing tier."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(..., description="Model identifier.")
    backend_ref: str = Field(
        ...,
        description="Backend key in the deployed bifrost contract (bifrost_delegation.yaml).",
    )
    max_context_tokens: int = Field(
        ..., ge=1, description="Max context window in tokens."
    )
    use_for: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Task types this model handles.",
    )
    fast_path_threshold_tokens: int | None = Field(
        default=None,
        ge=0,
        description="If set, prefer this model when prompt tokens <= threshold.",
    )


class ModelRoutingTier(BaseModel):
    """Ordered routing tier configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(..., description="Tier name: local, cheap_cloud, or claude.")
    models: tuple[ModelTierModel, ...] = Field(
        default_factory=tuple,
        description="Ordered list of candidate models in this tier.",
    )
    eval_before_accept: bool = Field(
        default=False,
        description="Whether to run eval before accepting result from this tier.",
    )
    eval_model: str | None = Field(
        default=None,
        description="Model to use for eval scoring (tier name required).",
    )
    cost_per_1k_tokens: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated tier cost per 1,000 tokens.",
    )
    max_retries: int = Field(
        default=0,
        ge=0,
        description="Max retry attempts within this tier before escalating.",
    )


class ModelDelegationConfig(BaseModel):
    """Delegation routing policy configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tiers: tuple[ModelRoutingTier, ...] = Field(
        default_factory=tuple,
        description="Ordered escalation tiers.",
    )


__all__: list[str] = ["ModelDelegationConfig", "ModelRoutingTier", "ModelTierModel"]
