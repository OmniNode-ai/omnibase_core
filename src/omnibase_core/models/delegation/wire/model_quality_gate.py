# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation quality gate wire DTOs."""

from __future__ import annotations

from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from omnibase_core.enums.enum_quality_gate_result import EnumQualityGateResult
from omnibase_core.enums.enum_quality_rule_enforcement import (
    EnumQualityRuleEnforcement,
)
from omnibase_core.models.delegation.wire.model_delegation_deliverable_evidence import (
    ModelDelegationDeliverableEvidence,
)
from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    EnumQualityContractMode,
    validate_response_contract,
)

EnumQualityGateCategory = EnumQualityGateResult


class ModelQualityGateInput(BaseModel):
    """Gate input: LLM response content and expected quality markers."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Tracks this input back to the original request.",
    )
    task_type: str = Field(
        ...,
        description="The task classification for type-specific checks.",
    )
    llm_response_content: str = Field(
        ...,
        description="The raw LLM response to evaluate.",
    )
    expected_markers: tuple[str, ...] = Field(
        default=(),
        description="Strings expected in the response for the task type.",
    )
    min_response_length: int = Field(
        default=60,
        ge=0,
        description="Minimum acceptable response length in characters.",
    )
    dod_deterministic: tuple[str, ...] = Field(
        default=(),
        description=(
            "Deterministic DoD check names from the task-class contract (OMN-10614). "
            "These checks BLOCK delegation result injection on failure."
        ),
    )
    dod_heuristic: tuple[str, ...] = Field(
        default=(),
        description=(
            "Heuristic DoD check names from the task-class contract (OMN-10614). "
            "These checks escalate per contract policy on failure."
        ),
    )
    quality_contract_mode: EnumQualityContractMode = Field(
        default="extend_task_class",
        description="How request-level acceptance criteria interact with task-class DoD.",
    )
    acceptance_criteria: tuple[str, ...] = Field(
        default=(),
        description="Request-level quality checks enforced by the quality gate.",
    )
    deliverable_evidence: ModelDelegationDeliverableEvidence | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Exact declared-contract extraction evidence. It is required when a "
            "cleaned text deliverable reaches the gate without its raw marker."
        ),
    )
    response_contract: dict[str, object] | None = Field(
        default=None,
        exclude_if=lambda value: value is None,
        description=(
            "Optional caller-declared JSON Schema used as the structural "
            "acceptance authority. None lets the consumer resolve the "
            "task-class default contract."
        ),
    )

    @field_validator("response_contract")
    @classmethod
    def _validate_response_contract(
        cls, response_contract: dict[str, object] | None
    ) -> dict[str, object] | None:
        return validate_response_contract(response_contract)


class ModelQualityRuleEvaluation(BaseModel):
    """One declared rule's own verdict, with the threshold it was judged against.

    OMN-18295. Before this, a delegation terminal carried an aggregate
    ``quality_score``, a ``required_quality_bar``, and a free-text
    ``failed_acceptance_criteria`` list. Those three could disagree with each
    other and did: ``ca144d1a-ea03-475f-bc81-650ccfa0495e`` printed
    ``actual_score=0.900 required_bar=0.800 score_vs_bar=at_or_above_bar`` and
    terminalised ``failed``, with the deciding rule appearing only as an
    unattributed sentence fragment. Nothing said which rule decided, what
    threshold it applied, or whether it was even entitled to decide. The
    250-word limit that actually rejected that response was a literal inside
    the gate's own code: a number a customer was held to that appeared in no
    contract and on no receipt.

    Recorded for PASSING rules too. A record that exists only on failure
    cannot distinguish "this rule passed" from "this rule never ran" — and it
    cannot show a reader that a ``scored`` miss did NOT decide an outcome the
    bar decided.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    rule: str = Field(
        ...,
        min_length=1,
        description="The declared check name, e.g. 'concise'.",
    )
    enforcement: EnumQualityRuleEnforcement = Field(
        ...,
        description=(
            "Whether this rule vetoes acceptance outright ('blocking') or "
            "moves the graded score and leaves the verdict to the required "
            "bar ('scored')."
        ),
    )
    passed: bool = Field(..., description="This rule's own verdict.")
    threshold: int | None = Field(
        default=None,
        ge=0,
        description=(
            "The numeric threshold applied, where the rule declares one. None "
            "means the rule declares no numeric threshold — never zero."
        ),
    )
    threshold_unit: str | None = Field(
        default=None,
        description="What the threshold counts — 'words', 'characters'.",
    )
    detail: str | None = Field(
        default=None,
        description="The failure message, when this rule failed. None on a pass.",
    )

    @field_validator("rule")
    @classmethod
    def _validate_rule_name(cls, rule: str) -> str:
        if not rule.strip():
            msg = "rule must name a declared check, not blank"
            raise ValueError(msg)
        return rule

    @model_validator(mode="after")
    def validate_detail_accompanies_a_failure(self) -> Self:
        """A pass carrying a failure message reads, to a customer, as a failure."""
        if self.passed and self.detail is not None:
            msg = "a rule that passed cannot carry a failure detail"
            raise ValueError(msg)
        return self


class ModelQualityGateResult(BaseModel):
    """Gate output: pass/fail verdict, score, failure reasons, and fallback flag."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Tracks this result back to the original request.",
    )
    passed: bool = Field(
        ..., description="Whether the LLM response passed the quality gate."
    )
    fail_category: EnumQualityGateCategory = Field(
        default=EnumQualityGateResult.PASS,
        description=(
            "Structured outcome: 'pass', 'fail_deterministic' (hard block), "
            "or 'fail_heuristic' (escalate per contract policy)."
        ),
    )
    quality_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Quality score from 0.0 to 1.0.",
    )
    failure_reasons: tuple[str, ...] = Field(
        default=(),
        description="Tuple of human-readable failure reason strings.",
    )
    fallback_recommended: bool = Field(
        default=False,
        description="Whether fallback to Claude is recommended.",
    )


__all__: list[str] = [
    "EnumQualityGateCategory",
    "EnumQualityRuleEnforcement",
    "ModelQualityGateInput",
    "ModelQualityGateResult",
    "ModelQualityRuleEvaluation",
]
