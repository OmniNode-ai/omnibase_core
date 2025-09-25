"""
Operations models for strongly-typed data structures.

This module provides typed models to replace dict[str, Any] usage patterns.
"""

from .model_computation_data import (
    ModelComputationInputData,
    ModelComputationOutputData,
)
from .model_metadata_structures import (
    ModelEventMetadata,
    ModelExecutionMetadata,
    ModelSystemMetadata,
    ModelWorkflowMetadata,
)
from .model_operation_parameters import (
    ModelEffectParameters,
    ModelOperationParameters,
    ModelWorkflowParameters,
)
from .model_payload_structures import (
    ModelEventPayload,
    ModelMessagePayload,
    ModelOperationPayload,
    ModelWorkflowPayload,
)

__all__ = [
    "ModelComputationInputData",
    "ModelComputationOutputData",
    "ModelExecutionMetadata",
    "ModelWorkflowMetadata",
    "ModelEventMetadata",
    "ModelSystemMetadata",
    "ModelOperationParameters",
    "ModelWorkflowParameters",
    "ModelEffectParameters",
    "ModelMessagePayload",
    "ModelWorkflowPayload",
    "ModelOperationPayload",
    "ModelEventPayload",
]
