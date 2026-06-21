# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelHarnessCommand: typed command for the core-resident local runtime harness (OMN-13420)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelHarnessCommand(BaseModel):
    """Typed command published into the harness for the delegation/sea workflows."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(..., description="Correlation ID for the run.")
    workflow: str = Field(..., description="Workflow name (delegation | sea).")
    prompt: str = Field(..., description="Prompt / task description.")
    task_type: str = Field(default="harness", description="Task class for routing.")
    max_tokens: int = Field(default=512, gt=0, description="Inference token budget.")


__all__ = ["ModelHarnessCommand"]
