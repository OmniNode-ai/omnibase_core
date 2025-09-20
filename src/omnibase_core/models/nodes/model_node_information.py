"""
Node information model.
"""

import uuid
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from ...enums.enum_metadata_node_status import EnumMetadataNodeStatus
from ...enums.enum_registry_status import EnumRegistryStatus
from ..metadata.model_semver import ModelSemVer
from ..nodes.model_node_configuration import ModelNodeConfiguration


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
    node_version: ModelSemVer = Field(..., description="Node version")

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
