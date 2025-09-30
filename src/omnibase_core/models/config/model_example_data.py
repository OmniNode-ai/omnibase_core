"""
Example data model.

Clean, strongly-typed replacement for dict[str, Any] in example input/output data.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

# Re-export models from their individual files
from .model_example_input_data import ModelExampleInputData
from .model_example_output_data import ModelExampleOutputData

# Export the models
__all__ = [
    "ModelExampleInputData",
    "ModelExampleOutputData",
]
