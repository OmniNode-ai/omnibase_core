# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the design-record check (OMN-21509)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelDesignRecordCheckResult(BaseModel):
    """Emitted issues and facts computed independently of rule enablement."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
    record_issue_count: int = Field(description="Number of emitted issues")
    failure_mode_rows: int = Field(
        description="Rows in the first matching failure-mode table"
    )
    rows_without_detector_or_gap: int = Field(
        description="Rows lacking a detector or explicit gap mark"
    )
    live_check_command_present: bool = Field(
        description="Whether the command field is nonempty"
    )
    live_check_failing_reading: bool = Field(
        description="Whether the failing reading field is nonempty"
    )
