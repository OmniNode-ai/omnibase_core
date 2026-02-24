# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Graph Boundary Enforcement and Backward Chaining Types (OMN-2554, OMN-2561).

Implements:
- ValidationResult discriminated union (Valid | Rejected) for OMN-2554
- RejectionReason discriminated union for OMN-2554
- GraphBoundaryEnforcer for OMN-2554
- GoalCondition, PlanStep, PlanResult, NoPlanReason types for OMN-2561

Design principles:
- Structured rejection reasons (machine-readable, not free-form strings)
- Enforcer is stateless (no side effects beyond structured logging)
- Validation completes in O(1) given the pre-enumerated action set
- Never passes invalid actions to any node or downstream system
- Never raises unhandled exceptions for model-generated invalid selections
"""

import logging
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.navigation.model_action_set import TypedAction

logger = logging.getLogger(__name__)


# =============================================================================
# Rejection Reasons (structured, machine-readable)
# =============================================================================


class NotInActionSet(BaseModel):
    """Rejection reason: the selected action is not in the enumerated action set."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["not_in_action_set"] = Field(default="not_in_action_set")
    transition_id: str = Field(
        ...,
        description="The transition_id that was not found in the action set",
    )
    state_id: str = Field(
        ...,
        description="The state node_id at which the action was attempted",
    )


class GuardFailed(BaseModel):
    """Rejection reason: the selected action's guard failed at validation time."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["guard_failed"] = Field(default="guard_failed")
    transition_id: str = Field(
        ...,
        description="The transition_id whose guard failed",
    )
    guard_name: str = Field(
        ...,
        description="Name of the guard that failed (e.g., 'capability', 'schema_version', 'policy_tier', 'precondition_keys')",
    )
    detail: str = Field(
        ...,
        description="Human-readable detail about why the guard failed",
    )


class PreconditionNotSatisfied(BaseModel):
    """Rejection reason: a declared precondition for the transition is not satisfied."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["precondition_not_satisfied"] = Field(
        default="precondition_not_satisfied"
    )
    transition_id: str = Field(
        ...,
        description="The transition_id whose precondition is not satisfied",
    )
    precondition: str = Field(
        ...,
        description="The precondition that is not satisfied",
    )


RejectionReason = Annotated[
    NotInActionSet | GuardFailed | PreconditionNotSatisfied,
    Field(discriminator="kind"),
]


# =============================================================================
# ValidationResult discriminated union
# =============================================================================


class Valid(BaseModel):
    """Validation result: the selected action is valid and may proceed."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["valid"] = Field(default="valid")
    transition_id: str = Field(
        ...,
        description="The validated transition_id",
    )


class Rejected(BaseModel):
    """Validation result: the selected action is rejected."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["rejected"] = Field(default="rejected")
    reason: RejectionReason = Field(
        ...,
        description="Structured reason for rejection",
    )


ValidationResult = Annotated[
    Valid | Rejected,
    Field(discriminator="kind"),
]


# =============================================================================
# Goal condition and plan types (OMN-2561)
# =============================================================================


class GoalCondition(BaseModel):
    """Declared terminal predicates for backward chaining navigation.

    The backward chaining planner works backwards from the goal state.
    A goal condition declares what must be true of the terminal state.

    Attributes:
        target_node_id: If set, the goal state must have this node_id.
        required_output_types: Output types the goal state's incoming transition
            must produce (at least one must match if non-empty).
        required_capabilities: Capabilities the goal state must have
            (intersection must be non-empty if non-empty).
        policy_tier_max: Maximum policy tier of the goal state.
        required_metadata_keys: Keys that must be present in goal state metadata.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target_node_id: str | None = Field(
        default=None,
        description="If set, goal state must have exactly this node_id",
    )
    required_output_types: frozenset[str] = Field(
        default_factory=frozenset,
        description="At least one of these output types must be produced by the reaching transition",
    )
    required_capabilities: frozenset[str] = Field(
        default_factory=frozenset,
        description="Goal state must have all of these capabilities",
    )
    policy_tier_max: int | None = Field(
        default=None,
        description="Goal state policy_tier must be <= this value if set",
    )
    required_metadata_keys: frozenset[str] = Field(
        default_factory=frozenset,
        description="Goal state metadata must contain all of these keys",
    )


class PlanStep(BaseModel):
    """A single step in a backward-chained execution plan.

    Each step corresponds to exactly one declared ContractTransition.

    Attributes:
        transition_id: The ContractTransition to execute.
        pre_state_id: Expected node_id of the state before this transition.
        post_state_id: Expected node_id of the state after this transition.
        step_index: 0-based index in the ordered plan (0 = first step to execute).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    transition_id: str = Field(
        ...,
        description="The transition to execute in this step",
    )
    pre_state_id: str = Field(
        ...,
        description="Expected state node_id before this transition",
    )
    post_state_id: str = Field(
        ...,
        description="Expected state node_id after this transition",
    )
    step_index: int = Field(
        ...,
        ge=0,
        description="0-based index in the ordered plan",
    )


# =============================================================================
# NoPlanReason discriminated union
# =============================================================================


class RequiredTransitionNotInGraph(BaseModel):
    """No plan found: goal is unreachable because required transitions are absent."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["required_transition_not_in_graph"] = Field(
        default="required_transition_not_in_graph"
    )
    goal_node_id: str | None = Field(
        default=None,
        description="The goal node_id that could not be reached, if known",
    )


class CycleDetected(BaseModel):
    """No plan found: all paths to the goal contain cycles (no acyclic path exists)."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["cycle_detected"] = Field(default="cycle_detected")
    cycle_node_ids: tuple[str, ...] = Field(
        default=(),
        description="Node IDs involved in the detected cycle, if available",
    )


class MaxDepthExceeded(BaseModel):
    """No plan found: depth limit was reached before goal was satisfied."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["max_depth_exceeded"] = Field(default="max_depth_exceeded")
    max_depth: int = Field(
        ...,
        ge=1,
        description="The depth limit that was exceeded",
    )


NoPlanReason = Annotated[
    RequiredTransitionNotInGraph | CycleDetected | MaxDepthExceeded,
    Field(discriminator="kind"),
]


# =============================================================================
# PlanResult discriminated union
# =============================================================================


class Plan(BaseModel):
    """Plan result: a valid execution plan was found."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["plan"] = Field(default="plan")
    steps: tuple[PlanStep, ...] = Field(
        ...,
        description="Ordered execution steps (index 0 is first)",
    )


class NoPlanFound(BaseModel):
    """Plan result: no valid plan could be found."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["no_plan_found"] = Field(default="no_plan_found")
    reason: NoPlanReason = Field(
        ...,
        description="Structured reason why no plan was found",
    )


class GoalAlreadySatisfied(BaseModel):
    """Plan result: the current state already satisfies the goal condition."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    kind: Literal["goal_already_satisfied"] = Field(default="goal_already_satisfied")
    current_state_id: str = Field(
        ...,
        description="The state node_id that satisfies the goal",
    )


PlanResult = Annotated[
    Plan | NoPlanFound | GoalAlreadySatisfied,
    Field(discriminator="kind"),
]


# =============================================================================
# GraphBoundaryEnforcer (OMN-2554)
# =============================================================================


class GraphBoundaryEnforcer:
    """Enforces the graph boundary: only valid typed actions may proceed.

    The enforcer is stateless — no side effects beyond structured logging.
    It never raises unhandled exceptions for model-generated invalid selections;
    those are expected inputs, not programming errors.

    Validation completes in O(1) given the pre-enumerated action set.

    Example:
        >>> enforcer = GraphBoundaryEnforcer()
        >>> action_set = enumerator.enumerate(graph, current_state)
        >>> result = enforcer.validate(
        ...     current_state=current_state,
        ...     selected_action=my_action,
        ...     action_set=action_set,
        ...     session_id="nav-001",
        ... )
        >>> if isinstance(result, Valid):
        ...     proceed_with_transition(result.transition_id)
    """

    def validate(
        self,
        current_state_id: str,
        selected_action: TypedAction,
        action_set: list[TypedAction],
        session_id: str = "",
    ) -> ValidationResult:
        """Validate that the selected action is in the enumerated action set.

        Args:
            current_state_id: The node_id of the current contract state.
            selected_action: The TypedAction the model selected.
            action_set: The pre-enumerated list of valid TypedAction instances
                for this state (from ActionSetEnumerator.enumerate()).
            session_id: Navigation session ID for structured logging.

        Returns:
            Valid if the action is in the action set.
            Rejected with a structured RejectionReason if not.
        """
        # Build O(1) lookup from pre-enumerated action set
        valid_ids: frozenset[str] = frozenset(a.transition_id for a in action_set)

        if selected_action.transition_id not in valid_ids:
            reason: RejectionReason = NotInActionSet(
                transition_id=selected_action.transition_id,
                state_id=current_state_id,
            )
            logger.warning(
                "Graph boundary rejected action: not in action set",
                extra={
                    "session_id": session_id,
                    "current_state_id": current_state_id,
                    "attempted_transition_id": selected_action.transition_id,
                    "rejection_kind": "not_in_action_set",
                    "valid_transition_count": len(valid_ids),
                },
            )
            return Rejected(reason=reason)

        logger.debug(
            "Graph boundary accepted action",
            extra={
                "session_id": session_id,
                "current_state_id": current_state_id,
                "transition_id": selected_action.transition_id,
            },
        )
        return Valid(transition_id=selected_action.transition_id)


__all__ = [
    # Rejection reasons
    "CycleDetected",
    "GoalAlreadySatisfied",
    "GoalCondition",
    "GraphBoundaryEnforcer",
    "GuardFailed",
    "MaxDepthExceeded",
    "NoPlanFound",
    "NoPlanReason",
    "NotInActionSet",
    "Plan",
    "PlanResult",
    "PlanStep",
    "PreconditionNotSatisfied",
    "Rejected",
    "RejectionReason",
    "RequiredTransitionNotInGraph",
    "Valid",
    "ValidationResult",
]
