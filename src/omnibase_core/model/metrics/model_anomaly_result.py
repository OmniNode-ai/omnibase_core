"""
Model for anomaly detection results in the metrics collector service.

This model defines the structure for detected anomalies in metrics.
"""

from pydantic import BaseModel


class ModelAnomalyResult(BaseModel):
    """Result of anomaly detection for a metric."""

    metric_key: str
    timestamp: str  # ISO format timestamp
    value: float
    expected_range: tuple[float, float]
    z_score: float
    severity: str  # "high" or "medium"
