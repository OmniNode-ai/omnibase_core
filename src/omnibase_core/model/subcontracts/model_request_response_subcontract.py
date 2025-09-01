"""
Request Response Subcontract Models for ONEX Nodes.

Provides Pydantic models for standardized request/response interaction patterns
and communication protocols for all ONEX node types.

Generated from request_response subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Import existing enums instead of duplicating
from omnibase.protocols.types.core_types import HealthStatus, NodeType
from pydantic import BaseModel, Field


class RequestPriority(str, Enum):
    """Request priority levels."""

    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ResponseStatus(str, Enum):
    """Response status values."""

    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    INVALID = "INVALID"


class ErrorType(str, Enum):
    """Error type classifications."""

    VALIDATION = "VALIDATION"
    PROCESSING = "PROCESSING"
    TIMEOUT = "TIMEOUT"
    RESOURCE = "RESOURCE"
    SYSTEM = "SYSTEM"


class ModelProcessingOptions(BaseModel):
    """Options for request processing."""

    timeout_ms: int = Field(
        default=30000, description="Request timeout in milliseconds", ge=1000, le=300000
    )

    priority: RequestPriority = Field(
        default=RequestPriority.NORMAL, description="Request priority level"
    )


class ModelRequestEnvelope(BaseModel):
    """Standard request envelope for ONEX nodes."""

    request_id: str = Field(
        ...,
        description="Unique identifier for the request",
        pattern=r"^[a-zA-Z0-9-]{36}$",
    )

    correlation_id: str = Field(
        ..., description="Correlation identifier for request tracking"
    )

    timestamp: datetime = Field(..., description="Request timestamp")

    source_node: str = Field(..., description="Node that originated the request")

    target_node: Optional[str] = Field(
        default=None, description="Target node for the request"
    )

    request_type: str = Field(
        ..., description="Type of request", pattern=r"^[a-z][a-z_]*[a-z]$"
    )

    headers: Dict[str, str] = Field(default_factory=dict, description="Request headers")

    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Request payload data"
    )

    processing_options: ModelProcessingOptions = Field(
        default_factory=ModelProcessingOptions,
        description="Processing options for the request",
    )


class ModelResponseEnvelope(BaseModel):
    """Standard response envelope for ONEX nodes."""

    response_id: str = Field(..., description="Unique identifier for the response")

    request_id: str = Field(..., description="Identifier of the original request")

    correlation_id: str = Field(..., description="Correlation identifier for tracking")

    timestamp: datetime = Field(..., description="Response timestamp")

    source_node: str = Field(..., description="Node that generated the response")

    processing_time_ms: int = Field(
        ..., description="Time taken to process the request in milliseconds", ge=0
    )

    status: ResponseStatus = Field(..., description="Status of the response")

    headers: Dict[str, str] = Field(
        default_factory=dict, description="Response headers"
    )

    payload: Dict[str, Any] = Field(
        default_factory=dict, description="Response payload data"
    )


class ModelResourceUsage(BaseModel):
    """Resource usage metrics for request processing."""

    cpu_time_ms: int = Field(..., description="CPU time used in milliseconds", ge=0)

    memory_used_mb: float = Field(..., description="Memory used in megabytes", ge=0.0)


class ModelValidationResults(BaseModel):
    """Validation results for request/response."""

    input_valid: bool = Field(..., description="Whether input validation passed")

    output_valid: bool = Field(..., description="Whether output validation passed")


class ModelProcessingMetadata(BaseModel):
    """Metadata about request processing."""

    processing_node: str = Field(..., description="Node that processed the request")

    processing_time_ms: int = Field(
        ..., description="Time taken for processing in milliseconds", ge=0
    )

    processing_stage: str = Field(..., description="Current or final processing stage")

    resource_usage: ModelResourceUsage = Field(
        ..., description="Resource usage during processing"
    )

    validation_results: ModelValidationResults = Field(
        ..., description="Validation results"
    )


class ModelErrorDetails(BaseModel):
    """Detailed error information."""

    stack_trace: Optional[str] = Field(
        default=None, description="Stack trace for the error"
    )

    context: Dict[str, Any] = Field(
        default_factory=dict, description="Error context information"
    )

    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for resolving the error"
    )


class ModelErrorResponse(BaseModel):
    """Error response structure."""

    error_code: str = Field(..., description="Error code identifier")

    error_message: str = Field(..., description="Human-readable error message")

    error_type: ErrorType = Field(..., description="Classification of the error")

    error_details: ModelErrorDetails = Field(
        default_factory=ModelErrorDetails, description="Detailed error information"
    )

    recovery_actions: List[str] = Field(
        default_factory=list, description="Suggested recovery actions"
    )


class ModelValidationSchema(BaseModel):
    """Schema for request/response validation."""

    required_fields: List[str] = Field(
        default_factory=list, description="List of required field names"
    )

    field_types: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of field names to their expected types",
    )

    field_constraints: Dict[str, str] = Field(
        default_factory=dict,
        description="Mapping of field names to validation constraints (regex patterns)",
    )


class ModelValidationResult(BaseModel):
    """Result of validation operation."""

    is_valid: bool = Field(..., description="Whether validation passed")

    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation error messages"
    )

    validated_fields: List[str] = Field(
        default_factory=list, description="List of successfully validated fields"
    )


class ModelNodeRequestPattern(BaseModel):
    """Request pattern configuration for a node type."""

    request_types: List[str] = Field(
        default_factory=list, description="Types of requests this node can handle"
    )

    response_types: List[str] = Field(
        default_factory=list, description="Types of responses this node can generate"
    )

    typical_processing_time_ms: int = Field(
        default=5000, description="Typical processing time in milliseconds", ge=100
    )

    supports_streaming: bool = Field(
        default=False, description="Whether this node supports streaming responses"
    )

    supports_batching: bool = Field(
        default=False, description="Whether this node supports batch processing"
    )


class ModelRetryPolicy(BaseModel):
    """Retry policy configuration."""

    max_retries: int = Field(
        default=3, description="Maximum number of retries", ge=0, le=10
    )

    retry_delay_ms: int = Field(
        default=1000,
        description="Delay between retries in milliseconds",
        ge=100,
        le=60000,
    )

    exponential_backoff: bool = Field(
        default=True, description="Whether to use exponential backoff"
    )

    backoff_multiplier: float = Field(
        default=2.0, description="Multiplier for exponential backoff", ge=1.0, le=10.0
    )


class ModelResponseCacheConfig(BaseModel):
    """Configuration for response caching."""

    enabled: bool = Field(
        default=False, description="Whether response caching is enabled"
    )

    ttl_ms: int = Field(
        default=300000,
        description="Time-to-live for cached responses in milliseconds",
        ge=60000,
    )

    max_cache_size_mb: int = Field(
        default=100, description="Maximum cache size in megabytes", ge=1, le=1000
    )


# Main subcontract definition model
class ModelRequestResponseSubcontract(BaseModel):
    """
    Request Response Subcontract for all ONEX nodes.

    Provides standardized request/response interaction patterns and
    communication protocols for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.
    """

    subcontract_name: str = Field(
        default="request_response_subcontract", description="Name of the subcontract"
    )

    subcontract_version: str = Field(
        default="1.0.0", description="Version of the subcontract"
    )

    applicable_node_types: List[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types this subcontract applies to",
    )

    # Configuration
    default_timeout_ms: int = Field(
        default=30000,
        description="Default request timeout in milliseconds",
        ge=5000,
        le=300000,
    )

    max_request_size_mb: int = Field(
        default=10, description="Maximum request size in megabytes", ge=1, le=100
    )

    max_response_size_mb: int = Field(
        default=50, description="Maximum response size in megabytes", ge=1, le=1000
    )

    compression_enabled: bool = Field(
        default=True,
        description="Whether compression is enabled for requests/responses",
    )

    encryption_required: bool = Field(
        default=False,
        description="Whether encryption is required for requests/responses",
    )

    correlation_tracking: bool = Field(
        default=True, description="Whether correlation tracking is enabled"
    )

    request_logging_enabled: bool = Field(
        default=True, description="Whether request logging is enabled"
    )

    response_caching: ModelResponseCacheConfig = Field(
        default_factory=ModelResponseCacheConfig,
        description="Response caching configuration",
    )

    # Error handling configuration
    retry_policies: Dict[str, ModelRetryPolicy] = Field(
        default_factory=lambda: {
            "transient_errors": ModelRetryPolicy(
                max_retries=3,
                retry_delay_ms=1000,
                exponential_backoff=True,
                backoff_multiplier=2.0,
            ),
            "timeout_errors": ModelRetryPolicy(
                max_retries=1, retry_delay_ms=500, exponential_backoff=False
            ),
            "validation_errors": ModelRetryPolicy(max_retries=0),
        },
        description="Retry policies for different error types",
    )

    # Circuit breaker configuration
    circuit_breaker_enabled: bool = Field(
        default=True, description="Whether circuit breaker is enabled"
    )

    circuit_breaker_failure_threshold: int = Field(
        default=5, description="Failure threshold for circuit breaker", ge=1, le=20
    )

    circuit_breaker_timeout_ms: int = Field(
        default=60000,
        description="Circuit breaker timeout in milliseconds",
        ge=30000,
        le=300000,
    )

    circuit_breaker_recovery_timeout_ms: int = Field(
        default=30000,
        description="Circuit breaker recovery timeout in milliseconds",
        ge=10000,
        le=120000,
    )

    class Config:
        json_schema_extra = {
            "example": {
                "subcontract_name": "request_response_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": [
                    "COMPUTE",
                    "EFFECT",
                    "REDUCER",
                    "ORCHESTRATOR",
                ],
                "default_timeout_ms": 30000,
                "max_request_size_mb": 10,
                "max_response_size_mb": 50,
                "compression_enabled": True,
                "encryption_required": False,
                "correlation_tracking": True,
                "request_logging_enabled": True,
                "response_caching": {
                    "enabled": False,
                    "ttl_ms": 300000,
                    "max_cache_size_mb": 100,
                },
                "circuit_breaker_enabled": True,
                "circuit_breaker_failure_threshold": 5,
                "circuit_breaker_timeout_ms": 60000,
                "circuit_breaker_recovery_timeout_ms": 30000,
            }
        }
