"""
Custom Metrics Model

Strongly typed model for custom metrics to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with strict typing - no Any types allowed.

Re-exports ModelCustomMetrics, ModelMetricValue, AnyMetricValue, and MetricValueT
for convenient imports.
"""

from omnibase_core.models.discovery.model_custommetrics import ModelCustomMetrics
from omnibase_core.models.discovery.model_metric_value import (
    AnyMetricValue,
    MetricValueT,
    ModelMetricValue,
)

__all__ = ["ModelCustomMetrics", "ModelMetricValue", "AnyMetricValue", "MetricValueT"]
