"""
Request Introspection Event Model

Event sent to request real-time introspection from all connected nodes.
Enables on-demand discovery of currently available nodes with their current status.
"""

from typing import List, Optional
from uuid import UUID, uuid4

from pydantic import Field

from omnibase_core.constants.event_types import CoreEventTypes
from omnibase_core.model.core.model_onex_event import ModelOnexEvent

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
        default=CoreEventTypes.REQUEST_REAL_TIME_INTROSPECTION,
        description="Event type identifier",
    )

    # Request control
    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Unique ID for matching responses to this request",
    )
    timeout_ms: int = Field(
        default=5000, description="Request timeout in milliseconds", ge=100, le=60000
    )

    # Request targeting
    filters: Optional[ModelIntrospectionFilters] = Field(
        None, description="Optional filters for targeting specific nodes"
    )

    # Request metadata
    requester_id: str = Field(
        ...,
        description="Identifier of the requesting service (e.g., 'mcp_server', 'cli')",
    )

    # Optional response control
    include_resource_usage: bool = Field(
        default=False,
        description="Whether to include current resource usage in responses",
    )
    include_performance_metrics: bool = Field(
        default=False, description="Whether to include performance metrics in responses"
    )
    max_responses: Optional[int] = Field(
        None, description="Maximum number of responses to collect", ge=1, le=1000
    )

    @classmethod
    def create_discovery_request(
        cls,
        requester_id: str,
        node_id: str = "discovery_client",
        filters: Optional[ModelIntrospectionFilters] = None,
        timeout_ms: int = 5000,
        include_resource_usage: bool = False,
        **kwargs,
    ) -> "ModelRequestIntrospectionEvent":
        """
        Factory method for creating discovery requests.

        Args:
            requester_id: Identifier of the requesting service
            node_id: Node ID of the requester
            filters: Optional filters for targeting specific nodes
            timeout_ms: Request timeout in milliseconds
            include_resource_usage: Whether to include resource usage
            **kwargs: Additional fields

        Returns:
            ModelRequestIntrospectionEvent instance
        """
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
        node_id: str = "mcp_server",
        protocols: List[str] = None,
        timeout_ms: int = 3000,
        **kwargs,
    ) -> "ModelRequestIntrospectionEvent":
        """
        Factory method for MCP server discovery requests.

        Args:
            node_id: MCP server node ID
            protocols: Required protocols (defaults to ['mcp'])
            timeout_ms: Request timeout
            **kwargs: Additional fields

        Returns:
            ModelRequestIntrospectionEvent for MCP discovery
        """
        filters = ModelIntrospectionFilters(
            protocols=protocols or ["mcp"],
            status=["ready", "busy"],  # Only active nodes
        )

        return cls(
            node_id=node_id,
            requester_id="mcp_server",
            filters=filters,
            timeout_ms=timeout_ms,
            include_resource_usage=True,
            **kwargs,
        )

    @classmethod
    def create_health_check_request(
        cls,
        requester_id: str = "health_monitor",
        node_id: str = "health_monitor",
        timeout_ms: int = 2000,
        **kwargs,
    ) -> "ModelRequestIntrospectionEvent":
        """
        Factory method for health monitoring requests.

        Args:
            requester_id: Health monitor identifier
            node_id: Health monitor node ID
            timeout_ms: Request timeout
            **kwargs: Additional fields

        Returns:
            ModelRequestIntrospectionEvent for health checking
        """
        return cls(
            node_id=node_id,
            requester_id=requester_id,
            timeout_ms=timeout_ms,
            include_resource_usage=True,
            include_performance_metrics=True,
            **kwargs,
        )
