# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Recorded envelope node in an execution graph."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphNodeKind,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref import (
    ModelExecutionGraphSourceRef,
)


class ModelExecutionGraphNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: UUID  # Recorded envelope_id; never a derived identity.
    kind: EnumExecutionGraphNodeKind
    topic: str
    partition: int
    kafka_offset: int
    parent_envelope_id: UUID | None = None
    replay_green: bool | None
    verifier_verdict: str | None = None
    source_ref: ModelExecutionGraphSourceRef

    @model_validator(mode="after")
    def validate_source_and_grade(self) -> ModelExecutionGraphNode:
        if (self.topic, self.partition, self.kafka_offset) != (
            self.source_ref.topic,
            self.source_ref.partition,
            self.source_ref.kafka_offset,
        ):
            raise ValueError("source_ref must match the node's ledger position")
        if self.kind is EnumExecutionGraphNodeKind.REROUTE_EVIDENCE and (
            self.replay_green is not None or self.verifier_verdict is not None
        ):
            raise ValueError("re-route evidence nodes are not graded")
        return self
