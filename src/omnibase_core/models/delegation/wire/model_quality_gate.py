# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Delegation quality gate wire DTOs."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_quality_gate_result import EnumQualityGateResult
from omnibase_core.models.delegation.wire.model_delegation_wire_request import (
    EnumQualityContractMode,
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
    "ModelQualityGateInput",
    "ModelQualityGateResult",
]
