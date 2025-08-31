"""
Circuit Breaker Metadata Model

Type-safe circuit breaker metadata that replaces Dict[str, Any] usage.
"""

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_custom_fields import ModelCustomFields


class ModelCircuitBreakerMetadata(BaseModel):
    """
    Type-safe circuit breaker metadata.

    Provides structured metadata for circuit breaker monitoring and diagnostics.
    """

    # Failure tracking
    last_error_message: str | None = Field(
        None,
        description="Last error message that triggered the circuit",
    )

    last_error_code: str | None = Field(
        None,
        description="Last error code encountered",
    )

    error_categories: dict[str, int] = Field(
        default_factory=dict,
        description="Count of errors by category",
    )

    # Performance metrics
    average_response_time_ms: float | None = Field(
        None,
        description="Average response time in current window",
    )

    p95_response_time_ms: float | None = Field(
        None,
        description="95th percentile response time",
    )

    p99_response_time_ms: float | None = Field(
        None,
        description="99th percentile response time",
    )

    # Recovery information
    recovery_attempts: int = Field(0, description="Number of recovery attempts made")

    last_recovery_timestamp: str | None = Field(
        None,
        description="Timestamp of last recovery attempt (ISO format)",
    )

    recovery_success_rate: float | None = Field(
        None,
        description="Success rate of recovery attempts",
        ge=0.0,
        le=1.0,
    )

    # Service information
    service_name: str | None = Field(
        None,
        description="Name of the service protected by this circuit breaker",
    )

    service_endpoint: str | None = Field(
        None,
        description="Endpoint being protected",
    )

    dependency_chain: list[str] = Field(
        default_factory=list,
        description="Chain of dependencies affected",
    )

    # Alert information
    alerts_triggered: int = Field(0, description="Number of alerts triggered")

    last_alert_timestamp: str | None = Field(
        None,
        description="Timestamp of last alert (ISO format)",
    )

    alert_channels_notified: list[str] = Field(
        default_factory=list,
        description="Alert channels that were notified",
    )

    # State history
    state_transitions: list[dict[str, str]] = Field(
        default_factory=list,
        description="History of state transitions",
    )

    # Custom metadata for extensibility
    custom_fields: ModelCustomFields | None = Field(
        None,
        description="Additional custom metadata",
    )
