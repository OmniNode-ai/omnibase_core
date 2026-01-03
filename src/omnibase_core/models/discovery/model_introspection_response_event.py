from typing import Any

from omnibase_core.models.primitives.model_semver import (
    ModelSemVer,
    default_model_version,
)

"\nIntrospection Response Event Model\n\nEvent sent by nodes in response to REQUEST_REAL_TIME_INTROSPECTION events.\nProvides real-time node status and capabilities for discovery coordination.\n"
from uuid import UUID

from pydantic import Field, field_validator

from omnibase_core.constants.constants_event_types import (
    REAL_TIME_INTROSPECTION_RESPONSE,
)
from omnibase_core.enums.enum_node_current_status import EnumNodeCurrentStatus
from omnibase_core.models.core.model_onex_event import ModelOnexEvent
from omnibase_core.models.discovery.model_node_introspection_event import (
    ModelNodeCapabilities,
)
from omnibase_core.utils.util_uuid_utilities import uuid_from_string

from .model_current_tool_availability import ModelCurrentToolAvailability
from .model_discovery_performance_metrics import ModelPerformanceMetrics
from .model_introspection_additional_info import ModelIntrospectionAdditionalInfo
from .model_resource_usage import ModelResourceUsage


class ModelIntrospectionResponseEvent(ModelOnexEvent):
    """
    Event sent by nodes in response to REQUEST_REAL_TIME_INTROSPECTION events.

    Provides real-time status and capabilities information for discovery
    coordination and health monitoring.
    """

    event_type: str = Field(
        default=REAL_TIME_INTROSPECTION_RESPONSE, description="Event type identifier"
    )
    correlation_id: UUID = Field(
        default=..., description="Correlation ID matching the original request"
    )
    node_name: str = Field(default=..., description="Name of the responding node")
    version: ModelSemVer = Field(
        default_factory=default_model_version,
        description="Version of the responding node",
    )
    current_status: EnumNodeCurrentStatus = Field(
        default=..., description="Current operational status of the node"
    )
    capabilities: ModelNodeCapabilities = Field(
        default=...,
        description="Node capabilities including actions, protocols, and metadata",
    )
    tools: list[ModelCurrentToolAvailability] = Field(
        default_factory=list,
        description="Current availability status of tools within the node",
    )
    resource_usage: ModelResourceUsage | None = Field(
        default=None, description="Current resource usage (if requested)"
    )
    performance_metrics: ModelPerformanceMetrics | None = Field(
        default=None, description="Performance metrics (if requested)"
    )
    response_time_ms: float = Field(
        default=...,
        description="Time taken to process the introspection request in milliseconds",
        ge=0.0,
    )
    health_endpoint: str | None = Field(
        default=None, description="Health check endpoint if available"
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorization and discovery filtering",
    )
    additional_info: ModelIntrospectionAdditionalInfo | None = Field(
        default=None, description="Additional node-specific information"
    )

    @field_validator("node_id", mode="before")
    @classmethod
    def convert_node_id_to_uuid(cls, v: Any) -> UUID:
        """Convert string node_id to UUID if needed."""
        from typing import cast

        if isinstance(v, str):
            return uuid_from_string(v, namespace="node")
        return cast("UUID", v)

    @classmethod
    def create_response(
        cls,
        correlation_id: UUID,
        node_id: UUID | str,
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
        # Convert node_id to UUID if it's a string
        node_uuid = (
            uuid_from_string(node_id, namespace="node")
            if isinstance(node_id, str)
            else node_id
        )

        return cls(
            correlation_id=correlation_id,
            node_id=node_uuid,
            node_name=node_name,
            version=version,
            current_status=current_status,
            capabilities=capabilities,
            response_time_ms=response_time_ms,
            tools=tools if tools is not None else [],
            resource_usage=resource_usage,
            performance_metrics=performance_metrics,
            **kwargs,
        )

    @classmethod
    def create_ready_response(
        cls,
        correlation_id: UUID,
        node_id: UUID | str,
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
        # Convert node_id to UUID if it's a string
        node_uuid = (
            uuid_from_string(node_id, namespace="node")
            if isinstance(node_id, str)
            else node_id
        )

        return cls(
            correlation_id=correlation_id,
            node_id=node_uuid,
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
        node_id: UUID | str,
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
        # Convert node_id to UUID if it's a string
        node_uuid = (
            uuid_from_string(node_id, namespace="node")
            if isinstance(node_id, str)
            else node_id
        )

        capabilities = ModelNodeCapabilities(
            actions=[],
            protocols=[],
            # Error message is stored in additional_info.error_message, not metadata
        )
        return cls(
            correlation_id=correlation_id,
            node_id=node_uuid,
            node_name=node_name,
            version=version,
            current_status=EnumNodeCurrentStatus.ERROR,
            capabilities=capabilities,
            response_time_ms=response_time_ms,
            additional_info=ModelIntrospectionAdditionalInfo(
                error_message=error_message
            ),
            **kwargs,
        )
