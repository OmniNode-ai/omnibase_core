import uuid
from typing import Any, Optional

from omnibase_core.models.core.model_semver import ModelSemVer

"""
Introspection Response Event Model

Event sent by nodes in response to REQUEST_REAL_TIME_INTROSPECTION events.
Provides real-time node status and capabilities for discovery coordination.
"""

from uuid import UUID

from pydantic import Field

from omnibase_core.constants.event_types import REAL_TIME_INTROSPECTION_RESPONSE
from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)

from .model_current_tool_availability import ModelCurrentToolAvailability
from .model_introspection_additional_info import ModelIntrospectionAdditionalInfo
from .model_performance_metrics import ModelPerformanceMetrics
from .model_resource_usage import ModelResourceUsage


class ModelIntrospectionResponseEvent(ModelOnexEvent):
    """
    Event sent by nodes in response to REQUEST_REAL_TIME_INTROSPECTION events.

    Provides real-time status and capabilities information for discovery
    coordination and health monitoring.
    """

    # Override event_type to be fixed for this event
    event_type: str = Field(
        default=REAL_TIME_INTROSPECTION_RESPONSE,
        description="Event type identifier",
    )

    # Response correlation
    correlation_id: UUID = Field(
        default=...,
        description="Correlation ID matching the original request",
    )

    # Node identification
    node_name: str = Field(default=..., description="Name of the responding node")
    version: ModelSemVer = Field(
        default=..., description="Version of the responding node"
    )

    # Current status
    current_status: EnumNodeCurrentStatus = Field(
        default=...,
        description="Current operational status of the node",
    )

    # Node capabilities (from introspection)
    capabilities: ModelNodeCapabilities = Field(
        default=...,
        description="Node capabilities including actions, protocols, and metadata",
    )

    # Real-time information
    tools: list[ModelCurrentToolAvailability] = Field(
        default_factory=list,
        description="Current availability status of tools within the node",
    )

    # Optional detailed information
    resource_usage: ModelResourceUsage | None = Field(
        default=None,
        description="Current resource usage (if requested)",
    )
    performance_metrics: ModelPerformanceMetrics | None = Field(
        default=None,
        description="Performance metrics (if requested)",
    )

    # Response metadata
    response_time_ms: float = Field(
        default=...,
        description="Time taken to process the introspection request in milliseconds",
        ge=0.0,
    )

    # Discovery metadata
    health_endpoint: str | None = Field(
        default=None,
        description="Health check endpoint if available",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery filtering",
    )

    # Additional context
    additional_info: ModelIntrospectionAdditionalInfo | None = Field(
        default=None,
        description="Additional node-specific information",
    )

    @classmethod
    def create_response(
        cls,
        correlation_id: UUID,
        node_id: str,
        node_name: str,
        version: ModelSemVer,
        current_status: EnumNodeCurrentStatus,
        capabilities: ModelNodeCapabilities,
        response_time_ms: float,
        tools: list[ModelCurrentToolAvailability] | None = None,
        resource_usage: ModelResourceUsage | None = None,
        performance_metrics: ModelPerformanceMetrics | None = None,
        **kwargs: Any,
    ) -> "ModelIntrospectionResponseEvent":
        """
        Factory method for creating introspection responses.

        Args:
            correlation_id: Correlation ID from the original request
            node_id: Responding node ID
            node_name: Responding node name
            version: Node version
            current_status: Current operational status
            capabilities: Node capabilities
            response_time_ms: Processing time
            tools: Tool availability information
            resource_usage: Current resource usage
            performance_metrics: Performance metrics
            **kwargs: Additional fields

        Returns:
            ModelIntrospectionResponseEvent instance
        """
        return cls(
            correlation_id=correlation_id,
            node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            node_name=node_name,
            version=version,
            current_status=current_status,
            capabilities=capabilities,
            response_time_ms=response_time_ms,
            tools=tools or [],
            resource_usage=resource_usage,
            performance_metrics=performance_metrics,
            **kwargs,
        )

    @classmethod
    def create_ready_response(
        cls,
        correlation_id: UUID,
        node_id: str,
        node_name: str,
        version: ModelSemVer,
        capabilities: ModelNodeCapabilities,
        response_time_ms: float,
        **kwargs: Any,
    ) -> "ModelIntrospectionResponseEvent":
        """
        Factory method for simple "ready" status responses.

        Args:
            correlation_id: Correlation ID from the original request
            node_id: Responding node ID
            node_name: Responding node name
            version: Node version
            capabilities: Node capabilities
            response_time_ms: Processing time
            **kwargs: Additional fields

        Returns:
            ModelIntrospectionResponseEvent with ready status
        """
        return cls(
            correlation_id=correlation_id,
            node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            node_name=node_name,
            version=version,
            current_status=EnumNodeCurrentStatus.READY,
            capabilities=capabilities,
            response_time_ms=response_time_ms,
            **kwargs,
        )

    @classmethod
    def create_error_response(
        cls,
        correlation_id: UUID,
        node_id: str,
        node_name: str,
        version: ModelSemVer,
        error_message: str,
        response_time_ms: float,
        **kwargs: Any,
    ) -> "ModelIntrospectionResponseEvent":
        """
        Factory method for error responses.

        Args:
            correlation_id: Correlation ID from the original request
            node_id: Responding node ID
            node_name: Responding node name
            version: Node version
            error_message: Error description
            response_time_ms: Processing time
            **kwargs: Additional fields

        Returns:
            ModelIntrospectionResponseEvent with error status
        """
        # Create minimal capabilities for error response
        capabilities = ModelNodeCapabilities(
            actions=[],
            protocols=[],
            metadata={"error": error_message},
        )

        return cls(
            correlation_id=correlation_id,
            node_id=UUID(node_id) if isinstance(node_id, str) else node_id,
            node_name=node_name,
            version=version,
            current_status=EnumNodeCurrentStatus.ERROR,
            capabilities=capabilities,
            response_time_ms=response_time_ms,
            additional_info=ModelIntrospectionAdditionalInfo(
                error_message=error_message,
            ),
            **kwargs,
        )
