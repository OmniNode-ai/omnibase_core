# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Typed Action Set Enumeration (OMN-2546).

Implements TypedAction and ActionSetEnumerator. Given a current contract state,
ActionSetEnumerator.enumerate() returns the bounded, guard-filtered set of valid
typed actions available at that state.

Design principles:
- TypedAction is a strongly typed representation (not a free-form string)
- Guard evaluation is pure and side-effect-free (no network calls)
- Enumeration runs in O(E) where E is the out-degree of the current state
- Result is ordered by feasibility then estimated cost (cheaper first)
- Empty action set is valid (terminal state)
- The action set never includes transitions not in the declared graph
"""

from __future__ import annotations

import logging

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    ContractTransition,
    TransitionGuard,
)

logger = logging.getLogger(__name__)


class TypedAction(BaseModel):
    """A strongly typed action (transition) available at a contract state.

    TypedAction wraps a ContractTransition for presentation to the model.
    It is a value object with full type information — never a free-form string.

    Attributes:
        transition_id: Unique identifier matching the ContractTransition.
        label: Human-readable label for display.
        source_state_id: node_id of the state this action is available at.
        target_state_id: node_id of the resulting state after taking this action.
        input_type_signature: Declared input type names.
        output_type_signature: Declared output type names.
        diff_size_estimate: Estimated diff size (for ordering).
        latency_estimate_ms: Estimated latency in ms (for ordering).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    transition_id: str = Field(
        ...,
        description="Unique identifier matching the ContractTransition",
        min_length=1,
    )
    label: str = Field(
        default="",
        description="Human-readable label for display",
    )
    source_state_id: str = Field(
        ...,
        description="node_id of the state this action is available at",
        min_length=1,
    )
    target_state_id: str = Field(
        ...,
        description="node_id of the resulting state after this action",
        min_length=1,
    )
    input_type_signature: tuple[str, ...] = Field(
        default=(),
        description="Declared input type names",
    )
    output_type_signature: tuple[str, ...] = Field(
        default=(),
        description="Declared output type names",
    )
    diff_size_estimate: int = Field(
        default=0,
        ge=0,
        description="Estimated diff size for ordering",
    )
    latency_estimate_ms: int = Field(
        default=0,
        ge=0,
        description="Estimated latency in milliseconds for ordering",
    )

    @property
    def total_cost(self) -> int:
        """Composite cost score for ordering (lower = cheaper)."""
        return self.diff_size_estimate + self.latency_estimate_ms

    def __hash__(self) -> int:
        return hash(self.transition_id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TypedAction):
            return NotImplemented
        return self.transition_id == other.transition_id


def _evaluate_guard(
    guard: TransitionGuard,
    current_state: ContractState,
    agent_capabilities: frozenset[str],
) -> tuple[bool, str]:
    """Evaluate a transition guard against the current state.

    Pure function — no side effects, no network calls.

    Args:
        guard: The guard to evaluate.
        current_state: The state the guard is evaluated against.
        agent_capabilities: Capabilities the executing agent has.

    Returns:
        (passes, reason): passes=True if guard passes, reason is empty string
        on pass or a human-readable reason string on failure.
    """
    # Check capability constraint
    if guard.required_capabilities:
        missing = guard.required_capabilities - agent_capabilities
        if missing:
            return False, f"Missing capabilities: {sorted(missing)}"

    # Check schema version constraint
    if guard.required_schema_version is not None:
        if current_state.schema_version != guard.required_schema_version:
            return (
                False,
                f"Schema version mismatch: required={guard.required_schema_version!r}, "
                f"current={current_state.schema_version!r}",
            )

    # Check policy tier constraint
    if guard.policy_tier_max is not None:
        if current_state.policy_tier > guard.policy_tier_max:
            return (
                False,
                f"Policy tier {current_state.policy_tier} exceeds max {guard.policy_tier_max}",
            )

    # Check precondition metadata keys
    if guard.precondition_keys:
        missing_keys = guard.precondition_keys - set(current_state.metadata.keys())
        if missing_keys:
            return False, f"Missing precondition metadata keys: {sorted(missing_keys)}"

    return True, ""


def _transition_to_typed_action(transition: ContractTransition) -> TypedAction:
    """Convert a ContractTransition to a TypedAction."""
    return TypedAction(
        transition_id=transition.transition_id,
        label=transition.label,
        source_state_id=transition.source_state_id,
        target_state_id=transition.target_state_id,
        input_type_signature=transition.input_types,
        output_type_signature=transition.output_types,
        diff_size_estimate=transition.cost.diff_size_estimate,
        latency_estimate_ms=transition.cost.latency_estimate_ms,
    )


class ActionSetEnumerator:
    """Enumerates the valid typed action set for a given contract state.

    The action set is the bounded, strongly typed set of transitions the model
    can select from. Only transitions whose guards pass are included. The result
    is ordered by cost (cheaper transitions first).

    Example:
        >>> enumerator = ActionSetEnumerator()
        >>> actions = enumerator.enumerate(graph, current_state)
        >>> # actions is [] if terminal state (no outgoing transitions or all guarded)
    """

    def enumerate(
        self,
        graph: ContractGraph,
        current_state: ContractState,
        agent_capabilities: frozenset[str] | None = None,
    ) -> list[TypedAction]:
        """Enumerate valid typed actions from the current state.

        Runs in O(E) where E is the out-degree of current_state. No full graph
        scan is performed.

        Args:
            graph: The contract graph for this navigation session.
            current_state: The state to enumerate actions from.
            agent_capabilities: Capabilities of the executing agent. If None,
                assumes no capabilities (most restrictive evaluation).

        Returns:
            List of TypedAction instances ordered by total cost (ascending).
            Empty list if the state is terminal or all transitions are guarded.
        """
        if agent_capabilities is None:
            agent_capabilities = frozenset()

        outgoing = graph.get_outgoing_transitions(current_state.node_id)

        valid_actions: list[TypedAction] = []
        for transition in outgoing:
            guard = transition.guard
            passes, reason = _evaluate_guard(guard, current_state, agent_capabilities)
            if passes:
                valid_actions.append(_transition_to_typed_action(transition))
            else:
                logger.debug(
                    "Transition excluded by guard",
                    extra={
                        "transition_id": transition.transition_id,
                        "source_state_id": current_state.node_id,
                        "guard_reason": reason,
                    },
                )

        # Order by cost (lower = better), then by transition_id for determinism
        valid_actions.sort(key=lambda a: (a.total_cost, a.transition_id))
        return valid_actions


__all__ = [
    "ActionSetEnumerator",
    "TypedAction",
]
