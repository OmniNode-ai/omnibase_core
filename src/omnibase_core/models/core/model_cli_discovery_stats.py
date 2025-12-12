"""
Model for CLI tool discovery statistics.

Provides structured statistics about CLI tool discovery operations,
replacing primitive dictionary types with type-safe Pydantic models.
"""

from pydantic import BaseModel, Field

from omnibase_core.types.type_serializable_value import SerializedDict


class ModelCliDiscoveryStats(BaseModel):
    """
    Model for CLI tool discovery statistics.

    Provides comprehensive statistics about tool discovery operations
    including counts, health metrics, and performance data.
    """

    # Tool counts
    total_tools_discovered: int = Field(
        default=0,
        description="Total number of tools discovered by the system",
    )
    healthy_tools_count: int = Field(
        default=0,
        description="Number of healthy tools currently available",
    )
    unhealthy_tools_count: int = Field(
        default=0,
        description="Number of tools with health issues",
    )

    # Registry and cache metrics
    discovery_cache_size: int = Field(
        default=0,
        description="Number of tools currently cached in discovery registry",
    )
    cache_hit_rate: float | None = Field(
        default=None,
        description="Discovery cache hit rate as percentage (0-100)",
    )

    # Performance metrics
    last_discovery_duration_ms: float | None = Field(
        default=None,
        description="Duration of last discovery operation in milliseconds",
    )
    average_discovery_duration_ms: float | None = Field(
        default=None,
        description="Average discovery operation duration in milliseconds",
    )

    # Timestamp tracking
    last_refresh_timestamp: str | None = Field(
        default=None,
        description="ISO timestamp of last registry refresh",
    )
    last_health_check_timestamp: str | None = Field(
        default=None,
        description="ISO timestamp of last health check cycle",
    )

    # Error tracking
    discovery_errors_count: int = Field(
        default=0,
        description="Number of discovery errors since last reset",
    )
    last_error_message: str | None = Field(
        default=None,
        description="Message from most recent discovery error",
    )

    # Registry health
    registries_online: int = Field(
        default=0,
        description="Number of tool registries currently online",
    )
    registries_total: int = Field(
        default=0,
        description="Total number of tool registries configured",
    )

    @property
    def health_percentage(self) -> float:
        """Calculate percentage of healthy tools."""
        if self.total_tools_discovered == 0:
            return 100.0
        return (self.healthy_tools_count / self.total_tools_discovered) * 100.0

    @property
    def registry_health_percentage(self) -> float:
        """Calculate percentage of healthy registries."""
        if self.registries_total == 0:
            return 100.0
        return (self.registries_online / self.registries_total) * 100.0

    def to_summary_dict(self) -> SerializedDict:
        """
        Convert to a summary dictionary for display purposes.

        Returns:
            Dictionary with key statistics for display
        """
        return {
            "total_tools": self.total_tools_discovered,
            "healthy_tools": self.healthy_tools_count,
            "health_percentage": round(self.health_percentage, 1),
            "cache_size": self.discovery_cache_size,
            "registries_online": f"{self.registries_online}/{self.registries_total}",
            "last_refresh": self.last_refresh_timestamp,
        }
