# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Terminal evidence returned by a model-swap validator."""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.enum_model_swap_cost_measurement_source import (
    EnumModelSwapCostMeasurementSource,
)
from omnibase_core.enums.enum_model_swap_decision import EnumModelSwapDecision
from omnibase_core.enums.enum_model_swap_judge_mode import EnumModelSwapJudgeMode
from omnibase_core.enums.enum_model_swap_validation_failure import (
    EnumModelSwapValidationFailure,
)
from omnibase_core.enums.enum_model_swap_validation_status import (
    EnumModelSwapValidationStatus,
)
from omnibase_core.models.model_swap_validation.model_model_swap_validation_case import (
    ModelModelSwapValidationCase,
)
from omnibase_core.models.model_swap_validation.model_model_swap_validation_gate import (
    ModelModelSwapValidationGate,
)
from omnibase_core.models.model_swap_validation.model_model_swap_validation_gateway_call import (
    ModelModelSwapValidationGatewayCall,
)


class ModelModelSwapValidationResult(BaseModel):
    """Evidence only: consumers retain ownership of every routing decision.

    Pin and report fields are optional on preflight failures, because a refused
    request has not run an image or produced a report. A completed validation
    must identify its image, tool version and reported decision.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, allow_inf_nan=False
    )

    correlation_id: UUID
    status: EnumModelSwapValidationStatus
    failure_reason: EnumModelSwapValidationFailure | None = None
    tool_commit: str | None = Field(default=None, pattern=r"^[0-9a-f]{40}$")
    image_digest: str | None = Field(default=None, pattern=r"^sha256:[0-9a-f]{64}$")
    decision: EnumModelSwapDecision | None = None
    reported_decision: EnumModelSwapDecision | None = Field(
        default=None,
        description="Raw scoring verdict before recommendation eligibility gates",
    )
    recommendation_effective: bool | None = Field(
        default=None, description="Whether the reported recommendation is eligible"
    )
    recommended_model: str | None = Field(default=None, min_length=1)
    lower_bound: float | None = Field(default=None, ge=0, le=1)
    quality_floor: float = Field(gt=0.8, lt=1.0)
    gates: tuple[ModelModelSwapValidationGate, ...] = ()
    per_case: tuple[ModelModelSwapValidationCase, ...] = ()
    judge_model: str | None = Field(default=None, min_length=1)
    judge_mode: EnumModelSwapJudgeMode
    gateway_calls: tuple[ModelModelSwapValidationGatewayCall, ...] = ()
    provider_reported_cost_usd: float = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0, ge=0)
    tool_estimated_cost_usd: float | None = Field(default=None, ge=0)
    tool_cost_measurement_source: EnumModelSwapCostMeasurementSource = (
        EnumModelSwapCostMeasurementSource.ESTIMATED_LIST_PRICE
    )
    exit_code: int | None = None
    tool_error_code: str | None = None
    evidence_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_terminal(self) -> ModelModelSwapValidationResult:
        """Refuse contradictory terminal or cost evidence."""
        if self.status == EnumModelSwapValidationStatus.COMPLETED:
            if self.failure_reason is not None:
                raise ValueError("completed validation cannot carry a failure reason")
            if (
                self.decision is None
                or self.tool_commit is None
                or self.image_digest is None
            ):
                raise ValueError(
                    "completed validation requires a decision, tool commit and image digest"
                )
        elif self.failure_reason is None:
            raise ValueError("failed validation requires a failure reason")
        if (
            self.recommended_model is not None
            and self.decision != EnumModelSwapDecision.RECOMMEND
        ):
            raise ValueError("only a recommend decision can name a recommended model")
        if (
            self.tool_cost_measurement_source
            != EnumModelSwapCostMeasurementSource.ESTIMATED_LIST_PRICE
        ):
            raise ValueError("the tool's own cost is always an estimated list price")
        return self


__all__ = ["ModelModelSwapValidationResult"]
