import json

from pydantic import Field

from omnibase_core.models.core.model_discovery_filters import ModelDiscoveryFilters

"""
Discovery Request Model

Model for discovery client requests with proper typing and validation
following ONEX canonical patterns.
"""

from typing import Any

from pydantic import BaseModel, Field

from omnibase_core.models.discovery.model_tool_discovery_request import (
    ModelDiscoveryFilters,
)


class ModelDiscoveryRequest(BaseModel):
    """
    Request model for discovery client operations.

    Follows ONEX canonical patterns with strong typing and validation.
    All discovery operations use this standardized request format.
    """

    # Operation identification
    operation: str = Field(
        default=...,
        description="Discovery operation type",
        json_schema_extra={
            "enum": ["discover_tools", "get_client_status", "close_client"],
        },
    )

    # Discovery parameters
    filters: ModelDiscoveryFilters | None = Field(
        default=None,
        description="Discovery filters for tool matching",
    )

    # Request control
    timeout_seconds: float | None = Field(
        default=5.0,
        description="Request timeout in seconds",
        ge=0.1,
        le=300.0,
    )

    max_results: int | None = Field(
        default=None,
        description="Maximum number of results to return",
        ge=1,
        le=1000,
    )

    include_metadata: bool = Field(
        default=True,
        description="Whether to include full metadata in response",
    )

    # Retry configuration
    retry_count: int = Field(
        default=0, description="Number of retries on timeout", ge=0, le=5
    )

    retry_delay: float = Field(
        default=1.0,
        description="Initial delay between retries in seconds",
        ge=0.1,
        le=60.0,
    )

    # Client identification
    client_id: str | None = Field(
        default=None, description="Client identifier for tracking"
    )

    # Request tracking
    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for request tracking",
    )

    # Additional metadata
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional request metadata",
    )

    @classmethod
    def create_discover_tools_request(
        cls,
        filters: ModelDiscoveryFilters | None = None,
        timeout_seconds: float = 5.0,
        max_results: int | None = None,
        **kwargs,
    ) -> "ModelDiscoveryRequest":
        """
        Factory method for tool discovery requests.

        Args:
            filters: Discovery filters
            timeout_seconds: Request timeout
            max_results: Maximum results
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryRequest for tool discovery
        """
        return cls(
            operation="discover_tools",
            filters=filters,
            timeout_seconds=timeout_seconds,
            max_results=max_results,
            **kwargs,
        )

    @classmethod
    def create_status_request(
        cls,
        client_id: str | None = None,
        **kwargs,
    ) -> "ModelDiscoveryRequest":
        """
        Factory method for client status requests.

        Args:
            client_id: Client identifier
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryRequest for status query
        """
        return cls(operation="get_client_status", client_id=client_id, **kwargs)

    @classmethod
    def create_close_request(
        cls,
        client_id: str | None = None,
        **kwargs,
    ) -> "ModelDiscoveryRequest":
        """
        Factory method for client close requests.

        Args:
            client_id: Client identifier
            **kwargs: Additional fields

        Returns:
            ModelDiscoveryRequest for client closure
        """
        return cls(operation="close_client", client_id=client_id, **kwargs)
