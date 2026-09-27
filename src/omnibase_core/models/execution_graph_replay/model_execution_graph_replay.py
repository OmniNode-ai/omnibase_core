# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT
from __future__ import annotations

"""Deterministic execution graph replay payload."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from omnibase_core.enums.execution_graph_replay import (
    EnumExecutionGraphEndpointKind,
    EnumExecutionGraphRefusalReason,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_anchor import (
    ModelExecutionGraphAnchor,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_edge import (
    ModelExecutionGraphEdge,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_node import (
    ModelExecutionGraphNode,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_replay_policy import (
    ModelExecutionGraphReplayPolicy,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_source_cursor import (
    ModelExecutionGraphSourceCursor,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_topology_version import (
    ModelExecutionGraphTopologyVersion,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_unresolved import (
    ModelExecutionGraphUnresolved,
)
from omnibase_core.models.execution_graph_replay.model_execution_graph_verdict import (
    ModelExecutionGraphVerdict,
)
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelExecutionGraphReplay(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    fold_version: ModelSemVer
    topology_version: ModelExecutionGraphTopologyVersion
    grader_version: ModelSemVer
    verdict_reducer_version: ModelSemVer
    policy: ModelExecutionGraphReplayPolicy
    source_cursors: tuple[ModelExecutionGraphSourceCursor, ...]
    correlation_id: UUID
    anchor: ModelExecutionGraphAnchor
    nodes: tuple[ModelExecutionGraphNode, ...]
    edges: tuple[ModelExecutionGraphEdge, ...]
    order: tuple[UUID, ...]
    verdicts: tuple[ModelExecutionGraphVerdict, ...]
    unresolved: tuple[ModelExecutionGraphUnresolved, ...]
    withheld_count: int = Field(ge=0)
    refusal: EnumExecutionGraphRefusalReason | None = None

    @model_validator(mode="after")
    def validate_identity_and_order(self) -> ModelExecutionGraphReplay:
        cursor_keys = [
            (cursor.topic, cursor.partition) for cursor in self.source_cursors
        ]
        if len(cursor_keys) != len(set(cursor_keys)):
            raise ValueError("duplicate source cursor for topic partition")
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("duplicate envelope id in replay node set")
        ids = set(node_ids)
        if len(self.order) != len(set(self.order)) or set(self.order) != ids:
            raise ValueError("order must list each replay node id exactly once")
        verdict_ids = {verdict.id for verdict in self.verdicts}
        for edge in self.edges:
            for endpoint in (edge.from_id, edge.to_id):
                if endpoint.kind is EnumExecutionGraphEndpointKind.NODE:
                    if endpoint.node_id not in ids:
                        raise ValueError("node endpoint must refer to a graph node")
                elif endpoint.kind is EnumExecutionGraphEndpointKind.VERDICT:
                    if endpoint.verdict_id not in verdict_ids:
                        raise ValueError(
                            "verdict endpoint must refer to a graph verdict"
                        )
                elif endpoint.session_id != self.anchor.session_id:
                    raise ValueError("session endpoint must match the graph anchor")
        return self
