# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Issues and block counts produced by the diagram drift predicate."""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.common.model_validation_issue import ModelValidationIssue


class ModelDiagramDriftReport(BaseModel):
    """Every reported issue in document order and the discovered block counts."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    issues: tuple[ModelValidationIssue, ...]
    diagrams_checked: int = Field(ge=0)
    fragments_found: int = Field(ge=0)

    @property
    def exit_code(self) -> int:
        """Return 1 when any issue was reported, otherwise 0."""
        return 1 if self.issues else 0
