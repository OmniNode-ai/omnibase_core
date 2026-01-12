"""
Load Balancing Model.

Individual model for load balancing configuration.
Part of the Routing Subcontract Model family.

Strict typing is enforced: No Any types allowed in implementation.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.constants import TIMEOUT_DEFAULT_MS
from omnibase_core.models.primitives.model_semver import ModelSemVer


class ModelLoadBalancing(BaseModel):
    """
    Load balancing configuration for ONEX microservices.

    Defines load balancing strategies optimized for microservices,
    health checking, and failover policies with service discovery integration.
    """

    # Model version for instance tracking
    version: ModelSemVer = Field(
        ...,  # REQUIRED - specify in contract
        description="Model version (MUST be provided in YAML contract)",
    )

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
        default=TIMEOUT_DEFAULT_MS,
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

    model_config = ConfigDict(
        extra="ignore",
        use_enum_values=False,
        validate_assignment=True,
    )
