"""
Routing configuration model for ORCHESTRATOR nodes.
"""

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.enums.nodes import EnumRoutingStrategy


class ModelRoutingConfig(BaseModel):
    """Routing configuration for ORCHESTRATOR nodes."""

    model_config = ConfigDict(extra="forbid")

    strategy: EnumRoutingStrategy = Field(
        ...,
        description="Routing strategy for load distribution",
    )
    load_balancing: bool = Field(
        default=True,
        description="Enable load balancing",
    )
    health_check_interval_ms: int = Field(
        default=30000,
        description="Health check interval in milliseconds",
        ge=1000,
    )
    failover_enabled: bool = Field(
        default=True,
        description="Enable automatic failover",
    )
