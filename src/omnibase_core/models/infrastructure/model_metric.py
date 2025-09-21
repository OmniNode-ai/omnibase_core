"""
Metric model.

Individual metric model with universal type support.
Follows ONEX one-model-per-file naming conventions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ...enums.enum_metric_data_type import EnumMetricDataType


class ModelMetric(BaseModel):
    """Universal metric model for any supported type."""

    key: str = Field(..., description="Metric key")
    value: Any = Field(
        ..., description="Metric value - supports str, int, float, bool as determined by metric_type"
    )
    metric_type: EnumMetricDataType = Field(
        ..., description="Data type of metric (string, numeric, boolean)"
    )
    unit: str | None = Field(
        None, description="Unit of measurement (for numeric metrics)"
    )
    description: str | None = Field(None, description="Metric description")


# Export for use
__all__ = ["ModelMetric"]
