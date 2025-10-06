from pydantic import BaseModel, Field


class ModelEventRouting(BaseModel):
    """
    Event routing configuration.

    Defines routing strategies, target groups,
    and distribution policies for event delivery.
    """

    routing_strategy: str = Field(
        default=...,
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
