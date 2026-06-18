# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read-only dialect adapter: UI component contracts -> Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

Imports a Phase-0 ``ModelComponentContract`` instance (or its serialized dict)
into one IR ``COMPONENT`` node, plus ``ACTION_EMITS`` edges (one per declared
command-emitting action) and ``DATA_BINDS`` edges (one per projection binding).
STRICTLY READ-ONLY: parses the component contract and produces frozen IR models;
no mutation, no I/O.

Dialect identity is ``ui_component``.
"""

from __future__ import annotations

import inspect

from omnibase_core.contract_graph.canonical_hash import (
    adapter_version_sha256,
    canonical_contract_sha256,
)
from omnibase_core.enums.enum_contract_graph_edge_kind import (
    EnumContractGraphEdgeKind,
)
from omnibase_core.enums.enum_contract_graph_node_role import (
    EnumContractGraphNodeRole,
)
from omnibase_core.models.contract_graph.model_contract_graph_contract_ref import (
    ModelContractGraphContractRef,
)
from omnibase_core.models.contract_graph.model_contract_graph_edge import (
    ModelContractGraphEdge,
)
from omnibase_core.models.contract_graph.model_contract_graph_node import (
    ModelContractGraphNode,
)
from omnibase_core.models.dashboard.model_component_contract import (
    ModelComponentContract,
)
from omnibase_core.types.type_json import JsonType

__all__ = [
    "DIALECT_NAME",
    "ui_component_adapter_version",
    "supports_ui_component",
    "import_ui_component",
    "round_trip_ui_component",
]

DIALECT_NAME = "ui_component"


def ui_component_adapter_version() -> str:
    """Stable version hash of this adapter (name + implementing function source)."""
    return adapter_version_sha256(
        DIALECT_NAME,
        (
            inspect.getsource(supports_ui_component),
            inspect.getsource(import_ui_component),
            inspect.getsource(round_trip_ui_component),
        ),
    )


def supports_ui_component(data: dict[str, JsonType]) -> bool:
    """True if ``data`` is a serialized UI component contract.

    Identified by the presence of a ``component_id`` and ``component_kind``
    (the required ``ModelComponentContract`` discriminating fields) and the
    absence of a backend ``node_type``.
    """
    return (
        "component_id" in data and "component_kind" in data and "node_type" not in data
    )


def import_ui_component(
    contract: ModelComponentContract,
    source_path: str,
) -> tuple[ModelContractGraphNode, tuple[ModelContractGraphEdge, ...]]:
    """Import one UI component contract into a COMPONENT IR node + edges.

    Produces one ``ACTION_EMITS`` edge per declared action (target = the action's
    command topic) and one ``DATA_BINDS`` edge per data binding (target = the
    binding's projection topic). Edges are deterministically ordered by id.
    """
    node_id = contract.component_id
    source_ref = ModelContractGraphContractRef(
        ref_id=node_id,
        source_path=source_path,
        dialect=DIALECT_NAME,
        source_contract_sha256=canonical_contract_sha256(
            contract.model_dump(mode="json")
        ),
        adapter_version_sha256=ui_component_adapter_version(),
    )

    node = ModelContractGraphNode(
        node_id=node_id,
        role=EnumContractGraphNodeRole.COMPONENT,
        title=contract.title,
        source_ref=source_ref,
        protocols=(),
    )

    edges: list[ModelContractGraphEdge] = []
    for action in contract.actions:
        edges.append(
            ModelContractGraphEdge(
                edge_id=f"{node_id}--action_emits-->{action.command_topic}",
                source_node_id=node_id,
                target_node_id=action.command_topic,
                kind=EnumContractGraphEdgeKind.ACTION_EMITS,
                topic=action.command_topic,
            )
        )
    for binding in contract.data_bindings:
        edges.append(
            ModelContractGraphEdge(
                edge_id=f"{node_id}--data_binds-->{binding.projection_topic}",
                source_node_id=node_id,
                target_node_id=binding.projection_topic,
                kind=EnumContractGraphEdgeKind.DATA_BINDS,
                topic=binding.projection_topic,
            )
        )
    edges.sort(key=lambda e: e.edge_id)
    return node, tuple(edges)


def round_trip_ui_component(
    node: ModelContractGraphNode,
    edges: tuple[ModelContractGraphEdge, ...],
) -> dict[str, JsonType]:
    """Round-trip a COMPONENT IR node + edges back to canonical normalized form.

    The round-trip target is the canonical normalized component shape: the
    component id, kind, title, plus the sorted command topics it emits and the
    sorted projection topics it binds. A no-op round-trip reproduces these
    semantic fields so ``cli_contract_diff`` reports zero diff against the
    normalized source.
    """
    if node.role is not EnumContractGraphNodeRole.COMPONENT:
        raise ValueError(  # error-ok: caller passed a non-component node to this adapter
            f"node role {node.role!r} is not a UI component role; cannot round-trip via this adapter"
        )

    emits = sorted(
        e.topic
        for e in edges
        if e.source_node_id == node.node_id
        and e.kind is EnumContractGraphEdgeKind.ACTION_EMITS
        and e.topic is not None
    )
    binds = sorted(
        e.topic
        for e in edges
        if e.source_node_id == node.node_id
        and e.kind is EnumContractGraphEdgeKind.DATA_BINDS
        and e.topic is not None
    )

    result: dict[str, JsonType] = {
        "component_id": node.node_id,
        "title": node.title,
    }
    if emits:
        result["action_command_topics"] = list(emits)
    if binds:
        result["data_binding_projection_topics"] = list(binds)
    return result
