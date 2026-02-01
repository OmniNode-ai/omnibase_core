"""Producer health status model for event bus health monitoring.

Thread Safety:
    ModelProducerHealthStatus instances are immutable (frozen=True) after creation,
    making them thread-safe for concurrent read access.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ModelProducerHealthStatus(BaseModel):
    """
    Health status for event bus producer.

    Represents the current health state of an event bus producer including
    connectivity status, latency metrics, pending message counts, and error information.

    Attributes:
        healthy: Overall health status of the producer.
        latency_ms: Current latency to the broker in milliseconds.
        connected: Whether the producer is currently connected to the broker.
        pending_messages: Number of messages pending delivery.
        last_error: Last error message if any.
        last_error_timestamp: Timestamp of the last error.
        messages_sent: Total number of messages sent since startup.
        messages_failed: Total number of failed message deliveries.
        broker_count: Number of connected brokers.
    """

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    healthy: bool = Field(
        ...,
        description="Overall health status of the producer",
    )
    latency_ms: float | None = Field(
        default=None,
        description="Current latency to the broker in milliseconds",
        ge=0.0,
    )
    connected: bool = Field(
        ...,
        description="Whether the producer is currently connected to the broker",
    )
    pending_messages: int = Field(
        default=0,
        description="Number of messages pending delivery",
        ge=0,
    )
    last_error: str | None = Field(
        default=None,
        description="Last error message if any",
        max_length=2000,
    )
    last_error_timestamp: datetime | None = Field(
        default=None,
        description="Timestamp of the last error",
    )
    messages_sent: int = Field(
        default=0,
        description="Total number of messages sent since startup",
        ge=0,
    )
    messages_failed: int = Field(
        default=0,
        description="Total number of failed message deliveries",
        ge=0,
    )
    broker_count: int = Field(
        default=0,
        description="Number of connected brokers",
        ge=0,
    )

    @field_validator("last_error")
    @classmethod
    def validate_last_error(cls, v: str | None) -> str | None:
        """Strip whitespace from error message."""
        if v is None:
            return None
        v = v.strip()
        return v if v else None

    def is_healthy(self) -> bool:
        """Check if the producer is healthy."""
        return self.healthy

    def is_connected(self) -> bool:
        """Check if the producer is connected."""
        return self.connected

    def has_pending_messages(self) -> bool:
        """Check if there are pending messages."""
        return self.pending_messages > 0

    def has_recent_error(self) -> bool:
        """Check if there is a recent error."""
        return self.last_error is not None

    def get_success_rate(self) -> float:
        """Calculate message delivery success rate."""
        total = self.messages_sent + self.messages_failed
        if total == 0:
            return 1.0
        return self.messages_sent / total

    def get_failure_rate(self) -> float:
        """Calculate message delivery failure rate."""
        return 1.0 - self.get_success_rate()

    def get_latency_category(self) -> str:
        """Categorize latency performance."""
        if self.latency_ms is None:
            return "unknown"
        if self.latency_ms < 10.0:
            return "excellent"
        if self.latency_ms < 50.0:
            return "good"
        if self.latency_ms < 100.0:
            return "acceptable"
        if self.latency_ms < 500.0:
            return "slow"
        return "very_slow"

    def is_latency_concerning(self) -> bool:
        """Check if latency is at a concerning level."""
        category = self.get_latency_category()
        return category in ["slow", "very_slow"]

    def get_health_summary(self) -> str:
        """Get human-readable health summary."""
        status = "HEALTHY" if self.healthy else "UNHEALTHY"
        connection = "connected" if self.connected else "disconnected"
        return (
            f"{status}: {connection}, "
            f"pending={self.pending_messages}, "
            f"success_rate={self.get_success_rate():.1%}"
        )

    def needs_attention(self) -> bool:
        """Check if producer needs attention."""
        if not self.healthy:
            return True
        if not self.connected:
            return True
        if self.pending_messages > 1000:
            return True
        if self.get_failure_rate() > 0.1:
            return True
        if self.is_latency_concerning():
            return True
        return False

    def get_status_dict(self) -> dict[str, str | int | float | bool | None]:
        """Get status as a dictionary for logging/monitoring."""
        return {
            "healthy": self.healthy,
            "connected": self.connected,
            "latency_ms": self.latency_ms,
            "latency_category": self.get_latency_category(),
            "pending_messages": self.pending_messages,
            "messages_sent": self.messages_sent,
            "messages_failed": self.messages_failed,
            "success_rate": self.get_success_rate(),
            "broker_count": self.broker_count,
            "has_error": self.has_recent_error(),
            "needs_attention": self.needs_attention(),
        }

    @classmethod
    def create_healthy(
        cls,
        latency_ms: float | None = None,
        pending_messages: int = 0,
        messages_sent: int = 0,
        broker_count: int = 1,
    ) -> "ModelProducerHealthStatus":
        """Create a healthy producer status."""
        return cls(
            healthy=True,
            latency_ms=latency_ms,
            connected=True,
            pending_messages=pending_messages,
            last_error=None,
            last_error_timestamp=None,
            messages_sent=messages_sent,
            messages_failed=0,
            broker_count=broker_count,
        )

    @classmethod
    def create_unhealthy(
        cls,
        error_message: str,
        connected: bool = False,
        pending_messages: int = 0,
        messages_sent: int = 0,
        messages_failed: int = 0,
    ) -> "ModelProducerHealthStatus":
        """Create an unhealthy producer status."""
        return cls(
            healthy=False,
            latency_ms=None,
            connected=connected,
            pending_messages=pending_messages,
            last_error=error_message,
            last_error_timestamp=datetime.now(UTC),
            messages_sent=messages_sent,
            messages_failed=messages_failed,
            broker_count=0 if not connected else 1,
        )

    @classmethod
    def create_disconnected(
        cls,
        error_message: str | None = None,
    ) -> "ModelProducerHealthStatus":
        """Create a disconnected producer status."""
        return cls(
            healthy=False,
            latency_ms=None,
            connected=False,
            pending_messages=0,
            last_error=error_message or "Producer disconnected from broker",
            last_error_timestamp=datetime.now(UTC),
            messages_sent=0,
            messages_failed=0,
            broker_count=0,
        )


__all__ = ["ModelProducerHealthStatus"]
