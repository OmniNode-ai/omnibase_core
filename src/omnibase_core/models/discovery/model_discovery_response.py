"""
Discovery Response Model

Model for discovery client responses with proper typing and validation
following ONEX canonical patterns.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_tool_discovery_response import (
    ModelDiscoveredTool,
)
from omnibase_core.types.type_json import PrimitiveValue


class ModelDiscoveryResponse(BaseModel):
    """
    Response model for discovery client operations.

    Follows ONEX canonical patterns with strong typing and validation.
    All discovery operations return this standardized response format.
    """

    # Operation result
    operation: str = Field(
        default=..., description="Discovery operation that was performed"
    )

    status: str = Field(
        default=...,
        description="Operation status",
        json_schema_extra={"enum": ["success", "error", "timeout", "partial"]},
    )

    message: str | None = Field(
        default=None,
        description="Status message or error description",
    )

    # Discovery results
    tools: list[ModelDiscoveredTool] = Field(
        default_factory=list,
        description="List of discovered tools",
    )

    # Result metadata
    total_count: int = Field(
        default=0,
        description="Total number of tools found before filtering",
    )

    filtered_count: int = Field(
        default=0, description="Number of tools after applying filters"
    )

    # Performance metrics
    response_time_ms: float | None = Field(
        default=None,
        description="Response time in milliseconds",
    )

    started_at: datetime | None = Field(
        default=None,
        description="When the operation started",
    )

    completed_at: datetime | None = Field(
        default=None,
        description="When the operation completed",
    )

    # Error handling
    timeout_occurred: bool = Field(
        default=False, description="Whether the operation timed out"
    )

    partial_response: bool = Field(
        default=False,
        description="Whether this is a partial response",
    )

    errors: list[str] = Field(
        default_factory=list,
        description="List of errors encountered",
    )

    # Client information
    client_id: UUID | None = Field(default=None, description="Client identifier")

    client_stats: dict[str, PrimitiveValue] = Field(
        default_factory=dict,
        description="Client statistics and status",
    )

    # Request tracking
    correlation_id: UUID | None = Field(
        default=None,
        description="Correlation ID from the request",
    )

    # Additional metadata
    metadata: dict[str, PrimitiveValue] = Field(
        default_factory=dict,
        description="Additional response metadata",
    )

    @classmethod
    def create_success_response(
        cls,
        operation: str,
        tools: list[ModelDiscoveredTool],
        response_time_ms: float | None = None,
        **kwargs: Any,
    ) -> "ModelDiscoveryResponse":
        """
        Factory method for successful discovery responses.

        Args:
            operation: Operation that was performed
            tools: Discovered tools
            response_time_ms: Response time
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryResponse for success
        """
        return cls(
            operation=operation,
            status="success",
            tools=tools,
            total_count=len(tools),
            filtered_count=len(tools),
            response_time_ms=response_time_ms,
            completed_at=datetime.now(),
            **kwargs,
        )

    @classmethod
    def create_error_response(
        cls,
        operation: str,
        message: str,
        errors: list[str] | None = None,
        **kwargs: Any,
    ) -> "ModelDiscoveryResponse":
        """
        Factory method for error discovery responses.

        Args:
            operation: Operation that was attempted
            message: Error message
            errors: List of specific errors
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryResponse for error
        """
        return cls(
            operation=operation,
            status="error",
            message=message,
            errors=errors if errors is not None else [],
            completed_at=datetime.now(),
            **kwargs,
        )

    @classmethod
    def create_timeout_response(
        cls,
        operation: str,
        timeout_seconds: float,
        partial_tools: list[ModelDiscoveredTool] | None = None,
        **kwargs: Any,
    ) -> "ModelDiscoveryResponse":
        """
        Factory method for timeout discovery responses.

        Args:
            operation: Operation that timed out
            timeout_seconds: Timeout duration
            partial_tools: Any tools discovered before timeout
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryResponse for timeout
        """
        tools = partial_tools if partial_tools is not None else []

        return cls(
            operation=operation,
            status="timeout",
            message=f"Operation timed out after {timeout_seconds}s",
            tools=tools,
            total_count=len(tools),
            filtered_count=len(tools),
            timeout_occurred=True,
            partial_response=len(tools) > 0,
            response_time_ms=timeout_seconds * 1000,
            completed_at=datetime.now(),
            **kwargs,
        )

    @classmethod
    def create_status_response(
        cls,
        client_id: str,
        client_stats: dict[str, PrimitiveValue],
        **kwargs: Any,
    ) -> "ModelDiscoveryResponse":
        """
        Factory method for client status responses.

        Args:
            client_id: Client identifier (string representation of UUID)
            client_stats: Client statistics
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryResponse for status
        """
        # Convert string client_id to UUID
        client_uuid = None
        try:
            client_uuid = UUID(client_id)
        except ValueError:
            # If conversion fails, leave as None
            client_uuid = None

        return cls(
            operation="get_client_status",
            status="success",
            message=f"Client {client_id} status",
            client_id=client_uuid,
            client_stats=client_stats,
            completed_at=datetime.now(),
            **kwargs,
        )
