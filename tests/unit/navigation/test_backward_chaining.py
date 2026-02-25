# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for Goal-Conditioned Backward Chaining Planner (OMN-2561).

Covers:
- Trivial 1-step plan
- Multi-step plan
- Goal already satisfied at current state
- No-path graph (disconnected) -> NoPlanFound(RequiredTransitionNotInGraph)
- Cyclic graph with no acyclic path -> NoPlanFound(CycleDetected)
- Max depth exceeded -> NoPlanFound(MaxDepthExceeded)
- GoalCondition predicates: target_node_id, required_output_types,
  required_capabilities, policy_tier_max, required_metadata_keys
- Plan steps are in correct forward order
- Planner is deterministic (same inputs -> same output)
- All steps in plan correspond to declared graph transitions
- BackwardChainingPlanner constructor rejects max_depth < 1
"""

import pytest

from omnibase_core.navigation.model_backward_chaining import BackwardChainingPlanner
from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    ContractTransition,
)
from omnibase_core.navigation.model_graph_boundary import (
    GoalAlreadySatisfied,
    GoalCondition,
    MaxDepthExceeded,
    NoPlanFound,
    Plan,
    PlanStep,
    RequiredTransitionNotInGraph,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_state(
    node_id: str,
    capabilities: frozenset[str] | None = None,
    policy_tier: int = 0,
    metadata: dict[str, str] | None = None,
) -> ContractState:
    return ContractState(
        node_id=node_id,
        schema_version="1.0.0",
        capabilities=capabilities or frozenset(),
        policy_tier=policy_tier,
        metadata=metadata or {},
    )


def make_transition(
    transition_id: str,
    source_id: str,
    target_id: str,
    output_types: tuple[str, ...] = (),
) -> ContractTransition:
    return ContractTransition(
        transition_id=transition_id,
        source_state_id=source_id,
        target_state_id=target_id,
        output_types=output_types,
    )


def build_graph(
    states: list[ContractState],
    transitions: list[ContractTransition],
) -> ContractGraph:
    """Build ContractGraph from lists of states and transitions."""
    state_map = {s.node_id: s for s in states}
    transition_map = {t.transition_id: t for t in transitions}

    # Build adjacency and predecessors
    adjacency: dict[str, list[str]] = {s.node_id: [] for s in states}
    predecessors: dict[str, list[str]] = {s.node_id: [] for s in states}
    for t in transitions:
        adjacency[t.source_state_id].append(t.transition_id)
        predecessors[t.target_state_id].append(t.transition_id)

    return ContractGraph(
        states=state_map,
        transitions=transition_map,
        adjacency={k: tuple(v) for k, v in adjacency.items()},
        predecessors={k: tuple(v) for k, v in predecessors.items()},
    )


# ---------------------------------------------------------------------------
# BackwardChainingPlanner constructor tests
# ---------------------------------------------------------------------------


class TestBackwardChainingPlannerConstructor:
    def test_default_max_depth(self) -> None:
        planner = BackwardChainingPlanner()
        assert planner.max_depth == 10

    def test_custom_max_depth(self) -> None:
        planner = BackwardChainingPlanner(max_depth=5)
        assert planner.max_depth == 5

    def test_invalid_max_depth_zero(self) -> None:
        with pytest.raises(ValueError):
            BackwardChainingPlanner(max_depth=0)

    def test_invalid_max_depth_negative(self) -> None:
        with pytest.raises(ValueError):
            BackwardChainingPlanner(max_depth=-1)


# ---------------------------------------------------------------------------
# GoalAlreadySatisfied tests
# ---------------------------------------------------------------------------


class TestGoalAlreadySatisfied:
    def test_goal_satisfied_by_node_id(self) -> None:
        planner = BackwardChainingPlanner()
        state = make_state("node.goal")
        graph = build_graph([state], [])
        goal = GoalCondition(target_node_id="node.goal")
        result = planner.plan(graph, goal, state)
        assert isinstance(result, GoalAlreadySatisfied)
        assert result.current_state_id == "node.goal"

    def test_goal_satisfied_by_capabilities(self) -> None:
        planner = BackwardChainingPlanner()
        state = make_state("node.a", capabilities=frozenset({"llm.gen"}))
        graph = build_graph([state], [])
        goal = GoalCondition(required_capabilities=frozenset({"llm.gen"}))
        result = planner.plan(graph, goal, state)
        assert isinstance(result, GoalAlreadySatisfied)

    def test_goal_satisfied_by_policy_tier(self) -> None:
        planner = BackwardChainingPlanner()
        state = make_state("node.a", policy_tier=1)
        graph = build_graph([state], [])
        goal = GoalCondition(policy_tier_max=3)
        result = planner.plan(graph, goal, state)
        assert isinstance(result, GoalAlreadySatisfied)

    def test_goal_satisfied_by_metadata_keys(self) -> None:
        planner = BackwardChainingPlanner()
        state = make_state("node.a", metadata={"ready": "true"})
        graph = build_graph([state], [])
        goal = GoalCondition(required_metadata_keys=frozenset({"ready"}))
        result = planner.plan(graph, goal, state)
        assert isinstance(result, GoalAlreadySatisfied)


# ---------------------------------------------------------------------------
# 1-step plan tests
# ---------------------------------------------------------------------------


class TestOnestepPlan:
    def test_trivial_one_step_plan(self) -> None:
        planner = BackwardChainingPlanner()
        start = make_state("node.start")
        goal_state = make_state("node.goal")
        t = make_transition("t.start-goal", "node.start", "node.goal")
        graph = build_graph([start, goal_state], [t])
        goal = GoalCondition(target_node_id="node.goal")
        result = planner.plan(graph, goal, start)
        assert isinstance(result, Plan)
        assert len(result.steps) == 1
        step = result.steps[0]
        assert step.transition_id == "t.start-goal"
        assert step.pre_state_id == "node.start"
        assert step.post_state_id == "node.goal"
        assert step.step_index == 0

    def test_one_step_plan_step_declared_in_graph(self) -> None:
        """Every step in the plan must correspond to a declared graph transition."""
        planner = BackwardChainingPlanner()
        start = make_state("node.start")
        goal_state = make_state("node.goal")
        t = make_transition("t.sg", "node.start", "node.goal")
        graph = build_graph([start, goal_state], [t])
        goal = GoalCondition(target_node_id="node.goal")
        result = planner.plan(graph, goal, start)
        assert isinstance(result, Plan)
        for step in result.steps:
            assert graph.get_transition(step.transition_id) is not None


# ---------------------------------------------------------------------------
# Multi-step plan tests
# ---------------------------------------------------------------------------


class TestMultistepPlan:
    def test_two_step_plan(self) -> None:
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start")
        s_mid = make_state("node.mid")
        s_goal = make_state("node.goal")
        t1 = make_transition("t.sm", "node.start", "node.mid")
        t2 = make_transition("t.mg", "node.mid", "node.goal")
        graph = build_graph([s_start, s_mid, s_goal], [t1, t2])
        goal = GoalCondition(target_node_id="node.goal")
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, Plan)
        assert len(result.steps) == 2
        # Forward order: step 0 = start->mid, step 1 = mid->goal
        assert result.steps[0].transition_id == "t.sm"
        assert result.steps[0].step_index == 0
        assert result.steps[1].transition_id == "t.mg"
        assert result.steps[1].step_index == 1

    def test_three_step_plan(self) -> None:
        planner = BackwardChainingPlanner()
        states = [make_state(f"node.{i}") for i in range(4)]
        transitions = [
            make_transition(f"t.{i}-{i + 1}", f"node.{i}", f"node.{i + 1}")
            for i in range(3)
        ]
        graph = build_graph(states, transitions)
        goal = GoalCondition(target_node_id="node.3")
        result = planner.plan(graph, goal, states[0])
        assert isinstance(result, Plan)
        assert len(result.steps) == 3
        for i, step in enumerate(result.steps):
            assert step.step_index == i

    def test_all_steps_reference_declared_transitions(self) -> None:
        planner = BackwardChainingPlanner()
        s0 = make_state("node.0")
        s1 = make_state("node.1")
        s2 = make_state("node.2")
        t01 = make_transition("t.01", "node.0", "node.1")
        t12 = make_transition("t.12", "node.1", "node.2")
        graph = build_graph([s0, s1, s2], [t01, t12])
        goal = GoalCondition(target_node_id="node.2")
        result = planner.plan(graph, goal, s0)
        assert isinstance(result, Plan)
        for step in result.steps:
            assert graph.get_transition(step.transition_id) is not None


# ---------------------------------------------------------------------------
# No plan found tests
# ---------------------------------------------------------------------------


class TestNoPlanFound:
    def test_disconnected_graph_unreachable_goal(self) -> None:
        """Goal in disconnected part of graph -> NoPlanFound."""
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start")
        s_isolated = make_state("node.isolated")
        # No transitions connecting start to isolated
        graph = build_graph([s_start, s_isolated], [])
        goal = GoalCondition(target_node_id="node.isolated")
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, NoPlanFound)
        assert isinstance(result.reason, RequiredTransitionNotInGraph)

    def test_no_goal_states_in_graph(self) -> None:
        """Goal condition satisfied by no state in graph."""
        planner = BackwardChainingPlanner()
        start = make_state("node.start", capabilities=frozenset())
        graph = build_graph([start], [])
        goal = GoalCondition(required_capabilities=frozenset({"nonexistent.cap"}))
        result = planner.plan(graph, goal, start)
        assert isinstance(result, NoPlanFound)
        assert isinstance(result.reason, RequiredTransitionNotInGraph)

    def test_cycle_with_no_acyclic_path(self) -> None:
        """Graph is A <-> B with goal=C (not in graph) — cycles exist, no path."""
        planner = BackwardChainingPlanner()
        s_a = make_state("node.a")
        s_b = make_state("node.b")
        t_ab = make_transition("t.ab", "node.a", "node.b")
        t_ba = make_transition("t.ba", "node.b", "node.a")
        graph = build_graph([s_a, s_b], [t_ab, t_ba])
        goal = GoalCondition(target_node_id="node.c")
        result = planner.plan(graph, goal, s_a)
        assert isinstance(result, NoPlanFound)

    def test_max_depth_exceeded(self) -> None:
        """Path exists but is longer than max_depth."""
        planner = BackwardChainingPlanner(max_depth=2)
        # Chain: 0 -> 1 -> 2 -> 3 (requires 3 steps, max_depth=2)
        states = [make_state(f"node.{i}") for i in range(4)]
        transitions = [
            make_transition(f"t.{i}{i + 1}", f"node.{i}", f"node.{i + 1}")
            for i in range(3)
        ]
        graph = build_graph(states, transitions)
        goal = GoalCondition(target_node_id="node.3")
        result = planner.plan(graph, goal, states[0])
        assert isinstance(result, NoPlanFound)
        assert isinstance(result.reason, MaxDepthExceeded)
        assert result.reason.max_depth == 2

    def test_within_max_depth_succeeds(self) -> None:
        """Path length exactly equal to max_depth is valid."""
        planner = BackwardChainingPlanner(max_depth=3)
        states = [make_state(f"node.{i}") for i in range(4)]
        transitions = [
            make_transition(f"t.{i}{i + 1}", f"node.{i}", f"node.{i + 1}")
            for i in range(3)
        ]
        graph = build_graph(states, transitions)
        goal = GoalCondition(target_node_id="node.3")
        result = planner.plan(graph, goal, states[0])
        assert isinstance(result, Plan)
        assert len(result.steps) == 3


# ---------------------------------------------------------------------------
# Goal condition predicate tests
# ---------------------------------------------------------------------------


class TestGoalConditionPredicates:
    def test_required_output_types_goal(self) -> None:
        """Goal requires specific output types from the reaching transition."""
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start")
        s_goal = make_state("node.goal")
        # Only transition that produces "TypeResult"
        t = make_transition(
            "t.sg", "node.start", "node.goal", output_types=("TypeResult",)
        )
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(
            target_node_id="node.goal",
            required_output_types=frozenset({"TypeResult"}),
        )
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, Plan)

    def test_required_output_types_mismatch_skips_transition(self) -> None:
        """Transition producing wrong output type is skipped for output-typed goals."""
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start")
        s_goal = make_state("node.goal")
        t = make_transition(
            "t.sg", "node.start", "node.goal", output_types=("WrongType",)
        )
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(
            target_node_id="node.goal",
            required_output_types=frozenset({"TypeResult"}),
        )
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, NoPlanFound)

    def test_required_capabilities_goal(self) -> None:
        """Goal requires state to have specific capabilities."""
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start", capabilities=frozenset())
        s_goal = make_state("node.goal", capabilities=frozenset({"storage.db"}))
        t = make_transition("t.sg", "node.start", "node.goal")
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(required_capabilities=frozenset({"storage.db"}))
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, Plan)

    def test_policy_tier_max_goal(self) -> None:
        """Goal requires policy tier <= max. Start state does not satisfy (wrong tier), goal does."""
        planner = BackwardChainingPlanner()
        # Start has capabilities that don't match goal; goal has policy_tier=1 <= max=2
        s_start = make_state("node.start", policy_tier=5)  # 5 > 2, fails goal
        s_goal = make_state("node.goal", policy_tier=1)  # 1 <= 2, satisfies goal
        t = make_transition("t.sg", "node.start", "node.goal")
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(policy_tier_max=2)
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, Plan)

    def test_policy_tier_max_goal_violated(self) -> None:
        """Goal state with policy tier > max is not a valid goal."""
        planner = BackwardChainingPlanner()
        # Start and goal both have high policy tier that violates the goal
        s_start = make_state("node.start", policy_tier=5)
        s_goal = make_state("node.goal", policy_tier=5)
        t = make_transition("t.sg", "node.start", "node.goal")
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(policy_tier_max=2)
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, NoPlanFound)

    def test_required_metadata_keys_goal(self) -> None:
        """Goal requires state to have specific metadata keys."""
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start")
        s_goal = make_state("node.goal", metadata={"rendered": "true"})
        t = make_transition("t.sg", "node.start", "node.goal")
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(required_metadata_keys=frozenset({"rendered"}))
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, Plan)

    def test_metadata_key_missing_goal_not_satisfied(self) -> None:
        planner = BackwardChainingPlanner()
        s_start = make_state("node.start")
        s_goal = make_state("node.goal", metadata={})
        t = make_transition("t.sg", "node.start", "node.goal")
        graph = build_graph([s_start, s_goal], [t])
        goal = GoalCondition(required_metadata_keys=frozenset({"rendered"}))
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, NoPlanFound)


# ---------------------------------------------------------------------------
# Determinism tests
# ---------------------------------------------------------------------------


class TestPlannerDeterminism:
    def test_same_inputs_produce_same_plan(self) -> None:
        """Planner is deterministic: same inputs -> same plan across runs."""
        planner = BackwardChainingPlanner()
        states = [make_state(f"node.{i}") for i in range(3)]
        transitions = [
            make_transition(f"t.{i}{i + 1}", f"node.{i}", f"node.{i + 1}")
            for i in range(2)
        ]
        graph = build_graph(states, transitions)
        goal = GoalCondition(target_node_id="node.2")
        current = states[0]

        results = [planner.plan(graph, goal, current) for _ in range(5)]
        # All results must be Plan instances with identical steps
        for result in results:
            assert isinstance(result, Plan)
        plans = [r for r in results if isinstance(r, Plan)]
        for plan in plans[1:]:
            assert len(plan.steps) == len(plans[0].steps)
            for a, b in zip(plan.steps, plans[0].steps, strict=True):
                assert a.transition_id == b.transition_id

    def test_multiple_paths_returns_shortest(self) -> None:
        """When multiple paths exist, planner returns shortest (fewest steps)."""
        planner = BackwardChainingPlanner()
        # Short path: start -> goal (1 step)
        # Long path: start -> mid -> goal (2 steps)
        s_start = make_state("node.start")
        s_mid = make_state("node.mid")
        s_goal = make_state("node.goal")
        t_direct = make_transition("t.direct", "node.start", "node.goal")
        t_via_mid1 = make_transition("t.sm", "node.start", "node.mid")
        t_via_mid2 = make_transition("t.mg", "node.mid", "node.goal")
        graph = build_graph(
            [s_start, s_mid, s_goal], [t_direct, t_via_mid1, t_via_mid2]
        )
        goal = GoalCondition(target_node_id="node.goal")
        result = planner.plan(graph, goal, s_start)
        assert isinstance(result, Plan)
        assert len(result.steps) == 1
        assert result.steps[0].transition_id == "t.direct"


# ---------------------------------------------------------------------------
# PlanStep type tests
# ---------------------------------------------------------------------------


class TestPlanStep:
    def test_plan_step_construction(self) -> None:
        step = PlanStep(
            transition_id="t1",
            pre_state_id="node.a",
            post_state_id="node.b",
            step_index=0,
        )
        assert step.transition_id == "t1"
        assert step.step_index == 0

    def test_plan_step_frozen(self) -> None:
        step = PlanStep(
            transition_id="t1",
            pre_state_id="node.a",
            post_state_id="node.b",
            step_index=0,
        )
        with pytest.raises(Exception):
            step.transition_id = "t2"  # type: ignore[misc]

    def test_plan_step_index_nonnegative(self) -> None:
        with pytest.raises(Exception):
            PlanStep(
                transition_id="t1",
                pre_state_id="node.a",
                post_state_id="node.b",
                step_index=-1,
            )
