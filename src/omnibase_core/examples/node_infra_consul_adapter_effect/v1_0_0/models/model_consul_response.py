#!/usr/bin/env python3
"""
Infrastructure Consul Response Models.

Strongly typed response models for consul adapter operations.
"""

from enum import Enum

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_core_errors import OnexError
from omnibase_core.models.core.model_semver import ModelSemVer


class EnumConsulOperationType(str, Enum):
    """Consul operation types."""

    SERVICE_REGISTER = "service_register"
    SERVICE_DEREGISTER = "service_deregister"
    SERVICE_DISCOVERY = "service_discovery"
    HEALTH_CHECK = "health_check"
    KV_READ = "kv_read"
    KV_WRITE = "kv_write"
    KV_DELETE = "kv_delete"


class EnumConsulStatus(str, Enum):
    """Consul operation status."""

    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SKIPPED = "skipped"
    FIXED = "fixed"
    PARTIAL = "partial"
    INFO = "info"
    UNKNOWN = "unknown"


class EnumConsulErrorType(str, Enum):
    """Consul error types."""

    CONNECTION_FAILED = "connection_failed"
    SERVICE_NOT_FOUND = "service_not_found"
    INVALID_CONFIGURATION = "invalid_configuration"
    REGISTRATION_FAILED = "registration_failed"
    HEALTH_CHECK_FAILED = "health_check_failed"
    KV_OPERATION_FAILED = "kv_operation_failed"
    AUTHENTICATION_FAILED = "authentication_failed"


class ModelConsulHealthStatus(BaseModel):
    """Consul health check status information."""

    status: str = Field(description="Health status (healthy/unhealthy/degraded)")
    consul_agent: str = Field(description="Consul agent node name")
    datacenter: str = Field(description="Consul datacenter")
    error: str | None = Field(default=None, description="Error message if unhealthy")


class ModelConsulKVResponse(BaseModel):
    """Consul KV store operation response."""

    status: str = Field(description="Operation status (success/not_found/failed)")
    key: str = Field(description="KV store key")
    value: str | None = Field(default=None, description="KV store value")
    modify_index: int | None = Field(default=None, description="Consul modify index")


class ModelConsulHealthCheck(BaseModel):
    """Individual health check data."""

    url: str = Field(description="Health check URL")
    interval: str = Field(default="10s", description="Check interval")
    timeout: str = Field(default="5s", description="Check timeout")


class ModelConsulServiceRegistration(BaseModel):
    """Consul service registration data."""

    service_id: str = Field(description="Unique service identifier")
    name: str = Field(description="Service name")
    port: int = Field(description="Service port")
    address: str = Field(default="localhost", description="Service address")
    health_check: ModelConsulHealthCheck | None = Field(
        default=None,
        description="Health check configuration",
    )


class ModelConsulServiceInfo(BaseModel):
    """Consul service information."""

    id: str = Field(description="Service ID")
    name: str = Field(description="Service name")
    port: int = Field(description="Service port")
    address: str = Field(description="Service address")
    tags: list[str] = Field(default_factory=list, description="Service tags")


class ModelConsulServiceListResponse(BaseModel):
    """Consul service list response."""

    status: str = Field(description="Operation status")
    services: list[ModelConsulServiceInfo] = Field(description="List of services")
    count: int = Field(description="Number of services")


class ModelConsulServiceResponse(BaseModel):
    """Consul service registration response."""

    status: str = Field(description="Operation status (success/failed)")
    service_id: str = Field(description="Service ID")
    service_name: str = Field(description="Service name")


class ModelConsulHealthCheckNode(BaseModel):
    """Consul health check node information."""

    node: str | None = Field(default=None, description="Node name")
    service_id: str | None = Field(default=None, description="Service ID")
    service_name: str | None = Field(default=None, description="Service name")
    status: str = Field(description="Health status")


class ModelConsulHealthResponse(BaseModel):
    """Consul health check response."""

    status: str = Field(description="Operation status")
    service_name: str | None = Field(default=None, description="Service name")
    health_checks: list[ModelConsulHealthCheckNode] | None = Field(
        default=None,
        description="Health check details for specific service",
    )
    health_summary: dict[str, dict[str, str]] | None = Field(
        default=None,
        description="Health summary for all services",
    )


class ModelConsulAdapterHealth(BaseModel):
    """Consul adapter health response."""

    adapter: str = Field(description="Adapter name")
    status: str = Field(description="Adapter status")
    consul: ModelConsulHealthStatus = Field(description="Consul health status")


class ModelConsulResponse(BaseModel):
    """Single consul response model for all consul operations."""

    version: ModelSemVer = Field(description="Model version")
    operation_type: EnumConsulOperationType = Field(
        description="Type of consul operation",
    )
    status: EnumConsulStatus = Field(description="Operation status")
    success: bool = Field(description="Whether operation succeeded")
    data: dict | None = Field(default=None, description="Operation response data")
    error: OnexError | None = Field(
        default=None,
        description="Error details if operation failed",
    )
