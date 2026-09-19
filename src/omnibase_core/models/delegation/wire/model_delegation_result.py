# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation result wire DTO."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_credential_source import EnumCredentialSource
from omnibase_core.enums.enum_delegation_terminal_failure_cause import (
    EnumDelegationTerminalFailureCause,
)
from omnibase_core.enums.enum_quality_score_comparison import (
    EnumQualityScoreComparison,
)
from omnibase_core.models.delegation.wire.model_delegation_budget_evidence import (
    ModelDelegationBudgetEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_budget_refusal import (
    ModelDelegationBudgetRefusal,
)
from omnibase_core.models.delegation.wire.model_delegation_contract_evidence import (
    ModelDelegationContractEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_output_refusal import (
    ModelDelegationOutputRefusal,
)
from omnibase_core.models.delegation.wire.model_delegation_provenance import (
    ModelDelegationProvenance,
)
from omnibase_core.models.delegation.wire.model_quality_gate import (
    EnumQualityRuleEnforcement,
    ModelQualityRuleEvaluation,
)


class ModelDelegationResult(BaseModel):
    """Delegation outcome: content, quality status, model info, and metrics."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Tracks this result back to the original request.",
    )
    task_type: str = Field(
        ..., description="The task classification from the original request."
    )
    model_used: str = Field(
        ...,
        description="Name of the LLM model that produced the response.",
    )
    endpoint_url: str = Field(..., description="URL of the LLM endpoint used.")
    route: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Selected backend route that produced this terminal result. Paired "
            "with provider; absent is explicit legacy or pre-backend unknown."
        ),
    )
    provider: str | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Declared provider identity for the selected route. Never inferred "
            "from a post-terminal tenant overlay."
        ),
    )
    # OMN-18196: the credential class that served the call, copied verbatim
    # from the inference response that the effect boundary stamped. Axiom 9
    # forbids a customer route binding a house credential; before this field
    # nothing durable recorded which one answered, so the prohibition was
    # unfalsifiable after the fact. Unpaired from route/provider on purpose: a
    # refused call has a credential source (``NONE``) and no route at all.
    credential_source: EnumCredentialSource | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Credential class that served this terminal, as resolved at the "
            "effect boundary. Absent is explicit legacy provenance."
        ),
    )
    provenance: ModelDelegationProvenance | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Typed request provenance copied unchanged from delegation acceptance. "
            "None is explicit legacy/unclassified provenance."
        ),
    )
    content: str = Field(..., description="The LLM-generated response content.")
    response_contract_evidence: ModelDelegationContractEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Observed response-contract conveyance and validation evidence. Absent "
            "only when this delegation declared no response contract."
        ),
    )
    budget_evidence: ModelDelegationBudgetEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Declared and executed task-class timeout evidence. An omitted CLI "
            "timeout is represented inside the block as null, never by omitting it."
        ),
    )
    budget_refusal: ModelDelegationBudgetRefusal | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Typed pre-dispatch timeout refusal. It is mutually exclusive with "
            "budget_evidence because no execution occurred."
        ),
    )
    output_refusal: ModelDelegationOutputRefusal | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Typed refusal when a declared response contract cannot locate a "
            "safe deliverable."
        ),
    )
    preamble_chars: int | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        ge=0,
        description=(
            "Raw response characters removed before returning content. Content is "
            "the extracted deliverable, never the raw provider payload."
        ),
    )
    quality_passed: bool = Field(
        ...,
        description="Whether the quality gate accepted the response.",
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality score from 0.0 to 1.0.",
    )
    required_quality_bar: float | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        ge=0.0,
        le=1.0,
        description=(
            "Authoritative minimum quality score applied to this result. None when "
            "no quality bar was evaluated."
        ),
    )
    score_vs_required_bar: EnumQualityScoreComparison | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Typed comparison of quality_score to required_quality_bar. None when "
            "no quality bar was evaluated."
        ),
    )
    failed_acceptance_criteria: tuple[str, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
        description=(
            "Authoritative quality-gate failure details. Empty when no acceptance "
            "criterion failed or no quality gate ran."
        ),
    )
    rule_evaluations: tuple[ModelQualityRuleEvaluation, ...] = Field(
        default=(),
        exclude_if=lambda value: not value,
        description=(
            "Per-rule quality-gate verdicts (OMN-18295): each declared check's "
            "own result, the threshold it applied, and whether it was entitled "
            "to veto. Carried for PASSING rules too, so a reader can tell a "
            "rule that passed from one that never ran, and can see that a "
            "'scored' miss did not decide an outcome the bar decided. Empty "
            "when no quality gate ran, or when the producer predates this "
            "field."
        ),
    )
    latency_ms: int = Field(
        ..., ge=0, description="End-to-end latency in milliseconds."
    )
    prompt_tokens: int = Field(
        default=0, ge=0, description="Number of tokens in the prompt."
    )
    completion_tokens: int = Field(
        default=0, ge=0, description="Number of tokens in the completion."
    )
    total_tokens: int = Field(
        default=0, ge=0, description="Total tokens used (prompt + completion)."
    )
    fallback_to_claude: bool = Field(
        ...,
        description="Whether fallback to Claude was triggered.",
    )
    failure_reason: str = Field(
        default="",
        description="Reason for failure, empty string if successful.",
    )
    tokens_to_compliance: int = Field(
        default=0,
        ge=0,
        description="Total tokens across all compliance attempts.",
    )
    compliance_attempts: int = Field(
        default=1,
        ge=1,
        description="Number of LLM invocations to reach compliance.",
    )
    escalation_count: int = Field(
        default=0,
        ge=0,
        description="Number of tier-escalation attempts that occurred.",
    )
    escalation_history: tuple[dict[str, object], ...] = Field(
        default=(),
        description="Serialized per-tier escalation attempt records.",
    )
    terminal_failure_reason: str | None = Field(
        default=None,
        description="Terminal failure reason when delegation fails after escalation.",
    )
    terminal_failure_cause: EnumDelegationTerminalFailureCause | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Stable machine-readable cause for a terminal delegation failure. "
            "None for completed results and legacy failure producers."
        ),
    )
    routing_tiers_hash: str | None = Field(
        default=None,
        description="SHA-256 of serialized routing_tiers.yaml at execution time.",
    )
    escalation_config_hash: str | None = Field(
        default=None,
        description="SHA-256 of the escalation contract section at execution time.",
    )
    attempts_count: int = Field(
        default=1,
        ge=1,
        description="Total delegation attempts including the initial attempt.",
    )
    cumulative_attempt_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Total estimated cost across all attempts.",
    )
    cumulative_input_tokens: int = Field(
        default=0,
        ge=0,
        description="Total input tokens across all attempts.",
    )
    cumulative_output_tokens: int = Field(
        default=0,
        ge=0,
        description="Total output tokens across all attempts.",
    )
    final_attempt_cost: float = Field(
        default=0.0,
        ge=0.0,
        description="Estimated cost of the final attempt.",
    )
    context_pack_hash: str = Field(
        default="",
        description=(
            "Stable sha256 hash of the context pack injected into the delegated "
            "prompt, propagated onto the terminal result for ROI correlation. "
            "Empty string means the OFF arm or no context pack."
        ),
    )
    cost_tier_name: str = Field(
        default="",
        description=(
            "Resolved routing/cost tier that served this delegation (e.g. "
            "'local', 'cheap_cloud', 'cheap_frontier', 'claude'). This is the "
            "authoritative tier from the routing decision, carried onto the "
            "terminal so the delegation projection persists it instead of "
            "reconstructing it. Empty string when no serving tier was resolved "
            "(e.g. a remote-agent A2A terminal). OMN-13649."
        ),
    )
    # string-id-ok: tenant_id is a named tenant identifier, not a UUID
    tenant_id: str | None = Field(
        default=None,
        description=(
            "Multi-tenant isolation identifier carried from the originating "
            "request (or the ONEX_TENANT_ID env-var fallback at "
            "request-acceptance). OPERATOR-ACCEPTED INTERIM (OMN-14058): None "
            "means no tenant identity was resolved and the delegation "
            "projection falls back to the shared 'omninode' tenant column "
            "default. The durable per-tenant identity design is OMN-14107."
        ),
    )

    @model_validator(mode="after")
    def validate_total_tokens(self) -> Self:
        """Keep token accounting internally consistent at the wire boundary."""
        expected_total = self.prompt_tokens + self.completion_tokens
        if self.total_tokens != expected_total:
            msg = "total_tokens must equal prompt_tokens + completion_tokens"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_receipt_provenance_pair(self) -> Self:
        """Require terminal route/provider provenance to be complete when present."""
        if (self.route is None) != (self.provider is None):
            msg = "route and provider must be provided together"
            raise ValueError(msg)
        if self.route is not None:
            assert self.provider is not None
            if not self.route.strip() or not self.provider.strip():
                msg = "route and provider must be nonblank when provided"
                raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_structured_terminal_evidence(self) -> Self:
        """Reject incomplete or contradictory structured terminal evidence."""
        if any(not item.strip() for item in self.failed_acceptance_criteria):
            msg = "failed_acceptance_criteria entries must not be blank"
            raise ValueError(msg)
        if self.budget_evidence is not None and self.budget_refusal is not None:
            msg = "budget_evidence and budget_refusal are mutually exclusive"
            raise ValueError(msg)

        required_bar = self.required_quality_bar
        comparison = self.score_vs_required_bar
        if (required_bar is None) != (comparison is None):
            msg = (
                "required_quality_bar and score_vs_required_bar must be "
                "provided together"
            )
            raise ValueError(msg)

        if required_bar is not None and comparison is not None:
            expected = (
                EnumQualityScoreComparison.BELOW_BAR
                if self.quality_score < required_bar
                else EnumQualityScoreComparison.AT_OR_ABOVE_BAR
            )
            if comparison is not expected:
                msg = (
                    "score_vs_required_bar must match quality_score and "
                    "required_quality_bar"
                )
                raise ValueError(msg)

            if (
                comparison is EnumQualityScoreComparison.BELOW_BAR
                and self.quality_passed
            ):
                msg = "quality_passed result cannot be below required_quality_bar"
                raise ValueError(msg)

            if (
                comparison is EnumQualityScoreComparison.AT_OR_ABOVE_BAR
                and not self.quality_passed
                and not self.failed_acceptance_criteria
            ):
                msg = (
                    "quality-failed result at or above required_quality_bar must "
                    "carry failed_acceptance_criteria"
                )
                raise ValueError(msg)

        if self.quality_passed and self.failed_acceptance_criteria:
            msg = "quality_passed result cannot carry failed_acceptance_criteria"
            raise ValueError(msg)

        if self.quality_passed and self.terminal_failure_cause is not None:
            msg = "completed delegation cannot carry terminal_failure_cause"
            raise ValueError(msg)
        return self

    @model_validator(mode="after")
    def validate_rule_evaluations(self) -> Self:
        """Refuse a per-rule record that contradicts itself structurally.

        A rule appears at most ONCE. Two rows for the same rule are two
        verdicts for one check, and a reader has no way to know which is the
        gate's.

        What this deliberately does NOT refuse: a FAILED ``blocking`` rule on
        a terminal whose ``quality_passed`` is true. That combination looks
        like the self-contradiction this ticket opened on, and it was refused
        here in the first draft of this model -- which two existing proofs
        immediately falsified. ``enforcement`` records the authority a rule
        holds WITHIN the heuristic band; it is not the only authority that can
        decide a run. When the judge is unreachable, the deterministic
        acceptance floor decides instead (``score_source ==
        "deterministic_acceptance"``), and a run whose ``follows_codebase_
        conventions`` and ``no_obvious_regressions`` checks both failed
        completes on that floor -- correctly, by declared policy.

        Refusing that pairing would have forced the producer to either drop
        the record on the floor path or lie about the rules' verdicts. Both
        are the failure OMN-18295 exists to remove: a receipt that cannot say
        what actually happened. The record states the rules' own results; the
        terminal's ``score_source`` and ``authority_source`` say which
        authority decided. A reader needs both, and neither may be silently
        edited to agree with the other.
        """
        names = [evaluation.rule for evaluation in self.rule_evaluations]
        if len(set(names)) != len(names):
            msg = "rule_evaluations must record each rule at most once"
            raise ValueError(msg)
        return self


__all__: list[str] = [
    "EnumCredentialSource",
    "EnumDelegationTerminalFailureCause",
    "EnumQualityRuleEnforcement",
    "EnumQualityScoreComparison",
    "ModelDelegationResult",
    "ModelQualityRuleEvaluation",
]
