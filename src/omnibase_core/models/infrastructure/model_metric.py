"""
Metric model.

Individual metric model with universal type support.
Follows ONEX one-model-per-file naming conventions.
"""

from typing import Union

from pydantic import BaseModel, Field


class ModelMetric(BaseModel):
    """Universal metric model for any supported type."""

    key: str = Field(..., description="Metric key")
    value: Union[str, int, float, bool] = Field(
        ..., description="Metric value (string, int, float, or bool)"
    )
    metric_type: str = Field(
        ..., description="Type of metric (string, numeric, boolean)"
    )
    unit: str | None = Field(
        None, description="Unit of measurement (for numeric metrics)"
    )
    description: str | None = Field(None, description="Metric description")


# Export for use
__all__ = ["ModelMetric"]
