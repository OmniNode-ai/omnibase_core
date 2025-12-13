"""
Strongly-typed operation parameters models.

Replaces dict[str, Any] usage in operation parameters with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.

"""

from __future__ import annotations

from .model_effect_parameters import ModelEffectParameters

# Import models from individual files following ONEX one-model-per-file architecture
from .model_operationparameters import ModelOperationParameters
from .model_workflow_parameters import ModelWorkflowParameters

# Export all models
__all__ = [
    "ModelEffectParameters",
    "ModelOperationParameters",
    "ModelWorkflowParameters",
]
