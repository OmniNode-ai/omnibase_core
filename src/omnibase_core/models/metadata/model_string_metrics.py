"""
String metrics model.

Clean, strongly-typed model for string-based metrics.
Follows ONEX one-model-per-file naming conventions.
"""

from pydantic import BaseModel, Field


class ModelStringMetrics(BaseModel):
    """Model for string-based metrics."""

    name: str = Field(..., description="Metric name")
    value: str = Field(..., description="String metric value")


# Export the model
__all__ = ["ModelStringMetrics"]
