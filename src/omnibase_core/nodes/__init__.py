# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Omnibase Core - ONEX Four-Node Architecture

Node implementations for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR patterns.

All nodes use declarative YAML contracts for configuration.

STABILITY: This module's public API is frozen as of v0.4.0.
Exported symbols in __all__ are guaranteed stable for the v0.x series.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnibase_core.enums.enum_orchestrator_types import (
        EnumActionType,
        EnumBranchCondition,
        EnumExecutionMode,
    )
    from omnibase_core.enums.enum_reducer_types import (
        EnumConflictResolution,
        EnumReductionType,
        EnumStreamingMode,
    )
    from omnibase_core.enums.enum_workflow_status import EnumWorkflowStatus
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

# Importing a concrete node submodule also initializes this package. Keep its
# unrelated base nodes and models unloaded until a caller requests an export.
_LAZY_EXPORTS: dict[str, str] = {
    "EnumActionType": "omnibase_core.enums.enum_orchestrator_types",
    "EnumBranchCondition": "omnibase_core.enums.enum_orchestrator_types",
    "EnumExecutionMode": "omnibase_core.enums.enum_orchestrator_types",
    "EnumConflictResolution": "omnibase_core.enums.enum_reducer_types",
    "EnumReductionType": "omnibase_core.enums.enum_reducer_types",
    "EnumStreamingMode": "omnibase_core.enums.enum_reducer_types",
    "EnumWorkflowStatus": "omnibase_core.enums.enum_workflow_status",
    "ModelComputeInput": "omnibase_core.models.compute.model_compute_input",
    "ModelComputeOutput": "omnibase_core.models.compute.model_compute_output",
    "ModelEffectInput": "omnibase_core.models.effect.model_effect_input",
    "ModelEffectOutput": "omnibase_core.models.effect.model_effect_output",
    "ModelEffectTransaction": "omnibase_core.models.infrastructure.model_effect_transaction",
    "ModelOrchestratorOutput": "omnibase_core.models.orchestrator",
    "ModelOrchestratorInput": "omnibase_core.models.orchestrator.model_orchestrator_input",
    "ModelReducerInput": "omnibase_core.models.reducer.model_reducer_input",
    "ModelReducerOutput": "omnibase_core.models.reducer.model_reducer_output",
    "NodeCompute": "omnibase_core.nodes.node_compute",
    "NodeEffect": "omnibase_core.nodes.node_effect",
    "NodeOrchestrator": "omnibase_core.nodes.node_orchestrator",
    "NodeReducer": "omnibase_core.nodes.node_reducer",
}


def __getattr__(name: str) -> object:
    module_path = _LAZY_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(importlib.import_module(module_path), name)
    globals()[name] = value
    return value


# NOTE: Internal utilities like UtilConflictResolver, ModelDependencyGraph, ModelLoadBalancer,
# UtilStreamingWindow, ModelAction, ModelWorkflowStep are NOT exported - they are internal
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
    "EnumWorkflowStatus",
    "EnumConflictResolution",
    "EnumReductionType",
    "EnumStreamingMode",
]
