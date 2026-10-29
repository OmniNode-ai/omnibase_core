# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""One count-locked-ratchet gap, as returned by the COMPUTE node."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ModelPullRequestWorkflowRatchetGapEntry(BaseModel):
    """A single ratchet gap: the workflow file, the failure code, the detail."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    workflow_file: str
    code: str
    detail: str

    def format(self) -> str:
        return f"  {self.workflow_file} [{self.code}] — {self.detail}"
