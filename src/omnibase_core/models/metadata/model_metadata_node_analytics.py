"""
Metadata Node Analytics Model.

Analytics and metrics for metadata node collections with
performance tracking and health monitoring.
"""

from __future__ import annotations

from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_metrics_data import ModelMetricsData

from .model_metadatanodeanalytics import ModelMetadataNodeAnalytics


def _create_default_metrics_data() -> ModelMetricsData:
    """Create default ModelMetricsData with proper typing."""
    return ModelMetricsData(
        collection_id=None,
        collection_display_name=ModelSchemaValue.from_value("custom_analytics"),
    )


# Export for use
__all__ = [
    "ModelMetadataNodeAnalytics",
]
