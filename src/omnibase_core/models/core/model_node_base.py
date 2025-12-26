"""
Model for ModelNodeBase representation in ONEX ModelNodeBase implementation.

This model supports the PATTERN-005 ModelNodeBase functionality for
universal node state management.

"""

from pathlib import Path
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.context import ModelNodeInitMetadata
from omnibase_core.models.core.model_container_reference import ModelContainerReference
from omnibase_core.models.core.model_contract_content import ModelContractContent
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelNodeBase(BaseModel):
    """Model representing ModelNodeBase state and configuration."""

    contract_path: Path = Field(default=..., description="Path to the contract file")
    node_id: UUID = Field(default=..., description="Unique node identifier")
    contract_content: ModelContractContent = Field(
        default=...,
        description="Loaded contract content",
    )
    container_reference: ModelContainerReference = Field(
        default=...,
        description="Container reference metadata",
    )
    node_name: str = Field(default=..., description="Node name from contract")
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Node version",
    )
    node_tier: int = Field(default=1, description="Node tier classification")
    node_classification: str = Field(
        default=..., description="Node classification type"
    )
    event_bus: object = Field(default=None, description="Event bus instance")
    initialization_metadata: ModelNodeInitMetadata | None = Field(
        default=None,
        description="Typed initialization metadata for the node",
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,  # For ProtocolRegistry and event_bus
        extra="ignore",  # Allow extra fields from YAML contracts
    )
