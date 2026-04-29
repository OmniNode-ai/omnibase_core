# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval run model for a single task execution in one mode."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.governance.enum_eval_metric_type import EnumEvalMetricType
from omnibase_core.enums.governance.enum_eval_mode import EnumEvalMode
from omnibase_core.models.governance.model_eval_metric import ModelEvalMetric

_MAX_STRING_LENGTH = 10000


class ModelEvalRun(BaseModel):
    """A single eval run: one task executed in one mode."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-id-ok: UUID stored as str for YAML wire serialization compatibility
    run_id: str = Field(..., description="Unique run identifier (UUID)", max_length=200)
    # string-id-ok: user-facing task identifier (e.g., eval-001-fix-import-error)
    task_id: str = Field(
        ..., description="References ModelEvalTask.task_id", max_length=200
    )
    mode: EnumEvalMode = Field(..., description="ONEX_ON or ONEX_OFF")
    started_at: datetime = Field(..., description="When the run started")
    completed_at: datetime | None = Field(
        default=None,
        description="When the run completed (None if still running or crashed)",
    )
    success: bool = Field(..., description="Whether all success criteria were met")
    metrics: list[ModelEvalMetric] = Field(
        default_factory=list, description="Collected metrics"
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if the run failed",
        max_length=_MAX_STRING_LENGTH,
    )
    git_sha: str = Field(..., description="Commit hash at time of run", max_length=64)
    env_snapshot: dict[str, str] = Field(
        default_factory=dict,
        description="Relevant ENABLE_* flags at time of run",
    )

    def get_metric(self, metric_type: EnumEvalMetricType) -> float | None:
        """Return the value of a specific metric type, or None if not collected."""
        for m in self.metrics:
            if m.metric_type == metric_type:
                return m.value
        return None
