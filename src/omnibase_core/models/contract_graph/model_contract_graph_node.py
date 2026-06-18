# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""ContractGraphNode — one node in the Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

DISTINCT from the workflow-viz ``ModelGraphNode`` (``models/graph/``), whose
``node_id`` is a ``UUID`` for orchestrator-graph visualization. This IR node is a
*platform-neutral* representation of one imported contract surface: a backend
node contract or a UI component contract. Its ``node_id`` is a stable semantic
string (not a UUID) so the IR is deterministic across runs.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_contract_graph_node_role import (
    EnumContractGraphNodeRole,
)
from omnibase_core.models.contract_graph.model_contract_graph_contract_ref import (
    ModelContractGraphContractRef,
)
from omnibase_core.models.contract_graph.model_contract_graph_protocol import (
    ModelContractGraphProtocol,
)

__all__ = ["ModelContractGraphNode"]


class ModelContractGraphNode(BaseModel):
    """A platform-neutral IR node for one imported contract surface.

    ``role`` classifies the surface (a backend archetype, a UI ``COMPONENT``, a
    ``RENDERER``, or a ``PROTOCOL``). ``source_ref`` pins the source contract +
    adapter that produced this node (with stable hashes). ``protocols`` carries
    any protocol boundaries the node types against. Topic membership is expressed
    as edges in the IR, not inlined here.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    node_id: str = Field(  # string-id-ok: stable semantic IR node label, not a UUID
        ...,
        description="Stable semantic identifier for this IR node (deterministic across runs)",
        min_length=1,
    )
    role: EnumContractGraphNodeRole = Field(
        ...,
        description="Role this node plays in the IR (effect/compute/reducer/orchestrator/component/renderer/protocol)",
    )
    title: str = Field(
        ...,
        description="Human-readable title of the imported contract surface",
        min_length=1,
    )
    source_ref: ModelContractGraphContractRef = Field(
        ...,
        description="Hashed reference to the source contract + adapter that produced this node",
    )
    protocols: tuple[ModelContractGraphProtocol, ...] = Field(
        default=(),
        description="Protocol/interface boundaries this node types against",
    )
