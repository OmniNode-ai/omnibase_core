"""
Request Introspection Event Model

Event sent to request real-time introspection from all connected nodes.
Enables on-demand discovery of currently available nodes with their current status.
"""

from typing import Any
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.constants import KAFKA_REQUEST_TIMEOUT_MS
from omnibase_core.constants.constants_event_types import (
    REQUEST_REAL_TIME_INTROSPECTION,
)
from omnibase_core.models.core.model_onex_event import ModelOnexEvent

from .model_introspection_filters import ModelIntrospectionFilters


class ModelRequestIntrospectionEvent(ModelOnexEvent):
    """
    Event sent to request real-time introspection from connected nodes.

    This event is broadcast to all connected nodes to gather their current
    status and capabilities. Nodes respond with REAL_TIME_INTROSPECTION_RESPONSE events
    if they match the filters.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=REQUEST_REAL_TIME_INTROSPECTION,
        description="Event type identifier",
    )

    # Request control
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for matching responses to this request",
    )
    timeout_ms: int = Field(
        default=KAFKA_REQUEST_TIMEOUT_MS,
        description="Request timeout in milliseconds",
        ge=100,
        le=60000,
    )

    # Request targeting
    filters: ModelIntrospectionFilters | None = Field(
        default=None,
        description="Optional filters for targeting specific nodes",
    )

    # Request metadata
    requester_id: UUID = Field(
        default=...,
        description="Identifier of the requesting service (e.g., 'mcp_server', 'cli')",
    )

    # Optional response control
    include_resource_usage: bool = Field(
        default=False,
        description="Whether to include current resource usage in responses",
    )
    include_performance_metrics: bool = Field(
        default=False,
        description="Whether to include performance metrics in responses",
    )
    max_responses: int | None = Field(
        default=None,
        description="Maximum number of responses to collect",
        ge=1,
        le=1000,
    )

    @classmethod
    def create_discovery_request(
        cls,
        requester_id: UUID,
        node_id: UUID | None = None,
        filters: ModelIntrospectionFilters | None = None,
        timeout_ms: int = 5000,
        include_resource_usage: bool = False,
        **kwargs: Any,
    ) -> "ModelRequestIntrospectionEvent":
        """
        Factory method for creating discovery requests.

        Args:
            requester_id: Identifier of the requesting service
            node_id: Node ID of the requester (defaults to new UUID)
            filters: Optional filters for targeting specific nodes
            timeout_ms: Request timeout in milliseconds
            include_resource_usage: Whether to include resource usage
            **kwargs: Additional fields

        Returns:
            ModelRequestIntrospectionEvent instance
        """
        if node_id is None:
            node_id = uuid4()

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            filters=filters,
            timeout_ms=timeout_ms,
            include_resource_usage=include_resource_usage,
            **kwargs,
        )

    @classmethod
    def create_mcp_discovery_request(
        cls,
        node_id: UUID | None = None,
        requester_id: UUID | None = None,
        protocols: list[str] | None = None,
        timeout_ms: int = 3000,
        **kwargs: Any,
    ) -> "ModelRequestIntrospectionEvent":
        """
        Factory method for MCP server discovery requests.

        Args:
            node_id: MCP server node ID (defaults to new UUID)
            requester_id: Requester identifier (defaults to new UUID)
            protocols: Required protocols (defaults to ['mcp'])
            timeout_ms: Request timeout
            **kwargs: Additional fields

        Returns:
            ModelRequestIntrospectionEvent for MCP discovery
        """
        if node_id is None:
            node_id = uuid4()
        if requester_id is None:
            requester_id = uuid4()

        filters = ModelIntrospectionFilters(
            protocols=protocols or ["mcp"],
            status=["ready", "busy"],  # Only active nodes
        )

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            filters=filters,
            timeout_ms=timeout_ms,
            include_resource_usage=True,
            **kwargs,
        )

    @classmethod
    def create_health_check_request(
        cls,
        requester_id: UUID | None = None,
        node_id: UUID | None = None,
        timeout_ms: int = 2000,
        **kwargs: Any,
    ) -> "ModelRequestIntrospectionEvent":
        """
        Factory method for health monitoring requests.

        Args:
            requester_id: Health monitor identifier (defaults to new UUID)
            node_id: Health monitor node ID (defaults to new UUID)
            timeout_ms: Request timeout
            **kwargs: Additional fields

        Returns:
            ModelRequestIntrospectionEvent for health checking
        """
        if requester_id is None:
            requester_id = uuid4()
        if node_id is None:
            node_id = uuid4()

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            timeout_ms=timeout_ms,
            include_resource_usage=True,
            include_performance_metrics=True,
            **kwargs,
        )
