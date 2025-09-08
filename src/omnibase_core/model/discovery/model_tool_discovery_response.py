"""
Tool Discovery Response Event Model

Event published by the registry in response to TOOL_DISCOVERY_REQUEST events.
Contains discovered tools matching the request filters.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.core.constants.event_types import CoreEventTypes
from omnibase_core.model.core.model_onex_event import ModelOnexEvent
from omnibase_core.model.core.model_semver import ModelSemVer


class ModelDiscoveredTool(BaseModel):
    """Information about a discovered tool"""

    # Node identification
    node_id: str = Field(..., description="Unique identifier for the node")
    node_name: str = Field(..., description="Name of the node (e.g. 'node_generator')")
    version: ModelSemVer = Field(..., description="Version of the node")

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
    service_id: str | None = Field(
        None,
        description="Service ID for Consul compatibility",
    )
    health_endpoint: str | None = Field(
        None,
        description="Health check endpoint if available",
    )


class ModelToolDiscoveryResponse(ModelOnexEvent):
    """
    Event published by registry in response to tool discovery requests.

    Contains a list of tools that match the request filters, along with
    metadata about the discovery operation.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=CoreEventTypes.TOOL_DISCOVERY_RESPONSE,
        description="Event type identifier",
    )

    # Response identification
    request_correlation_id: str | None = Field(
        None,
        description="Correlation ID from the original request",
    )
    requester_id: str = Field(
        ...,
        description="ID of the service that made the request",
    )

    # Discovery results
    tools: list[ModelDiscoveredTool] = Field(
        default_factory=list,
        description="List of discovered tools matching the request",
    )

    # Response metadata
    total_count: int = Field(
        0,
        description="Total number of tools found (may be > len(tools) if limited)",
    )
    filtered_count: int = Field(0, description="Number of tools after applying filters")
    response_time_ms: float | None = Field(
        None,
        description="Time taken to process the request in milliseconds",
    )

    # Status flags
    partial_response: bool = Field(
        False,
        description="True if some registries didn't respond in time",
    )
    timeout_occurred: bool = Field(False, description="True if the request timed out")
    registry_errors: list[str] = Field(
        default_factory=list,
        description="List of errors from registries during discovery",
    )

    @classmethod
    def create_success_response(
        cls,
        node_id: str,
        requester_id: str,
        tools: list[ModelDiscoveredTool],
        request_correlation_id: str | None = None,
        response_time_ms: float | None = None,
        **kwargs,
    ) -> "ModelToolDiscoveryResponse":
        """
        Factory method to create a successful discovery response.

        Args:
            node_id: Node ID of the registry
            requester_id: ID of the requesting service
            tools: List of discovered tools
            request_correlation_id: Correlation ID from request
            response_time_ms: Processing time
            **kwargs: Additional fields

        Returns:
            ModelToolDiscoveryResponse instance
        """
        # Convert string correlation_id to UUID if provided
        correlation_uuid = None
        if request_correlation_id:
            try:
                from uuid import UUID

                correlation_uuid = UUID(request_correlation_id)
            except ValueError:
                # If it's not a valid UUID string, leave correlation_id as None
                correlation_uuid = None

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            tools=tools,
            total_count=len(tools),
            filtered_count=len(tools),
            request_correlation_id=request_correlation_id,
            response_time_ms=response_time_ms,
            correlation_id=correlation_uuid,
            **kwargs,
        )

    @classmethod
    def create_timeout_response(
        cls,
        node_id: str,
        requester_id: str,
        partial_tools: list[ModelDiscoveredTool] | None = None,
        request_correlation_id: str | None = None,
        timeout_ms: int | None = None,
        **kwargs,
    ) -> "ModelToolDiscoveryResponse":
        """
        Factory method to create a timeout response.

        Args:
            node_id: Node ID of the registry
            requester_id: ID of the requesting service
            partial_tools: Any tools discovered before timeout
            request_correlation_id: Correlation ID from request
            timeout_ms: Timeout that occurred
            **kwargs: Additional fields

        Returns:
            ModelToolDiscoveryResponse for timeout
        """
        tools = partial_tools or []

        # Convert string correlation_id to UUID if provided
        correlation_uuid = None
        if request_correlation_id:
            try:
                from uuid import UUID

                correlation_uuid = UUID(request_correlation_id)
            except ValueError:
                # If it's not a valid UUID string, leave correlation_id as None
                correlation_uuid = None

        return cls(
            node_id=node_id,
            requester_id=requester_id,
            tools=tools,
            total_count=len(tools),
            filtered_count=len(tools),
            request_correlation_id=request_correlation_id,
            correlation_id=correlation_uuid,
            partial_response=True,
            timeout_occurred=True,
            response_time_ms=timeout_ms,
            **kwargs,
        )

    def get_tools_by_protocol(self, protocol: str) -> list[ModelDiscoveredTool]:
        """
        Filter tools by protocol.

        Args:
            protocol: Protocol to filter by (e.g. 'mcp')

        Returns:
            List of tools supporting the protocol
        """
        return [tool for tool in self.tools if protocol in tool.protocols]

    def get_tools_by_tag(self, tag: str) -> list[ModelDiscoveredTool]:
        """
        Filter tools by tag.

        Args:
            tag: Tag to filter by (e.g. 'generator')

        Returns:
            List of tools with the tag
        """
        return [tool for tool in self.tools if tag in tool.tags]
