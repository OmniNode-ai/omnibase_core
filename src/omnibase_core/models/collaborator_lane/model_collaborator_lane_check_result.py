# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the collaborator-lane check (OMN-21599)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelCollaboratorLaneCheckResult(BaseModel):
    """Emitted issues and the exit code that follows from their severity."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
