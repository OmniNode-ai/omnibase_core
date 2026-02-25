# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for Contract Graph Data Model and Builder (OMN-2540).

Covers:
- ContractState, ContractTransition, TransitionGuard, TransitionCost construction
- ContractGraph: node lookup, edge lookup, adjacency, predecessor lookup
- ContractGraphBuilder: empty registry, single-node, multi-node with cycles,
  nodes with no outgoing edges, unknown target nodes skipped
- JSON serialization and deserialization with full fidelity
- Idempotency: same snapshot -> same graph
"""

import json

import pytest

from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    ContractTransition,
    RegistryNode,
    RegistrySnapshot,
    RegistryTransitionDecl,
    TransitionCost,
    TransitionGuard,
)
from omnibase_core.navigation.model_contract_graph_builder import ContractGraphBuilder

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_state(
    node_id: str,
    schema_version: str = "1.0.0",
    capabilities: tuple[str, ...] = (),
    policy_tier: int = 0,
    metadata: dict[str, str] | None = None,
) -> ContractState:
    return ContractState(
        node_id=node_id,
        schema_version=schema_version,
        capabilities=frozenset(capabilities),
        policy_tier=policy_tier,
        metadata=metadata or {},
    )


def make_registry_node(
    node_id: str,
    schema_version: str = "1.0.0",
    capabilities: tuple[str, ...] = (),
    policy_tier: int = 0,
    metadata: dict[str, str] | None = None,
    transitions: tuple[RegistryTransitionDecl, ...] = (),
) -> RegistryNode:
    return RegistryNode(
        node_id=node_id,
        schema_version=schema_version,
        capabilities=capabilities,
        policy_tier=policy_tier,
        metadata=metadata or {},
        declared_transitions=transitions,
    )


def make_transition_decl(
    transition_id: str,
    target_node_id: str,
    input_types: tuple[str, ...] = (),
    output_types: tuple[str, ...] = (),
    preconditions: tuple[str, ...] = (),
    required_capabilities: tuple[str, ...] = (),
    required_schema_version: str | None = None,
    policy_tier_max: int | None = None,
    precondition_keys: tuple[str, ...] = (),
    diff_size_estimate: int = 0,
    latency_estimate_ms: int = 0,
    label: str = "",
) -> RegistryTransitionDecl:
    return RegistryTransitionDecl(
        transition_id=transition_id,
        target_node_id=target_node_id,
        input_types=input_types,
        output_types=output_types,
        preconditions=preconditions,
        required_capabilities=required_capabilities,
        required_schema_version=required_schema_version,
        policy_tier_max=policy_tier_max,
        precondition_keys=precondition_keys,
        diff_size_estimate=diff_size_estimate,
        latency_estimate_ms=latency_estimate_ms,
        label=label,
    )


# ---------------------------------------------------------------------------
# TransitionGuard tests
# ---------------------------------------------------------------------------


class TestTransitionGuard:
    def test_default_guard_is_empty(self) -> None:
        guard = TransitionGuard()
        assert guard.required_capabilities == frozenset()
        assert guard.required_schema_version is None
        assert guard.policy_tier_max is None
        assert guard.precondition_keys == frozenset()

    def test_guard_with_capabilities(self) -> None:
        guard = TransitionGuard(
            required_capabilities=frozenset({"llm.gen", "storage.db"})
        )
        assert "llm.gen" in guard.required_capabilities
        assert "storage.db" in guard.required_capabilities

    def test_guard_frozen(self) -> None:
        guard = TransitionGuard()
        with pytest.raises(Exception):
            guard.policy_tier_max = 5  # type: ignore[misc]

    def test_guard_extra_fields_forbidden(self) -> None:
        with pytest.raises(Exception):
            TransitionGuard(unknown_field="x")  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# TransitionCost tests
# ---------------------------------------------------------------------------


class TestTransitionCost:
    def test_default_cost_is_zero(self) -> None:
        cost = TransitionCost()
        assert cost.diff_size_estimate == 0
        assert cost.latency_estimate_ms == 0
        assert cost.total_cost == 0

    def test_total_cost(self) -> None:
        cost = TransitionCost(diff_size_estimate=3, latency_estimate_ms=100)
        assert cost.total_cost == 103

    def test_negative_values_forbidden(self) -> None:
        with pytest.raises(Exception):
            TransitionCost(diff_size_estimate=-1)
        with pytest.raises(Exception):
            TransitionCost(latency_estimate_ms=-1)


# ---------------------------------------------------------------------------
# ContractState tests
# ---------------------------------------------------------------------------


class TestContractState:
    def test_minimal_state(self) -> None:
        state = ContractState(node_id="node.a", schema_version="1.0.0")
        assert state.node_id == "node.a"
        assert state.schema_version == "1.0.0"
        assert state.capabilities == frozenset()
        assert state.policy_tier == 0
        assert state.metadata == {}

    def test_state_with_all_fields(self) -> None:
        state = ContractState(
            node_id="node.b",
            schema_version="2.1.0",
            capabilities=frozenset({"llm.gen", "storage.db"}),
            policy_tier=2,
            metadata={"env": "prod"},
        )
        assert state.policy_tier == 2
        assert "llm.gen" in state.capabilities

    def test_state_equality_by_node_id(self) -> None:
        a = ContractState(node_id="node.a", schema_version="1.0.0")
        b = ContractState(node_id="node.a", schema_version="2.0.0")
        assert a == b

    def test_state_hash_by_node_id(self) -> None:
        a = ContractState(node_id="node.a", schema_version="1.0.0")
        b = ContractState(node_id="node.a", schema_version="2.0.0")
        assert hash(a) == hash(b)

    def test_state_frozen(self) -> None:
        state = ContractState(node_id="node.a", schema_version="1.0.0")
        with pytest.raises(Exception):
            state.node_id = "node.b"  # type: ignore[misc]

    def test_empty_node_id_forbidden(self) -> None:
        with pytest.raises(Exception):
            ContractState(node_id="", schema_version="1.0.0")

    def test_json_serialization(self) -> None:
        state = ContractState(
            node_id="node.x",
            schema_version="1.0.0",
            capabilities=frozenset({"cap.a"}),
            policy_tier=1,
            metadata={"key": "val"},
        )
        data = json.loads(state.model_dump_json())
        assert data["node_id"] == "node.x"
        assert "cap.a" in data["capabilities"]


# ---------------------------------------------------------------------------
# ContractTransition tests
# ---------------------------------------------------------------------------


class TestContractTransition:
    def test_minimal_transition(self) -> None:
        t = ContractTransition(
            transition_id="t1",
            source_state_id="node.a",
            target_state_id="node.b",
        )
        assert t.transition_id == "t1"
        assert t.input_types == ()
        assert t.output_types == ()
        assert t.preconditions == ()

    def test_transition_with_all_fields(self) -> None:
        guard = TransitionGuard(required_capabilities=frozenset({"llm"}))
        cost = TransitionCost(diff_size_estimate=5, latency_estimate_ms=50)
        t = ContractTransition(
            transition_id="t2",
            source_state_id="node.a",
            target_state_id="node.b",
            input_types=("TypeA",),
            output_types=("TypeB",),
            preconditions=("datasource_ready",),
            guard=guard,
            cost=cost,
            label="Resolve datasource",
        )
        assert "llm" in t.guard.required_capabilities
        assert t.cost.total_cost == 55

    def test_transition_equality_by_id(self) -> None:
        t1 = ContractTransition(
            transition_id="t1", source_state_id="a", target_state_id="b"
        )
        t2 = ContractTransition(
            transition_id="t1", source_state_id="x", target_state_id="y"
        )
        assert t1 == t2

    def test_transition_frozen(self) -> None:
        t = ContractTransition(
            transition_id="t1", source_state_id="a", target_state_id="b"
        )
        with pytest.raises(Exception):
            t.transition_id = "t2"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContractGraph tests
# ---------------------------------------------------------------------------


class TestContractGraph:
    def test_empty_graph(self) -> None:
        g = ContractGraph()
        assert g.node_count == 0
        assert g.edge_count == 0
        assert g.get_state("any") is None
        assert g.get_outgoing_transitions("any") == []
        assert g.get_incoming_transitions("any") == []

    def test_get_state_present(self) -> None:
        state = make_state("node.a")
        g = ContractGraph(
            states={"node.a": state},
            transitions={},
            adjacency={"node.a": ()},
            predecessors={"node.a": ()},
        )
        assert g.get_state("node.a") is state
        assert g.get_state("node.x") is None

    def test_get_outgoing_transitions(self) -> None:
        state_a = make_state("node.a")
        state_b = make_state("node.b")
        t = ContractTransition(
            transition_id="t1", source_state_id="node.a", target_state_id="node.b"
        )
        g = ContractGraph(
            states={"node.a": state_a, "node.b": state_b},
            transitions={"t1": t},
            adjacency={"node.a": ("t1",), "node.b": ()},
            predecessors={"node.a": (), "node.b": ("t1",)},
        )
        outgoing = g.get_outgoing_transitions("node.a")
        assert len(outgoing) == 1
        assert outgoing[0].transition_id == "t1"
        assert g.get_outgoing_transitions("node.b") == []

    def test_get_incoming_transitions(self) -> None:
        state_a = make_state("node.a")
        state_b = make_state("node.b")
        t = ContractTransition(
            transition_id="t1", source_state_id="node.a", target_state_id="node.b"
        )
        g = ContractGraph(
            states={"node.a": state_a, "node.b": state_b},
            transitions={"t1": t},
            adjacency={"node.a": ("t1",), "node.b": ()},
            predecessors={"node.a": (), "node.b": ("t1",)},
        )
        incoming = g.get_incoming_transitions("node.b")
        assert len(incoming) == 1
        assert incoming[0].transition_id == "t1"
        assert g.get_incoming_transitions("node.a") == []

    def test_get_transition(self) -> None:
        t = ContractTransition(
            transition_id="t1", source_state_id="a", target_state_id="b"
        )
        g = ContractGraph(transitions={"t1": t})
        assert g.get_transition("t1") is t
        assert g.get_transition("missing") is None

    def test_node_count_edge_count(self) -> None:
        state_a = make_state("node.a")
        state_b = make_state("node.b")
        t1 = ContractTransition(
            transition_id="t1", source_state_id="node.a", target_state_id="node.b"
        )
        t2 = ContractTransition(
            transition_id="t2", source_state_id="node.b", target_state_id="node.a"
        )
        g = ContractGraph(
            states={"node.a": state_a, "node.b": state_b},
            transitions={"t1": t1, "t2": t2},
        )
        assert g.node_count == 2
        assert g.edge_count == 2

    def test_json_serialization_roundtrip(self) -> None:
        state_a = make_state("node.a")
        state_b = make_state("node.b")
        t = ContractTransition(
            transition_id="t1",
            source_state_id="node.a",
            target_state_id="node.b",
            input_types=("TypeX",),
        )
        g = ContractGraph(
            states={"node.a": state_a, "node.b": state_b},
            transitions={"t1": t},
            adjacency={"node.a": ("t1",), "node.b": ()},
            predecessors={"node.a": (), "node.b": ("t1",)},
        )
        json_str = g.model_dump_json()
        data = json.loads(json_str)
        g2 = ContractGraph.model_validate(data)
        assert g2.node_count == g.node_count
        assert g2.edge_count == g.edge_count
        assert g2.get_state("node.a") is not None
        assert g2.get_transition("t1") is not None


# ---------------------------------------------------------------------------
# ContractGraphBuilder tests
# ---------------------------------------------------------------------------


class TestContractGraphBuilder:
    def setup_method(self) -> None:
        self.builder = ContractGraphBuilder()

    def test_empty_registry(self) -> None:
        snapshot = RegistrySnapshot()
        graph = self.builder.build(snapshot)
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_single_node_no_transitions(self) -> None:
        node = make_registry_node("node.a")
        snapshot = RegistrySnapshot(nodes=(node,))
        graph = self.builder.build(snapshot)
        assert graph.node_count == 1
        assert graph.edge_count == 0
        state = graph.get_state("node.a")
        assert state is not None
        assert state.node_id == "node.a"
        assert graph.get_outgoing_transitions("node.a") == []

    def test_single_node_self_loop(self) -> None:
        """A node can have a transition back to itself (self-loop)."""
        decl = make_transition_decl("t.loop", "node.a")
        node = make_registry_node("node.a", transitions=(decl,))
        snapshot = RegistrySnapshot(nodes=(node,))
        graph = self.builder.build(snapshot)
        assert graph.node_count == 1
        assert graph.edge_count == 1
        outgoing = graph.get_outgoing_transitions("node.a")
        assert len(outgoing) == 1
        assert outgoing[0].transition_id == "t.loop"

    def test_multi_node_linear_chain(self) -> None:
        decl_ab = make_transition_decl("t.ab", "node.b")
        decl_bc = make_transition_decl("t.bc", "node.c")
        node_a = make_registry_node("node.a", transitions=(decl_ab,))
        node_b = make_registry_node("node.b", transitions=(decl_bc,))
        node_c = make_registry_node("node.c")
        snapshot = RegistrySnapshot(nodes=(node_a, node_b, node_c))
        graph = self.builder.build(snapshot)
        assert graph.node_count == 3
        assert graph.edge_count == 2
        assert len(graph.get_outgoing_transitions("node.a")) == 1
        assert len(graph.get_outgoing_transitions("node.b")) == 1
        assert graph.get_outgoing_transitions("node.c") == []
        # Predecessors
        assert len(graph.get_incoming_transitions("node.b")) == 1
        assert len(graph.get_incoming_transitions("node.c")) == 1
        assert graph.get_incoming_transitions("node.a") == []

    def test_multi_node_with_cycle(self) -> None:
        """Builder correctly represents cycles in the graph."""
        decl_ab = make_transition_decl("t.ab", "node.b")
        decl_ba = make_transition_decl("t.ba", "node.a")
        node_a = make_registry_node("node.a", transitions=(decl_ab,))
        node_b = make_registry_node("node.b", transitions=(decl_ba,))
        snapshot = RegistrySnapshot(nodes=(node_a, node_b))
        graph = self.builder.build(snapshot)
        assert graph.node_count == 2
        assert graph.edge_count == 2
        assert len(graph.get_outgoing_transitions("node.a")) == 1
        assert len(graph.get_outgoing_transitions("node.b")) == 1

    def test_unknown_target_node_skipped(self) -> None:
        """Transitions referencing non-existent targets are skipped."""
        decl_ghost = make_transition_decl("t.ghost", "node.nonexistent")
        node_a = make_registry_node("node.a", transitions=(decl_ghost,))
        snapshot = RegistrySnapshot(nodes=(node_a,))
        graph = self.builder.build(snapshot)
        assert graph.node_count == 1
        assert graph.edge_count == 0

    def test_guard_fields_propagated(self) -> None:
        decl = make_transition_decl(
            "t.ab",
            "node.b",
            required_capabilities=("llm.gen",),
            required_schema_version="2.0.0",
            policy_tier_max=3,
            precondition_keys=("datasource",),
        )
        node_a = make_registry_node("node.a", transitions=(decl,))
        node_b = make_registry_node("node.b")
        snapshot = RegistrySnapshot(nodes=(node_a, node_b))
        graph = self.builder.build(snapshot)
        t = graph.get_transition("t.ab")
        assert t is not None
        assert "llm.gen" in t.guard.required_capabilities
        assert t.guard.required_schema_version == "2.0.0"
        assert t.guard.policy_tier_max == 3
        assert "datasource" in t.guard.precondition_keys

    def test_cost_fields_propagated(self) -> None:
        decl = make_transition_decl(
            "t.ab", "node.b", diff_size_estimate=10, latency_estimate_ms=200
        )
        node_a = make_registry_node("node.a", transitions=(decl,))
        node_b = make_registry_node("node.b")
        snapshot = RegistrySnapshot(nodes=(node_a, node_b))
        graph = self.builder.build(snapshot)
        t = graph.get_transition("t.ab")
        assert t is not None
        assert t.cost.diff_size_estimate == 10
        assert t.cost.latency_estimate_ms == 200

    def test_idempotency(self) -> None:
        """Same snapshot always produces same graph."""
        decl_ab = make_transition_decl("t.ab", "node.b")
        node_a = make_registry_node("node.a", transitions=(decl_ab,))
        node_b = make_registry_node("node.b")
        snapshot = RegistrySnapshot(nodes=(node_a, node_b))
        g1 = self.builder.build(snapshot)
        g2 = self.builder.build(snapshot)
        assert g1.node_count == g2.node_count
        assert g1.edge_count == g2.edge_count
        assert set(g1.states.keys()) == set(g2.states.keys())
        assert set(g1.transitions.keys()) == set(g2.transitions.keys())

    def test_capabilities_propagated(self) -> None:
        node = make_registry_node("node.a", capabilities=("llm.gen", "storage.db"))
        snapshot = RegistrySnapshot(nodes=(node,))
        graph = self.builder.build(snapshot)
        state = graph.get_state("node.a")
        assert state is not None
        assert "llm.gen" in state.capabilities
        assert "storage.db" in state.capabilities

    def test_policy_tier_propagated(self) -> None:
        node = make_registry_node("node.a", policy_tier=5)
        snapshot = RegistrySnapshot(nodes=(node,))
        graph = self.builder.build(snapshot)
        state = graph.get_state("node.a")
        assert state is not None
        assert state.policy_tier == 5

    def test_metadata_propagated(self) -> None:
        node = make_registry_node(
            "node.a", metadata={"env": "staging", "owner": "team-x"}
        )
        snapshot = RegistrySnapshot(nodes=(node,))
        graph = self.builder.build(snapshot)
        state = graph.get_state("node.a")
        assert state is not None
        assert state.metadata["env"] == "staging"

    def test_graph_json_serialization(self) -> None:
        decl_ab = make_transition_decl(
            "t.ab", "node.b", input_types=("T1",), output_types=("T2",)
        )
        node_a = make_registry_node("node.a", transitions=(decl_ab,))
        node_b = make_registry_node("node.b")
        snapshot = RegistrySnapshot(nodes=(node_a, node_b))
        graph = self.builder.build(snapshot)
        json_str = graph.model_dump_json()
        data = json.loads(json_str)
        g2 = ContractGraph.model_validate(data)
        assert g2.node_count == graph.node_count
        assert g2.edge_count == graph.edge_count
        t = g2.get_transition("t.ab")
        assert t is not None
        assert "T1" in t.input_types
        assert "T2" in t.output_types
