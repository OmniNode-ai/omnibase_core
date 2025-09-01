"""
External Dependencies Subcontract Models for ONEX EFFECT Nodes.

Provides Pydantic models for external service integration patterns, API calls,
circuit breaker patterns, and fallback strategies for EFFECT nodes only.

Generated from external_dependencies subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

# Import existing enums instead of duplicating
from omnibase.protocols.types.core_types import HealthStatus, NodeType
from pydantic import BaseModel, Field

# Import existing models instead of duplicating
from omnibase_core.enums.intelligence.enum_circuit_breaker_state import (
    EnumCircuitBreakerState,
)
from omnibase_core.model.service.model_service_health import ServiceHealthStatus


class DegradationLevel(str, Enum):
    """Service degradation levels for fallback scenarios."""

    NONE = "NONE"
    PARTIAL = "PARTIAL"
    FULL = "FULL"


class ModelCallResult(BaseModel):
    """Result of external service call execution."""

    success: bool = Field(..., description="Whether the external call was successful")

    response_data: Dict[str, Any] = Field(
        default_factory=dict, description="Response data from external service"
    )

    http_status: int = Field(
        ..., description="HTTP status code from external service", ge=100, le=599
    )

    response_time_ms: int = Field(
        ..., description="Response time in milliseconds", ge=0
    )

    service_endpoint: str = Field(
        ..., description="External service endpoint that was called"
    )

    headers: Dict[str, str] = Field(
        default_factory=dict, description="Response headers from external service"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional call metadata including retry count and circuit breaker state",
    )

    retry_count: int = Field(default=0, description="Number of retries attempted", ge=0)

    circuit_breaker_state: EnumCircuitBreakerState = Field(
        default=EnumCircuitBreakerState.CLOSED,
        description="Current circuit breaker state",
    )


class ModelExecutionMetadata(BaseModel):
    """Metadata about external service call execution."""

    service_name: str = Field(..., description="Name of the external service")

    operation_name: str = Field(..., description="Name of the operation performed")

    start_time: datetime = Field(..., description="When the operation started")

    end_time: datetime = Field(..., description="When the operation completed")

    total_time_ms: int = Field(
        ..., description="Total execution time in milliseconds", ge=0
    )

    network_time_ms: int = Field(..., description="Network time in milliseconds", ge=0)

    processing_time_ms: int = Field(
        ..., description="Processing time in milliseconds", ge=0
    )

    bytes_sent: int = Field(default=0, description="Number of bytes sent", ge=0)

    bytes_received: int = Field(default=0, description="Number of bytes received", ge=0)


class ModelHealthStatus(BaseModel):
    """Health status of an external service."""

    service_name: str = Field(..., description="Name of the external service")

    status: ServiceHealthStatus = Field(
        ..., description="Current health status of the service"
    )

    last_check: datetime = Field(
        ..., description="When the health check was last performed"
    )

    response_time_ms: int = Field(
        ..., description="Response time of last health check in milliseconds", ge=0
    )

    error_rate_percent: float = Field(
        ..., description="Error rate percentage over recent window", ge=0.0, le=100.0
    )

    availability_percent: float = Field(
        ..., description="Availability percentage over recent window", ge=0.0, le=100.0
    )

    circuit_breaker_state: str = Field(..., description="Current circuit breaker state")


class ModelFallbackResult(BaseModel):
    """Result of fallback strategy execution."""

    fallback_strategy_used: str = Field(
        ..., description="Name of the fallback strategy that was used"
    )

    fallback_success: bool = Field(
        ..., description="Whether the fallback strategy was successful"
    )

    fallback_data: Dict[str, Any] = Field(
        default_factory=dict, description="Data returned by the fallback strategy"
    )

    original_error: str = Field(
        ..., description="Original error that triggered the fallback"
    )

    degradation_level: DegradationLevel = Field(
        ..., description="Level of service degradation applied"
    )


class ModelValidationResult(BaseModel):
    """Result of external service response validation."""

    validation_success: bool = Field(
        ..., description="Whether validation was successful"
    )

    validation_errors: list[str] = Field(
        default_factory=list, description="List of validation errors if any"
    )

    normalized_response: Dict[str, Any] = Field(
        default_factory=dict, description="Response data normalized to internal format"
    )


class ModelTransformationMetadata(BaseModel):
    """Metadata about data transformation operations."""

    source_format: str = Field(..., description="Source data format")

    target_format: str = Field(..., description="Target data format")

    transformation_type: str = Field(
        ..., description="Type of transformation performed"
    )

    transformation_time_ms: int = Field(
        ..., description="Time taken for transformation in milliseconds", ge=0
    )

    records_processed: int = Field(
        default=0, description="Number of records processed", ge=0
    )


# Main subcontract definition model
class ModelExternalDependenciesSubcontract(BaseModel):
    """
    External Dependencies Subcontract for EFFECT nodes.

    Provides comprehensive external service integration capabilities including
    API calls, health monitoring, circuit breaker patterns, and fallback strategies.
    """

    subcontract_name: str = Field(
        default="external_dependencies_subcontract",
        description="Name of the subcontract",
    )

    subcontract_version: str = Field(
        default="1.0.0", description="Version of the subcontract"
    )

    applicable_node_types: list[str] = Field(
        default=["EFFECT"], description="Node types this subcontract applies to"
    )

    # Configuration
    connection_pool_size: int = Field(
        default=20,
        description="Size of connection pool for external services",
        ge=1,
        le=100,
    )

    default_timeout_ms: int = Field(
        default=15000,
        description="Default timeout for external calls in milliseconds",
        ge=1000,
        le=60000,
    )

    max_concurrent_calls: int = Field(
        default=50, description="Maximum concurrent external calls", ge=1, le=1000
    )

    circuit_breaker_enabled: bool = Field(
        default=True, description="Whether circuit breaker is enabled"
    )

    # Circuit breaker configuration
    failure_threshold: int = Field(
        default=10,
        description="Number of failures before opening circuit breaker",
        ge=1,
        le=100,
    )

    timeout_duration_ms: int = Field(
        default=60000,
        description="Circuit breaker timeout duration in milliseconds",
        ge=10000,
        le=300000,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "subcontract_name": "external_dependencies_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": ["EFFECT"],
                "connection_pool_size": 20,
                "default_timeout_ms": 15000,
                "max_concurrent_calls": 50,
                "circuit_breaker_enabled": True,
                "failure_threshold": 10,
                "timeout_duration_ms": 60000,
            }
        }
