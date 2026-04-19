# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkflowVerification — verification step in the ticket-work state."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowVerification(BaseModel):
    """A verification step declared during SPEC and executed during REVIEW."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="")
    title: str = Field(default="")
    kind: str = Field(default="unit_tests")
    command: str = Field(default="")
    expected: str = Field(default="exit 0")
    blocking: bool = Field(default=True)
    status: str = Field(default="pending")
    evidence: str | None = Field(default=None)
    executed_at: str | None = Field(default=None)


__all__ = ["ModelWorkflowVerification"]
