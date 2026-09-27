# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Recorded relation connecting typed graph entities."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphEdgeKind,
    EnumExecutionGraphEndpointKind,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_endpoint import (
    ModelExecutionGraphEndpoint,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_ref import (
    ModelExecutionGraphSourceRef,
)


class ModelExecutionGraphEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(
        min_length=1, description="Deterministic relation key, not event identity"
    )
    from_id: ModelExecutionGraphEndpoint
    to_id: ModelExecutionGraphEndpoint
    kind: EnumExecutionGraphEdgeKind
    evidence_ref: ModelExecutionGraphSourceRef

    @model_validator(mode="after")
    def endpoint_kinds_match_relation(self) -> ModelExecutionGraphEdge:
        expected = {
            EnumExecutionGraphEdgeKind.CAUSED: ("node", "node"),
            EnumExecutionGraphEdgeKind.REROUTED: ("node", "node"),
            EnumExecutionGraphEdgeKind.VERIFIED: ("node", "verdict"),
            EnumExecutionGraphEdgeKind.ANCHORED: ("session_anchor", "node"),
        }[self.kind]
        if (self.from_id.kind, self.to_id.kind) != tuple(
            EnumExecutionGraphEndpointKind(k) for k in expected
        ):
            raise ValueError("edge endpoint kinds do not match relation kind")
        return self
