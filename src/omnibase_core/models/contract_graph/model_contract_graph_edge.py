# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContractGraphEdge — one typed relationship in the Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

DISTINCT from the workflow-viz ``ModelGraphEdge`` (``models/graph/``). This IR
edge connects two ``ModelContractGraphNode`` by their stable semantic
``node_id`` and carries a typed ``kind`` (publishes / subscribes /
implements_protocol / component_renders / action_emits / data_binds). When the
edge concerns a topic (publish/subscribe/emit/bind), ``topic`` names it.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_graph_edge_kind import (
    EnumContractGraphEdgeKind,
)

__all__ = ["ModelContractGraphEdge"]


class ModelContractGraphEdge(BaseModel):
    """A typed directed relationship between two IR nodes.

    ``source_node_id`` and ``target_node_id`` reference ``ModelContractGraphNode``
    ids. ``kind`` is the typed relationship; ``topic`` carries the canonical topic
    name for topic-bearing kinds (publishes / subscribes / action_emits /
    data_binds) and is ``None`` for ``implements_protocol`` and
    ``component_renders``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    edge_id: str = Field(  # string-id-ok: stable semantic IR edge label, not a UUID
        ...,
        description="Stable semantic identifier for this IR edge (deterministic across runs)",
        min_length=1,
    )
    source_node_id: str = Field(  # string-id-ok: references a ModelContractGraphNode id
        ...,
        description="node_id of the source IR node",
        min_length=1,
    )
    target_node_id: str = Field(  # string-id-ok: references a ModelContractGraphNode id
        ...,
        description="node_id of the target IR node",
        min_length=1,
    )
    kind: EnumContractGraphEdgeKind = Field(
        ...,
        description="Typed relationship between the two nodes",
    )
    topic: str | None = Field(
        default=None,
        description="Canonical topic for topic-bearing edges; None for protocol/render edges",
    )
