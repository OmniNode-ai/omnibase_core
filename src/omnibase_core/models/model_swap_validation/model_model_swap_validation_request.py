# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Platform-neutral request for evidence about one candidate model."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.constants.constants_model_swap_validation import (
    MODEL_SWAP_QUALITY_FLOOR_BOUNDS,
)
from omnibase_core.enums.enum_model_swap_answer_source import EnumModelSwapAnswerSource
from omnibase_core.enums.enum_model_swap_judge_mode import EnumModelSwapJudgeMode


class ModelModelSwapValidationRequest(BaseModel):
    """Validate one model substitution without authorizing a routing change.

    A missing work-unit repository remains representable so the effect handler
    can publish a typed repository-refused terminal before any external call.
    """

    model_config = ConfigDict(
        frozen=True, extra="forbid", from_attributes=True, allow_inf_nan=False
    )

    correlation_id: UUID
    task_type: str = Field(min_length=1)
    reference_model: str = Field(min_length=1)
    candidate_model: str = Field(min_length=1)
    judge_mode: EnumModelSwapJudgeMode
    judge_backend_id: str | None = Field(default=None, min_length=1)
    answer_source: EnumModelSwapAnswerSource
    replay_set_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    quality_floor: Annotated[float, MODEL_SWAP_QUALITY_FLOOR_BOUNDS]
    max_cost_usd: float = Field(gt=0)
    work_unit_repository: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def validate_backend(self) -> ModelModelSwapValidationRequest:
        """Require an explicitly selected backend when using a real judge."""
        if (
            self.judge_mode == EnumModelSwapJudgeMode.BACKEND
            and self.judge_backend_id is None
        ):
            raise ValueError("judge_backend_id is required for backend judge mode")
        return self


__all__ = ["ModelModelSwapValidationRequest"]
