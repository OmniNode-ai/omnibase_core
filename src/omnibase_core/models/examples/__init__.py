"""
Configuration Models

Models for system configuration, artifacts, and declarative settings.
"""

from omnibase_core.models.core.model_examples_collection import ModelExamplesCollection
from omnibase_core.models.examples.model_data_handling_declaration import (
    ModelDataHandlingDeclaration,
)
from omnibase_core.models.examples.model_example import ModelExample
from omnibase_core.models.examples.model_example_metadata import ModelExampleMetadata
from omnibase_core.models.examples.model_fallback_strategy import ModelFallbackStrategy

from .model_artifact_type_config import ModelArtifactTypeConfig
from .model_environment_properties import ModelEnvironmentProperties
from .model_example_context_data import ModelExampleContextData
from .model_example_data import ModelExampleInputData, ModelExampleOutputData
from .model_example_metadata_summary import ModelExampleMetadataSummary
from .model_example_summary import ModelExampleSummary
from .model_examples_collection_summary import ModelExamplesCollectionSummary
from .model_fallback_metadata import ModelFallbackMetadata
from .model_namespace_config import ModelNamespaceConfig
from .model_property_collection import ModelPropertyCollection
from .model_property_metadata import ModelPropertyMetadata
from .model_property_value import ModelPropertyValue
from .model_typed_property import ModelTypedProperty
from .model_uri import ModelOnexUri

__all__ = [
    "ModelArtifactTypeConfig",
    "ModelDataHandlingDeclaration",
    "ModelEnvironmentProperties",
    "ModelExample",
    "ModelExampleContextData",
    "ModelExampleInputData",
    "ModelExampleMetadata",
    "ModelExampleMetadataSummary",
    "ModelExampleOutputData",
    "ModelExampleSummary",
    "ModelExamplesCollection",
    "ModelExamplesCollectionSummary",
    "ModelFallbackMetadata",
    "ModelFallbackStrategy",
    "ModelNamespaceConfig",
    "ModelOnexUri",
    "ModelPropertyCollection",
    "ModelPropertyMetadata",
    "ModelPropertyValue",
    "ModelTypedProperty",
]
