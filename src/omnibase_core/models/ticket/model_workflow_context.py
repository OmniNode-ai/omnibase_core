# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkflowContext — research context embedded in ModelTicketWorkflowState."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowContext(BaseModel):
    """Research context populated during the RESEARCH phase of ticket-work."""

    model_config = ConfigDict(extra="forbid")

    relevant_files: list[str] = Field(default_factory=list)
    patterns_found: list[str] = Field(default_factory=list)
    notes: str = Field(default="")


__all__ = ["ModelWorkflowContext"]
