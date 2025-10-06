from typing import Any

from pydantic import BaseModel, Field


class ModelLoadBalancingParameters(BaseModel):
    """Parameters for load balancing algorithms."""

    # Resource-based weights (0.0-1.0, should sum to 1.0)
    cpu_weight: float = Field(
        0.4,
        description="Weight for CPU usage in resource-based routing",
        ge=0.0,
        le=1.0,
    )
    memory_weight: float = Field(
        0.3,
        description="Weight for memory usage in resource-based routing",
        ge=0.0,
        le=1.0,
    )
    network_weight: float = Field(
        0.2,
        description="Weight for network usage in resource-based routing",
        ge=0.0,
        le=1.0,
    )
    disk_weight: float = Field(
        0.1,
        description="Weight for disk I/O in resource-based routing",
        ge=0.0,
        le=1.0,
    )

    # Connection limits
    max_connections_per_node: int | None = Field(
        None,
        description="Maximum connections per node",
        ge=1,
    )
    connection_threshold: int | None = Field(
        None,
        description="Connection count threshold for overflow",
        ge=1,
    )

    # Response time parameters
    response_time_window_seconds: int = Field(
        60,
        description="Window for calculating average response time",
        ge=1,
    )
    response_time_percentile: int = Field(
        95,
        description="Percentile to use for response time (e.g., p95)",
        ge=1,
        le=100,
    )

    # Hash parameters
    hash_algorithm: str = Field(
        "fnv1a",
        description="Hash algorithm for IP-based routing",
        pattern="^(fnv1a|murmur3|xxhash|md5|sha1)$",
    )
    hash_virtual_nodes: int = Field(
        150,
        description="Number of virtual nodes for consistent hashing",
        ge=1,
        le=1000,
    )

    # Failover parameters
    failover_threshold: int = Field(
        3,
        description="Number of failures before marking node unhealthy",
        ge=1,
    )
    recovery_threshold: int = Field(
        2,
        description="Number of successes before marking node healthy",
        ge=1,
    )
    health_check_interval_ms: int = Field(
        5000,
        description="Health check interval in milliseconds",
        ge=100,
    )

    # Custom algorithm parameters
    custom_algorithm_class: str | None = Field(
        None,
        description="Fully qualified class name for custom algorithm",
    )
    custom_algorithm_config: dict[str, str] | None = Field(
        None,
        description="Configuration for custom algorithm",
    )

    # Performance tuning
    cache_routing_decisions: bool = Field(
        False,
        description="Cache routing decisions for performance",
    )
    cache_ttl_ms: int = Field(
        1000,
        description="Cache TTL in milliseconds",
        ge=100,
        le=60000,
    )

    def validate_weights(self) -> bool:
        """Validate that resource weights sum to approximately 1.0"""
        total = (
            self.cpu_weight
            + self.memory_weight
            + self.network_weight
            + self.disk_weight
        )
        return 0.99 <= total <= 1.01  # Allow small floating point errors
