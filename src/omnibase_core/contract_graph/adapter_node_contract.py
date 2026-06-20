# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Read-only dialect adapter: backend node contracts -> Contract Graph IR.

Phase 2 Contract Graph IR (OMN-13132, epic OMN-13129) extended in Phase 3
(OMN-13223) to cover all four structural contract dialects in this repo.

**Four dialects handled by this single adapter (option b — single adapter
proven lossless for all four):**

- ``descriptor`` — contracts with a ``descriptor:`` section (node_archetype,
  purity, idempotent, timeout_ms) and top-level ``publish_topics`` /
  ``subscribe_topics``. The ``descriptor`` metadata is intentionally dropped
  from the IR projection (it is operational metadata, not routing topology);
  the round-trip is zero-diff because ``normalize_node_contract`` also drops it.

- ``event_bus`` — contracts where publish/subscribe topics are nested inside an
  ``event_bus:`` section (``event_bus.publish_topics`` /
  ``event_bus.subscribe_topics``) rather than at the top level. Used by
  orchestrator contracts (e.g. ``node_compliance_orchestrator/contract.yaml``).
  This adapter reads both top-level AND ``event_bus:``-nested topics so they
  appear as edges in the IR and survive the round-trip.

- ``state_machine`` — contracts using ``REDUCER_GENERIC`` / ``EFFECT_GENERIC``
  node_type tokens and a ``state_transitions:`` section (states, transitions,
  FSM operations). The FSM internals are intentionally dropped from the IR
  projection (too deep to be general routing topology); the adapter maps the
  generic node_type to the canonical archetype role and captures any declared
  topics. Zero-diff round-trip is proven against the normalized baseline which
  also omits the state_transitions section.

- ``workflow_coordination`` — contracts using ``ORCHESTRATOR_GENERIC`` node_type
  with a ``workflow_coordination:`` section (workflow_definition, execution_graph,
  sub-node wiring). Same treatment as state_machine: adapter maps the generic
  node_type to ORCHESTRATOR role; workflow_coordination is dropped from the IR
  projection intentionally; zero-diff round-trip proven.

STRICTLY READ-ONLY: the adapter parses a contract dict and produces frozen IR
models; it never mutates the source, performs no I/O, and resolves no endpoints.

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

# node_type token -> IR node role. Covers both canonical lowercase tokens
# (effect/compute/reducer/orchestrator, used by in-repo node contracts) and
# UPPER_GENERIC variants (REDUCER_GENERIC / ORCHESTRATOR_GENERIC /
# EFFECT_GENERIC / COMPUTE_GENERIC, used by contracts/runtime/ contracts that
# carry state_machine or workflow_coordination dialect sections). An unknown
# node_type still fails fast in import_node_contract.
_NODE_TYPE_TO_ROLE: dict[str, EnumContractGraphNodeRole] = {
    # canonical lowercase (descriptor + event_bus dialects)
    "effect": EnumContractGraphNodeRole.EFFECT,
    "compute": EnumContractGraphNodeRole.COMPUTE,
    "reducer": EnumContractGraphNodeRole.REDUCER,
    "orchestrator": EnumContractGraphNodeRole.ORCHESTRATOR,
    # UPPER_GENERIC variants (state_machine + workflow_coordination dialects)
    "EFFECT_GENERIC": EnumContractGraphNodeRole.EFFECT,
    "COMPUTE_GENERIC": EnumContractGraphNodeRole.COMPUTE,
    "REDUCER_GENERIC": EnumContractGraphNodeRole.REDUCER,
    "ORCHESTRATOR_GENERIC": EnumContractGraphNodeRole.ORCHESTRATOR,
}

# Canonical round-trip node_type string per role: always the lowercase token.
# Used by round_trip_node_node to emit a consistent normalized form regardless
# of whether the source used "reducer" or "REDUCER_GENERIC".
_ROLE_TO_CANONICAL_NODE_TYPE: dict[EnumContractGraphNodeRole, str] = {
    EnumContractGraphNodeRole.EFFECT: "effect",
    EnumContractGraphNodeRole.COMPUTE: "compute",
    EnumContractGraphNodeRole.REDUCER: "reducer",
    EnumContractGraphNodeRole.ORCHESTRATOR: "orchestrator",
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
            inspect.getsource(_raw_topic_list),
            inspect.getsource(_node_id_from_source_path),
        ),
    )


def supports_node_contract(data: dict[str, JsonType]) -> bool:
    """True if ``data`` is a backend node contract this adapter imports.

    A node contract is identified by a ``node_type`` whose token is one of the
    canonical archetype tokens (lowercase or UPPER_GENERIC). UI component
    contracts (no ``node_type``) are not matched.
    """
    node_type = data.get("node_type")
    return isinstance(node_type, str) and node_type in _NODE_TYPE_TO_ROLE


def _raw_topic_list(raw: object, label: str) -> tuple[str, ...]:
    """Validate and extract a topic list from a raw value already extracted from the dict.

    Raises ``ValueError`` if the value is not a list of strings — fail fast
    rather than silently dropping malformed entries.
    """
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(  # error-ok: input validation at the contract-import boundary
            f"{label!r} must be a list of topic strings, got {type(raw).__name__}"
        )
    topics: list[str] = []
    for entry in raw:
        if not isinstance(entry, str):
            raise ValueError(  # error-ok: input validation at the contract-import boundary
                f"{label!r} entries must be strings, got {type(entry).__name__}"
            )
        topics.append(entry)
    return tuple(topics)


def _topic_list(data: dict[str, JsonType], key: str) -> tuple[str, ...]:
    """Extract a tuple of topic strings from a top-level contract field.

    Checks the top-level ``key`` first; then checks inside the ``event_bus:``
    nested section if present (``event_bus`` dialect). When a topic is declared
    in both places the union is taken, de-duplicated, preserving order (top-level
    first, then event_bus entries not already included).

    Raises ``ValueError`` if either location has the field but it is not a list
    of strings — fail fast rather than silently dropping malformed entries.
    """
    top_level = _raw_topic_list(data.get(key), key)

    event_bus = data.get("event_bus")
    if not isinstance(event_bus, dict):
        return top_level

    nested = _raw_topic_list(event_bus.get(key), f"event_bus.{key}")
    if not nested:
        return top_level

    # Union: top-level entries first, then any event_bus entries not already seen.
    seen: set[str] = set(top_level)
    combined: list[str] = list(top_level)
    for t in nested:
        if t not in seen:
            combined.append(t)
            seen.add(t)
    return tuple(combined)


def _node_id_from_source_path(source_path: str) -> str:
    """Derive a stable node_id from the source file path when no explicit id is declared.

    Uses the filename stem (without extension) of the source path so contracts
    in the ``state_machine`` / ``workflow_coordination`` dialects (which do not
    declare ``handler_id`` or ``name``) still produce a stable, meaningful id.
    """
    from pathlib import Path  # import-local: avoids module-level Path import

    stem = Path(source_path).stem
    if not stem:
        raise ValueError(  # error-ok: input validation at the contract-import boundary
            f"{source_path}: cannot derive node_id — source path has no stem"
        )
    return stem


def import_node_contract(
    data: dict[str, JsonType],
    source_path: str,
) -> tuple[ModelContractGraphNode, tuple[ModelContractGraphEdge, ...]]:
    """Import one backend node contract into an IR node + its topic edges.

    Returns the node and a deterministically-ordered tuple of publish/subscribe
    edges. ``node_id`` is resolved in priority order:

    1. ``handler_id`` — canonical stable semantic id when declared.
    2. ``name`` — human-readable name as fallback.
    3. ``node_id`` — explicit node identity field (used by some compute contracts).
    4. Filename stem of ``source_path`` — for state_machine / workflow_coordination
       dialect contracts that declare no inline identity (e.g. REDUCER_GENERIC
       contracts in ``contracts/runtime/``).
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
    node_id_field = data.get("node_id")
    node_id_source = (
        handler_id
        if isinstance(handler_id, str) and handler_id
        else (
            name
            if isinstance(name, str) and name
            else (
                node_id_field
                if isinstance(node_id_field, str) and node_id_field
                else _node_id_from_source_path(source_path)
            )
        )
    )
    node_id = str(node_id_source)

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

    The round-trip target is the canonical normalized contract shape: lowercase
    ``node_type`` + ``handler_id`` + ``publish_topics`` / ``subscribe_topics``
    (sorted), plus ``input_model`` / ``output_model`` when the node carries an
    IO protocol.

    The output always uses the canonical lowercase ``node_type`` token (e.g.
    ``"reducer"``) regardless of whether the source used ``"REDUCER_GENERIC"``.
    This is intentional: ``normalize_node_contract`` also normalizes to lowercase,
    so the round-trip comparison is zero-diff for all four dialect variants.
    """
    if node.role not in _ROLE_TO_CANONICAL_NODE_TYPE:
        raise ValueError(  # error-ok: caller passed a non-backend node to this adapter
            f"node role {node.role!r} is not a backend node role; cannot round-trip via this adapter"
        )

    result: dict[str, JsonType] = {
        "handler_id": node.node_id,
        "name": node.title,
        "node_type": _ROLE_TO_CANONICAL_NODE_TYPE[node.role],
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
