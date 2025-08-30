"""
Tool Discovery Request Event Model

Event published by services to request discovery of available tools.
The registry responds with a TOOL_DISCOVERY_RESPONSE event.
"""

from pydantic import BaseModel, Field

from omnibase_core.constants.event_types import CoreEventTypes
from omnibase_core.model.core.model_onex_event import ModelOnexEvent


class ModelDiscoveryFilters(BaseModel):
    """Filters for tool discovery requests"""

    tags: list[str] | None = Field(
        None,
        description="Filter by node tags (e.g. ['generator', 'validated'])",
    )
    protocols: list[str] | None = Field(
        None,
        description="Filter by supported protocols (e.g. ['mcp', 'graphql'])",
    )
    actions: list[str] | None = Field(
        None,
        description="Filter by supported actions (e.g. ['health_check'])",
    )
    node_names: list[str] | None = Field(
        None,
        description="Filter by specific node names (e.g. ['node_generator'])",
    )
    exclude_nodes: list[str] | None = Field(
        None,
        description="Exclude specific node IDs from results",
    )
    min_trust_score: float | None = Field(
        None,
        description="Minimum trust score required (0.0-1.0)",
    )
    datacenter: str | None = Field(
        None,
        description="Filter by datacenter (future Consul support)",
    )
    health_status: str | None = Field(
        None,
        description="Filter by health status ('healthy', 'warning', 'critical')",
    )


class ModelToolDiscoveryRequest(ModelOnexEvent):
    """
    Event published to request discovery of available tools.

    Services like MCP server publish this event to discover what tools
    are available. The registry responds with a TOOL_DISCOVERY_RESPONSE
    event containing matching tools.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=CoreEventTypes.TOOL_DISCOVERY_REQUEST,
        description="Event type identifier",
    )

    # Request identification
    requester_id: str = Field(
        ...,
        description="ID of the service requesting discovery (e.g. 'mcp_server')",
    )

    # Query parameters
    filters: ModelDiscoveryFilters | None = Field(
        None,
        description="Filters to apply to the discovery request",
    )

    # Response control
    max_results: int | None = Field(
        None,
        description="Maximum number of results to return",
    )
    timeout_ms: int | None = Field(
        5000,
        description="Timeout in milliseconds for the request",
    )
    include_metadata: bool = Field(
        True,
        description="Whether to include full metadata in response",
    )

    @classmethod
    def create_simple_request(
        cls,
        node_id: str,
        requester_id: str,
        tags: list[str] | None = None,
        protocols: list[str] | None = None,
        correlation_id=None,
        **kwargs,
    ) -> "ModelToolDiscoveryRequest":
        """
        Factory method to create a simple discovery request.

        Args:
            node_id: Node ID making the request
            requester_id: Service ID requesting discovery
            tags: Filter by tags
            protocols: Filter by protocols
            correlation_id: Correlation ID for response matching
            **kwargs: Additional fields

        Returns:
            ModelToolDiscoveryRequest instance
        """
        filters = None
        if tags or protocols:
            filters = ModelDiscoveryFilters(tags=tags, protocols=protocols)

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            filters=filters,
            correlation_id=correlation_id,
            **kwargs,
        )

    @classmethod
    def create_mcp_request(
        cls,
        requester_id: str = "mcp_server",
        node_id: str = "mcp_server",
        correlation_id=None,
        **kwargs,
    ) -> "ModelToolDiscoveryRequest":
        """
        Factory method for MCP server discovery requests.

        Args:
            requester_id: MCP server identifier
            node_id: Node ID for the MCP server
            correlation_id: Correlation ID for response
            **kwargs: Additional fields

        Returns:
            ModelToolDiscoveryRequest for MCP tools
        """
        filters = ModelDiscoveryFilters(
            protocols=["mcp", "event_bus"],
            health_status="healthy",
        )

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            filters=filters,
            correlation_id=correlation_id,
            **kwargs,
        )
