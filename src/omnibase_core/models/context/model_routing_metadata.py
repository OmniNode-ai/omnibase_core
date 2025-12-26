# SPDX-FileCopyrightText: 2025 OmniNode Team
# SPDX-License-Identifier: Apache-2.0
"""
Routing metadata model for service routing and load balancing.

This module provides ModelRoutingMetadata, a typed model for routing-related
metadata that replaces untyped dict[str, ModelSchemaValue] fields. It captures
routing configuration for service discovery, load balancing, and traffic
management.

Thread Safety:
    ModelRoutingMetadata is immutable (frozen=True) after creation, making it
    thread-safe for concurrent read access from multiple threads or async tasks.

See Also:
    - omnibase_core.models.context.model_session_context: Session context
    - omnibase_core.models.context.model_http_request_metadata: HTTP request metadata
"""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

__all__ = ["ModelRoutingMetadata"]

# Type alias for load balance strategies
LoadBalanceStrategy = Literal["round_robin", "least_connections", "random", "weighted"]

# Valid load balance strategies (for validation error messages)
VALID_LOAD_BALANCE_STRATEGIES = frozenset(
    {"round_robin", "least_connections", "random", "weighted"}
)


class ModelRoutingMetadata(BaseModel):
    """Routing metadata for service routing and load balancing.

    Provides typed routing configuration for service discovery and traffic
    management. All fields have sensible defaults, allowing partial population
    based on routing requirements.

    Attributes:
        target_region: Target deployment region for geographic routing
            (e.g., "us-east-1", "eu-west-1"). None means no region preference.
        preferred_instance: Preferred service instance ID for routing.
            Used when a specific instance should handle the request.
        load_balance_strategy: Load balancing strategy to use. Must be one of:
            round_robin, least_connections, random, weighted.
        sticky_session_id: Session affinity ID for sticky routing. Requests
            with the same ID route to the same instance when possible.
        priority: Routing priority level. Higher values indicate higher
            priority. Used for priority-based routing decisions.
        weight: Routing weight for weighted load balancing strategies.
            Must be between 0.0 and 100.0 inclusive.
        timeout_override_ms: Override the default service timeout in
            milliseconds. None uses the default timeout.
        circuit_breaker_enabled: Whether circuit breaker is enabled for
            this route. Circuit breakers prevent cascading failures.

    Thread Safety:
        This model is frozen and immutable after creation.
        Safe for concurrent read access across threads.

    Example:
        >>> from omnibase_core.models.context import ModelRoutingMetadata
        >>>
        >>> routing = ModelRoutingMetadata(
        ...     target_region="us-east-1",
        ...     load_balance_strategy="weighted",
        ...     weight=2.5,
        ...     circuit_breaker_enabled=True,
        ... )
        >>> routing.target_region
        'us-east-1'
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    target_region: str | None = Field(
        default=None,
        description="Target deployment region (e.g., 'us-east-1')",
    )
    preferred_instance: str | None = Field(
        default=None,
        description="Preferred service instance ID for routing",
    )
    load_balance_strategy: LoadBalanceStrategy = Field(
        default="round_robin",
        description=(
            "Load balancing strategy. Valid values: round_robin, least_connections, "
            "random, weighted"
        ),
    )
    sticky_session_id: UUID | None = Field(
        default=None,
        description="UUID for session affinity in sticky routing",
    )
    priority: int = Field(
        default=0,
        description="Routing priority, higher values indicate higher priority",
    )
    weight: float = Field(
        default=1.0,
        ge=0.0,
        le=100.0,
        description="Routing weight for weighted load balancing strategies",
    )
    timeout_override_ms: int | None = Field(
        default=None,
        description=(
            "Override the default service timeout in milliseconds. "
            "Must be a positive integer when provided. None uses the default timeout."
        ),
    )
    circuit_breaker_enabled: bool = Field(
        default=True,
        description="Enable circuit breaker for this route",
    )

    @field_validator("timeout_override_ms")
    @classmethod
    def validate_timeout_positive(cls, v: int | None) -> int | None:
        """Validate that timeout_override_ms is positive when provided.

        Args:
            v: The timeout value in milliseconds to validate.

        Returns:
            The validated timeout value.

        Raises:
            ValueError: If the value is not positive when provided.
        """
        if v is not None and v <= 0:
            raise ValueError("timeout_override_ms must be positive")
        return v

    @field_validator("load_balance_strategy", mode="before")
    @classmethod
    def validate_load_balance_strategy(cls, v: str) -> LoadBalanceStrategy:
        """Validate that load_balance_strategy is a valid strategy.

        Args:
            v: The load balance strategy string to validate.

        Returns:
            The validated strategy as a Literal type.

        Raises:
            ValueError: If the value is not a valid load balance strategy.
        """
        if v not in VALID_LOAD_BALANCE_STRATEGIES:
            valid_strategies = ", ".join(sorted(VALID_LOAD_BALANCE_STRATEGIES))
            raise ValueError(
                f"Invalid load_balance_strategy '{v}': must be one of {valid_strategies}"
            )
        # Cast to LoadBalanceStrategy since we've validated it's a valid value
        return v  # type: ignore[return-value]
