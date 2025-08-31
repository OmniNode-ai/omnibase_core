"""
ModelLoadBalancingAlgorithm - Load balancing algorithm configuration

Load balancing algorithm model for defining how traffic should be distributed
across multiple nodes with algorithm-specific parameters and behavior.
"""

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


class ModelLoadBalancingAlgorithm(BaseModel):
    """
    Load balancing algorithm configuration model

    This model defines the algorithm used for distributing traffic across
    multiple nodes, including algorithm-specific parameters and behavior.
    """

    algorithm_name: str = Field(
        ...,
        description="Load balancing algorithm name",
        pattern="^(round_robin|least_connections|weighted_round_robin|ip_hash|least_response_time|resource_based|custom)$",
    )

    display_name: str = Field(..., description="Human-readable algorithm name")

    description: str = Field(..., description="Algorithm description and behavior")

    parameters: ModelLoadBalancingParameters = Field(
        default_factory=ModelLoadBalancingParameters,
        description="Algorithm-specific parameters",
    )

    supports_weights: bool = Field(
        default=False,
        description="Whether algorithm supports node weights",
    )

    supports_priorities: bool = Field(
        default=False,
        description="Whether algorithm supports node priorities",
    )

    supports_health_checks: bool = Field(
        default=True,
        description="Whether algorithm considers health status",
    )

    stateful: bool = Field(
        default=False,
        description="Whether algorithm maintains state between requests",
    )

    session_affinity_support: bool = Field(
        default=False,
        description="Whether algorithm supports session affinity",
    )

    performance_characteristics: dict[str, str] = Field(
        default_factory=dict,
        description="Performance characteristics (latency, throughput, fairness)",
    )

    def is_simple_algorithm(self) -> bool:
        """Check if this is a simple stateless algorithm"""
        return not self.stateful and self.algorithm_name in ["round_robin", "random"]

    def requires_node_metrics(self) -> bool:
        """Check if algorithm requires node performance metrics"""
        return self.algorithm_name in [
            "least_connections",
            "least_response_time",
            "resource_based",
        ]

    def supports_custom_parameters(self) -> bool:
        """Check if algorithm supports custom parameters"""
        return (
            self.algorithm_name == "custom"
            or self.parameters.custom_algorithm_class is not None
        )

    def get_parameter(self, key: str, default: Any = None) -> Any:
        """Get algorithm-specific parameter value"""
        return getattr(self.parameters, key, default)

    def set_parameter(self, key: str, value: Any) -> None:
        """Set algorithm-specific parameter value"""
        setattr(self.parameters, key, value)

    @classmethod
    def create_round_robin(cls) -> "ModelLoadBalancingAlgorithm":
        """Create round-robin load balancing algorithm"""
        return cls(
            algorithm_name="round_robin",
            display_name="Round Robin",
            description="Distributes requests sequentially across all healthy nodes",
            supports_weights=False,
            supports_priorities=False,
            stateful=True,  # Maintains position counter
            performance_characteristics={
                "latency": "consistent",
                "throughput": "high",
                "fairness": "excellent",
            },
        )

    @classmethod
    def create_least_connections(cls) -> "ModelLoadBalancingAlgorithm":
        """Create least-connections load balancing algorithm"""
        return cls(
            algorithm_name="least_connections",
            display_name="Least Connections",
            description="Routes requests to node with fewest active connections",
            supports_weights=True,
            supports_priorities=True,
            stateful=False,  # Uses real-time metrics
            performance_characteristics={
                "latency": "adaptive",
                "throughput": "high",
                "fairness": "good",
            },
        )

    @classmethod
    def create_weighted_round_robin(cls) -> "ModelLoadBalancingAlgorithm":
        """Create weighted round-robin load balancing algorithm"""
        return cls(
            algorithm_name="weighted_round_robin",
            display_name="Weighted Round Robin",
            description="Distributes requests based on node weights in round-robin fashion",
            supports_weights=True,
            supports_priorities=False,
            stateful=True,  # Maintains weighted position
            performance_characteristics={
                "latency": "consistent",
                "throughput": "high",
                "fairness": "weighted",
            },
        )

    @classmethod
    def create_ip_hash(cls) -> "ModelLoadBalancingAlgorithm":
        """Create IP hash load balancing algorithm"""
        return cls(
            algorithm_name="ip_hash",
            display_name="IP Hash",
            description="Routes requests based on client IP hash for session affinity",
            supports_weights=False,
            supports_priorities=False,
            stateful=False,  # Hash-based, no state
            session_affinity_support=True,
            performance_characteristics={
                "latency": "consistent",
                "throughput": "medium",
                "fairness": "deterministic",
            },
        )

    @classmethod
    def create_least_response_time(cls) -> "ModelLoadBalancingAlgorithm":
        """Create least response time load balancing algorithm"""
        return cls(
            algorithm_name="least_response_time",
            display_name="Least Response Time",
            description="Routes requests to node with lowest average response time",
            supports_weights=True,
            supports_priorities=True,
            stateful=False,  # Uses real-time metrics
            performance_characteristics={
                "latency": "optimized",
                "throughput": "adaptive",
                "fairness": "performance_based",
            },
        )

    @classmethod
    def create_resource_based(cls) -> "ModelLoadBalancingAlgorithm":
        """Create resource-based load balancing algorithm"""
        return cls(
            algorithm_name="resource_based",
            display_name="Resource Based",
            description="Routes requests based on node resource utilization (CPU, memory)",
            supports_weights=True,
            supports_priorities=True,
            stateful=False,  # Uses real-time metrics
            parameters=ModelLoadBalancingParameters(
                cpu_weight=0.6,
                memory_weight=0.3,
                network_weight=0.1,
                disk_weight=0.0,  # Explicitly set to 0 for backward compatibility
            ),
            performance_characteristics={
                "latency": "adaptive",
                "throughput": "optimized",
                "fairness": "resource_aware",
            },
        )

    @classmethod
    def create_custom(
        cls,
        name: str,
        display_name: str,
        description: str,
        parameters: ModelLoadBalancingParameters | None = None,
    ) -> "ModelLoadBalancingAlgorithm":
        """Create custom load balancing algorithm"""
        return cls(
            algorithm_name="custom",
            display_name=display_name,
            description=description,
            parameters=parameters or ModelLoadBalancingParameters(),
            supports_weights=True,
            supports_priorities=True,
            supports_health_checks=True,
            performance_characteristics={
                "latency": "custom",
                "throughput": "custom",
                "fairness": "custom",
            },
        )
