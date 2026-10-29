# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Typed output for the pull-request workflow ratchet COMPUTE validator."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.nodes.pull_request_workflow_ratchet_check.model_pull_request_workflow_ratchet_gap_entry import (
    ModelPullRequestWorkflowRatchetGapEntry,
)


class ModelPullRequestWorkflowRatchetCheckOutput(BaseModel):
    """Ratchet gaps; an empty list means the ratchet holds."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    gaps: list[ModelPullRequestWorkflowRatchetGapEntry] = Field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True iff the ratchet holds."""
        return not self.gaps
