"""
Event Routing Model - ONEX Standards Compliant.

Model for event routing configuration in the ONEX event-driven architecture system.
"""

from pydantic import BaseModel, Field


class ModelRetryPolicy(BaseModel):
    """
    Strongly-typed retry policy configuration.

    Replaces dict[str, int | bool] pattern with proper type safety.
    """

    max_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10,
    )

    initial_delay_ms: int = Field(
        default=1000,
        description="Initial delay before first retry in milliseconds",
        ge=100,
        le=60000,
    )

    backoff_multiplier: int = Field(
        default=2,
        description="Exponential backoff multiplier",
        ge=1,
        le=10,
    )

    max_delay_ms: int = Field(
        default=30000,
        description="Maximum delay between retries in milliseconds",
        ge=1000,
        le=300000,
    )

    enabled: bool = Field(
        default=True,
        description="Whether retry policy is enabled",
    )

    retry_on_timeout: bool = Field(
        default=True,
        description="Whether to retry on timeout errors",
    )


class ModelEventRouting(BaseModel):
    """
    Event routing configuration.

    Defines routing strategies, target groups,
    and distribution policies for event delivery.
    """

    routing_strategy: str = Field(
        ...,
        description="Routing strategy (broadcast, unicast, multicast, topic)",
        min_length=1,
    )

    target_groups: list[str] = Field(
        default_factory=list,
        description="Target groups for event routing",
    )

    routing_rules: list[str] = Field(
        default_factory=list,
        description="Conditional routing rules",
    )

    load_balancing: str = Field(
        default="round_robin",
        description="Load balancing strategy for targets",
    )

    retry_policy: ModelRetryPolicy = Field(
        default_factory=ModelRetryPolicy,
        description="Strongly-typed retry policy for failed deliveries",
    )

    dead_letter_queue: str | None = Field(
        default=None,
        description="Dead letter queue for undeliverable events",
    )

    circuit_breaker_enabled: bool = Field(
        default=False,
        description="Enable circuit breaker for routing failures",
    )

    model_config = {
        "extra": "ignore",
        "use_enum_values": False,
        "validate_assignment": True,
    }
