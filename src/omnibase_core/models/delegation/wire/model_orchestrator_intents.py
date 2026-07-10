# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation orchestrator intent and response wire DTOs."""

from __future__ import annotations

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_budget_action import EnumBudgetAction
from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    ModelDelegationRequest,
)
from omnibase_core.models.delegation.wire.model_quality_gate import (
    ModelQualityGateInput,
)


class ModelRoutingIntent(BaseModel):
    """Intent sent from the orchestrator to the delegation routing reducer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: Literal["routing_reducer"] = Field(default="routing_reducer")
    payload: ModelDelegationRequest
    min_tier_name: str | None = Field(
        default=None,
        description=(
            "When set, the routing reducer skips tiers appearing before this "
            "tier in routing_tiers.yaml. Used by the escalation path to force "
            "routing to a higher-cost tier after quality gate failure. "
            "None means normal tier selection from the lowest eligible tier."
        ),
    )


class ModelInferenceIntent(BaseModel):
    """Intent sent from the orchestrator to the LLM inference effect."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: Literal["llm_inference"] = Field(default="llm_inference")
    base_url: str
    model: str
    system_prompt: str
    prompt: str
    max_tokens: int
    temperature: float = Field(default=0.3, ge=0.0, le=2.0)
    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=600.0,
        description="Backend-owned timeout for the downstream inference call.",
    )
    correlation_id: UUID
    api_key_ref: str | None = Field(
        default=None,
        description=(
            "Secret reference for authenticated model backends. The effect "
            "boundary resolves the referenced secret value immediately before "
            "making the outbound provider call."
        ),
    )
    extra_headers: dict[str, str] | None = Field(
        default=None,
        description="Additional HTTP headers required by the selected backend.",
    )
    provider_request_options: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Additional OpenAI-compatible request body options required by the "
            "selected model protocol. The inference effect merges these at the "
            "provider-call boundary after core fields are constructed."
        ),
    )
    # string-id-ok: tenant identity is a named slug (e.g. "omninode"), not a UUID.
    # OMN-14280 (OMN-14208 slice-2 A-now): the orchestrator stamps the workflow
    # tenant onto the inference intent so the inference effect can independently
    # attribute its own side effects (tenant-tagged logging/metrics, per-tenant
    # credential/quota/cost) to the owning tenant instead of trusting a shared
    # correlation_id -> tenant lookup. Optional now (backward-compatible wire);
    # the fail-closed wire==topic-tenant guard + required-flip is A-enforce,
    # gated behind the gateway topic-tenant stamp (deferred, not this slice).
    tenant_id: str | None = Field(
        default=None,
        description=(
            "Owning tenant for this inference call. Set by the delegation "
            "orchestrator from the workflow tenant identity; the inference "
            "effect reads it to tenant-tag its logs/metrics and round-trips it "
            "onto ModelInferenceResponseData. Isolation-ready wire (not yet "
            "isolation-enforced)."
        ),
    )


class ModelQualityGateIntent(BaseModel):
    """Intent sent from the orchestrator to the quality gate reducer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: Literal["quality_gate"] = Field(default="quality_gate")
    payload: ModelQualityGateInput


class ModelBaselineIntent(BaseModel):
    """Intent sent from the orchestrator for baseline cost comparison."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    intent: Literal["baseline_comparison"] = Field(default="baseline_comparison")
    correlation_id: UUID = Field(..., description="Delegation correlation ID.")
    task_type: str = Field(..., description="Task classification.")
    baseline_cost_usd: float = Field(
        ..., description="Estimated Claude cost for this task."
    )
    candidate_cost_usd: float = Field(
        default=0.0,
        description="Actual local LLM cost (near-zero for self-hosted).",
    )
    prompt_tokens: int = Field(default=0, ge=0, description="Prompt token count.")
    completion_tokens: int = Field(
        default=0, ge=0, description="Completion token count."
    )
    total_tokens: int = Field(default=0, ge=0, description="Total token count.")


class ModelInferenceResponseData(BaseModel):
    """Response data returned by the LLM inference effect."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: UUID = Field(..., description="Workflow correlation ID.")
    content: str = Field(..., description="Generated text from the LLM.")
    model_used: str = Field(
        ..., description="Model identifier that produced the response."
    )
    # string-id-ok: LLM call ID is an opaque upstream string (e.g. OpenAI "chatcmpl-..." format)
    llm_call_id: str = Field(
        default="",
        description="Upstream LLM call ID for cost reconciliation (e.g. OpenAI id field).",
    )
    latency_ms: int = Field(
        default=0, ge=0, description="Inference latency in milliseconds."
    )
    prompt_tokens: int = Field(default=0, ge=0, description="Prompt token count.")
    completion_tokens: int = Field(
        default=0, ge=0, description="Completion token count."
    )
    total_tokens: int = Field(default=0, ge=0, description="Total token count.")
    error_message: str = Field(
        default="",
        description="Failure reason when inference could not produce content.",
    )
    # string-id-ok: tenant identity is a named slug (e.g. "omninode"), not a UUID.
    # OMN-14280 (OMN-14208 slice-2 A-now): round-tripped from ModelInferenceIntent
    # by the inference effect so the tenant that owned the call is auditable on
    # the response and the orchestrator can observability-cross-check it against
    # the workflow tenant. Optional now; required-flip is A-enforce (deferred).
    tenant_id: str | None = Field(
        default=None,
        description=(
            "Owning tenant echoed back from the inference intent by the "
            "inference effect. Isolation-ready wire (not yet isolation-enforced)."
        ),
    )


class ModelComplianceLoopResult(BaseModel):
    """One-shot outcome of evaluating a single LLM attempt for schema compliance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    compliant: bool = Field(
        ...,
        description="True if the candidate output validated against the target schema.",
    )
    validated_output: str = Field(
        default="",
        description=(
            "The candidate output, exactly as supplied. Empty when the schema lookup failed "
            "before validation could run."
        ),
    )
    tokens_to_compliance: int = Field(
        default=0,
        ge=0,
        description="Total tokens consumed across all attempts so far (including this one).",
    )
    compliance_attempts: int = Field(
        default=1,
        ge=1,
        description=(
            "Number of LLM attempts evaluated so far (including this one). The first call to "
            "the loop is always attempt 1."
        ),
    )
    repair_prompt: str = Field(
        default="",
        description=(
            "Prompt to feed back to the LLM for the next attempt when ``compliant`` is False "
            "and ``budget_action`` is CONTINUE. Empty when the loop terminates."
        ),
    )
    budget_action: EnumBudgetAction = Field(
        default=EnumBudgetAction.CONTINUE,
        description=(
            "Result of the budget-policy check after this attempt. CONTINUE means the "
            "orchestrator may issue another repair attempt; ABORT means it must stop."
        ),
    )
    abort_reason: str = Field(
        default="",
        description=(
            "Human-readable explanation when ``budget_action`` is ABORT or when the loop "
            "terminated without compliance for another reason."
        ),
    )


__all__: list[str] = [
    "ModelBaselineIntent",
    "ModelComplianceLoopResult",
    "ModelInferenceIntent",
    "ModelInferenceResponseData",
    "ModelQualityGateIntent",
    "ModelRoutingIntent",
]
