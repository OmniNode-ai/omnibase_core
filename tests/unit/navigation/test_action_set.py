# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for Typed Action Set Enumeration (OMN-2546).

Covers:
- TypedAction type definition and validation
- ActionSetEnumerator.enumerate() returns only guard-passing transitions
- Precondition evaluation prunes unavailable transitions
- Policy tier mismatch causes exclusion (not error)
- Capability mismatch causes exclusion
- Schema version mismatch causes exclusion
- Precondition metadata key missing causes exclusion
- State with no outgoing edges -> empty list
- State with multiple transitions -> filtered correctly
- Result is ordered by cost (cheaper first), then transition_id
- Empty action set is valid (terminal state)
"""

import pytest

from omnibase_core.navigation.model_action_set import ActionSetEnumerator, TypedAction
from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    ContractTransition,
    TransitionCost,
    TransitionGuard,
)

# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def make_state(
    node_id: str,
    schema_version: str = "1.0.0",
    capabilities: frozenset[str] | None = None,
    policy_tier: int = 0,
    metadata: dict[str, str] | None = None,
) -> ContractState:
    return ContractState(
        node_id=node_id,
        schema_version=schema_version,
        capabilities=capabilities or frozenset(),
        policy_tier=policy_tier,
        metadata=metadata or {},
    )


def make_transition(
    transition_id: str,
    source_id: str,
    target_id: str,
    input_types: tuple[str, ...] = (),
    output_types: tuple[str, ...] = (),
    required_capabilities: frozenset[str] | None = None,
    required_schema_version: str | None = None,
    policy_tier_max: int | None = None,
    precondition_keys: frozenset[str] | None = None,
    diff_size: int = 0,
    latency: int = 0,
    label: str = "",
) -> ContractTransition:
    guard = TransitionGuard(
        required_capabilities=required_capabilities or frozenset(),
        required_schema_version=required_schema_version,
        policy_tier_max=policy_tier_max,
        precondition_keys=precondition_keys or frozenset(),
    )
    cost = TransitionCost(diff_size_estimate=diff_size, latency_estimate_ms=latency)
    return ContractTransition(
        transition_id=transition_id,
        source_state_id=source_id,
        target_state_id=target_id,
        input_types=input_types,
        output_types=output_types,
        guard=guard,
        cost=cost,
        label=label,
    )


def make_graph_with_transitions(
    source_id: str,
    target_id: str,
    transitions: list[ContractTransition],
    source_state: ContractState | None = None,
) -> ContractGraph:
    """Build a minimal ContractGraph for enumeration tests."""
    src = source_state or make_state(source_id)
    tgt = make_state(target_id)
    transition_map = {t.transition_id: t for t in transitions}
    adjacency = {source_id: tuple(t.transition_id for t in transitions), target_id: ()}
    predecessors = {
        source_id: (),
        target_id: tuple(t.transition_id for t in transitions),
    }
    return ContractGraph(
        states={source_id: src, target_id: tgt},
        transitions=transition_map,
        adjacency=adjacency,
        predecessors=predecessors,
    )


# ---------------------------------------------------------------------------
# TypedAction tests
# ---------------------------------------------------------------------------


class TestTypedAction:
    def test_minimal_typed_action(self) -> None:
        action = TypedAction(
            transition_id="t1",
            source_state_id="node.a",
            target_state_id="node.b",
        )
        assert action.transition_id == "t1"
        assert action.input_type_signature == ()
        assert action.output_type_signature == ()
        assert action.total_cost == 0

    def test_total_cost(self) -> None:
        action = TypedAction(
            transition_id="t1",
            source_state_id="node.a",
            target_state_id="node.b",
            diff_size_estimate=3,
            latency_estimate_ms=100,
        )
        assert action.total_cost == 103

    def test_typed_action_equality(self) -> None:
        a = TypedAction(transition_id="t1", source_state_id="a", target_state_id="b")
        b = TypedAction(transition_id="t1", source_state_id="x", target_state_id="y")
        assert a == b

    def test_typed_action_hash(self) -> None:
        a = TypedAction(transition_id="t1", source_state_id="a", target_state_id="b")
        b = TypedAction(transition_id="t1", source_state_id="x", target_state_id="y")
        assert hash(a) == hash(b)

    def test_typed_action_frozen(self) -> None:
        action = TypedAction(
            transition_id="t1",
            source_state_id="node.a",
            target_state_id="node.b",
        )
        with pytest.raises(Exception):
            action.transition_id = "t2"  # type: ignore[misc]

    def test_negative_cost_forbidden(self) -> None:
        with pytest.raises(Exception):
            TypedAction(
                transition_id="t1",
                source_state_id="a",
                target_state_id="b",
                diff_size_estimate=-1,
            )


# ---------------------------------------------------------------------------
# ActionSetEnumerator tests
# ---------------------------------------------------------------------------


class TestActionSetEnumerator:
    def setup_method(self) -> None:
        self.enumerator = ActionSetEnumerator()

    def test_state_with_no_outgoing_edges(self) -> None:
        state = make_state("node.terminal")
        graph = ContractGraph(
            states={"node.terminal": state},
            adjacency={"node.terminal": ()},
            predecessors={"node.terminal": ()},
        )
        actions = self.enumerator.enumerate(graph, state)
        assert actions == []

    def test_state_with_one_open_transition(self) -> None:
        t = make_transition("t1", "node.a", "node.b")
        graph = make_graph_with_transitions("node.a", "node.b", [t])
        state = graph.get_state("node.a")
        assert state is not None
        actions = self.enumerator.enumerate(graph, state)
        assert len(actions) == 1
        assert actions[0].transition_id == "t1"

    def test_multiple_transitions_all_pass(self) -> None:
        t1 = make_transition("t1", "node.a", "node.b", diff_size=5)
        t2 = make_transition("t2", "node.a", "node.b", diff_size=2)
        t3 = make_transition("t3", "node.a", "node.b", diff_size=10)

        src = make_state("node.a")
        tgt = make_state("node.b")
        graph = ContractGraph(
            states={"node.a": src, "node.b": tgt},
            transitions={"t1": t1, "t2": t2, "t3": t3},
            adjacency={"node.a": ("t1", "t2", "t3"), "node.b": ()},
            predecessors={"node.a": (), "node.b": ("t1", "t2", "t3")},
        )
        actions = self.enumerator.enumerate(graph, src)
        assert len(actions) == 3
        # Ordered by cost (ascending)
        assert actions[0].transition_id == "t2"  # cost=2
        assert actions[1].transition_id == "t1"  # cost=5
        assert actions[2].transition_id == "t3"  # cost=10

    def test_capability_mismatch_excludes_transition(self) -> None:
        t = make_transition(
            "t1", "node.a", "node.b", required_capabilities=frozenset({"llm.gen"})
        )
        graph = make_graph_with_transitions("node.a", "node.b", [t])
        state = graph.get_state("node.a")
        assert state is not None
        # Agent has no capabilities
        actions = self.enumerator.enumerate(
            graph, state, agent_capabilities=frozenset()
        )
        assert actions == []

    def test_capability_match_includes_transition(self) -> None:
        t = make_transition(
            "t1", "node.a", "node.b", required_capabilities=frozenset({"llm.gen"})
        )
        graph = make_graph_with_transitions("node.a", "node.b", [t])
        state = graph.get_state("node.a")
        assert state is not None
        actions = self.enumerator.enumerate(
            graph, state, agent_capabilities=frozenset({"llm.gen"})
        )
        assert len(actions) == 1
        assert actions[0].transition_id == "t1"

    def test_schema_version_mismatch_excludes_transition(self) -> None:
        t = make_transition("t1", "node.a", "node.b", required_schema_version="2.0.0")
        # State has schema version "1.0.0"
        source = make_state("node.a", schema_version="1.0.0")
        graph = make_graph_with_transitions(
            "node.a", "node.b", [t], source_state=source
        )
        actions = self.enumerator.enumerate(graph, source)
        assert actions == []

    def test_schema_version_match_includes_transition(self) -> None:
        t = make_transition("t1", "node.a", "node.b", required_schema_version="1.0.0")
        source = make_state("node.a", schema_version="1.0.0")
        graph = make_graph_with_transitions(
            "node.a", "node.b", [t], source_state=source
        )
        actions = self.enumerator.enumerate(graph, source)
        assert len(actions) == 1

    def test_policy_tier_mismatch_excludes_transition(self) -> None:
        """Policy tier too high -> transition excluded (not error)."""
        t = make_transition("t1", "node.a", "node.b", policy_tier_max=2)
        # State has policy tier 5 which exceeds max of 2
        source = make_state("node.a", policy_tier=5)
        graph = make_graph_with_transitions(
            "node.a", "node.b", [t], source_state=source
        )
        actions = self.enumerator.enumerate(graph, source)
        assert actions == []

    def test_policy_tier_match_includes_transition(self) -> None:
        t = make_transition("t1", "node.a", "node.b", policy_tier_max=5)
        source = make_state("node.a", policy_tier=3)  # 3 <= 5
        graph = make_graph_with_transitions(
            "node.a", "node.b", [t], source_state=source
        )
        actions = self.enumerator.enumerate(graph, source)
        assert len(actions) == 1

    def test_precondition_key_missing_excludes_transition(self) -> None:
        t = make_transition(
            "t1", "node.a", "node.b", precondition_keys=frozenset({"datasource_ready"})
        )
        source = make_state("node.a", metadata={})  # key missing
        graph = make_graph_with_transitions(
            "node.a", "node.b", [t], source_state=source
        )
        actions = self.enumerator.enumerate(graph, source)
        assert actions == []

    def test_precondition_key_present_includes_transition(self) -> None:
        t = make_transition(
            "t1", "node.a", "node.b", precondition_keys=frozenset({"datasource_ready"})
        )
        source = make_state("node.a", metadata={"datasource_ready": "true"})
        graph = make_graph_with_transitions(
            "node.a", "node.b", [t], source_state=source
        )
        actions = self.enumerator.enumerate(graph, source)
        assert len(actions) == 1

    def test_mixed_guards_partial_pass(self) -> None:
        """Some transitions pass guards, some don't."""
        t_pass = make_transition("t.pass", "node.a", "node.b")
        t_fail = make_transition(
            "t.fail", "node.a", "node.b", required_capabilities=frozenset({"llm.gen"})
        )
        src = make_state("node.a")
        tgt = make_state("node.b")
        graph = ContractGraph(
            states={"node.a": src, "node.b": tgt},
            transitions={"t.pass": t_pass, "t.fail": t_fail},
            adjacency={"node.a": ("t.pass", "t.fail"), "node.b": ()},
            predecessors={"node.a": (), "node.b": ("t.pass", "t.fail")},
        )
        actions = self.enumerator.enumerate(graph, src, agent_capabilities=frozenset())
        assert len(actions) == 1
        assert actions[0].transition_id == "t.pass"

    def test_typed_action_carries_type_signatures(self) -> None:
        t = make_transition(
            "t1",
            "node.a",
            "node.b",
            input_types=("TypeA", "TypeB"),
            output_types=("TypeC",),
        )
        graph = make_graph_with_transitions("node.a", "node.b", [t])
        state = graph.get_state("node.a")
        assert state is not None
        actions = self.enumerator.enumerate(graph, state)
        assert len(actions) == 1
        assert actions[0].input_type_signature == ("TypeA", "TypeB")
        assert actions[0].output_type_signature == ("TypeC",)

    def test_none_agent_capabilities_treated_as_empty(self) -> None:
        """None agent_capabilities is treated as frozenset() (no capabilities)."""
        t = make_transition(
            "t1", "node.a", "node.b", required_capabilities=frozenset({"llm"})
        )
        graph = make_graph_with_transitions("node.a", "node.b", [t])
        state = graph.get_state("node.a")
        assert state is not None
        actions = self.enumerator.enumerate(graph, state, agent_capabilities=None)
        assert actions == []

    def test_ordering_tie_broken_by_transition_id(self) -> None:
        """When cost is equal, ordering is by transition_id for determinism."""
        t_z = make_transition("t.z", "node.a", "node.b", diff_size=1)
        t_a = make_transition("t.a", "node.a", "node.b", diff_size=1)
        src = make_state("node.a")
        tgt = make_state("node.b")
        graph = ContractGraph(
            states={"node.a": src, "node.b": tgt},
            transitions={"t.z": t_z, "t.a": t_a},
            adjacency={"node.a": ("t.z", "t.a"), "node.b": ()},
            predecessors={"node.a": (), "node.b": ("t.z", "t.a")},
        )
        actions = self.enumerator.enumerate(graph, src)
        assert len(actions) == 2
        # Same cost, ordered by transition_id alphabetically
        assert actions[0].transition_id == "t.a"
        assert actions[1].transition_id == "t.z"
