"""
Model for registry configuration representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 RegistryFactory functionality for
strongly typed registry configuration.

Author: ONEX Framework Team
"""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field


class EnumRegistryType(str, Enum):
    """Registry type classifications for ONEX node registry systems."""

    TOOL_REGISTRY = "tool_registry"
    SERVICE_REGISTRY = "service_registry"
    WORKFLOW_REGISTRY = "workflow_registry"
    PROTOCOL_REGISTRY = "protocol_registry"
    CONTRACT_REGISTRY = "contract_registry"
    METADATA_REGISTRY = "metadata_registry"


class ModelRegistryConfiguration(BaseModel):
    """Model representing registry configuration for factory creation."""

    registry_type: EnumRegistryType = Field(
        ...,
        description="Type of registry to create",
    )
    node_id: str = Field(..., description="Node identifier for the registry")
    node_dir: Path = Field(..., description="Node directory path")
    main_tool_class: str = Field(..., description="Main tool class name to instantiate")
    registry_class: str = Field(..., description="Registry class name to create")
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
