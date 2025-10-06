from uuid import UUID

from pydantic import Field

from omnibase_core.constants.constants_contract_fields import TOOL_DISCOVERY_REQUEST
from omnibase_core.models.core.model_discovery_filters import ModelDiscoveryFilters
from omnibase_core.models.core.model_onex_event import ModelOnexEvent


class ModelToolDiscoveryRequest(ModelOnexEvent):
    """
    Event published to request discovery of available tools.

    Services like MCP server publish this event to discover what tools
    are available. The registry responds with a TOOL_DISCOVERY_RESPONSE
    event containing matching tools.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=TOOL_DISCOVERY_REQUEST,
        description="Event type identifier",
    )

    # Request identification
    requester_id: UUID = Field(
        default=...,
        description="ID of the service requesting discovery (e.g. 'mcp_server')",
    )

    # Query parameters
    filters: ModelDiscoveryFilters | None = Field(
        default=None,
        description="Filters to apply to the discovery request",
    )

    # Response control
    max_results: int | None = Field(
        default=None,
        description="Maximum number of results to return",
    )
    timeout_ms: int | None = Field(
        default=5000,
        description="Timeout in milliseconds for the request",
    )
    include_metadata: bool = Field(
        default=True,
        description="Whether to include full metadata in response",
    )

    @classmethod
    def create_simple_request(
        cls,
        node_id: UUID,
        requester_id: UUID,
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
        requester_id: str | UUID = "mcp_server",
        node_id: str | UUID = "mcp_server",
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
