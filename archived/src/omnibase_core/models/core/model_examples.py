"""
Examples model to replace Dict[str, Any] usage for examples fields.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from .model_custom_settings import ModelCustomSettings
from .model_example import ModelExample

# Import separated models
from .model_example_metadata import ModelExampleMetadata
from .model_examples_collection import ModelExamples
from .model_node_information import ModelNodeInformation

# Compatibility aliases
ExampleMetadata = ModelExampleMetadata

# Re-export for current standards
__all__ = [
    # Compatibility
    "ExampleMetadata",
    "ModelCustomSettings",
    "ModelExample",
    "ModelExampleMetadata",
    "ModelExamples",
    "ModelNodeInformation",
]
