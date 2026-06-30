# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""ModelHarnessTerminal: terminal-event payload for the harness workflows (OMN-13420)."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ModelHarnessTerminal(BaseModel):
    """Terminal event payload for both harness workflows."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    correlation_id: UUID = Field(..., description="Correlation ID for the run.")
    workflow: str = Field(..., description="Workflow name (delegation | sea).")
    status: str = Field(..., description="Terminal status: success | failure.")
    completion: str = Field(..., description="Inference completion text.")
    model: str = Field(..., description="Model that produced the completion.")
    adapter: str = Field(..., description="Inference adapter provenance.")
    source: str = Field(default="harness", description="Terminal producer identifier.")


__all__ = ["ModelHarnessTerminal"]
