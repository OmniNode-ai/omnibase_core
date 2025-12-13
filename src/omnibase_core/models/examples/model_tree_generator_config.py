"""
Tree generator configuration model.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_onex_ignore_section import ModelOnexIgnoreSection
from omnibase_core.models.examples.model_artifact_type_config import (
    ModelArtifactTypeConfig,
)

from .model_metadata_validation_config import ModelMetadataValidationConfig
from .model_namespace_config import ModelNamespaceConfig


class ModelTreeGeneratorConfig(BaseModel):
    """Configuration for tree generator."""

    artifact_types: list[ModelArtifactTypeConfig] = Field(default_factory=list)
    namespace: ModelNamespaceConfig = Field(default_factory=ModelNamespaceConfig)
    metadata_validation: ModelMetadataValidationConfig = Field(
        default_factory=ModelMetadataValidationConfig,
    )
    tree_ignore: ModelOnexIgnoreSection | None = Field(
        default=None,
        description="Glob patterns for files/directories to ignore during tree generation, using canonical .onexignore format. Example: {'patterns': ['__pycache__/', '*.pyc', '.git/']}",
    )
