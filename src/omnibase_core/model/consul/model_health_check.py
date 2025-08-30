"""
Health check models for Consul integration.
"""

from omnibase.enums.enum_health_status import EnumHealthStatus
from pydantic import BaseModel, Field

# Backward compatibility alias
HealthCheckStatus = EnumHealthStatus


class ModelHealthComponent(BaseModel):
    """Individual health check component."""

    name: str = Field(..., description="Name of the health check component")
    status: EnumHealthStatus = Field(..., description="Current status of the component")
    message: str = Field(..., description="Human-readable status message")
    details: dict[str, str] = Field(
        default_factory=dict,
        description="Additional details about the component health",
    )
    check_duration_ms: float = Field(
        ...,
        description="Time taken to perform this health check",
    )


class ModelHealthCheckResponse(BaseModel):
    """Response from health check endpoint."""

    status: EnumHealthStatus = Field(..., description="Overall health status")
    timestamp: str = Field(
        ...,
        description="ISO timestamp when health check was performed",
    )
    components: list[ModelHealthComponent] = Field(
        default_factory=list,
        description="Individual component health checks",
    )
    total_check_duration_ms: float = Field(
        ...,
        description="Total time for all health checks",
    )
    service_info: dict[str, str] = Field(
        default_factory=dict,
        description="Service metadata and information",
    )


class ModelReadinessCheckResponse(BaseModel):
    """Response from readiness check endpoint."""

    ready: bool = Field(
        ...,
        description="Whether the service is ready to accept traffic",
    )
    timestamp: str = Field(
        ...,
        description="ISO timestamp when readiness check was performed",
    )
    dependencies: list[ModelHealthComponent] = Field(
        default_factory=list,
        description="Status of service dependencies",
    )
    initialization_status: dict[str, bool] = Field(
        default_factory=dict,
        description="Status of initialization tasks",
    )
    check_duration_ms: float = Field(..., description="Time taken for readiness check")


class ModelMetricsResponse(BaseModel):
    """Response from metrics endpoint."""

    timestamp: str = Field(..., description="ISO timestamp when metrics were collected")
    metrics: dict[str, float] = Field(
        default_factory=dict,
        description="Performance metrics as key-value pairs",
    )
    format: str = Field(
        "prometheus",
        description="Format of the metrics (prometheus, json, etc.)",
    )
    collection_duration_ms: float = Field(
        ...,
        description="Time taken to collect metrics",
    )
