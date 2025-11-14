from pydantic import Field

"""
Load Balancing Model - ONEX Standards Compliant.

Individual model for load balancing configuration.
Part of the Routing Subcontract Model family.

ZERO TOLERANCE: No Any types allowed in implementation.
"""

from typing import Any

from pydantic import BaseModel


class ModelLoadBalancing(BaseModel):
    """
    Load balancing configuration for ONEX microservices.

    Defines load balancing strategies optimized for microservices,
    health checking, and failover policies with service discovery integration.
    """

    strategy: str = Field(
        default="service_aware_round_robin",
        description="Load balancing strategy (service_aware_round_robin, consistent_hash, least_connections, weighted_response_time)",
    )

    health_check_enabled: bool = Field(
        default=True,
        description="Enable health checking for targets",
    )

    health_check_path: str = Field(
        default="/health",
        description="Health check endpoint path",
    )

    health_check_interval_ms: int = Field(
        default=30000,
        description="Health check interval",
        ge=1000,
    )

    health_check_timeout_ms: int = Field(
        default=5000,
        description="Health check timeout",
        ge=100,
    )

    unhealthy_threshold: int = Field(
        default=3,
        description="Failures before marking unhealthy",
        ge=1,
    )

    healthy_threshold: int = Field(
        default=2,
        description="Successes before marking healthy",
        ge=1,
    )

    sticky_sessions: bool = Field(
        default=False,
        description="Enable sticky session routing",
    )

    session_affinity_cookie: str | None = Field(
        default=None,
        description="Cookie name for session affinity",
    )

    # ONEX microservices specific load balancing features
    service_discovery_enabled: bool = Field(
        default=True,
        description="Enable automatic service discovery for targets",
    )

    container_aware_routing: bool = Field(
        default=True,
        description="Enable container-aware routing for ONEX 4-node architecture",
    )

    node_type_affinity: str | None = Field(
        default=None,
        description="Preferred ONEX node type (Effect, Compute, Reducer, Orchestrator)",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
