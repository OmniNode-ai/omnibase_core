# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation orchestrator intent and response wire DTOs."""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_budget_action import EnumBudgetAction
from omnibase_core.enums.enum_credential_source import EnumCredentialSource
from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    ModelDelegationRequest,
    validate_response_format,
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
    # OMN-14402: same-tier backend fallback. A local-backend transport/inference
    # failure used to escalate the WHOLE tier straight to the next (possibly
    # cloud) tier, even when a sibling backend in the SAME tier also declares the
    # task type (e.g. routing_tiers.yaml's local tier carries both
    # local-heavy-reasoning and local-reasoner for "research"). Backend refs
    # already attempted and failed within the target tier are listed here so the
    # routing reducer's selection can skip them and land on an untried sibling
    # instead of deterministically re-resolving the one that just failed.
    excluded_backend_refs: tuple[str, ...] = Field(
        default_factory=tuple,
        description=(
            "Backend refs (routing_tiers.yaml backend_id) already attempted and "
            "failed within the tier this intent routes to. The routing reducer "
            "skips these when selecting a model, so a same-tier retry after a "
            "transport/inference failure lands on a different backend instead "
            "of deterministically re-selecting the one that just failed."
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
    inference_attempt_id: UUID | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Identity of this specific inference attempt within the delegation "
            "workflow. The inference effect echoes it on the response so the "
            "orchestrator can reject a late response from an earlier route."
        ),
    )
    route: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Selected backend route that the inference effect is to execute. "
            "Paired with provider; both are absent for legacy or pre-backend "
            "events."
        ),
    )
    provider: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Declared provider identity for the selected backend route. Paired "
            "with route and never inferred after execution."
        ),
    )
    api_key_ref: str | None = Field(
        default=None,
        description=(
            "Secret reference for authenticated model backends. The effect "
            "boundary resolves the referenced secret value immediately before "
            "making the outbound provider call."
        ),
    )
    # OMN-18201: what the ROUTING AUTHORITY expected the effect boundary to
    # authenticate with. The sibling ``api_key_ref`` above is the reference
    # itself; this is the claim that one was supposed to be there.
    #
    # The two are not redundant, and the difference is the whole point. An
    # absent ``api_key_ref`` is ambiguous on its own: it is what a genuinely
    # auth-free backend looks like, and it is also what a customer's route
    # looks like after its reference has gone missing anywhere between the
    # routing decision and this call. The effect boundary cannot tell those
    # apart, so it did the only thing an absent reference permits -- it posted
    # the request with no Authorization header, and the vendor's 401 came back
    # as the delegation's failure. That is an unauthenticated outbound call on
    # a customer's route, made silently, with the platform reporting the
    # vendor for a condition it could have refused locally.
    #
    # Stamped by the producer of the intent, which is the only party that has
    # read the routing decision. ``CUSTOMER_KEY`` / ``HOUSE`` mean a credential
    # of that class is REQUIRED: the boundary refuses before any outbound call
    # if it cannot resolve one. ``NONE`` is a deliberate declaration that this
    # backend takes no credential -- a customer's own local model, say -- and
    # is the only value under which a headerless call is legitimate.
    #
    # ``None`` is an intent from a producer that predates this field and makes
    # no claim either way; the boundary keeps the pre-OMN-18201 behaviour for
    # it rather than refusing traffic mid-release. It is NOT a synonym for
    # ``EnumCredentialSource.NONE``, which is a positive assertion that no
    # credential is needed.
    expected_credential_source: EnumCredentialSource | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Credential class the routing authority expected this call to be "
            "authenticated with. CUSTOMER_KEY/HOUSE require the effect "
            "boundary to resolve one or refuse; NONE declares an auth-free "
            "backend; absent is a legacy producer making no claim."
        ),
    )
    extra_headers: dict[str, str] | None = Field(
        default=None,
        description="Additional HTTP headers required by the selected backend.",
    )
    provider_request_options: dict[str, object] | None = Field(
        default=None,
        description=(
            "Additional OpenAI-compatible request body options required by the "
            "selected model protocol. The inference effect merges these at the "
            "provider-call boundary after core fields are constructed."
        ),
    )
    response_format: dict[str, object] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Optional provider response-format directive carried separately "
            "from provider_request_options so callers cannot override core "
            "request fields through an untyped options mapping."
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
    # string-id-ok: tenant identity is a named slug, not a UUID
    tenant_id: str | None = (
        Field(  # string-id-ok: tenant identity is a named slug, not a UUID
            default=None,
            description=(
                "Owning tenant for this inference call. Set by the delegation "
                "orchestrator from the workflow tenant identity; the inference "
                "effect reads it to tenant-tag its logs/metrics and round-trips it "
                "onto ModelInferenceResponseData. Isolation-ready wire (not yet "
                "isolation-enforced)."
            ),
        )
    )

    @field_validator("response_format")
    @classmethod
    def _validate_response_format(
        cls, response_format: dict[str, object] | None
    ) -> dict[str, object] | None:
        return validate_response_format(response_format)

    @model_validator(mode="after")
    def _validate_receipt_provenance_pair(self) -> Self:
        """Require route/provider provenance to be complete when present."""
        if (self.route is None) != (self.provider is None):
            msg = "route and provider must be provided together"
            raise ValueError(msg)
        if self.route is not None:
            assert self.provider is not None
            if not self.route.strip() or not self.provider.strip():
                msg = "route and provider must be nonblank when provided"
                raise ValueError(msg)
        return self


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
    inference_attempt_id: UUID | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Inference-attempt identity echoed from ModelInferenceIntent. "
            "Optional for backward-compatible parsing of pre-OMN-15542 events."
        ),
    )
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
    route: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Route actually selected for this inference response. Paired with "
            "provider; absent is explicit unknown provenance."
        ),
    )
    provider: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Declared provider for the route that produced this response. Never "
            "reconstructed from tenant configuration after execution."
        ),
    )
    # OMN-18196: which credential actually served this call, stamped by the
    # effect boundary from the binding it resolved. This is the ONLY place the
    # fact exists first-hand; every downstream carrier copies it. A consumer
    # must never re-derive it from ``model_used``, ``route``, ``provider`` or a
    # tier name -- the same model is reachable on a customer key and on a house
    # credential, which is exactly why the field exists. ``None`` is a response
    # emitted before this field existed, NOT a call that ran without a
    # credential; that case is ``EnumCredentialSource.NONE``.
    credential_source: EnumCredentialSource | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Credential class the effect boundary resolved for this call. "
            "Absent is explicit legacy provenance, not an absent credential."
        ),
    )
    # string-id-ok: tenant identity is a named slug (e.g. "omninode"), not a UUID.
    # OMN-14280 (OMN-14208 slice-2 A-now): round-tripped from ModelInferenceIntent
    # by the inference effect so the tenant that owned the call is auditable on
    # the response and the orchestrator can observability-cross-check it against
    # the workflow tenant. Optional now; required-flip is A-enforce (deferred).
    # string-id-ok: tenant identity is a named slug, not a UUID
    tenant_id: str | None = (
        Field(  # string-id-ok: tenant identity is a named slug, not a UUID
            default=None,
            description=(
                "Owning tenant echoed back from the inference intent by the "
                "inference effect. Isolation-ready wire (not yet isolation-enforced)."
            ),
        )
    )

    @model_validator(mode="after")
    def _validate_receipt_provenance_pair(self) -> Self:
        """Require route/provider provenance to be complete when present."""
        if (self.route is None) != (self.provider is None):
            msg = "route and provider must be provided together"
            raise ValueError(msg)
        if self.route is not None:
            assert self.provider is not None
            if not self.route.strip() or not self.provider.strip():
                msg = "route and provider must be nonblank when provided"
                raise ValueError(msg)
        return self


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
