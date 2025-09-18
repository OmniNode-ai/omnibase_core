"""
Generic YAML models for common YAML structure patterns.

These models provide type-safe validation for various YAML structures
that appear throughout the codebase, ensuring proper validation without
relying on yaml.safe_load() directly.

Author: ONEX Framework Team
"""

from typing import Any, TypeVar

import yaml
from pydantic import BaseModel, ConfigDict, Field

from .model_contract_action import ModelContractAction
from .model_generic_metadata import ModelGenericMetadata
from .model_yaml_items import (
    ModelYamlCommand,
    ModelYamlEntry,
    ModelYamlExample,
    ModelYamlOptions,
    ModelYamlParameters,
    ModelYamlPermissions,
    ModelYamlRegistryItem,
    ModelYamlRule,
)
from .model_yaml_items import ModelYamlState as ModelYamlStateItem

T = TypeVar("T", bound=BaseModel)


class ModelGenericYaml(BaseModel):
    """Generic YAML model for unstructured YAML data."""

    model_config = ConfigDict(extra="allow")

    # Allow any additional fields for maximum flexibility
    root_list: list[dict[str, str]] | None = Field(
        None, description="Root level list for YAML arrays"
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
            raise ValueError(f"Invalid YAML content: {e}") from e


class ModelYamlDictionary(BaseModel):
    """Model for YAML files that are primarily key-value dictionaries."""

    model_config = ConfigDict(extra="allow")

    # Common dictionary patterns in YAML files
    name: str | None = Field(None, description="Optional name field")
    version: str | None = Field(None, description="Optional version field")
    description: str | None = Field(None, description="Optional description field")


class ModelYamlConfiguration(BaseModel):
    """Model for YAML configuration files."""

    model_config = ConfigDict(extra="allow")

    # Common configuration patterns
    config: ModelGenericMetadata | None = Field(
        None, description="Configuration section"
    )
    settings: ModelGenericMetadata | None = Field(None, description="Settings section")
    options: ModelYamlOptions | None = Field(None, description="Options section")
    parameters: ModelYamlParameters | None = Field(
        None, description="Parameters section"
    )


class ModelYamlMetadata(BaseModel):
    """Model for YAML files containing metadata."""

    model_config = ConfigDict(extra="allow")

    # Common metadata patterns
    metadata: ModelGenericMetadata | None = Field(None, description="Metadata section")
    title: str | None = Field(None, description="Optional title")
    description: str | None = Field(None, description="Optional description")
    author: str | None = Field(None, description="Optional author")
    version: str | None = Field(None, description="Optional version")
    created_at: str | None = Field(None, description="Optional creation timestamp")
    updated_at: str | None = Field(None, description="Optional update timestamp")


class ModelYamlRegistry(BaseModel):
    """Model for YAML files that define registries or lists of items."""

    model_config = ConfigDict(extra="allow")

    # Common registry patterns
    registry: dict[str, ModelYamlRegistryItem] | None = Field(
        None, description="Registry section"
    )
    items: list[ModelYamlRegistryItem] | None = Field(None, description="Items list")
    entries: list[ModelYamlEntry] | None = Field(None, description="Entries list")
    actions: list[ModelContractAction] | None = Field(None, description="Actions list")
    commands: list[ModelYamlCommand] | None = Field(None, description="Commands list")


class ModelYamlWithExamples(BaseModel):
    """Model for YAML files that contain examples sections."""

    model_config = ConfigDict(extra="allow")

    # For schema files with examples
    examples: list[ModelYamlExample] | None = Field(
        None, description="Examples section"
    )

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "ModelYamlWithExamples":
        """
        Create ModelYamlWithExamples from YAML content.

        This is the only place where yaml.safe_load should be used
        for the ModelYamlWithExamples class.
        """
        try:
            data = yaml.safe_load(yaml_content)
            if data is None:
                data = {}
            if isinstance(data, list):
                # For root-level lists, try to find examples
                return cls(examples=data if data else None)
            return cls(**data)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML content: {e}") from e


class ModelYamlPolicy(BaseModel):
    """Model for YAML policy files."""

    model_config = ConfigDict(extra="allow")

    # Common policy patterns
    policy: dict[str, str] | None = Field(None, description="Policy definition")
    rules: list[ModelYamlRule] | None = Field(None, description="Policy rules")
    permissions: ModelYamlPermissions | None = Field(None, description="Permissions")
    restrictions: ModelYamlPermissions | None = Field(None, description="Restrictions")


class ModelYamlState(BaseModel):
    """Model for YAML state files."""

    model_config = ConfigDict(extra="allow")

    # Common state patterns
    state: ModelYamlStateItem | None = Field(None, description="State section")
    status: str | None = Field(None, description="Status field")
    data: ModelGenericMetadata | None = Field(None, description="Data section")


class ModelYamlList(BaseModel):
    """Model for YAML files that are primarily lists."""

    model_config = ConfigDict(extra="allow")

    # For files that are root-level arrays
    root_list: list[dict[str, str]] = Field(
        default_factory=list, description="Root level list"
    )

    def __init__(self, data: list[dict[str, str]] | None = None, **kwargs: Any) -> None:
        """Handle case where YAML root is a list."""
        if isinstance(data, list):
            super().__init__(root_list=data, **kwargs)
        else:
            super().__init__(**kwargs)
