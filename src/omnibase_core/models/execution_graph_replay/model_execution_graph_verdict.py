# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
"""Recorded DoD verdict admitted to an execution graph."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphVerdictOutcome,
    EnumExecutionGraphVerdictStatus,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref import (
    ModelExecutionGraphSourceRef,
)


class ModelExecutionGraphVerdict(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID
    delegation_correlation_id: UUID
    status: EnumExecutionGraphVerdictStatus
    outcome: EnumExecutionGraphVerdictOutcome
    outcome_refusal: str | None = None
    source_ref: ModelExecutionGraphSourceRef
