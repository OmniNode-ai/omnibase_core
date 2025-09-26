"""
Node core information summary model.

Clean, strongly-typed replacement for node core info dict return types.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.enums.enum_node_health_status import EnumNodeHealthStatus
from omnibase_core.enums.enum_status import EnumStatus
from omnibase_core.models.metadata.model_semver import ModelSemVer


class ModelNodeCoreInfoSummary(BaseModel):
    """Core node information summary with specific types."""

    node_id: UUID = Field(description="Node identifier")
    node_name: str = Field(description="Node name")
    node_type: EnumMetadataNodeType = Field(description="Node type value")
    node_version: ModelSemVer = Field(description="Node version")
    status: EnumStatus = Field(description="Node status value")
    health: EnumNodeHealthStatus = Field(description="Node health status")
    is_active: bool = Field(description="Whether node is active")
    is_healthy: bool = Field(description="Whether node is healthy")
    has_description: bool = Field(description="Whether node has description")
    has_author: bool = Field(description="Whether node has author")

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }


# Export the model
__all__ = ["ModelNodeCoreInfoSummary"]
