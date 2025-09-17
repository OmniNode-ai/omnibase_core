"""
Service Resolution Subcontract Models for ONEX Nodes.

Provides Pydantic models for service discovery, dependency injection, and
service registry integration patterns for all ONEX node types.

Generated from service_resolution subcontract following ONEX patterns.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

# Import existing enums instead of duplicating
from omnibase_spi.protocols.types.core_types import HealthStatus, NodeType
from pydantic import BaseModel, Field

from omnibase_core.models.service.model_service_health import ServiceHealthStatus


class ServiceProtocol(str, Enum):
    """Supported service protocols."""

    HTTP = "HTTP"
    HTTPS = "HTTPS"
    GRPC = "GRPC"
    TCP = "TCP"
    UDP = "UDP"

    # Use ServiceHealthStatus from omnibase_core.models.service.model_service_health instead
    """Health status levels for services."""

    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    UNKNOWN = "UNKNOWN"


class DiscoveryMethod(str, Enum):
    """Service discovery methods."""

    CONSUL = "CONSUL"
    ENVIRONMENT = "ENVIRONMENT"
    CACHE = "CACHE"


class ModelServiceEndpoint(BaseModel):
    """Service endpoint information from resolution."""

    service_name: str = Field(..., description="Name of the resolved service")

    endpoint_url: str = Field(..., description="Complete URL endpoint for the service")

    protocol: ServiceProtocol = Field(..., description="Protocol used by the service")

    port: int = Field(..., description="Port number for the service", ge=1, le=65535)

    health_status: ServiceHealthStatus = Field(
        ..., description="Current health status of the service"
    )

    last_checked: datetime = Field(
        ..., description="When the service health was last checked"
    )

    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional service metadata"
    )


class ModelServiceMetadata(BaseModel):
    """Metadata about a discovered service."""

    service_version: str = Field(..., description="Version of the service")

    node_type: str = Field(
        ..., description="Type of ONEX node (COMPUTE, EFFECT, REDUCER, ORCHESTRATOR)"
    )

    capabilities: List[str] = Field(
        default_factory=list, description="List of capabilities provided by the service"
    )

    discovery_method: DiscoveryMethod = Field(
        ..., description="Method used to discover this service"
    )


class ModelServiceDiscoveryEndpoint(BaseModel):
    """Individual endpoint in service discovery results."""

    url: str = Field(..., description="Service endpoint URL")

    health_status: str = Field(..., description="Health status of this endpoint")

    weight: int = Field(
        default=1, description="Load balancing weight for this endpoint", ge=0, le=100
    )


class ModelDiscoveredService(BaseModel):
    """A service discovered through service discovery."""

    service_name: str = Field(..., description="Name of the discovered service")

    service_type: str = Field(..., description="Type or category of the service")

    endpoints: List[ModelServiceDiscoveryEndpoint] = Field(
        default_factory=list, description="List of endpoints for this service"
    )

    discovery_time: datetime = Field(
        ..., description="When this service was discovered"
    )


class ModelDiscoveredServices(BaseModel):
    """Collection of services discovered through service discovery."""

    services: List[ModelDiscoveredService] = Field(
        default_factory=list, description="List of discovered services"
    )

    total_count: int = Field(
        default=0, description="Total number of services discovered", ge=0
    )

    discovery_duration_ms: int = Field(
        default=0,
        description="Time taken for discovery operation in milliseconds",
        ge=0,
    )


class ModelRegistrationStatus(BaseModel):
    """Status of service registration operation."""

    registration_id: str = Field(
        ..., description="Unique identifier for the service registration"
    )

    registration_success: bool = Field(
        ..., description="Whether the registration was successful"
    )

    registration_time: datetime = Field(
        ..., description="When the registration occurred"
    )

    service_name: str = Field(..., description="Name of the registered service")

    health_check_endpoint: Optional[str] = Field(
        default=None, description="Health check endpoint for the registered service"
    )


class ModelDeregistrationStatus(BaseModel):
    """Status of service deregistration operation."""

    registration_id: str = Field(
        ..., description="Registration ID that was deregistered"
    )

    deregistration_success: bool = Field(
        ..., description="Whether the deregistration was successful"
    )

    deregistration_time: datetime = Field(
        ..., description="When the deregistration occurred"
    )


class ModelServiceHealthCheck(BaseModel):
    """Result of service health check operation."""

    service_name: str = Field(..., description="Name of the service that was checked")

    endpoint_url: str = Field(..., description="Endpoint that was checked")

    health_status: ServiceHealthStatus = Field(..., description="Health status result")

    response_time_ms: int = Field(
        ..., description="Response time for health check in milliseconds", ge=0
    )

    check_time: datetime = Field(..., description="When the health check was performed")

    error_message: Optional[str] = Field(
        default=None, description="Error message if health check failed"
    )


# Main subcontract definition model
class ModelServiceResolutionSubcontract(BaseModel):
    """
    Service Resolution Subcontract for all ONEX nodes.

    Provides service discovery, dependency injection, and service registry
    integration capabilities for COMPUTE, EFFECT, REDUCER, and ORCHESTRATOR nodes.
    """

    subcontract_name: str = Field(
        default="service_resolution_subcontract", description="Name of the subcontract"
    )

    subcontract_version: str = Field(
        default="1.0.0", description="Version of the subcontract"
    )

    applicable_node_types: List[str] = Field(
        default=["COMPUTE", "EFFECT", "REDUCER", "ORCHESTRATOR"],
        description="Node types this subcontract applies to",
    )

    # Configuration
    primary_strategy: str = Field(
        default="consul", description="Primary service resolution strategy"
    )

    fallback_strategy: str = Field(
        default="environment", description="Fallback service resolution strategy"
    )

    cache_enabled: bool = Field(
        default=True, description="Whether service resolution caching is enabled"
    )

    cache_ttl_ms: int = Field(
        default=300000,
        description="Cache time-to-live in milliseconds",
        ge=1000,
        le=3600000,
    )

    health_check_interval_ms: int = Field(
        default=30000,
        description="Health check interval in milliseconds",
        ge=5000,
        le=300000,
    )

    max_retries: int = Field(
        default=3, description="Maximum number of resolution retries", ge=1, le=10
    )

    retry_delay_ms: int = Field(
        default=500,
        description="Delay between retries in milliseconds",
        ge=100,
        le=5000,
    )

    exponential_backoff: bool = Field(
        default=True, description="Whether to use exponential backoff for retries"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "subcontract_name": "service_resolution_subcontract",
                "subcontract_version": "1.0.0",
                "applicable_node_types": [
                    "COMPUTE",
                    "EFFECT",
                    "REDUCER",
                    "ORCHESTRATOR",
                ],
                "primary_strategy": "consul",
                "fallback_strategy": "environment",
                "cache_enabled": True,
                "cache_ttl_ms": 300000,
                "health_check_interval_ms": 30000,
                "max_retries": 3,
                "retry_delay_ms": 500,
                "exponential_backoff": True,
            }
        }
