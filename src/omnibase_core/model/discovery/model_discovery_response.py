"""
Discovery Response Model

Model for discovery client responses with proper typing and validation
following ONEX canonical patterns.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from omnibase_core.model.discovery.model_custom_metrics import \
    ModelCustomMetrics
from omnibase_core.model.discovery.model_tool_discovery_response import \
    ModelDiscoveredTool


class ModelDiscoveryResponse(BaseModel):
    """
    Response model for discovery client operations.

    Follows ONEX canonical patterns with strong typing and validation.
    All discovery operations return this standardized response format.
    """

    # Operation result
    operation: str = Field(..., description="Discovery operation that was performed")

    status: str = Field(
        ...,
        description="Operation status",
        json_schema_extra={"enum": ["success", "error", "timeout", "partial"]},
    )

    message: Optional[str] = Field(
        None, description="Status message or error description"
    )

    # Discovery results
    tools: List[ModelDiscoveredTool] = Field(
        default_factory=list, description="List of discovered tools"
    )

    # Result metadata
    total_count: int = Field(
        0, description="Total number of tools found before filtering"
    )

    filtered_count: int = Field(0, description="Number of tools after applying filters")

    # Performance metrics
    response_time_ms: Optional[float] = Field(
        None, description="Response time in milliseconds"
    )

    started_at: Optional[datetime] = Field(
        None, description="When the operation started"
    )

    completed_at: Optional[datetime] = Field(
        None, description="When the operation completed"
    )

    # Error handling
    timeout_occurred: bool = Field(False, description="Whether the operation timed out")

    partial_response: bool = Field(
        False, description="Whether this is a partial response"
    )

    errors: List[str] = Field(
        default_factory=list, description="List of errors encountered"
    )

    # Client information
    client_id: Optional[str] = Field(None, description="Client identifier")

    client_stats: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict, description="Client statistics and status"
    )

    # Request tracking
    correlation_id: Optional[str] = Field(
        None, description="Correlation ID from the request"
    )

    # Additional metadata
    metadata: Dict[str, Union[str, int, float, bool]] = Field(
        default_factory=dict, description="Additional response metadata"
    )

    @classmethod
    def create_success_response(
        cls,
        operation: str,
        tools: List[ModelDiscoveredTool],
        response_time_ms: Optional[float] = None,
        **kwargs,
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
        cls, operation: str, message: str, errors: Optional[List[str]] = None, **kwargs
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
            errors=errors or [],
            completed_at=datetime.now(),
            **kwargs,
        )

    @classmethod
    def create_timeout_response(
        cls,
        operation: str,
        timeout_seconds: float,
        partial_tools: Optional[List[ModelDiscoveredTool]] = None,
        **kwargs,
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
        tools = partial_tools or []

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
        client_stats: Dict[str, Union[str, int, float, bool]],
        **kwargs,
    ) -> "ModelDiscoveryResponse":
        """
        Factory method for client status responses.

        Args:
            client_id: Client identifier
            client_stats: Client statistics
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryResponse for status
        """
        return cls(
            operation="get_client_status",
            status="success",
            message=f"Client {client_id} status",
            client_id=client_id,
            client_stats=client_stats,
            completed_at=datetime.now(),
            **kwargs,
        )
