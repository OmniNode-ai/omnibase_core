"""
Event Bus Service Configuration Model.

Configuration model for EventBusService behavior and settings.

Author: ONEX Framework Team
"""

from pydantic import BaseModel, Field


class ModelEventBusConfig(BaseModel):
    """
    Configuration model for Event Bus Service operations.

    Controls event emission, introspection publishing, pattern management,
    and event bus connection behavior.
    """

    # Event emission configuration
    enable_lifecycle_events: bool = Field(
        default=True,
        description="Enable NODE_START, NODE_SUCCESS, NODE_FAILURE event emission",
    )

    enable_introspection_publishing: bool = Field(
        default=True,
        description="Enable automatic introspection event publishing for service discovery",
    )

    # Event bus connection configuration
    auto_resolve_event_bus: bool = Field(
        default=True,
        description="Automatically resolve event bus from environment if not provided",
    )

    event_bus_url: str | None = Field(
        default=None,
        description="Event bus URL override (defaults to EVENT_BUS_URL environment variable)",
    )

    connection_timeout_seconds: int = Field(
        default=30,
        description="Timeout for event bus connection attempts",
    )

    # Event pattern configuration
    use_contract_event_patterns: bool = Field(
        default=True,
        description="Extract event patterns from contract YAML first",
    )

    fallback_to_node_name_patterns: bool = Field(
        default=True,
        description="Fall back to node name-based patterns if no contract patterns found",
    )

    default_event_patterns: list[str] = Field(
        default_factory=lambda: [
            "*.discovery.*",
            "core.discovery.introspection_request",
        ],
        description="Default event patterns if no other patterns can be determined",
    )

    # Publishing configuration
    enable_event_retry: bool = Field(
        default=True,
        description="Enable retry logic for failed event publishing",
    )

    max_retry_attempts: int = Field(
        default=3,
        description="Maximum number of retry attempts for event publishing",
    )

    retry_delay_seconds: float = Field(
        default=1.0,
        description="Delay between retry attempts",
    )

    # Envelope configuration
    use_broadcast_envelopes: bool = Field(
        default=True,
        description="Wrap events in broadcast envelopes for proper routing",
    )

    include_source_metadata: bool = Field(
        default=True,
        description="Include source node metadata in event envelopes",
    )

    # Logging and monitoring
    enable_event_logging: bool = Field(
        default=True,
        description="Enable structured logging for event operations",
    )

    log_event_payloads: bool = Field(
        default=False,
        description="Include event payloads in log output (may contain sensitive data)",
    )

    # Performance configuration
    enable_event_caching: bool = Field(
        default=True,
        description="Enable caching for frequently created events",
    )

    cache_max_size: int = Field(
        default=100,
        description="Maximum number of events to cache",
    )

    # Error handling configuration
    fail_fast_on_validation_errors: bool = Field(
        default=True,
        description="Fail immediately on event validation errors",
    )

    suppress_connection_errors: bool = Field(
        default=False,
        description="Suppress connection errors and continue without event bus",
    )

    # Environment variable mappings
    environment_variable_mappings: dict[str, str] = Field(
        default_factory=lambda: {
            "EVENT_BUS_URL": "event_bus_url",
            "EVENT_BUS_TIMEOUT": "connection_timeout_seconds",
            "ENABLE_EVENT_LOGGING": "enable_event_logging",
        },
        description="Mapping of environment variables to config fields",
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
        use_enum_values = True
