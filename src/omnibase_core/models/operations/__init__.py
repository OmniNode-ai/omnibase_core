"""
Operations models for strongly-typed data structures.

This module provides typed models to replace dict[str, Any] usage patterns.
"""

from .model_change_proposal import ModelChangeProposal
from .model_computation_data import (
    ModelComputationInputData,
    ModelComputationOutputData,
)
from .model_compute_operation_data import ModelComputeOperationData
from .model_effect_operation_config import ModelEffectOperationConfig
from .model_effect_operation_data import ModelEffectOperationData
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
from .model_orchestrator_operation_data import ModelOrchestratorOperationData
from .model_payload_structures import (
    ModelEventPayload,
    ModelMessagePayload,
    ModelOperationPayload,
    ModelWorkflowPayload,
)
from .model_reducer_operation_data import ModelReducerOperationData

__all__ = [
    "ModelChangeProposal",
    "ModelComputationInputData",
    "ModelComputationOutputData",
    "ModelComputeOperationData",
    "ModelEffectOperationConfig",
    "ModelEffectOperationData",
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
    "ModelOrchestratorOperationData",
    "ModelReducerOperationData",
    "ModelSystemMetadata",
    "ModelWorkflowInstanceMetadata",
    "ModelWorkflowParameters",
    "ModelWorkflowPayload",
]
