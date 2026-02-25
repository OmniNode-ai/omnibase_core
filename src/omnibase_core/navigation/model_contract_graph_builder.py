# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Contract Graph Builder (OMN-2540).

Implements ContractGraphBuilder which constructs a ContractGraph from a
RegistrySnapshot. Construction is synchronous and idempotent — the same
registry state always produces the same graph.

Design principles:
- No mutable global state
- Edges derived strictly from declared node contracts
- Async-compatible (can be awaited if wrapped in executor)
- JSON-serializable output via ContractGraph model
"""

import logging

from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    ContractTransition,
    RegistrySnapshot,
    TransitionCost,
    TransitionGuard,
)

logger = logging.getLogger(__name__)


class ContractGraphBuilder:
    """Constructs a ContractGraph from a RegistrySnapshot.

    Each call to build() produces a fresh ContractGraph instance with no
    shared mutable state. The same snapshot always produces the same graph
    (idempotent).

    Example:
        >>> snapshot = RegistrySnapshot(nodes=(node_a, node_b))
        >>> builder = ContractGraphBuilder()
        >>> graph = builder.build(snapshot)
        >>> state = graph.get_state("node.a")
    """

    def build(self, snapshot: RegistrySnapshot) -> ContractGraph:
        """Build a ContractGraph from a registry snapshot.

        Args:
            snapshot: The registry snapshot to build from.

        Returns:
            A fully constructed ContractGraph. Every node in the snapshot
            becomes a ContractState. Every declared transition becomes a
            ContractTransition. Transitions referencing unknown target nodes
            are logged and skipped (not silently included as ghost edges).
        """
        logger.debug(
            "Building contract graph from snapshot",
            extra={
                "snapshot_id": snapshot.snapshot_id,
                "node_count": len(snapshot.nodes),
            },
        )

        # Phase 1: Build state index from all registry nodes
        states: dict[str, ContractState] = {}
        for registry_node in snapshot.nodes:
            state = ContractState(
                node_id=registry_node.node_id,
                schema_version=registry_node.schema_version,
                capabilities=frozenset(registry_node.capabilities),
                policy_tier=registry_node.policy_tier,
                metadata=dict(registry_node.metadata),
            )
            states[state.node_id] = state

        # Phase 2: Build transition index and adjacency lists
        transitions: dict[str, ContractTransition] = {}
        # source_node_id -> list of transition_ids
        adjacency_lists: dict[str, list[str]] = {nid: [] for nid in states}
        # target_node_id -> list of transition_ids
        predecessor_lists: dict[str, list[str]] = {nid: [] for nid in states}

        for registry_node in snapshot.nodes:
            source_id = registry_node.node_id
            for decl in registry_node.declared_transitions:
                target_id = decl.target_node_id

                # Validate target exists in the snapshot
                if target_id not in states:
                    logger.warning(
                        "Skipping transition to unknown target node",
                        extra={
                            "transition_id": decl.transition_id,
                            "source_node_id": source_id,
                            "target_node_id": target_id,
                            "snapshot_id": snapshot.snapshot_id,
                        },
                    )
                    continue

                guard = TransitionGuard(
                    required_capabilities=frozenset(decl.required_capabilities),
                    required_schema_version=decl.required_schema_version,
                    policy_tier_max=decl.policy_tier_max,
                    precondition_keys=frozenset(decl.precondition_keys),
                )
                cost = TransitionCost(
                    diff_size_estimate=decl.diff_size_estimate,
                    latency_estimate_ms=decl.latency_estimate_ms,
                )
                transition = ContractTransition(
                    transition_id=decl.transition_id,
                    source_state_id=source_id,
                    target_state_id=target_id,
                    input_types=decl.input_types,
                    output_types=decl.output_types,
                    preconditions=decl.preconditions,
                    guard=guard,
                    cost=cost,
                    label=decl.label,
                )
                transitions[transition.transition_id] = transition
                adjacency_lists[source_id].append(transition.transition_id)
                predecessor_lists[target_id].append(transition.transition_id)

        # Phase 3: Convert lists to immutable tuples for frozen model
        adjacency: dict[str, tuple[str, ...]] = {
            nid: tuple(tids) for nid, tids in adjacency_lists.items()
        }
        predecessors: dict[str, tuple[str, ...]] = {
            nid: tuple(tids) for nid, tids in predecessor_lists.items()
        }

        graph = ContractGraph(
            states=states,
            transitions=transitions,
            adjacency=adjacency,
            predecessors=predecessors,
        )

        logger.debug(
            "Contract graph built",
            extra={
                "snapshot_id": snapshot.snapshot_id,
                "node_count": graph.node_count,
                "edge_count": graph.edge_count,
            },
        )

        return graph


__all__ = ["ContractGraphBuilder"]
