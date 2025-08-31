"""
ONEX Event Bus Factory Model

Pydantic model for hybrid event bus factory configuration and capabilities.
Follows ONEX conventions: CamelCase model name, one model per file.
"""

from pydantic import BaseModel, Field


class ModelEventBusFactory(BaseModel):
    """
    ONEX-compliant model for hybrid event bus factory configuration.

    Represents the configuration and capabilities of a hybrid event bus
    that supports Kafka-first with EventBus fallback strategy.
    """

    kafka_bootstrap_servers: str | None = Field(
        default=None,
        description="Kafka bootstrap servers configuration",
    )

    event_bus_url: str | None = Field(
        default="http://onex-event-bus:8080",
        description="EventBus service URL for fallback",
    )

    fallback_enabled: bool = Field(
        default=True,
        description="Whether to enable EventBus fallback when Kafka fails",
    )

    kafka_producer_config: dict[str, object] = Field(
        default_factory=dict,
        description="Additional Kafka producer configuration",
    )

    event_bus_type: str | None = Field(
        default=None,
        description="Type of event bus instance created",
    )

    capabilities: list[str] = Field(
        default_factory=list,
        description="List of supported capabilities",
    )

    connection_timeout: int = Field(
        default=10,
        description="Connection timeout in seconds",
    )

    retry_attempts: int = Field(
        default=3,
        description="Number of retry attempts for failed connections",
    )

    class Config:
        """Pydantic model configuration."""

        frozen = True
        extra = "forbid"
        validate_assignment = True
