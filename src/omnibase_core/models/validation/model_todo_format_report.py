# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""The findings of one todo-format run (OMN-20068)."""

from pydantic import BaseModel, ConfigDict

from omnibase_core.models.validation.model_todo_format_finding import (
    ModelTodoFormatFinding,
)

__all__ = ["ModelTodoFormatReport"]


class ModelTodoFormatReport(BaseModel):
    """The findings of one todo-format run (OMN-20068)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    findings: tuple[ModelTodoFormatFinding, ...] = ()
