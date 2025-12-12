"""
Tool Discovery Response Event Model

Event published by the registry in response to TOOL_DISCOVERY_REQUEST events.
Contains discovered tools matching the request filters.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.common.model_typed_metadata import ModelToolMetadataFields
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelDiscoveredTool(BaseModel):
    """Information about a discovered tool"""

    # Node identification
    node_id: UUID = Field(default=..., description="Unique identifier for the node")
    node_name: str = Field(
        default=..., description="Name of the node (e.g. 'node_generator')"
    )
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Version of the node",
    )

    # Tool capabilities
    actions: list[str] = Field(
        default_factory=list,
        description="Actions supported by this tool",
    )
    protocols: list[str] = Field(
        default_factory=list,
        description="Protocols supported (mcp, graphql, event_bus)",
    )

    # Discovery metadata
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")
    metadata: ModelToolMetadataFields = Field(
        default_factory=ModelToolMetadataFields,
        description="Additional tool metadata",
    )

    # Health and status
    health_status: str = Field(
        default="unknown",
        description="Health status (healthy, warning, critical, unknown)",
    )
    last_seen: datetime = Field(
        default_factory=datetime.now,
        description="When this tool was last seen",
    )

    # Service discovery
    service_id: UUID | None = Field(
        default=None,
        description="Service ID for Consul compatibility",
    )
    health_endpoint: str | None = Field(
        default=None,
        description="Health check endpoint if available",
    )
