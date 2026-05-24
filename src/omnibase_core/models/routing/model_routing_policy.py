# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Contract-declared LLM routing policy models."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModelCiOverridePolicy(BaseModel):
    """CI-mode override: when ONEX_CI_MODE=true, use this primary model key."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    primary: str = Field(..., description="model_id key to use in CI mode.")


class ModelRoutingPolicy(BaseModel):
    """Contract-declared LLM routing policy for a node handler."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    primary: str = Field(..., description="model_id key for the primary route.")
    fallback: str | None = Field(
        default=None,
        description="model_id key for fallback. Required when fallback roles exist.",
    )
    timeout_per_attempt_s: float = Field(
        default=30.0,
        description="Per-attempt budget in seconds.",
        gt=0,
    )
    max_retries: int = Field(
        default=2,
        description="Maximum retry attempts per request.",
        ge=1,
    )
    reason_for_fallback: str = Field(
        default="",
        description="Required when fallback is declared.",
    )
    fallback_allowed_roles: list[str] = Field(
        default_factory=list,
        description="Roles permitted to trigger fallback.",
    )
    max_tokens: int = Field(
        default=4096,
        description="Maximum tokens in the model response.",
        gt=0,
    )
    temperature: float = Field(
        default=0.2,
        description="Sampling temperature.",
        ge=0.0,
        le=2.0,
    )
    call_style: Literal["sync", "async"] = Field(
        default="async",
        description="Whether to invoke the model synchronously or asynchronously.",
    )
    ci_override: ModelCiOverridePolicy | None = Field(
        default=None,
        description="Override policy applied when ONEX_CI_MODE=true.",
    )

    @model_validator(mode="after")
    def _fallback_required_when_roles_declared(self) -> Self:
        if self.fallback_allowed_roles and self.fallback is None:
            msg = "fallback must be set when fallback_allowed_roles is non-empty"
            raise ValueError(msg)
        return self


__all__ = [
    "ModelCiOverridePolicy",
    "ModelRoutingPolicy",
]
