from typing import Any, Dict

from pydantic import Field

from omnibase_core.models.core.model_semver import ModelSemVer
from uuid import UUID

"""
Model for ModelNodeBase representation in ONEX ModelNodeBase implementation.

This model supports the PATTERN-005 ModelNodeBase functionality for
universal node state management.

Author: ONEX Framework Team
"""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.core.model_registry_reference import ModelRegistryReference


class ModelNodeBase(BaseModel):
    """Model representing ModelNodeBase state and configuration."""

    contract_path: Path = Field(default=..., description="Path to the contract file")
    node_id: UUID = Field(default=..., description="Unique node identifier")
    contract_content: ModelContractContent = Field(
        default=...,
        description="Loaded contract content",
    )
    registry_reference: ModelRegistryReference = Field(
        default=...,
        description="Registry reference metadata",
    )
    node_name: str = Field(default=..., description="Node name from contract")
    version: ModelSemVer = Field(default=..., description="Node version")
    node_tier: int = Field(default=1, description="Node tier classification")
    node_classification: str = Field(
        default=..., description="Node classification type"
    )
    event_bus: object = Field(default=None, description="Event bus instance")
    initialization_metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Initialization metadata",
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # For ProtocolRegistry and event_bus
        extra="ignore",  # Allow extra fields from YAML contracts
    )
