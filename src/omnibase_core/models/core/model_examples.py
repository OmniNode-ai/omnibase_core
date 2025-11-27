"""
Examples model to replace Dict[str, Any] usage for examples fields.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from omnibase_core.models.examples.model_example import ModelExample
from omnibase_core.models.examples.model_example_metadata import ModelExampleMetadata
from omnibase_core.models.node_metadata.model_node_information import (
    ModelNodeInformation,
)

from .model_custom_settings import ModelCustomSettings

# Compatibility aliases
ExampleMetadata = ModelExampleMetadata

# Re-export for current standards
__all__ = [
    "ModelCustomSettings",
    "ModelExample",
    "ModelExampleMetadata",
    "ModelNodeInformation",
]
