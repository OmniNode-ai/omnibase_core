"""
Boolean metrics model.

Clean, strongly-typed model for boolean metrics.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field


class ModelBooleanMetrics(BaseModel):
    """Model for boolean metrics."""

    name: str = Field(..., description="Metric name")
    value: bool = Field(..., description="Boolean metric value")


# Export the model
__all__ = ["ModelBooleanMetrics"]
