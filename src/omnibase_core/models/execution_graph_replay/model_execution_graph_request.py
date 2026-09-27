# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Authenticated execution-graph replay request; tenant is not caller input."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphCursorMode,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_cursor import (
    ModelExecutionGraphSourceCursor,
)


class ModelExecutionGraphRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    correlation_id: UUID
    cursor_mode: EnumExecutionGraphCursorMode
    source_cursors: tuple[ModelExecutionGraphSourceCursor, ...] | None = None

    @model_validator(mode="after")
    def reject_duplicate_cursor_keys(self) -> ModelExecutionGraphRequest:
        if self.cursor_mode is EnumExecutionGraphCursorMode.LATEST:
            if self.source_cursors is not None:
                raise ValueError("latest cursor mode cannot accept source_cursors")
            return self
        if not self.source_cursors:
            raise ValueError("bounded cursor mode requires non-empty source_cursors")
        keys = [(cursor.topic, cursor.partition) for cursor in self.source_cursors]
        if len(keys) != len(set(keys)):
            raise ValueError("duplicate source cursor for topic partition")
        return self
