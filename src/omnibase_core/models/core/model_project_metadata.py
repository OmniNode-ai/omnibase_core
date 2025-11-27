# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-05-29T06:01:33.492378'
# description: Stamped by ToolPython
# entrypoint: python://model_project_metadata
# hash: c0f792ed6e667c4eca139b85b9a6ad5e660a1b71664fa23e328dc66b8c5c1112
# last_modified_at: '2025-05-29T14:13:58.911890+00:00'
# lifecycle: active
# meta_type: tool
# metadata_version: 0.1.0
# name: model_project_metadata.py
# namespace: python://omnibase.model.model_project_metadata
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: ce8a74b5-9b6e-494e-abec-c3e5248b21aa
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Project metadata models.

This module now imports from separated model files for better organization
and compliance with one-model-per-file naming conventions.
"""

from pathlib import Path

from omnibase_core.models.core.model_generic_yaml import ModelGenericYaml
from omnibase_core.models.core.model_onex_version import ModelOnexVersionInfo

# Import separated models
from omnibase_core.models.examples.model_artifact_type_config import (
    ModelArtifactTypeConfig,
)
from omnibase_core.models.examples.model_metadata_validation_config import (
    ModelMetadataValidationConfig,
)
from omnibase_core.models.examples.model_namespace_config import ModelNamespaceConfig
from omnibase_core.models.examples.model_tree_generator_config import (
    ModelTreeGeneratorConfig,
)
from omnibase_core.models.metadata.model_metadata_constants import (
    METADATA_VERSION_KEY,
    NAMESPACE_KEY,
    PROJECT_ONEX_YAML_FILENAME,
    PROTOCOL_VERSION_KEY,
    SCHEMA_VERSION_KEY,
)

from .model_project_metadata_block import ModelProjectMetadataBlock

# Compatibility aliases
ArtifactTypeConfig = ModelArtifactTypeConfig
NamespaceConfig = ModelNamespaceConfig
MetadataValidationConfig = ModelMetadataValidationConfig
TreeGeneratorConfig = ModelTreeGeneratorConfig
ProjectMetadataBlock = ModelProjectMetadataBlock

# Re-export for current standards
__all__ = [
    "ModelArtifactTypeConfig",
    "ModelMetadataValidationConfig",
    "ModelNamespaceConfig",
    "ModelProjectMetadataBlock",
    "ModelTreeGeneratorConfig",
]

PROJECT_ONEX_YAML_PATH = (
    Path(__file__).parent.parent.parent.parent.parent / PROJECT_ONEX_YAML_FILENAME
)


def get_canonical_versions() -> ModelOnexVersionInfo:
    """
    Load canonical version fields from project.onex.yaml.
    Returns an ModelOnexVersionInfo model.
    Raises FileNotFoundError or KeyError if missing.
    """
    # Import here to avoid circular dependency
    from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

    # Load and validate YAML using Pydantic model
    yaml_model = load_and_validate_yaml_model(PROJECT_ONEX_YAML_PATH, ModelGenericYaml)
    data = yaml_model.model_dump()
    return ModelOnexVersionInfo(
        metadata_version=data[METADATA_VERSION_KEY],
        protocol_version=data[PROTOCOL_VERSION_KEY],
        schema_version=data[SCHEMA_VERSION_KEY],
    )


def get_canonical_namespace_prefix() -> str:
    """
    Load the canonical namespace prefix from project.onex.yaml ('namespace' field).
    Returns a string, e.g., 'omnibase'.
    Raises FileNotFoundError or KeyError if missing.
    """
    # Import here to avoid circular dependency
    from omnibase_core.utils.util_safe_yaml_loader import load_and_validate_yaml_model

    # Load and validate YAML using Pydantic model
    yaml_model = load_and_validate_yaml_model(PROJECT_ONEX_YAML_PATH, ModelGenericYaml)
    data = yaml_model.model_dump()
    namespace = data[NAMESPACE_KEY]
    # Type narrowing: ensure str return
    return str(namespace)
