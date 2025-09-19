"""
Node information model.
"""

import uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_registry_status import EnumRegistryStatus
from omnibase_core.models.core.model_node_configuration import ModelNodeConfiguration


class ModelNodeInformation(BaseModel):
    """
    Node information with typed fields.
    Replaces Dict[str, Any] for node_information fields.
    """

    # Node identification
    node_id: UUID = Field(
        default_factory=uuid.uuid4,
        description="Node identifier",
    )
    node_name: str = Field(..., description="Node name")
    node_type: str = Field(..., description="Node type")
    node_version: str = Field(..., description="Node version")

    # Node metadata
    description: str | None = Field(None, description="Node description")
    author: str | None = Field(None, description="Node author")
    created_at: datetime | None = Field(None, description="Creation timestamp")
    updated_at: datetime | None = Field(None, description="Last update timestamp")

    # Node capabilities
    capabilities: list[str] = Field(
        default_factory=list,
        description="Node capabilities",
    )
    supported_operations: list[str] = Field(
        default_factory=list,
        description="Supported operations",
    )

    # Node configuration
    configuration: ModelNodeConfiguration = Field(
        default_factory=lambda: ModelNodeConfiguration(),
        description="Node configuration",
    )

    # Node status
    status: EnumMetadataNodeStatus = Field(
        default=EnumMetadataNodeStatus.ACTIVE,
        description="Node status",
    )
    health: EnumRegistryStatus = Field(
        default=EnumRegistryStatus.HEALTHY,
        description="Node health",
    )

    # Performance metrics
    performance_metrics: dict[str, float] | None = Field(
        None,
        description="Performance metrics",
    )

    # Dependencies
    dependencies: list[str] = Field(
        default_factory=list,
        description="Node dependencies",
    )

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> Optional["ModelNodeInformation"]:
        """Create from dictionary for easy migration."""
        if data is None:
            return None

        # Create a copy to avoid mutating original data
        normalized_data = data.copy()

        # Apply field mappings for current standards
        normalized_data.setdefault("node_id", normalized_data.get("id", "unknown"))
        normalized_data.setdefault("node_name", normalized_data.get("name", "unknown"))
        normalized_data.setdefault("node_type", normalized_data.get("type", "generic"))
        normalized_data.setdefault(
            "node_version",
            normalized_data.get("version", "1.0.0"),
        )

        # Use Pydantic validation instead of manual validation
        return cls.model_validate(normalized_data)
