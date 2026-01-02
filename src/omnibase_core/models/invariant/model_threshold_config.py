"""Configuration for threshold invariant.

Validates that a numeric metric falls within specified bounds.
"""

from pydantic import BaseModel, Field


class ModelThresholdConfig(BaseModel):
    """Configuration for threshold invariant.

    Validates that a numeric metric falls within specified bounds.
    At least one of min_value or max_value should be set for
    meaningful validation.
    """

    metric_name: str = Field(
        ...,
        description="Name of metric to check (e.g., 'confidence', 'token_count')",
    )
    min_value: float | None = Field(
        default=None,
        description="Minimum allowed value (inclusive)",
    )
    max_value: float | None = Field(
        default=None,
        description="Maximum allowed value (inclusive)",
    )


__all__ = ["ModelThresholdConfig"]
