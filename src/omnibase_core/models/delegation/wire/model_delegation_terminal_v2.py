# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Concrete, versioned terminal delegation wire contracts.

V2 replaces the nullable terminal shape with three mutually exclusive terminal
states.  Each state is a complete immutable transport record, so consumers do
not have to infer whether routing or quality evaluation occurred from nulls.
"""

from __future__ import annotations

from typing import Annotated, Literal, Self
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_delegation_routing_disposition import (
    EnumDelegationRoutingDisposition,
)
from omnibase_core.enums.enum_delegation_terminal_failure_cause import (
    EnumDelegationTerminalFailureCause,
)
from omnibase_core.enums.enum_delegation_terminal_outcome import (
    EnumDelegationTerminalOutcome,
)
from omnibase_core.enums.enum_delegation_unrouted_reason import (
    EnumDelegationUnroutedReason,
)
from omnibase_core.enums.enum_quality_score_comparison import (
    EnumQualityScoreComparison,
)


class ModelQualityBarEvaluation(BaseModel):
    """A self-consistent quality score evaluation against a required bar."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    quality_score: float = Field(..., ge=0.0, le=1.0)
    required_quality_bar: float = Field(..., ge=0.0, le=1.0)
    score_vs_required_bar: EnumQualityScoreComparison

    @model_validator(mode="after")
    def validate_score_comparison(self) -> Self:
        """Require the typed comparison to match the supplied score and bar."""
        expected = (
            EnumQualityScoreComparison.BELOW_BAR
            if self.quality_score < self.required_quality_bar
            else EnumQualityScoreComparison.AT_OR_ABOVE_BAR
        )
        if self.score_vs_required_bar is not expected:
            msg = (
                "score_vs_required_bar must match quality_score and "
                "required_quality_bar"
            )
            raise ValueError(msg)
        return self


class ModelDelegationProviderFailureCause(BaseModel):
    """A routed terminal failed because its selected provider failed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["provider"]
    cause: EnumDelegationTerminalFailureCause


class ModelDelegationQualityGateRejection(BaseModel):
    """A routed terminal failed the quality gate after provider completion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["quality_gate_rejection"]


type TypeDelegationRoutedFailureCause = Annotated[
    ModelDelegationProviderFailureCause | ModelDelegationQualityGateRejection,
    Field(discriminator="kind"),
]


class _ModelDelegationTerminalCommonV2(BaseModel):
    """Only the immutable fields common to every concrete V2 terminal state."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID
    task_type: str = Field(..., min_length=1)
    model_used: str = Field(..., min_length=1)
    endpoint_url: str = Field(..., min_length=1)
    content: str
    latency_ms: int = Field(..., ge=0)
    prompt_tokens: int = Field(..., ge=0)
    completion_tokens: int = Field(..., ge=0)
    total_tokens: int = Field(..., ge=0)
    fallback_to_claude: bool
    failure_reason: str
    tokens_to_compliance: int = Field(..., ge=0)
    compliance_attempts: int = Field(..., ge=1)
    escalation_count: int = Field(..., ge=0)
    escalation_history: tuple[dict[str, object], ...]
    routing_tiers_hash: str = Field(..., min_length=1)
    escalation_config_hash: str = Field(..., min_length=1)
    attempts_count: int = Field(..., ge=1)
    cumulative_attempt_cost: float = Field(..., ge=0.0)
    cumulative_input_tokens: int = Field(..., ge=0)
    cumulative_output_tokens: int = Field(..., ge=0)
    final_attempt_cost: float = Field(..., ge=0.0)
    context_pack_hash: str
    cost_tier_name: str = Field(..., min_length=1)
    # string-id-ok: tenant_id is a named tenant identifier, not a UUID
    tenant_id: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_total_tokens(self) -> Self:
        """Keep token accounting internally consistent at the wire boundary."""
        if self.total_tokens != self.prompt_tokens + self.completion_tokens:
            msg = "total_tokens must equal prompt_tokens + completion_tokens"
            raise ValueError(msg)
        return self


class ModelDelegationTerminalCompletedV2(_ModelDelegationTerminalCommonV2):
    """A routed terminal that completed and passed its quality evaluation."""

    routing_disposition: Literal[EnumDelegationRoutingDisposition.ROUTED]
    terminal_outcome: Literal[EnumDelegationTerminalOutcome.COMPLETED]
    backend_ref: str = Field(..., min_length=1)
    pricing_manifest_version: int = Field(..., ge=1)
    quality_passed: Literal[True]
    quality_bar_evaluation: ModelQualityBarEvaluation
    failed_acceptance_criteria: tuple[str, ...]

    @field_validator("backend_ref")
    @classmethod
    def validate_backend_ref(cls, value: str) -> str:
        """Keep a routed backend reference opaque and non-URL-shaped."""
        if value != value.strip() or not value:
            msg = (
                "backend_ref must be nonblank and must not have surrounding whitespace"
            )
            raise ValueError(msg)
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc:
            msg = "backend_ref must be a backend identifier, not a URL or URI"
            raise ValueError(msg)
        return value

    @field_validator("failed_acceptance_criteria")
    @classmethod
    def validate_failed_acceptance_criteria(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Reject blank criteria before enforcing completed-state emptiness."""
        if any(not criterion.strip() for criterion in value):
            msg = "failed_acceptance_criteria entries must not be blank"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_completed_quality_evidence(self) -> Self:
        """Completed terminals cannot carry quality-gate failure evidence."""
        if (
            self.quality_bar_evaluation.score_vs_required_bar
            is EnumQualityScoreComparison.BELOW_BAR
        ):
            msg = "quality_passed result cannot be below required_quality_bar"
            raise ValueError(msg)
        if self.failed_acceptance_criteria:
            msg = "quality_passed result cannot carry failed_acceptance_criteria"
            raise ValueError(msg)
        return self


class ModelDelegationTerminalFailedRoutedV2(_ModelDelegationTerminalCommonV2):
    """A routed terminal that failed with one closed, observed cause."""

    routing_disposition: Literal[EnumDelegationRoutingDisposition.ROUTED]
    terminal_outcome: Literal[EnumDelegationTerminalOutcome.FAILED]
    backend_ref: str = Field(..., min_length=1)
    pricing_manifest_version: int = Field(..., ge=1)
    quality_passed: bool
    quality_bar_evaluation: ModelQualityBarEvaluation
    failed_acceptance_criteria: tuple[str, ...]
    terminal_failure_reason: str = Field(..., min_length=1)
    routed_failure_cause: TypeDelegationRoutedFailureCause

    @field_validator("backend_ref")
    @classmethod
    def validate_backend_ref(cls, value: str) -> str:
        """Keep a routed backend reference opaque and non-URL-shaped."""
        if value != value.strip() or not value:
            msg = (
                "backend_ref must be nonblank and must not have surrounding whitespace"
            )
            raise ValueError(msg)
        parsed = urlparse(value)
        if parsed.scheme or parsed.netloc:
            msg = "backend_ref must be a backend identifier, not a URL or URI"
            raise ValueError(msg)
        return value

    @field_validator("failed_acceptance_criteria")
    @classmethod
    def validate_failed_acceptance_criteria(
        cls, value: tuple[str, ...]
    ) -> tuple[str, ...]:
        """Reject blank acceptance criteria in a terminal failure record."""
        if any(not criterion.strip() for criterion in value):
            msg = "failed_acceptance_criteria entries must not be blank"
            raise ValueError(msg)
        return value

    @model_validator(mode="after")
    def validate_routed_failure_quality_evidence(self) -> Self:
        """Preserve V1 quality consistency for routed failure terminals."""
        if self.quality_passed:
            msg = "routed failed terminal requires quality_passed=false"
            raise ValueError(msg)

        comparison = self.quality_bar_evaluation.score_vs_required_bar
        if (
            self.routed_failure_cause.kind == "quality_gate_rejection"
            and comparison is not EnumQualityScoreComparison.BELOW_BAR
        ):
            msg = "quality_gate_rejection requires below required_quality_bar"
            raise ValueError(msg)
        if (
            comparison is EnumQualityScoreComparison.AT_OR_ABOVE_BAR
            and not self.failed_acceptance_criteria
        ):
            msg = (
                "quality-failed result at or above required_quality_bar must "
                "carry failed_acceptance_criteria"
            )
            raise ValueError(msg)
        return self


class ModelDelegationTerminalFailedUnroutedV2(_ModelDelegationTerminalCommonV2):
    """A terminal failure where routing selected no backend at all."""

    routing_disposition: Literal[EnumDelegationRoutingDisposition.UNROUTED]
    terminal_outcome: Literal[EnumDelegationTerminalOutcome.FAILED]
    unrouted_reason: EnumDelegationUnroutedReason
    terminal_failure_reason: str = Field(..., min_length=1)


__all__: list[str] = [
    "EnumDelegationRoutingDisposition",
    "EnumDelegationTerminalOutcome",
    "EnumDelegationUnroutedReason",
    "ModelDelegationProviderFailureCause",
    "ModelDelegationQualityGateRejection",
    "ModelDelegationTerminalCompletedV2",
    "ModelDelegationTerminalFailedRoutedV2",
    "ModelDelegationTerminalFailedUnroutedV2",
    "ModelQualityBarEvaluation",
    "TypeDelegationRoutedFailureCause",
]
