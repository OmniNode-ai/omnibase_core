"""
Custom Metrics Model

Strongly typed model for custom metrics to replace Dict[str, Any] usage.
Follows ONEX canonical patterns with zero tolerance for Any types.

Re-exports ModelCustomMetrics and ModelMetricValue for convenient imports.
"""

from omnibase_core.models.discovery.model_custommetrics import ModelCustomMetrics
from omnibase_core.models.discovery.model_metric_value import ModelMetricValue

__all__ = ["ModelCustomMetrics", "ModelMetricValue"]
