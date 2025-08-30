#!/usr/bin/env python3
"""
Registry Event Models for Event-Driven Registry Communication.

Defines strongly-typed event models for registry request/response patterns
between infrastructure reducer and registry catalog aggregator.

ONEX Compliance:
- Strong typing with Pydantic models
- Proper correlation ID handling
- Comprehensive error handling
- Event-driven architecture patterns
"""

from datetime import datetime
from typing import Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ModelRegistryRequestEvent(BaseModel):
    """Registry request event for event-driven communication."""

    correlation_id: UUID = Field(
        default_factory=uuid4,
        description="Correlation ID for request-response matching",
    )
    operation: str = Field(..., description="Registry operation to perform")
    endpoint_path: str = Field(
        ..., description="HTTP endpoint path for the registry request"
    )
    http_method: str = Field(..., description="HTTP method (GET, POST, etc.)")
    params: Optional[Dict[str, Union[str, int, bool, float, List[str]]]] = Field(
        None, description="Optional parameters for the registry operation"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Event timestamp"
    )
    source_node_id: str = Field(..., description="Node ID of the requesting service")
    timeout_ms: int = Field(
        default=30000, description="Request timeout in milliseconds"
    )


class ModelRegistryResponseEvent(BaseModel):
    """Registry response event for event-driven communication."""

    correlation_id: UUID = Field(
        ..., description="Correlation ID matching the original request"
    )
    status: str = Field(..., description="Response status (success, error, timeout)")
    result: Optional[
        Dict[str, Union[str, int, bool, float, List[str], Dict[str, object]]]
    ] = Field(None, description="Registry operation result data")
    error_message: Optional[str] = Field(
        None, description="Error message if status is error"
    )
    error_code: Optional[str] = Field(
        None, description="Error code for programmatic handling"
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Response timestamp"
    )
    source_node_id: str = Field(..., description="Node ID of the responding service")
    processing_time_ms: Optional[int] = Field(
        None, description="Processing time in milliseconds"
    )


class ModelRegistryOperationMetrics(BaseModel):
    """Registry operation metrics for monitoring and debugging."""

    operation: str = Field(..., description="Registry operation name")
    endpoint_path: str = Field(..., description="HTTP endpoint path")
    success_count: int = Field(default=0, description="Number of successful operations")
    error_count: int = Field(default=0, description="Number of failed operations")
    timeout_count: int = Field(default=0, description="Number of timed out operations")
    average_processing_time_ms: float = Field(
        default=0.0, description="Average processing time"
    )
    last_operation_timestamp: Optional[datetime] = Field(
        None, description="Last operation timestamp"
    )


# Registry operation constants for type safety
class RegistryOperations:
    """Registry operation constants for type-safe event handling."""

    LIST_REGISTRY_TOOLS = "list_registry_tools"
    GET_AGGREGATED_CATALOG = "get_aggregated_catalog"
    GET_AGGREGATION_METRICS = "get_aggregation_metrics"
    TRIGGER_BOOTSTRAP_WORKFLOW = "trigger_bootstrap_workflow"
    TRIGGER_HELLO_COORDINATION = "trigger_hello_coordination"
    TRIGGER_CONSUL_SYNC = "trigger_consul_sync"

    # Event type constants
    REGISTRY_REQUEST_EVENT = "registry.request"
    REGISTRY_RESPONSE_EVENT = "registry.response"
    REGISTRY_ERROR_EVENT = "registry.error"

    @classmethod
    def get_all_operations(cls) -> List[str]:
        """Get all supported registry operations."""
        return [
            cls.LIST_REGISTRY_TOOLS,
            cls.GET_AGGREGATED_CATALOG,
            cls.GET_AGGREGATION_METRICS,
            cls.TRIGGER_BOOTSTRAP_WORKFLOW,
            cls.TRIGGER_HELLO_COORDINATION,
            cls.TRIGGER_CONSUL_SYNC,
        ]

    @classmethod
    def is_valid_operation(cls, operation: str) -> bool:
        """Check if an operation is valid."""
        return operation in cls.get_all_operations()


# Endpoint to operation mapping for type safety
ENDPOINT_OPERATION_MAPPING = {
    "/registry/tools": {"GET": RegistryOperations.LIST_REGISTRY_TOOLS},
    "/registry/catalog": {"GET": RegistryOperations.GET_AGGREGATED_CATALOG},
    "/registry/metrics": {"GET": RegistryOperations.GET_AGGREGATION_METRICS},
    "/registry/bootstrap": {"POST": RegistryOperations.TRIGGER_BOOTSTRAP_WORKFLOW},
    "/registry/hello-coordinate": {
        "POST": RegistryOperations.TRIGGER_HELLO_COORDINATION
    },
    "/registry/consul-sync": {"POST": RegistryOperations.TRIGGER_CONSUL_SYNC},
}


def get_operation_for_endpoint(endpoint_path: str, http_method: str) -> Optional[str]:
    """
    Get the registry operation for a given endpoint and HTTP method.

    Args:
        endpoint_path: HTTP endpoint path
        http_method: HTTP method

    Returns:
        Registry operation name or None if not found
    """
    endpoint_config = ENDPOINT_OPERATION_MAPPING.get(endpoint_path)
    if endpoint_config:
        return endpoint_config.get(http_method.upper())
    return None


def get_supported_endpoints() -> List[str]:
    """Get all supported registry endpoints."""
    return [
        f"{method} {endpoint}"
        for endpoint, methods in ENDPOINT_OPERATION_MAPPING.items()
        for method in methods.keys()
    ]
