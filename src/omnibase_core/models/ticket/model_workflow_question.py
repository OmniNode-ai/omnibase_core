# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ModelWorkflowQuestion — clarifying question raised during the QUESTIONS phase."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelWorkflowQuestion(BaseModel):
    """A clarifying question raised during the QUESTIONS phase of ticket-work."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(default="")
    text: str = Field(default="")
    category: str = Field(default="architecture")
    required: bool = Field(default=True)
    answer: str | None = Field(default=None)
    answered_at: str | None = Field(default=None)


__all__ = ["ModelWorkflowQuestion"]
