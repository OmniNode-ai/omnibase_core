# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval run pair model for paired A/B comparisons."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

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
