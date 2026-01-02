"""Configuration for latency invariant.

Enforces maximum response time constraints for
performance-sensitive operations.
"""

from pydantic import BaseModel, Field


class ModelLatencyConfig(BaseModel):
    """Configuration for latency invariant.

    Enforces maximum response time constraints for
    performance-sensitive operations.
    """

    max_ms: int = Field(
        ...,
        gt=0,
        description="Maximum latency in milliseconds",
    )


__all__ = ["ModelLatencyConfig"]
