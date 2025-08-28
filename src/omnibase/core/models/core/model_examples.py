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

# Backward compatibility aliases
ExampleMetadata = ModelExampleMetadata

# Re-export for backward compatibility
__all__ = [
    "ModelExampleMetadata",
    "ModelExample",
    "ModelExamples",
    "ModelCustomSettings",
    "ModelNodeInformation",
    # Backward compatibility
    "ExampleMetadata",
]
