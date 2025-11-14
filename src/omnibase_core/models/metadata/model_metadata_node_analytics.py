from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from pydantic import Field

from omnibase_core.models.primitives.model_semver import ModelSemVer

"""
Metadata Node Analytics Model.

Analytics and metrics for metadata node collections with
performance tracking and health monitoring.
"""

from datetime import UTC
from uuid import UUID

from pydantic import BaseModel

from omnibase_core.enums.enum_collection_purpose import EnumCollectionPurpose
from omnibase_core.enums.enum_metadata_node_status import EnumMetadataNodeStatus
from omnibase_core.enums.enum_metadata_node_type import EnumMetadataNodeType
from omnibase_core.models.common.model_schema_value import ModelSchemaValue
from omnibase_core.models.infrastructure.model_metrics_data import ModelMetricsData
from omnibase_core.models.infrastructure.model_value import ModelValue
from omnibase_core.types.constraints import BasicValueType
from omnibase_core.types.typed_dict_metadata_dict import TypedDictMetadataDict
from omnibase_core.utils.util_uuid_utilities import uuid_from_string

from .model_metadata_analytics_summary import ModelMetadataAnalyticsSummary
from .model_metadata_value import ModelMetadataValue
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
