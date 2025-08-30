"""
Model for registry configuration representation in ONEX NodeBase implementation.

This model supports the PATTERN-005 RegistryFactory functionality for
strongly typed registry configuration.

Author: ONEX Framework Team
"""

from pathlib import Path
from typing import Dict, List

from pydantic import BaseModel, Field

from omnibase_core.core.enums.enum_registry_type import EnumRegistryType


class ModelRegistryConfiguration(BaseModel):
    """Model representing registry configuration for factory creation."""

    registry_type: EnumRegistryType = Field(
        ..., description="Type of registry to create"
    )
    node_id: str = Field(..., description="Node identifier for the registry")
    node_dir: Path = Field(..., description="Node directory path")
    main_tool_class: str = Field(..., description="Main tool class name to instantiate")
    registry_class: str = Field(..., description="Registry class name to create")
    dependencies: List[str] = Field(
        default_factory=list, description="Required dependencies for registry"
    )
    tool_capabilities: List[str] = Field(
        default_factory=list, description="Tool capabilities to register"
    )
    configuration_overrides: Dict[str, str] = Field(
        default_factory=dict, description="Configuration value overrides"
    )
