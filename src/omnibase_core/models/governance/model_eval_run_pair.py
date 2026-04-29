# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval run pair model for paired A/B comparisons."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.governance.enum_eval_mode import EnumEvalMode
from omnibase_core.enums.governance.enum_eval_verdict import EnumEvalVerdict
from omnibase_core.models.governance.model_eval_run import ModelEvalRun


class ModelEvalRunPair(BaseModel):
    """A paired A/B comparison: same task, ONEX ON vs OFF."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-id-ok: user-facing task identifier (e.g., eval-001-fix-import-error)
    task_id: str = Field(..., description="The task that was compared", max_length=200)
    onex_on_run: ModelEvalRun = Field(..., description="Run with ONEX features enabled")
    onex_off_run: ModelEvalRun = Field(
        ..., description="Run with ONEX features disabled"
    )
    delta_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Per-metric delta (on - off). Negative = ONEX saves.",
    )
    verdict: EnumEvalVerdict = Field(..., description="Overall verdict for this pair")

    @model_validator(mode="after")
    def validate_pair_consistency(self) -> ModelEvalRunPair:
        if (
            self.onex_on_run.task_id != self.task_id
            or self.onex_off_run.task_id != self.task_id
        ):
            raise ValueError(
                "task_id must match both onex_on_run.task_id and onex_off_run.task_id"
            )
        if self.onex_on_run.mode != EnumEvalMode.ONEX_ON:
            raise ValueError("onex_on_run.mode must be ONEX_ON")
        if self.onex_off_run.mode != EnumEvalMode.ONEX_OFF:
            raise ValueError("onex_off_run.mode must be ONEX_OFF")
        return self
