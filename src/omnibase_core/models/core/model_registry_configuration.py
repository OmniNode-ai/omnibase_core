"""
Model for registry configuration representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 RegistryFactory functionality for
strongly typed registry configuration.

"""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_registry_type import EnumRegistryType


class ModelRegistryConfiguration(BaseModel):
    """Model representing registry configuration for factory creation."""

    registry_type: EnumRegistryType = Field(
        default=...,
        description="Type of registry to create",
    )
    node_id: UUID = Field(default=..., description="Node identifier for the registry")
    node_dir: Path = Field(default=..., description="Node directory path")
    main_tool_class: str = Field(
        default=..., description="Main tool class name to instantiate"
    )
    registry_class: str = Field(
        default=..., description="Registry class name to create"
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="Required dependencies for registry",
    )
    tool_capabilities: list[str] = Field(
        default_factory=list,
        description="Tool capabilities to register",
    )
    configuration_overrides: dict[str, str] = Field(
        default_factory=dict,
        description="Configuration value overrides",
    )
