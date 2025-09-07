#!/usr/bin/env python3
"""
Infrastructure Orchestrator Response Models.

Strongly typed response models for infrastructure orchestrator operations with enhanced validation.
"""

from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ModelInfrastructureNodeResult(BaseModel):
    """Result from individual infrastructure node operation with enhanced tracking."""

    status: str = Field(
        description="Operation status (success/error/healthy/unhealthy)",
    )
    node_name: str | None = Field(default=None, description="Node name")
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time_ms: int = Field(
        ...,
        description="Node operation execution time in milliseconds",
    )
    correlation_id: UUID = Field(
        ...,
        description="Request correlation ID for tracing",
    )
    # Additional node-specific data can be included as Union types or generic Dict
    # Using Dict[str, str] for additional metadata is acceptable
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional node metadata",
    )

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        """Validate status against allowed values."""
        allowed_statuses = {
            "success",
            "error",
            "healthy",
            "unhealthy",
            "degraded",
            "timeout",
            "in_progress",
            "cancelled",
        }
        if v not in allowed_statuses:
            raise ValueError(f"Invalid status. Must be one of: {allowed_statuses}")
        return v


class ModelInfrastructureBootstrapResults(BaseModel):
    """Bootstrap results for all infrastructure adapters."""

    consul_adapter: ModelInfrastructureNodeResult = Field(
        description="Consul adapter bootstrap result",
    )
    vault_adapter: ModelInfrastructureNodeResult = Field(
        description="Vault adapter bootstrap result",
    )
    kafka_wrapper: ModelInfrastructureNodeResult = Field(
        description="Kafka wrapper bootstrap result",
    )


class ModelInfrastructureBootstrapResponse(BaseModel):
    """Infrastructure bootstrap coordination response with enhanced tracking."""

    success: bool = Field(..., description="Whether bootstrap operation succeeded")
    bootstrap_results: ModelInfrastructureBootstrapResults = Field(
        description="Individual adapter bootstrap results",
    )
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time_ms: int = Field(
        ...,
        description="Total bootstrap execution time in milliseconds",
    )
    correlation_id: UUID = Field(
        ...,
        description="Request correlation ID for tracing",
    )


class ModelInfrastructureAdapterHealth(BaseModel):
    """Health status for individual infrastructure adapter."""

    status: str = Field(description="Adapter status (healthy/unhealthy/degraded)")
    error: str | None = Field(default=None, description="Error message if unhealthy")
    # Additional adapter-specific health data
    details: dict[str, str] = Field(
        default_factory=dict,
        description="Additional health details",
    )


class ModelInfrastructureHealthCheckResults(BaseModel):
    """Health check results for all infrastructure adapters."""

    consul_adapter: ModelInfrastructureAdapterHealth = Field(
        description="Consul adapter health",
    )
    vault_adapter: ModelInfrastructureAdapterHealth = Field(
        description="Vault adapter health",
    )
    kafka_wrapper: ModelInfrastructureAdapterHealth = Field(
        description="Kafka wrapper health",
    )


class ModelInfrastructureHealthCheckResponse(BaseModel):
    """Infrastructure health check coordination response with enhanced tracking."""

    success: bool = Field(..., description="Whether health check operation succeeded")
    adapter_health: ModelInfrastructureHealthCheckResults = Field(
        description="Individual adapter health results",
    )
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time_ms: int = Field(
        ...,
        description="Health check execution time in milliseconds",
    )
    correlation_id: UUID = Field(
        ...,
        description="Request correlation ID for tracing",
    )


class ModelInfrastructureFailoverResponse(BaseModel):
    """Infrastructure failover coordination response with enhanced tracking."""

    success: bool = Field(..., description="Whether failover operation succeeded")
    failed_adapter: str = Field(description="Name of failed adapter")
    failover_result: ModelInfrastructureNodeResult = Field(
        description="Failover operation result",
    )
    error: str | None = Field(default=None, description="Error message if failed")
    execution_time_ms: int = Field(
        ...,
        description="Failover execution time in milliseconds",
    )
    correlation_id: UUID = Field(
        ...,
        description="Request correlation ID for tracing",
    )
