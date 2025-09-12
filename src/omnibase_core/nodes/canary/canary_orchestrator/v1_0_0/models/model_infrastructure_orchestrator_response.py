#!/usr/bin/env python3
"""
Infrastructure Orchestrator Response Models.

Strongly typed response models for infrastructure orchestrator operations.
"""

from pydantic import BaseModel, Field


class ModelInfrastructureNodeResult(BaseModel):
    """Result from individual infrastructure node operation."""

    status: str = Field(
        description="Operation status (success/error/healthy/unhealthy)",
    )
    node_name: str | None = Field(default=None, description="Node name")
    error: str | None = Field(default=None, description="Error message if failed")
    # Additional node-specific data can be included as Union types or generic Dict
    # Using Dict[str, str] for additional metadata is acceptable
    metadata: dict[str, str] = Field(
        default_factory=dict,
        description="Additional node metadata",
    )


class ModelInfrastructureBootstrapResults(BaseModel):
    """Bootstrap results for all infrastructure adapters."""

    consul_adapter: ModelInfrastructureNodeResult = Field(
        description="Consul adapter bootstrap result",
    )
    vault_adapter: ModelInfrastructureNodeResult = Field(
        description="Vault adapter bootstrap result",
    )


class ModelInfrastructureBootstrapResponse(BaseModel):
    """Infrastructure bootstrap coordination response."""

    status: str = Field(description="Overall bootstrap status (success/error)")
    bootstrap_results: ModelInfrastructureBootstrapResults = Field(
        description="Individual adapter bootstrap results",
    )
    error: str | None = Field(default=None, description="Error message if failed")


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


class ModelInfrastructureHealthCheckResponse(BaseModel):
    """Infrastructure health check coordination response."""

    status: str = Field(description="Overall health status (healthy/degraded/error)")
    adapter_health: ModelInfrastructureHealthCheckResults = Field(
        description="Individual adapter health results",
    )
    error: str | None = Field(default=None, description="Error message if failed")


class ModelInfrastructureFailoverResponse(BaseModel):
    """Infrastructure failover coordination response."""

    status: str = Field(description="Failover status (failover_coordinated/error)")
    failed_adapter: str = Field(description="Name of failed adapter")
    failover_result: ModelInfrastructureNodeResult = Field(
        description="Failover operation result",
    )
    error: str | None = Field(default=None, description="Error message if failed")
