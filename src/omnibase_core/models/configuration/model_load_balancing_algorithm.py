"""
ModelLoadBalancingAlgorithm - Load balancing algorithm configuration

Load balancing algorithm model for defining how traffic should be distributed
across multiple nodes with algorithm-specific parameters and behavior.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.configuration.model_load_balancing_parameters import (
    ModelLoadBalancingParameters,
)


class ModelLoadBalancingAlgorithm(BaseModel):
    """
    Load balancing algorithm configuration model

    This model defines the algorithm used for distributing traffic across
    multiple nodes, including algorithm-specific parameters and behavior.
    """

    algorithm_name: str = Field(
        default=...,
        description="Load balancing algorithm name",
        pattern="^(round_robin|least_connections|weighted_round_robin|ip_hash|least_response_time|resource_based|custom)$",
    )

    display_name: str = Field(default=..., description="Human-readable algorithm name")

    description: str = Field(
        default=..., description="Algorithm description and behavior"
    )

    parameters: ModelLoadBalancingParameters = Field(
        default_factory=lambda: ModelLoadBalancingParameters(),
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
