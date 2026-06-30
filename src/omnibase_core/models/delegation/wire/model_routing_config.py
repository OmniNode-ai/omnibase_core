# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation routing configuration wire DTOs.

OMN-8596 owns ModelRoutingDecision; this module only carries routing config.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_tier_cost_type import EnumTierCostType


class ModelTierCost(BaseModel):
    """Typed per-tier cost model (OMN-13234).

    Declares HOW a tier is billed (``cost_type``) plus the rate/cap fields that
    measurement regime requires. Validated so each regime carries exactly the
    fields it needs and nothing it does not:

    - ``free_local`` — no rate, no cap.
    - ``metered`` — ``rate_per_1k_usd`` required (> 0); no cap.
    - ``budgeted`` — ``monthly_cap_usd`` and ``overage_rate_per_1k_usd``
      required; ``rate_per_1k_usd`` is the in-budget per-1k accounting rate
      used to draw down headroom.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    cost_type: EnumTierCostType = Field(
        ...,
        description="Measurement regime for this tier's actual dollar cost.",
    )
    rate_per_1k_usd: float = Field(
        default=0.0,
        ge=0.0,
        description=(
            "Per-1,000-token USD rate. For 'metered' this is the billed rate. "
            "For 'budgeted' this is the in-budget accounting rate that draws "
            "down monthly headroom. For 'free_local' it must be 0."
        ),
    )
    monthly_cap_usd: float | None = Field(
        default=None,
        ge=0.0,
        description=(
            "Monthly spend cap for 'budgeted' tiers. Tokens served while "
            "headroom remains cost 0 cash; tokens past the cap bill at "
            "overage_rate_per_1k_usd. Must be None for free_local/metered."
        ),
    )
    overage_rate_per_1k_usd: float = Field(
        default=0.0,
        ge=0.0,
        description=(
            "Per-1,000-token USD rate charged for 'budgeted' tokens served "
            "after the monthly cap is exhausted. Ignored for other types."
        ),
    )

    @model_validator(mode="after")
    def _validate_regime_fields(self) -> ModelTierCost:
        if self.cost_type is EnumTierCostType.FREE_LOCAL:
            if self.rate_per_1k_usd != 0.0:
                raise ValueError("free_local cost must have rate_per_1k_usd == 0")
            if self.monthly_cap_usd is not None:
                raise ValueError("free_local cost must not declare monthly_cap_usd")
            if self.overage_rate_per_1k_usd != 0.0:
                raise ValueError(
                    "free_local cost must have overage_rate_per_1k_usd == 0"
                )
        elif self.cost_type is EnumTierCostType.METERED:
            if self.rate_per_1k_usd <= 0.0:
                raise ValueError("metered cost requires rate_per_1k_usd > 0")
            if self.monthly_cap_usd is not None:
                raise ValueError(
                    "metered cost must not declare monthly_cap_usd; use 'budgeted'"
                )
        elif self.cost_type is EnumTierCostType.BUDGETED:
            if self.monthly_cap_usd is None:
                raise ValueError("budgeted cost requires monthly_cap_usd")
            if self.overage_rate_per_1k_usd <= 0.0:
                raise ValueError("budgeted cost requires overage_rate_per_1k_usd > 0")
        return self


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
        description=(
            "Legacy flat per-1,000-token estimate used by the ceiling-comparison "
            "routing check. Superseded for actual-cost measurement by the typed "
            "`cost` model (OMN-13234); kept for the routing policy comparison."
        ),
    )
    cost: ModelTierCost | None = Field(
        default=None,
        description=(
            "Typed per-tier cost model (OMN-13234): free_local | metered | "
            "budgeted with rate/cap/overage. When present, the projection cost "
            "computation uses this instead of the flat cost_per_1k_tokens. "
            "None means the tier has not been migrated to the typed model."
        ),
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


__all__: list[str] = [
    "EnumTierCostType",
    "ModelDelegationConfig",
    "ModelRoutingTier",
    "ModelTierCost",
    "ModelTierModel",
]
