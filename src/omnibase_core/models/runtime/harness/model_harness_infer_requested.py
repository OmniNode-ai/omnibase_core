# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelHarnessInferRequested: intermediate harness event (OMN-13420)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelHarnessInferRequested(BaseModel):
    """Intermediate event: the orchestrator has requested inference."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(..., description="Correlation ID for the run.")
    workflow: str = Field(..., description="Workflow name (delegation | sea).")
    prompt: str = Field(..., description="Prompt to complete.")
    max_tokens: int = Field(default=512, gt=0, description="Inference token budget.")


__all__ = ["ModelHarnessInferRequested"]
