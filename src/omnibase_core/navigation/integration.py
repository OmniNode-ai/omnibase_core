# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""Integration layer for cross-repo navigation consumers.

Provides a stable import surface for downstream repos (e.g., omniclaude
node_transition_selector_effect) that currently use TYPE_CHECKING-only imports.

The NavigationFacade wraps the four core navigation components into a single
convenience object. Downstream code can import and construct one facade instead
of managing four separate instances.

Example:
    >>> from omnibase_core.navigation.integration import NavigationFacade
    >>> facade = NavigationFacade()
    >>> graph = facade.build_graph(snapshot)
    >>> actions = facade.enumerate_actions(graph, current_state)
"""

from __future__ import annotations

from omnibase_core.navigation.model_action_set import ActionSetEnumerator, TypedAction
from omnibase_core.navigation.model_backward_chaining import BackwardChainingPlanner
from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    RegistrySnapshot,
)
from omnibase_core.navigation.model_contract_graph_builder import ContractGraphBuilder
from omnibase_core.navigation.model_graph_boundary import (
    GoalCondition,
    GraphBoundaryEnforcer,
    PlanResult,
    ValidationResult,
)


class NavigationFacade:
    """Convenience facade for navigation operations.

    Wraps ContractGraphBuilder, ActionSetEnumerator, GraphBoundaryEnforcer,
    and BackwardChainingPlanner into a single object. All methods delegate
    directly to the underlying component -- no additional logic is added.

    Thread-safe: all underlying components are stateless.
    """

    def __init__(self) -> None:
        self._graph_builder = ContractGraphBuilder()
        self._enumerator = ActionSetEnumerator()
        self._enforcer = GraphBoundaryEnforcer()
        self._planner = BackwardChainingPlanner()

    @property
    def graph_builder(self) -> ContractGraphBuilder:
        """Access the underlying ContractGraphBuilder."""
        return self._graph_builder

    @property
    def enumerator(self) -> ActionSetEnumerator:
        """Access the underlying ActionSetEnumerator."""
        return self._enumerator

    @property
    def enforcer(self) -> GraphBoundaryEnforcer:
        """Access the underlying GraphBoundaryEnforcer."""
        return self._enforcer

    @property
    def planner(self) -> BackwardChainingPlanner:
        """Access the underlying BackwardChainingPlanner."""
        return self._planner

    def build_graph(self, snapshot: RegistrySnapshot) -> ContractGraph:
        """Build a ContractGraph from a registry snapshot.

        Delegates to ContractGraphBuilder.build().
        """
        return self._graph_builder.build(snapshot)

    def enumerate_actions(
        self,
        graph: ContractGraph,
        current_state: ContractState,
        agent_capabilities: frozenset[str] | None = None,
    ) -> list[TypedAction]:
        """Enumerate valid typed actions from the current state.

        Delegates to ActionSetEnumerator.enumerate().
        """
        return self._enumerator.enumerate(graph, current_state, agent_capabilities)

    def validate_action(
        self,
        current_state_id: str,
        selected_action: TypedAction,
        action_set: list[TypedAction],
        session_id: str = "",
    ) -> ValidationResult:
        """Validate that the selected action is in the enumerated action set.

        Delegates to GraphBoundaryEnforcer.validate().
        """
        return self._enforcer.validate(
            current_state_id, selected_action, action_set, session_id
        )

    def plan_to_goal(
        self,
        graph: ContractGraph,
        goal: GoalCondition,
        current_state: ContractState,
    ) -> PlanResult:
        """Produce a verified execution plan from current_state to a goal state.

        Delegates to BackwardChainingPlanner.plan().
        """
        return self._planner.plan(graph, goal, current_state)
