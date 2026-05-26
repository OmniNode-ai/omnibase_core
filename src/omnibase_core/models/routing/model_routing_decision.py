# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelRoutingDecision — output contract of the overseer routing policy engine."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EnumCapabilityTier(StrEnum):
    """Model capability tier — used to select the appropriate inference backend."""

    LOCAL = "local"
    CHEAP_FRONTIER = "cheap_frontier"
    MID_FRONTIER = "mid_frontier"
    EXPENSIVE_FRONTIER = "expensive_frontier"


class EnumProvider(StrEnum):
    """LLM provider identifier."""

    LOCAL_VLLM = "local_vllm"
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    LOCAL_MLX = "local_mlx"


class EnumRetryType(StrEnum):
    """Retry strategy for the selected model."""

    NONE = "none"
    SAME_MODEL = "same_model"
    ESCALATE_TIER = "escalate_tier"
    FALLBACK_MODEL = "fallback_model"


class EnumRiskLevel(StrEnum):
    """Risk level of the routing decision — affects audit logging."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ModelRoutingDecision(BaseModel):
    """Output contract of the overseer routing policy engine.

    Frozen + extra=forbid: routing decisions are immutable once emitted.
    HIGH/CRITICAL risk decisions are flagged in the audit log.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    selected_model: str = Field(
        ...,
        description="model_id key of the selected model (e.g. 'qwen3-coder-30b').",
    )
    capability_tier: EnumCapabilityTier = Field(
        ...,
        description="Capability tier of the selected model.",
    )
    provider: EnumProvider = Field(
        ...,
        description="Provider of the selected model.",
    )
    retry_type: EnumRetryType = Field(
        default=EnumRetryType.NONE,
        description="Retry strategy if the selected model fails.",
    )
    fallback_model: str | None = Field(
        default=None,
        description="model_id key to use on fallback. Required when retry_type=FALLBACK_MODEL.",
    )
    risk_level: EnumRiskLevel = Field(
        default=EnumRiskLevel.LOW,
        description="Risk level — HIGH/CRITICAL decisions are flagged in the audit log.",
    )
    retry_budget: int = Field(
        default=0,
        description="Remaining retry attempts available for this decision.",
        ge=0,
    )
    rationale: str = Field(
        default="",
        description="Human-readable rationale for the routing decision.",
    )
    exploration_score: float | None = Field(
        default=None,
        description="Exploration score (0.0-1.0) for bandit-style routing. None = deterministic.",
        ge=0.0,
        le=1.0,
    )
    cost_estimate_usd: float | None = Field(
        default=None,
        description="Estimated cost in USD for this routing decision.",
        ge=0.0,
    )

    @model_validator(mode="after")
    def _validate_retry_fallback_consistency(self) -> ModelRoutingDecision:
        if self.retry_type == EnumRetryType.FALLBACK_MODEL and not self.fallback_model:
            raise ValueError(
                "fallback_model is required when retry_type=FALLBACK_MODEL"
            )
        if (
            self.retry_type != EnumRetryType.FALLBACK_MODEL
            and self.fallback_model is not None
        ):
            raise ValueError(
                "fallback_model must be None unless retry_type=FALLBACK_MODEL"
            )
        return self


__all__: list[str] = [
    "EnumCapabilityTier",
    "EnumProvider",
    "EnumRetryType",
    "EnumRiskLevel",
    "ModelRoutingDecision",
]
