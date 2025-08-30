"""
Tree generator configuration model.
"""

from typing import List, Optional

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_onex_ignore_section import \
    ModelOnexIgnoreSection

from .model_artifact_type_config import ModelArtifactTypeConfig
from .model_metadata_validation_config import ModelMetadataValidationConfig
from .model_namespace_config import ModelNamespaceConfig


class ModelTreeGeneratorConfig(BaseModel):
    """Configuration for tree generator."""

    artifact_types: List[ModelArtifactTypeConfig] = Field(default_factory=list)
    namespace: ModelNamespaceConfig = Field(default_factory=ModelNamespaceConfig)
    metadata_validation: ModelMetadataValidationConfig = Field(
        default_factory=ModelMetadataValidationConfig
    )
    tree_ignore: Optional[ModelOnexIgnoreSection] = Field(
        default=None,
        description="Glob patterns for files/directories to ignore during tree generation, using canonical .onexignore format. Example: {'patterns': ['__pycache__/', '*.pyc', '.git/']}",
    )
