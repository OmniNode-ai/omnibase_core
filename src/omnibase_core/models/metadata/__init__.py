"""
Metadata Management Models

Models for metadata collection, analytics, and field information.
"""

from omnibase_core.models.common.model_numeric_value import ModelNumericValue
from omnibase_core.models.primitives.model_semver import ModelSemVer

# Import ProtocolSupportedMetadataType from Core-native protocols
from omnibase_core.protocols import ProtocolSupportedMetadataType
from omnibase_core.types.typed_dict_analytics_summary_data import (
    TypedDictAnalyticsSummaryData,
)
from omnibase_core.types.typed_dict_categorization_update_data import (
    TypedDictCategorizationUpdateData,
)
from omnibase_core.types.typed_dict_core_analytics import TypedDictCoreAnalytics
from omnibase_core.types.typed_dict_node_core import TypedDictNodeCore
from omnibase_core.types.typed_dict_node_info_summary_data import (
    TypedDictNodeInfoSummaryData,
)
from omnibase_core.types.typed_dict_quality_data import TypedDictQualityData
from omnibase_core.types.typed_dict_timestamp_update_data import (
    TypedDictTimestampUpdateData,
)

from .model_metadata_analytics_summary import ModelMetadataAnalyticsSummary
from .model_metadata_field_info import ModelMetadataFieldInfo
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_collection import ModelMetadataNodeCollection
from .model_metadata_node_info import ModelMetadataNodeInfo, ModelMetadataNodeType
from .model_metadata_usage_metrics import ModelMetadataUsageMetrics
from .model_metadata_value import ModelMetadataValue
from .model_node_info_summary import ModelNodeInfoSummary
from .model_typed_metrics import ModelTypedMetrics

__all__ = [
    "ModelMetadataAnalyticsSummary",
    "ModelMetadataFieldInfo",
    "ModelMetadataNodeAnalytics",
    "ModelMetadataNodeCollection",
    "ModelMetadataNodeInfo",
    "ModelMetadataNodeType",
    "ModelMetadataUsageMetrics",
    "ModelMetadataValue",
    "ModelNodeInfoSummary",
    "ModelNumericValue",
    "ModelSemVer",
    "TypedDictAnalyticsSummaryData",
    "TypedDictCategorizationUpdateData",
    "TypedDictCoreAnalytics",
    "TypedDictNodeCore",
    "TypedDictNodeInfoSummaryData",
    "TypedDictQualityData",
    "TypedDictTimestampUpdateData",
    "ModelTypedMetrics",
    "ProtocolSupportedMetadataType",
]
