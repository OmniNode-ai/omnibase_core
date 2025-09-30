"""
Strongly-typed computation data models.

Replaces dict[str, Any] usage in computation operations with structured typing.
Follows ONEX strong typing principles and one-model-per-file architecture.

"""

from __future__ import annotations

# Import models from individual files following ONEX one-model-per-file architecture
from .model_computation_input_data import ModelComputationInputData
from .model_computation_output_data import ModelComputationOutputData

# Export all models
__all__ = ["ModelComputationInputData", "ModelComputationOutputData"]
