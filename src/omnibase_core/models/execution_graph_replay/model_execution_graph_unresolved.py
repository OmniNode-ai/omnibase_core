# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Recorded evidence whose graph relation cannot be resolved."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphUnresolvedReason,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref import (
    ModelExecutionGraphSourceRef,
)


class ModelExecutionGraphUnresolved(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    subject_id: UUID
    reason: EnumExecutionGraphUnresolvedReason
    source_ref: ModelExecutionGraphSourceRef
