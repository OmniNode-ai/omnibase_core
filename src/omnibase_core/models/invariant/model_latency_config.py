"""Configuration for latency invariant.

Enforces maximum response time constraints for
performance-sensitive operations.
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
    """

    model_config = ConfigDict(frozen=True, extra="ignore", from_attributes=True)

    max_ms: int = Field(
        ...,
        gt=0,
        description="Maximum latency in milliseconds",
    )


__all__ = ["ModelLatencyConfig"]
