"""
Model for metric metadata in the metrics collector service.

This model defines the structure for metric metadata including type, unit, and description.
"""

from pydantic import BaseModel

from omnibase_core.model.progress.model_progress_report import MetricType


class ModelMetricMetadata(BaseModel):
    """Metadata for a metric definition."""

    type: MetricType
    unit: str
    description: str
