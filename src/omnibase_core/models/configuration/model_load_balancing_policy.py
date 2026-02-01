"""
ModelLoadBalancingPolicy - Comprehensive load balancing policy configuration

Load balancing policy model that combines algorithm selection, node weights,
health checks, session affinity, and circuit breaker configurations.
"""

from typing import TYPE_CHECKING
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from omnibase_core.models.services.model_node_weights import ModelNodeWeights

from omnibase_core.models.health.model_health_check_config import ModelHealthCheckConfig
from omnibase_core.types import SerializedDict

from .model_circuit_breaker import ModelCircuitBreaker
from .model_load_balancing_algorithm import ModelLoadBalancingAlgorithm
from .model_retry_policy import ModelRetryPolicy
from .model_session_affinity import ModelSessionAffinity


class ModelLoadBalancingPolicy(BaseModel):
    """
    Comprehensive load balancing policy configuration

    This model defines complete load balancing behavior including algorithm
    selection, node weights, health monitoring, session affinity, fault tolerance,
    and retry handling for distributed node environments.
    """

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    policy_name: str = Field(
        default=...,
        description="Load balancing policy identifier",
        pattern="^[a-z][a-z0-9_-]*$",
    )

    display_name: str = Field(default=..., description="Human-readable policy name")

    description: str | None = Field(
        default=None,
        description="Policy description and usage guidelines",
    )

    enabled: bool = Field(default=True, description="Whether this policy is enabled")

    algorithm: ModelLoadBalancingAlgorithm = Field(
        default=...,
        description="Load balancing algorithm configuration",
    )

    node_weights: "ModelNodeWeights | None" = Field(
        default=None,
        description="Node weights for weighted algorithms",
    )

    health_check: ModelHealthCheckConfig = Field(
        default=...,
        description="Health check configuration",
    )

    session_affinity: ModelSessionAffinity | None = Field(
        default=None,
        description="Session affinity configuration",
    )

    circuit_breaker: ModelCircuitBreaker = Field(
        default_factory=lambda: ModelCircuitBreaker(),
        description="Circuit breaker configuration",
    )

    retry_policy: ModelRetryPolicy = Field(
        default_factory=lambda: ModelRetryPolicy(),
        description="Retry policy for failed requests",
    )

    excluded_nodes: list[UUID] = Field(
        default_factory=list,
        description="Nodes to exclude from load balancing",
    )

    preferred_nodes: list[UUID] = Field(
        default_factory=list,
        description="Preferred nodes for routing",
    )

    prefer_local: bool = Field(
        default=True,
        description="Prefer local nodes when available",
    )

    max_nodes_per_request: int | None = Field(
        default=None,
        description="Maximum nodes to consider per request",
        ge=1,
        le=100,
    )

    enable_metrics_collection: bool = Field(
        default=True,
        description="Whether to collect load balancing metrics",
    )

    enable_request_logging: bool = Field(
        default=False,
        description="Whether to log individual requests",
    )

    priority: int = Field(
        default=0,
        description="Policy priority (higher = preferred)",
        ge=0,
        le=100,
    )

    def is_node_excluded(self, node_id: UUID) -> bool:
        """Check if a node is excluded from load balancing"""
        return node_id in self.excluded_nodes

    def is_node_preferred(self, node_id: UUID) -> bool:
        return node_id in self.preferred_nodes

    def get_effective_nodes(self, available_nodes: list[UUID]) -> list[UUID]:
        """Get effective nodes after applying exclusions and preferences"""
        # Remove excluded nodes
        effective_nodes = [
            node for node in available_nodes if not self.is_node_excluded(node)
        ]

        # Apply preferred nodes if any are available
        if self.preferred_nodes:
            preferred_available = [
                node for node in effective_nodes if self.is_node_preferred(node)
            ]
            if preferred_available:
                effective_nodes = preferred_available

        # Apply max nodes limit
        if (
            self.max_nodes_per_request
            and len(effective_nodes) > self.max_nodes_per_request
        ):
            effective_nodes = effective_nodes[: self.max_nodes_per_request]

        return effective_nodes

    def should_use_weights(self) -> bool:
        """Check if node weights should be used"""
        return (
            self.algorithm.supports_weights
            and self.node_weights is not None
            and len(self.node_weights.weights) > 0
        )

    def should_use_session_affinity(self) -> bool:
        """Check if session affinity should be used"""
        return (
            self.session_affinity is not None
            and self.session_affinity.enabled
            and self.algorithm.session_affinity_support
        )

    def should_use_circuit_breaker(self) -> bool:
        """Check if circuit breaker should be used"""
        return self.circuit_breaker.enabled

    def get_node_weight(self, node_id: UUID) -> float:
        if not self.should_use_weights() or self.node_weights is None:
            return 1.0
        return self.node_weights.get_weight(node_id)

    def validate_configuration(self) -> list[str]:
        """Validate policy configuration and return any issues"""
        issues = []

        if not self.enabled:
            issues.append("Policy is disabled")

        if self.should_use_weights() and not self.algorithm.supports_weights:
            issues.append(
                "Algorithm does not support weights but weights are configured",
            )

        if (
            self.should_use_session_affinity()
            and not self.algorithm.session_affinity_support
        ):
            issues.append(
                "Algorithm does not support session affinity but affinity is configured",
            )

        if self.session_affinity and self.session_affinity.enabled:
            if (
                self.session_affinity.affinity_type == "cookie"
                and not self.session_affinity.cookie_name
            ):
                issues.append("Cookie affinity enabled but no cookie name specified")
            elif (
                self.session_affinity.affinity_type == "header"
                and not self.session_affinity.header_name
            ):
                issues.append("Header affinity enabled but no header name specified")

        if (
            self.health_check.timeout_seconds
            >= self.health_check.check_interval_seconds
        ):
            issues.append("Health check timeout should be less than check interval")

        return issues

    def get_configuration_summary(self) -> SerializedDict:
        """Get human-readable configuration summary"""
        return {
            "policy_name": self.policy_name,
            "algorithm": self.algorithm.display_name,
            "uses_weights": self.should_use_weights(),
            "uses_session_affinity": self.should_use_session_affinity(),
            "uses_circuit_breaker": self.should_use_circuit_breaker(),
            "health_checks_enabled": self.health_check.enabled,
            "excluded_nodes_count": len(self.excluded_nodes),
            "preferred_nodes_count": len(self.preferred_nodes),
            "configuration_issues": len(self.validate_configuration()),
        }
