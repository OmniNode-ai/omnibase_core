# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read-only dialect adapter: backend node contracts -> Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129; plan
docs/plans/2026-06-13-contract-driven-ui-platform-unified-plan.md §8 Phase 2).

Imports an existing ONEX node contract (``node_type`` effect/compute/reducer/
orchestrator, with ``publish_topics`` / ``subscribe_topics`` / ``descriptor`` /
``handler_routing``) into one IR node plus its topic edges. STRICTLY READ-ONLY:
the adapter parses a contract dict and produces frozen IR models; it never
mutates the source, performs no I/O, and resolves no endpoints.

Dialect identity is ``node``. Its version hash covers the source bytes of the
import + round-trip functions so any behavioral change is reflected in the IR's
embedded ``adapter_version_sha256``.
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
from omnibase_core.models.contract_graph.model_contract_graph_protocol import (
    ModelContractGraphProtocol,
)
from omnibase_core.types.type_json import JsonType

__all__ = [
    "DIALECT_NAME",
    "node_contract_adapter_version",
    "supports_node_contract",
    "import_node_contract",
    "round_trip_node_node",
]

DIALECT_NAME = "node"

# node_type token -> IR node role. Closed mapping: an unknown node_type fails
# fast in import_node_contract rather than defaulting silently.
_NODE_TYPE_TO_ROLE: dict[str, EnumContractGraphNodeRole] = {
    "effect": EnumContractGraphNodeRole.EFFECT,
    "compute": EnumContractGraphNodeRole.COMPUTE,
    "reducer": EnumContractGraphNodeRole.REDUCER,
    "orchestrator": EnumContractGraphNodeRole.ORCHESTRATOR,
}


def node_contract_adapter_version() -> str:
    """Stable version hash of this adapter (name + implementing function source)."""
    return adapter_version_sha256(
        DIALECT_NAME,
        (
            inspect.getsource(supports_node_contract),
            inspect.getsource(import_node_contract),
            inspect.getsource(round_trip_node_node),
            inspect.getsource(_topic_list),
        ),
    )


def supports_node_contract(data: dict[str, JsonType]) -> bool:
    """True if ``data`` is a backend node contract this adapter imports.

    A node contract is identified by a ``node_type`` whose token is one of the
    four canonical archetypes. UI component contracts (no ``node_type``) are not
    matched.
    """
    node_type = data.get("node_type")
    return isinstance(node_type, str) and node_type in _NODE_TYPE_TO_ROLE


def _topic_list(data: dict[str, JsonType], key: str) -> tuple[str, ...]:
    """Extract a tuple of topic strings from a contract list field.

    Raises ``ValueError`` if the field is present but not a list of strings —
    fail fast rather than silently dropping malformed entries.
    """
    raw = data.get(key)
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(  # error-ok: input validation at the contract-import boundary
            f"{key!r} must be a list of topic strings, got {type(raw).__name__}"
        )
    topics: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            raise ValueError(  # error-ok: input validation at the contract-import boundary
                f"{key!r} entries must be strings, got {type(entry).__name__}"
            )
        topics.append(entry)
    return tuple(topics)


def import_node_contract(
    data: dict[str, JsonType],
    source_path: str,
) -> tuple[ModelContractGraphNode, tuple[ModelContractGraphEdge, ...]]:
    """Import one backend node contract into an IR node + its topic edges.

    Returns the node and a deterministically-ordered tuple of publish/subscribe
    edges. ``node_id`` is the contract ``handler_id`` (a stable semantic id) or,
    when absent, ``name``. Missing both raises ``ValueError`` (fail fast — no
    synthesized id).
    """
    if not supports_node_contract(data):
        raise ValueError(  # error-ok: input validation at the contract-import boundary
            f"{source_path}: not a backend node contract (node_type must be one of "
            f"{sorted(_NODE_TYPE_TO_ROLE)})"
        )
    node_type = data.get("node_type")
    role = _NODE_TYPE_TO_ROLE[str(node_type)]

    handler_id = data.get("handler_id")
    name = data.get("name")
    node_id_source = handler_id if isinstance(handler_id, str) else name
    if not isinstance(node_id_source, str) or not node_id_source:
        raise ValueError(  # error-ok: input validation at the contract-import boundary
            f"{source_path}: node contract has no handler_id or name to use as node_id"
        )
    node_id = node_id_source

    title_raw = name if isinstance(name, str) and name else node_id
    title = title_raw

    protocols: tuple[ModelContractGraphProtocol, ...] = ()
    input_model = data.get("input_model")
    output_model = data.get("output_model")
    if isinstance(input_model, str) or isinstance(output_model, str):
        protocols = (
            ModelContractGraphProtocol(
                protocol_id=f"{node_id}::io",
                qualified_name=f"{node_id}::handler_io",
                input_model=input_model if isinstance(input_model, str) else None,
                output_model=output_model if isinstance(output_model, str) else None,
            ),
        )

    source_ref = ModelContractGraphContractRef(
        ref_id=node_id,
        source_path=source_path,
        dialect=DIALECT_NAME,
        source_contract_sha256=canonical_contract_sha256(data),
        adapter_version_sha256=node_contract_adapter_version(),
    )

    node = ModelContractGraphNode(
        node_id=node_id,
        role=role,
        title=title,
        source_ref=source_ref,
        protocols=protocols,
    )

    edges: list[ModelContractGraphEdge] = []
    for topic in _topic_list(data, "publish_topics"):
        edges.append(
            ModelContractGraphEdge(
                edge_id=f"{node_id}--publishes-->{topic}",
                source_node_id=node_id,
                target_node_id=topic,
                kind=EnumContractGraphEdgeKind.PUBLISHES,
                topic=topic,
            )
        )
    for topic in _topic_list(data, "subscribe_topics"):
        edges.append(
            ModelContractGraphEdge(
                edge_id=f"{node_id}--subscribes-->{topic}",
                source_node_id=node_id,
                target_node_id=topic,
                kind=EnumContractGraphEdgeKind.SUBSCRIBES,
                topic=topic,
            )
        )
    edges.sort(key=lambda e: e.edge_id)
    return node, tuple(edges)


def round_trip_node_node(
    node: ModelContractGraphNode,
    edges: tuple[ModelContractGraphEdge, ...],
) -> dict[str, JsonType]:
    """Round-trip one IR node + its edges back to canonical normalized node form.

    The round-trip target is the canonical normalized contract shape this
    adapter reads: ``node_type`` + ``handler_id`` + ``publish_topics`` /
    ``subscribe_topics`` (sorted), plus ``input_model`` / ``output_model`` when
    the node carries an IO protocol. A no-op round-trip of an imported contract
    reproduces these semantic fields so ``cli_contract_diff`` reports zero diff.
    """
    role_to_node_type = {v: k for k, v in _NODE_TYPE_TO_ROLE.items()}
    if node.role not in role_to_node_type:
        raise ValueError(  # error-ok: caller passed a non-backend node to this adapter
            f"node role {node.role!r} is not a backend node role; cannot round-trip via this adapter"
        )

    result: dict[str, JsonType] = {
        "handler_id": node.node_id,
        "name": node.title,
        "node_type": role_to_node_type[node.role],
    }

    publishes = sorted(
        e.topic
        for e in edges
        if e.source_node_id == node.node_id
        and e.kind is EnumContractGraphEdgeKind.PUBLISHES
        and e.topic is not None
    )
    subscribes = sorted(
        e.topic
        for e in edges
        if e.source_node_id == node.node_id
        and e.kind is EnumContractGraphEdgeKind.SUBSCRIBES
        and e.topic is not None
    )
    if publishes:
        result["publish_topics"] = list(publishes)
    if subscribes:
        result["subscribe_topics"] = list(subscribes)

    for protocol in node.protocols:
        if protocol.input_model is not None:
            result["input_model"] = protocol.input_model
        if protocol.output_model is not None:
            result["output_model"] = protocol.output_model

    return result
