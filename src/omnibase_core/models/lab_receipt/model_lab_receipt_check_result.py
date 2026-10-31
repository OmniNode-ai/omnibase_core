# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the lab-receipt check (OMN-21823)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelLabReceiptCheckResult(BaseModel):
    """Issues, the exit code, and why a receipt was or was not required."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
    required: bool = Field(description="Whether the change needs a lab receipt")
    classes: tuple[str, ...] = Field(
        description="Classes of the counted files that made a receipt required"
    )
