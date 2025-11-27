from uuid import UUID

from pydantic import BaseModel, Field


class ModelContextMetadata(BaseModel):
    """Metadata for execution context."""

    # Request tracking
    request_id: UUID | None = Field(
        default=None, description="Unique request identifier"
    )
    request_source: str | None = Field(
        default=None, description="Source of the request"
    )
    request_timestamp: str | None = Field(default=None, description="Request timestamp")

    # Authentication context
    auth_method: str | None = Field(
        default=None, description="Authentication method used"
    )
    auth_provider: str | None = Field(
        default=None, description="Authentication provider"
    )
    permissions: list[str] = Field(
        default_factory=list,
        description="Granted permissions",
    )

    # Execution constraints
    max_memory_mb: int | None = Field(
        default=None, description="Maximum memory allowed"
    )
    max_cpu_percent: float | None = Field(
        default=None,
        description="Maximum CPU usage allowed",
    )
    priority_level: str | None = Field(
        default=None, description="Execution priority level"
    )

    # Feature flags
    enabled_features: list[str] = Field(
        default_factory=list,
        description="Enabled features",
    )
    disabled_features: list[str] = Field(
        default_factory=list,
        description="Disabled features",
    )
    experimental_features: list[str] = Field(
        default_factory=list,
        description="Experimental features",
    )

    # Monitoring and telemetry
    trace_flags: str | None = Field(
        default=None, description="Distributed tracing flags"
    )
    baggage_items: dict[str, str] = Field(
        default_factory=dict,
        description="OpenTelemetry baggage",
    )
    parent_span_id: UUID | None = Field(
        default=None,
        description="Parent span ID for tracing",
    )

    # Custom metadata for extensibility
    custom_tags: dict[str, str] = Field(default_factory=dict, description="Custom tags")
    custom_metrics: dict[str, float] | None = Field(
        default=None,
        description="Custom metrics",
    )
