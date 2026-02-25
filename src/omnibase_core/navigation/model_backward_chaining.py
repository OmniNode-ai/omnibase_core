# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Goal-Conditioned Backward Chaining Planner (OMN-2561).

Implements BackwardChainingPlanner which takes a declared goal state and
produces a verified execution plan as a path through the contract graph.

Design principles:
- Pure graph search — no calls to the local model
- Every step corresponds to a declared ContractTransition in the graph
- Cycle detection via visited-set keyed on ContractState identity (node_id)
- Configurable max depth (default: 10)
- Deterministic: same graph + goal + current_state → same plan
- Handles disconnected graph regions gracefully (returns NoPlanFound)
- Depth-limited backward BFS from goal to current state
"""

import logging
from collections import deque
from enum import Enum, auto

from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
)
from omnibase_core.navigation.model_graph_boundary import (
    CycleDetected,
    GoalAlreadySatisfied,
    GoalCondition,
    MaxDepthExceeded,
    NoPlanFound,
    Plan,
    PlanResult,
    PlanStep,
    RequiredTransitionNotInGraph,
)

logger = logging.getLogger(__name__)

DEFAULT_MAX_DEPTH = 10


class _BfsSignal(Enum):
    """Internal signals returned by _backward_bfs when no plan is found."""

    CYCLE = auto()
    DEPTH_EXCEEDED = auto()


_BfsResult = list[PlanStep] | _BfsSignal | None


def _satisfies_goal(state: ContractState, goal: GoalCondition) -> bool:
    """Check if a state satisfies the goal condition.

    Args:
        state: The state to check.
        goal: The goal condition to check against.

    Returns:
        True if the state satisfies all declared predicates.
    """
    # target_node_id check
    if goal.target_node_id is not None:
        if state.node_id != goal.target_node_id:
            return False

    # required_capabilities check (state must have all required capabilities)
    if goal.required_capabilities:
        if not goal.required_capabilities.issubset(state.capabilities):
            return False

    # policy_tier_max check
    if goal.policy_tier_max is not None:
        if state.policy_tier > goal.policy_tier_max:
            return False

    # required_metadata_keys check
    if goal.required_metadata_keys:
        if not goal.required_metadata_keys.issubset(set(state.metadata.keys())):
            return False

    return True


def _transition_satisfies_output_goal(
    transition_output_types: tuple[str, ...],
    required_output_types: frozenset[str],
) -> bool:
    """Check if at least one of the required output types is produced by this transition.

    If required_output_types is empty, all transitions pass this check.
    """
    if not required_output_types:
        return True
    return bool(required_output_types & set(transition_output_types))


class BackwardChainingPlanner:
    """Goal-conditioned backward chaining planner over the contract graph.

    Works backwards from the goal state to find a path from the current
    state to any state that satisfies the goal condition. Returns a forward-
    ordered plan (first step first).

    The planner is deterministic: the same graph, goal, and current state
    always produce the same plan (BFS explores nodes in sorted order).

    Example:
        >>> planner = BackwardChainingPlanner(max_depth=10)
        >>> result = planner.plan(graph, goal, current_state)
        >>> if isinstance(result, Plan):
        ...     for step in result.steps:
        ...         execute_transition(step.transition_id)
    """

    def __init__(self, max_depth: int = DEFAULT_MAX_DEPTH) -> None:
        """Initialize the planner.

        Args:
            max_depth: Maximum search depth (plan length). Default: 10.
        """
        if max_depth < 1:
            raise ValueError(f"max_depth must be >= 1, got {max_depth}")
        self._max_depth = max_depth

    @property
    def max_depth(self) -> int:
        """The configured maximum search depth."""
        return self._max_depth

    def plan(
        self,
        graph: ContractGraph,
        goal: GoalCondition,
        current_state: ContractState,
    ) -> PlanResult:
        """Produce a verified execution plan from current_state to a goal-satisfying state.

        Implements depth-limited backward BFS:
        1. Check if current_state already satisfies the goal.
        2. Collect all goal-satisfying states in the graph.
        3. For each goal state, use backward BFS to find a path from current_state.
        4. Return the shortest plan found (fewest steps).

        Args:
            graph: The contract graph for this navigation session.
            goal: The goal condition declaring terminal predicates.
            current_state: The starting state for navigation.

        Returns:
            Plan: An ordered execution plan if one is found.
            GoalAlreadySatisfied: If current_state already satisfies the goal.
            NoPlanFound: If no valid plan exists (with structured reason).
        """
        logger.debug(
            "Starting backward chaining",
            extra={
                "current_state_id": current_state.node_id,
                "goal_target_node_id": goal.target_node_id,
                "max_depth": self._max_depth,
            },
        )

        # Step 1: Check if already satisfied
        if _satisfies_goal(current_state, goal):
            logger.debug(
                "Goal already satisfied at current state",
                extra={"current_state_id": current_state.node_id},
            )
            return GoalAlreadySatisfied(current_state_id=current_state.node_id)

        # Step 2: Collect all goal-satisfying states
        goal_state_ids: list[str] = sorted(
            node_id
            for node_id, state in graph.states.items()
            if _satisfies_goal(state, goal)
        )

        if not goal_state_ids:
            logger.debug(
                "No states in graph satisfy the goal condition",
                extra={"goal": str(goal)},
            )
            return NoPlanFound(
                reason=RequiredTransitionNotInGraph(
                    goal_node_id=goal.target_node_id,
                )
            )

        # Step 3: Backward BFS from each goal state to find shortest path to current_state
        # We search backwards: from goal states, follow predecessors to find current_state.
        # BFS state: (node_id, path_of_transition_ids_from_goal_backwards)
        # We convert to forward plan at the end.

        best_plan: list[PlanStep] | None = None
        cycle_detected = False
        depth_exceeded = False

        for goal_state_id in goal_state_ids:
            bfs_result = self._backward_bfs(
                graph=graph,
                start_id=current_state.node_id,
                goal_id=goal_state_id,
                goal=goal,
            )
            if bfs_result is None:
                # No path found for this goal state — disconnected
                continue
            if bfs_result is _BfsSignal.CYCLE:
                cycle_detected = True
                continue
            if bfs_result is _BfsSignal.DEPTH_EXCEEDED:
                depth_exceeded = True
                continue

            # bfs_result is a list of PlanStep
            plan_steps: list[PlanStep] = bfs_result
            if best_plan is None or len(plan_steps) < len(best_plan):
                best_plan = plan_steps

        if best_plan is not None:
            logger.debug(
                "Backward chaining produced plan",
                extra={
                    "step_count": len(best_plan),
                    "current_state_id": current_state.node_id,
                },
            )
            return Plan(steps=tuple(best_plan))

        # No plan found — return most specific reason
        if depth_exceeded:
            return NoPlanFound(reason=MaxDepthExceeded(max_depth=self._max_depth))
        if cycle_detected:
            return NoPlanFound(reason=CycleDetected())
        return NoPlanFound(
            reason=RequiredTransitionNotInGraph(goal_node_id=goal.target_node_id)
        )

    def _backward_bfs(
        self,
        graph: ContractGraph,
        start_id: str,
        goal_id: str,
        goal: GoalCondition,
    ) -> _BfsResult:
        """Depth-limited backward BFS from goal_id back to start_id.

        Returns:
            list[PlanStep]: A forward-ordered plan if found.
            None: No path found (disconnected).
            _BfsSignal.CYCLE: All paths contain cycles.
            _BfsSignal.DEPTH_EXCEEDED: Max depth exceeded before finding path.
        """
        # BFS queue: (current_node_id, path_backwards: list of (transition_id, from_id, to_id))
        # "path_backwards" records the transitions traversed going backward from goal.
        # visited set: frozenset of node_ids in current path (cycle detection)

        # Each queue entry: (node_id, visited_set, backward_path)
        # backward_path: list of (transition_id, pre_id, post_id) in backward traversal order
        initial_visited: frozenset[str] = frozenset({goal_id})
        initial_path: list[tuple[str, str, str]] = []  # (transition_id, pre, post)

        queue: deque[tuple[str, frozenset[str], list[tuple[str, str, str]]]] = deque()
        queue.append((goal_id, initial_visited, initial_path))

        found_cycle = False
        found_depth_exceeded = False

        while queue:
            current_id, visited, backward_path = queue.popleft()

            # Check if we've reached the start state (check before depth limit
            # so a path of exactly max_depth steps is accepted)
            if current_id == start_id and backward_path:
                # Convert backward path to forward plan
                return self._backward_path_to_plan(backward_path)

            # Check depth limit before expanding further
            if len(backward_path) >= self._max_depth:
                found_depth_exceeded = True
                continue

            # Explore predecessors (transitions incoming to current_id)
            # Sort for determinism
            incoming = sorted(
                graph.get_incoming_transitions(current_id),
                key=lambda t: (t.cost.total_cost, t.transition_id),
            )

            if not incoming:
                # Dead end (no predecessors) and not the start
                continue

            for transition in incoming:
                predecessor_id = transition.source_state_id

                # Check for output type constraint if goal requires it
                # (only check this for the first backward step, i.e., transitions entering the goal)
                if current_id == goal_id and goal.required_output_types:
                    if not _transition_satisfies_output_goal(
                        transition.output_types, goal.required_output_types
                    ):
                        continue

                # Cycle detection (in current path)
                if predecessor_id in visited:
                    found_cycle = True
                    continue

                new_visited = visited | {predecessor_id}
                new_backward_path = backward_path + [
                    (transition.transition_id, predecessor_id, current_id)
                ]
                queue.append((predecessor_id, new_visited, new_backward_path))

        # Check if we simply never reached start (not same as cycle)
        if found_depth_exceeded:
            return _BfsSignal.DEPTH_EXCEEDED
        if found_cycle:
            return _BfsSignal.CYCLE
        return None

    def _backward_path_to_plan(
        self,
        backward_path: list[tuple[str, str, str]],
    ) -> list[PlanStep]:
        """Convert a backward path to a forward-ordered list of PlanStep.

        Args:
            backward_path: List of (transition_id, pre_state_id, post_state_id)
                in backward traversal order (goal-first). The path does NOT include
                the trivial "goal reached" entry — it starts from the first predecessor.

        Returns:
            Forward-ordered list of PlanStep (first = step from start).
        """
        # The backward path is in reverse order: backward_path[0] is the last step
        # (the step that leads into the goal state), backward_path[-1] is the first step.
        forward_path = list(reversed(backward_path))
        steps = []
        for i, (transition_id, pre_id, post_id) in enumerate(forward_path):
            steps.append(
                PlanStep(
                    transition_id=transition_id,
                    pre_state_id=pre_id,
                    post_state_id=post_id,
                    step_index=i,
                )
            )
        return steps


__all__ = ["BackwardChainingPlanner"]
