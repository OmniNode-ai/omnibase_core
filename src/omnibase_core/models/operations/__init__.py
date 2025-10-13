from typing import Dict, List

from omnibase_core.models.core.model_workflow import ModelWorkflow

"""
Operations models for strongly-typed data structures.

This module provides typed models to replace dict[str, Any] usage patterns.
"""

from typing import Any

from .model_computation_data import (
    ModelComputationInputData,
    ModelComputationOutputData,
)
from .model_compute_input import ModelComputeInput
from .model_compute_operation_data import ModelComputeOperationData
from .model_compute_output import ModelComputeOutput
from .model_effect_input import ModelEffectInput
from .model_effect_operation_data import ModelEffectOperationData
from .model_effect_output import ModelEffectOutput
from .model_effect_result import (
    ModelEffectResult,
    ModelEffectResultBool,
    ModelEffectResultDict,
    ModelEffectResultList,
    ModelEffectResultStr,
)
from .model_metadata_structures import (
    ModelEventMetadata,
    ModelExecutionMetadata,
    ModelSystemMetadata,
    ModelWorkflowInstanceMetadata,
)
from .model_operation_data_base import ModelOperationDataBase
from .model_operation_parameters import (
    ModelEffectParameters,
    ModelOperationParameters,
    ModelWorkflowParameters,
)
from .model_operation_payload_parameters_base import ModelOperationParametersBase
from .model_orchestrator_input import ModelOrchestratorInput
from .model_orchestrator_operation_data import ModelOrchestratorOperationData
from .model_orchestrator_output import ModelOrchestratorOutput
from .model_payload_structures import (
    ModelEventPayload,
    ModelMessagePayload,
    ModelOperationPayload,
    ModelWorkflowPayload,
)
from .model_reducer_input import ModelReducerInput
from .model_reducer_operation_data import ModelReducerOperationData
from .model_reducer_output import ModelReducerOutput

__all__ = [
    "ModelComputationInputData",
    "ModelComputationOutputData",
    "ModelComputeInput",
    "ModelComputeOperationData",
    "ModelComputeOutput",
    "ModelEffectInput",
    "ModelEffectOperationData",
    "ModelEffectOutput",
    "ModelEffectParameters",
    "ModelEffectResult",
    "ModelEffectResultBool",
    "ModelEffectResultDict",
    "ModelEffectResultList",
    "ModelEffectResultStr",
    "ModelEventMetadata",
    "ModelEventPayload",
    "ModelExecutionMetadata",
    "ModelMessagePayload",
    "ModelOperationDataBase",
    "ModelOperationParameters",
    "ModelOperationPayload",
    "ModelOperationParametersBase",
    "ModelOrchestratorInput",
    "ModelOrchestratorOperationData",
    "ModelOrchestratorOutput",
    "ModelReducerInput",
    "ModelReducerOperationData",
    "ModelReducerOutput",
    "ModelSystemMetadata",
    "ModelWorkflowInstanceMetadata",
    "ModelWorkflowParameters",
    "ModelWorkflowPayload",
]
