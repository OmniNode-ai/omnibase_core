"""
Omnibase Core - ONEX Four-Node Architecture

Node implementations for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR patterns.

All nodes use declarative YAML contracts for configuration.

STABILITY: This module's public API is frozen as of VERSION 1.0.0.
The exported symbols (NodeCompute, NodeEffect, NodeReducer, NodeOrchestrator)
are guaranteed stable and will not change without deprecation warnings.

.. versionadded:: 0.4.0
"""

from omnibase_core.enums.enum_orchestrator_types import (
    EnumActionType,
    EnumBranchCondition,
    EnumExecutionMode,
    EnumWorkflowState,
)
from omnibase_core.enums.enum_reducer_types import (
    EnumConflictResolution,
    EnumReductionType,
    EnumStreamingMode,
)
from omnibase_core.models.compute.model_compute_input import ModelComputeInput
from omnibase_core.models.compute.model_compute_output import ModelComputeOutput
from omnibase_core.models.effect.model_effect_input import ModelEffectInput
from omnibase_core.models.effect.model_effect_output import ModelEffectOutput
from omnibase_core.models.infrastructure.model_effect_transaction import (
    ModelEffectTransaction,
)
from omnibase_core.models.orchestrator import ModelOrchestratorOutput
from omnibase_core.models.orchestrator.model_orchestrator_input import (
    ModelOrchestratorInput,
)
from omnibase_core.models.reducer.model_reducer_input import ModelReducerInput
from omnibase_core.models.reducer.model_reducer_output import ModelReducerOutput
from omnibase_core.nodes.node_compute import NodeCompute
from omnibase_core.nodes.node_effect import NodeEffect
from omnibase_core.nodes.node_orchestrator import NodeOrchestrator
from omnibase_core.nodes.node_reducer import NodeReducer

# NOTE: Internal models like ModelConflictResolver, ModelDependencyGraph, ModelLoadBalancer,
# ModelStreamingWindow, ModelAction, ModelWorkflowStep are NOT exported - they are internal
# implementation details used by the nodes themselves.

__all__ = [
    # Node implementations (inherit from these)
    "NodeCompute",
    "NodeEffect",
    "NodeOrchestrator",
    "NodeReducer",
    # Input/Output models (use these for process() calls)
    "ModelComputeInput",
    "ModelComputeOutput",
    "ModelEffectInput",
    "ModelEffectOutput",
    "ModelEffectTransaction",  # For rollback failure callback type hints
    "ModelOrchestratorInput",
    "ModelOrchestratorOutput",
    "ModelReducerInput",
    "ModelReducerOutput",
    # Public enums (use these for configuration)
    "EnumActionType",
    "EnumBranchCondition",
    "EnumExecutionMode",
    "EnumWorkflowState",
    "EnumConflictResolution",
    "EnumReductionType",
    "EnumStreamingMode",
]
