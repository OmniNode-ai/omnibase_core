# SPDX-FileCopyrightText: 2026 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
ONEX Contract Graph Navigation module.

Provides contract graph data models, construction from node registry,
typed action enumeration, graph boundary enforcement, and backward
chaining planning for goal-conditioned navigation.

Public API (OMN-2365 epic: Local Agent Graph Navigation):
    - ContractState: A declared, schema-validated node contract state
    - ContractTransition: A typed edge between contract states
    - TransitionGuard: Guard conditions on a transition
    - TransitionCost: Cost metadata for a transition
    - ContractGraph: The contract graph with node/edge lookup
    - RegistryNode: A node entry from the registry snapshot
    - RegistrySnapshot: Snapshot of the node registry
    - ContractGraphBuilder: Builds ContractGraph from registry snapshot
    - TypedAction: Strongly typed action (transition) available at a state
    - ActionSetEnumerator: Enumerates valid typed actions at a state
    - ValidationResult, Valid, Rejected: Validation result discriminated union
    - RejectionReason, NotInActionSet, GuardFailed, PreconditionNotSatisfied: Rejection reasons
    - GraphBoundaryEnforcer: Validates and enforces graph boundary
    - GoalCondition: Declared goal condition for backward chaining
    - PlanStep: A single step in a plan
    - PlanResult, Plan, NoPlanFound, GoalAlreadySatisfied: Plan result union
    - NoPlanReason, RequiredTransitionNotInGraph, CycleDetected, MaxDepthExceeded: No-plan reasons
    - BackwardChainingPlanner: Goal-conditioned backward chaining planner
"""

from omnibase_core.navigation.model_action_set import ActionSetEnumerator, TypedAction
from omnibase_core.navigation.model_backward_chaining import BackwardChainingPlanner
from omnibase_core.navigation.model_contract_graph import (
    ContractGraph,
    ContractState,
    ContractTransition,
    RegistryNode,
    RegistrySnapshot,
    TransitionCost,
    TransitionGuard,
)
from omnibase_core.navigation.model_contract_graph_builder import ContractGraphBuilder
from omnibase_core.navigation.model_graph_boundary import (
    CycleDetected,
    GoalAlreadySatisfied,
    GoalCondition,
    GraphBoundaryEnforcer,
    GuardFailed,
    MaxDepthExceeded,
    NoPlanFound,
    NoPlanReason,
    NotInActionSet,
    Plan,
    PlanResult,
    PlanStep,
    PreconditionNotSatisfied,
    Rejected,
    RejectionReason,
    RequiredTransitionNotInGraph,
    Valid,
    ValidationResult,
)

__all__ = [
    # Data models (OMN-2540)
    "ContractState",
    "ContractTransition",
    "TransitionGuard",
    "TransitionCost",
    "ContractGraph",
    "RegistryNode",
    "RegistrySnapshot",
    # Graph builder (OMN-2540)
    "ContractGraphBuilder",
    # Typed action enumeration (OMN-2546)
    "TypedAction",
    "ActionSetEnumerator",
    # Graph boundary enforcement (OMN-2554)
    "ValidationResult",
    "Valid",
    "Rejected",
    "RejectionReason",
    "NotInActionSet",
    "GuardFailed",
    "PreconditionNotSatisfied",
    "GraphBoundaryEnforcer",
    # Backward chaining planner (OMN-2561)
    "GoalCondition",
    "PlanStep",
    "PlanResult",
    "Plan",
    "NoPlanFound",
    "GoalAlreadySatisfied",
    "NoPlanReason",
    "RequiredTransitionNotInGraph",
    "CycleDetected",
    "MaxDepthExceeded",
    "BackwardChainingPlanner",
]
