from typing import Any
from uuid import UUID

from pydantic import Field

from omnibase_core.constants.constants_event_types import TOOL_DISCOVERY_RESPONSE
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.discovery.model_tool_discovery_response import (
    ModelDiscoveredTool,
)


class ModelToolDiscoveryResponse(ModelOnexEvent):
    """
    Event published by registry in response to tool discovery requests.

    Contains a list[Any]of tools that match the request filters, along with
    metadata about the discovery operation.
    """

    event_type: str = Field(
        default=TOOL_DISCOVERY_RESPONSE, description="Event type identifier"
    )
    request_correlation_id: UUID | None = Field(
        default=None, description="Correlation ID from the original request"
    )
    requester_id: UUID = Field(
        default=..., description="ID of the service that made the request"
    )
    tools: list[ModelDiscoveredTool] = Field(
        default_factory=list,
        description="List of discovered tools matching the request",
    )
    total_count: int = Field(
        default=0,
        description="Total number of tools found (may be > len(tools) if limited)",
    )
    filtered_count: int = Field(
        default=0, description="Number of tools after applying filters"
    )
    response_time_ms: float | None = Field(
        default=None, description="Time taken to process the request in milliseconds"
    )
    partial_response: bool = Field(
        default=False, description="True if some registries didn't respond in time"
    )
    timeout_occurred: bool = Field(
        default=False, description="True if the request timed out"
    )
    registry_errors: list[str] = Field(
        default_factory=list,
        description="List of errors from registries during discovery",
    )

    @classmethod
    def create_success_response(
        cls,
        node_id: UUID,
        requester_id: UUID,
        tools: list[ModelDiscoveredTool],
        request_correlation_id: UUID | None = None,
        response_time_ms: float | None = None,
        **kwargs: Any,
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
        correlation_uuid = request_correlation_id
        request_corr_uuid = request_correlation_id
        return cls(
            node_id=node_id,
            requester_id=requester_id,
            tools=tools,
            total_count=len(tools),
            filtered_count=len(tools),
            request_correlation_id=request_corr_uuid,
            response_time_ms=response_time_ms,
            correlation_id=correlation_uuid,
            **kwargs,
        )

    @classmethod
    def create_timeout_response(
        cls,
        node_id: UUID,
        requester_id: UUID,
        partial_tools: list[ModelDiscoveredTool] | None = None,
        request_correlation_id: UUID | None = None,
        timeout_ms: int | None = None,
        **kwargs: Any,
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
        tools = partial_tools if partial_tools is not None else []
        correlation_uuid = request_correlation_id
        request_corr_uuid = request_correlation_id
        return cls(
            node_id=node_id,
            requester_id=requester_id,
            tools=tools,
            total_count=len(tools),
            filtered_count=len(tools),
            request_correlation_id=request_corr_uuid,
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
