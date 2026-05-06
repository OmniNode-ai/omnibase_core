# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelEscalationEvent: structured event emitted on model escalation (OMN-10617)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_quality_gate_result import (
    EnumQualityGateResult,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelEscalationEvent(BaseModel):
    """Emitted by the delegation orchestrator FSM when a model escalation occurs.

    Escalation happens when the current model fails a quality gate and the
    orchestrator selects the next model in the escalation chain. The stopping
    rule (max_attempts) is enforced by the orchestrator; this model carries the
    audit trail for a single escalation step.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(
        ...,
        description="Ties this event to the originating delegation request.",
    )
    prior_model: str = Field(
        ...,
        description="Identifier of the model that failed the quality gate.",
    )
    next_model: str = Field(
        ...,
        description="Identifier of the model selected for the next attempt.",
    )
    reason: str = Field(
        ...,
        description="Human-readable explanation of why escalation occurred.",
    )
    quality_gate_result: EnumQualityGateResult = Field(
        ...,
        description="Gate verdict that triggered this escalation.",
    )
    attempt_number: int = Field(
        ...,
        ge=1,
        description="Current attempt number (1-indexed); must be >= 1.",
    )
    max_attempts: int = Field(
        ...,
        ge=1,
        description="Maximum number of attempts allowed by the orchestrator contract.",
    )
    contract_version: ModelSemVer = Field(
        ...,
        description="Delegation orchestrator contract version at time of escalation.",
    )

    @model_validator(mode="after")
    def _attempt_within_bounds(self) -> ModelEscalationEvent:
        if self.attempt_number > self.max_attempts:
            msg = (
                f"attempt_number ({self.attempt_number}) must not exceed "
                f"max_attempts ({self.max_attempts})"
            )
            raise ValueError(msg)
        return self


__all__ = ["ModelEscalationEvent"]
