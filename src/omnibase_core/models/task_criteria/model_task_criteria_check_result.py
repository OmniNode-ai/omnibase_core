# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the task-criteria check (OMN-21535)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelTaskCriteriaCheckResult(BaseModel):
    """Emitted issues and the number of task blocks that were read."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
    task_count: int = Field(description="Task blocks read from the document")
