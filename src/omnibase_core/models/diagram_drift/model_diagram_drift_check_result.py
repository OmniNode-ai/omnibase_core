# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Deterministic result of the diagram-drift check (OMN-21510)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelDiagramDriftCheckResult(BaseModel):
    """Every issue found, in document order, and what was read."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...] = Field(
        description="Enabled rule violations, ordered by document line"
    )
    exit_code: int = Field(
        description="One for an error or higher severity, otherwise zero"
    )
    diagrams_checked: int = Field(description="Diagram blocks read from the document")
    fragments_found: int = Field(
        description="Contract fragments read from the document"
    )
