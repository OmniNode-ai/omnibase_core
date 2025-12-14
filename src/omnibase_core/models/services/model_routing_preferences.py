"""
Routing Preferences Model.

Type-safe routing and load balancing preferences for node operations.
"""

from pydantic import BaseModel, Field


class ModelRoutingPreferences(BaseModel):
    """
    Routing preferences for load balancing.

    Provides structured preferences for how traffic should be
    routed to this node in a distributed system.
    """

    weight: float = Field(
        default=1.0,
        description="Load balancing weight",
        ge=0.0,
        le=10.0,
    )
    priority: int = Field(
        default=0,
        description="Routing priority (higher = preferred)",
        ge=0,
        le=100,
    )
    sticky_sessions: bool = Field(
        default=False,
        description="Whether to use session affinity",
    )
    prefer_local: bool = Field(
        default=True,
        description="Prefer local routing when available",
    )
    max_queue_size: int | None = Field(
        default=None,
        description="Maximum queue size before rejecting requests",
        ge=0,
    )
    drain_mode: bool = Field(
        default=False,
        description="Whether node is in drain mode (no new requests)",
    )
    excluded_zones: list[str] = Field(
        default_factory=list,
        description="Zones to exclude from routing",
    )
    preferred_zones: list[str] = Field(
        default_factory=list,
        description="Preferred zones for routing",
    )
    health_check_path: str | None = Field(
        default=None,
        description="Custom health check path",
    )

    def should_accept_traffic(self) -> bool:
        """Check if node should accept new traffic."""
        return not self.drain_mode and self.weight > 0.0

    def get_effective_weight(self, zone: str = "") -> float:
        """Get effective weight considering zone preferences."""
        if self.drain_mode:
            return 0.0

        if zone in self.excluded_zones:
            return 0.0

        if self.preferred_zones and zone in self.preferred_zones:
            return self.weight * 1.5  # Boost preferred zones

        return self.weight
