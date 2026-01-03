"""
Generic YAML models for common YAML structure patterns.

These models provide type-safe validation for various YAML structures
that appear throughout the codebase, ensuring proper validation without
relying on yaml.safe_load() directly.

"""

from typing import TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.enum_core_error_code import EnumCoreErrorCode

# Import extracted YAML model classes
from omnibase_core.models.core.model_yaml_configuration import ModelYamlConfiguration
from omnibase_core.models.core.model_yaml_dictionary import ModelYamlDictionary
from omnibase_core.models.core.model_yaml_list import ModelYamlList
from omnibase_core.models.core.model_yaml_metadata import ModelYamlMetadata
from omnibase_core.models.core.model_yaml_policy import ModelYamlPolicy
from omnibase_core.models.core.model_yaml_registry import ModelYamlRegistry
from omnibase_core.models.core.model_yaml_state import ModelYamlState
from omnibase_core.models.core.model_yaml_with_examples import ModelYamlWithExamples
from omnibase_core.models.errors.model_onex_error import ModelOnexError

T = TypeVar("T", bound=BaseModel)


class ModelGenericYaml(BaseModel):
    """Generic YAML model for unstructured YAML data."""

    model_config = ConfigDict(extra="allow")

    # Allow any additional fields for maximum flexibility
    root_list: list[object] | None = Field(
        default=None, description="Root level list for YAML arrays"
    )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelGenericYaml":
        """
        Create ModelGenericYaml from YAML content.

        This is the only place where yaml.safe_load should be used
        for the ModelGenericYaml class.
        """
        try:
            data = yaml.safe_load(yaml_content)
            if data is None:
                data = {}
            if isinstance(data, list):
                # For root-level lists, wrap in a dict
                return cls(root_list=data)
            return cls(**data)
        except yaml.YAMLError as e:
            raise ModelOnexError(
                error_code=EnumCoreErrorCode.VALIDATION_ERROR,
                message=f"Invalid YAML content: {e}",
            ) from e


# Public API exports
__all__ = [
    "ModelGenericYaml",
    "ModelYamlConfiguration",
    "ModelYamlDictionary",
    "ModelYamlList",
    "ModelYamlMetadata",
    "ModelYamlPolicy",
    "ModelYamlRegistry",
    "ModelYamlState",
    "ModelYamlWithExamples",
]
