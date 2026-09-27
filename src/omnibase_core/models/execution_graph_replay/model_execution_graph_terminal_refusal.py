# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Typed refusal body for an execution-graph terminal result."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ModelExecutionGraphTerminalRefusal(BaseModel):
    """Actionable reason a signed execution-graph workflow terminally failed."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    code: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
