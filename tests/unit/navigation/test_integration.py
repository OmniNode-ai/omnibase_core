# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Tests for NavigationFacade integration layer (OMN-6599).

Covers:
- Construction and attribute access
- Delegation to underlying components (build_graph, enumerate_actions,
  validate_action, plan_to_goal)
- Property accessors for direct component access
"""

import pytest

from omnibase_core.navigation.integration import NavigationFacade
from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    RegistryNode,
    RegistrySnapshot,
    RegistryTransitionDecl,
)
from omnibase_core.navigation.model_contract_graph_builder import ContractGraphBuilder
from omnibase_core.navigation.model_graph_boundary import (
    GoalCondition,
    Valid,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_snapshot_with_two_nodes() -> RegistrySnapshot:
    """Create a minimal registry snapshot with two nodes and one transition."""
    node_a = RegistryNode(
        node_id="node.a",
        schema_version="1.0.0",
        capabilities=("compute",),
        policy_tier=0,
        metadata={},
        declared_transitions=(
            RegistryTransitionDecl(
                transition_id="a_to_b",
                target_node_id="node.b",
            ),
        ),
    )
    node_b = RegistryNode(
        node_id="node.b",
        schema_version="1.0.0",
        capabilities=("store",),
        policy_tier=0,
        metadata={},
        declared_transitions=(),
    )
    return RegistrySnapshot(
        snapshot_id="test-snapshot",
        nodes=(node_a, node_b),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestNavigationFacade:
    """Tests for NavigationFacade."""

    def test_construction(self) -> None:
        """Facade can be constructed without arguments."""
        facade = NavigationFacade()
        assert facade is not None

    def test_property_accessors(self) -> None:
        """Property accessors return the correct component types."""
        facade = NavigationFacade()
        assert isinstance(facade.graph_builder, ContractGraphBuilder)
        assert hasattr(facade.enumerator, "enumerate")
        assert hasattr(facade.enforcer, "validate")
        assert hasattr(facade.planner, "plan")

    def test_build_graph(self) -> None:
        """build_graph delegates to ContractGraphBuilder.build()."""
        facade = NavigationFacade()
        snapshot = _make_snapshot_with_two_nodes()
        graph = facade.build_graph(snapshot)
        assert isinstance(graph, ContractGraph)
        state_a = graph.get_state("node.a")
        assert state_a is not None
        assert state_a.node_id == "node.a"

    def test_enumerate_actions(self) -> None:
        """enumerate_actions returns typed actions from the current state."""
        facade = NavigationFacade()
        snapshot = _make_snapshot_with_two_nodes()
        graph = facade.build_graph(snapshot)
        state_a = graph.get_state("node.a")
        assert state_a is not None

        actions = facade.enumerate_actions(graph, state_a)
        assert len(actions) == 1
        assert actions[0].transition_id == "a_to_b"
        assert actions[0].target_state_id == "node.b"

    def test_enumerate_actions_terminal_state(self) -> None:
        """enumerate_actions returns empty list for terminal state."""
        facade = NavigationFacade()
        snapshot = _make_snapshot_with_two_nodes()
        graph = facade.build_graph(snapshot)
        state_b = graph.get_state("node.b")
        assert state_b is not None

        actions = facade.enumerate_actions(graph, state_b)
        assert actions == []

    def test_validate_action_valid(self) -> None:
        """validate_action returns Valid for an action in the action set."""
        facade = NavigationFacade()
        snapshot = _make_snapshot_with_two_nodes()
        graph = facade.build_graph(snapshot)
        state_a = graph.get_state("node.a")
        assert state_a is not None

        actions = facade.enumerate_actions(graph, state_a)
        result = facade.validate_action("node.a", actions[0], actions)
        assert isinstance(result, Valid)

    def test_plan_to_goal(self) -> None:
        """plan_to_goal finds a plan from node.a to node.b."""
        facade = NavigationFacade()
        snapshot = _make_snapshot_with_two_nodes()
        graph = facade.build_graph(snapshot)
        state_a = graph.get_state("node.a")
        assert state_a is not None

        goal = GoalCondition(target_node_id="node.b")
        plan_result = facade.plan_to_goal(graph, goal, state_a)
        # Should find a plan (Plan type) since a_to_b transition exists
        assert hasattr(plan_result, "steps")

    def test_importable_from_navigation_package(self) -> None:
        """NavigationFacade is importable from the navigation package."""
        from omnibase_core.navigation import (
            NavigationFacade as NavigationFacadeFromPkg,
        )

        assert NavigationFacadeFromPkg is NavigationFacade
