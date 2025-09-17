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

T = TypeVar("T", bound=BaseModel)


class ModelGenericYaml(BaseModel):
    """Generic YAML model for unstructured YAML data."""

    model_config = ConfigDict(extra="allow")

    # Allow any additional fields for maximum flexibility
    root_list: list[Any] | None = Field(
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
    config: dict[str, Any] | None = Field(None, description="Configuration section")
    settings: dict[str, Any] | None = Field(None, description="Settings section")
    options: dict[str, Any] | None = Field(None, description="Options section")
    parameters: dict[str, Any] | None = Field(None, description="Parameters section")


class ModelYamlMetadata(BaseModel):
    """Model for YAML files containing metadata."""

    model_config = ConfigDict(extra="allow")

    # Common metadata patterns
    metadata: dict[str, Any] | None = Field(None, description="Metadata section")
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
    registry: dict[str, Any] | None = Field(None, description="Registry section")
    items: list[dict[str, Any]] | None = Field(None, description="Items list")
    entries: list[dict[str, Any]] | None = Field(None, description="Entries list")
    actions: list[dict[str, Any]] | None = Field(None, description="Actions list")
    commands: list[dict[str, Any]] | None = Field(None, description="Commands list")


class ModelYamlWithExamples(BaseModel):
    """Model for YAML files that contain examples sections."""

    model_config = ConfigDict(extra="allow")

    # For schema files with examples
    examples: list[dict[str, Any]] | None = Field(None, description="Examples section")

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
    policy: dict[str, Any] | None = Field(None, description="Policy definition")
    rules: list[dict[str, Any]] | None = Field(None, description="Policy rules")
    permissions: dict[str, Any] | None = Field(None, description="Permissions")
    restrictions: dict[str, Any] | None = Field(None, description="Restrictions")


class ModelYamlState(BaseModel):
    """Model for YAML state files."""

    model_config = ConfigDict(extra="allow")

    # Common state patterns
    state: dict[str, Any] | None = Field(None, description="State section")
    status: str | None = Field(None, description="Status field")
    data: dict[str, Any] | None = Field(None, description="Data section")


class ModelYamlList(BaseModel):
    """Model for YAML files that are primarily lists."""

    model_config = ConfigDict(extra="allow")

    # For files that are root-level arrays
    root_list: list[Any] = Field(default_factory=list, description="Root level list")

    def __init__(self, data: Any = None, **kwargs: Any) -> None:
        """Handle case where YAML root is a list."""
        if isinstance(data, list):
            super().__init__(root_list=data, **kwargs)
        else:
            super().__init__(**kwargs)
