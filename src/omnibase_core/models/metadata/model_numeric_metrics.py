"""
Numeric metrics model.

Clean, strongly-typed model for numeric metrics.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field


class ModelNumericMetrics(BaseModel):
    """Model for numeric metrics."""

    name: str = Field(..., description="Metric name")
    value: int | float = Field(..., description="Numeric metric value")


# Export the model
__all__ = ["ModelNumericMetrics"]
