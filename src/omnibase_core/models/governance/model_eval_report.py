# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Eval report model for full A/B comparison results."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.governance.model_eval_run_pair import ModelEvalRunPair
from omnibase_core.models.governance.model_eval_summary import ModelEvalSummary


class ModelEvalReport(BaseModel):
    """Full A/B comparison report across all tasks in an eval suite."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    # string-id-ok: opaque eval report correlation identifier, not a DB primary key
    report_id: str = Field(..., description="Unique report identifier", max_length=200)
    # string-id-ok: user-facing suite identifier (e.g., eval-suite-alpha)
    suite_id: str = Field(..., description="Which suite was evaluated", max_length=200)
    # string-version-ok: semver stored as str for YAML wire serialization
    suite_version: str = Field(
        default="",
        description="Version of the suite used for this report",
        max_length=50,
    )
    generated_at: datetime = Field(..., description="When this report was generated")
    pairs: list[ModelEvalRunPair] = Field(
        ..., description="Individual task comparisons"
    )
    summary: ModelEvalSummary = Field(..., description="Aggregated summary statistics")

    @model_validator(mode="after")
    def validate_summary_alignment(self) -> ModelEvalReport:
        if self.summary.total_tasks != len(self.pairs):
            raise ValueError(
                f"summary.total_tasks={self.summary.total_tasks} does not match "
                f"len(pairs)={len(self.pairs)}"
            )
        task_ids = [pair.task_id for pair in self.pairs]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("pairs must contain unique task_id values")
        return self
