"""Configuration for latency invariant.

Enforces maximum response time constraints for
performance-sensitive operations.

Thread Safety:
    ModelLatencyConfig is immutable (frozen=True) after creation,
    making it thread-safe for concurrent read access.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelLatencyConfig(BaseModel):
    """Configuration for latency invariant.

    Enforces maximum response time constraints for performance-sensitive
    operations. Useful for ensuring AI model inference stays within
    acceptable response time limits.

    Attributes:
        max_ms: Maximum allowed latency in milliseconds. Must be greater
            than zero.

    Thread Safety:
        This model is immutable (frozen=True) after creation, making it
        thread-safe for concurrent read access. No synchronization is needed
        when sharing instances across threads.
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    max_ms: int = Field(
        ...,
        gt=0,
        description="Maximum latency in milliseconds",
    )


__all__ = ["ModelLatencyConfig"]
