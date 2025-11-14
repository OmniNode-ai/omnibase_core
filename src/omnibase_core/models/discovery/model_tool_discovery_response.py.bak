from uuid import UUID

from pydantic import Field

from omnibase_core.constants.event_types import TOOL_DISCOVERY_REQUEST
from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Tool Discovery Response Event Model

Event published by the registry in response to TOOL_DISCOVERY_REQUEST events.
Contains discovered tools matching the request filters.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from omnibase_core.constants.event_types import TOOL_DISCOVERY_RESPONSE
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class ModelDiscoveredTool(BaseModel):
    """Information about a discovered tool"""

    # Node identification
    node_id: UUID = Field(default=..., description="Unique identifier for the node")
    node_name: str = Field(
        default=..., description="Name of the node (e.g. 'node_generator')"
    )
    version: ModelSemVer = Field(default=..., description="Version of the node")

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
    metadata: dict[str, Any] = Field(
        default_factory=dict,
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
