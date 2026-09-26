# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Transport-free signed workflow terminal body for execution-graph reads."""

from __future__ import annotations

from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.models.execution_graph_replay.model_execution_graph_replay_view import (
    ModelExecutionGraph,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_terminal_refusal import (
    ModelExecutionGraphTerminalRefusal,
)


class ModelExecutionGraphTerminalResult(BaseModel):
    """Terminal graph-read result bound to the authenticated workflow identity."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    tenant_id: UUID
    correlation_id: UUID
    workflow_type: str = Field(..., min_length=1)
    status: Literal["completed", "failed"]
    result: ModelExecutionGraph | None = None
    refusal: ModelExecutionGraphTerminalRefusal | None = None

    @model_validator(mode="after")
    def validate_terminal_shape(self) -> Self:
        """A completed result has a graph; a failure has exactly one refusal."""
        if self.status == "completed":
            if self.result is None:
                raise ValueError("completed terminal result requires result")
            if self.refusal is not None:
                raise ValueError("completed terminal result cannot include refusal")
            return self
        if self.refusal is None:
            raise ValueError("failed terminal result requires refusal")
        if self.result is not None:
            raise ValueError("failed terminal result cannot include result")
        return self
