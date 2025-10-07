from typing import Dict, Generic, TypedDict

from pydantic import Field

from omnibase_core.models.core.model_semver import ModelSemVer

"""
Metadata Management Models

Models for metadata collection, analytics, and field information.
"""

from typing import TYPE_CHECKING, Dict, TypedDict

if TYPE_CHECKING:
    # Use proper protocol type during type checking when available
    try:
        from omnibase_spi.protocols.types.protocol_core_types import (
            ProtocolSupportedMetadataType,
        )
    except ImportError:
        # Structured fallback type for development when SPI unavailable
        from omnibase_core.types.constraints import BasicValueType

        ProtocolSupportedMetadataType = BasicValueType
else:
    # Runtime fallback using structured type constraints

    ProtocolSupportedMetadataType = BasicValueType

from omnibase_core.models.common.model_numeric_value import ModelNumericValue

from .model_generic_metadata import ModelGenericMetadata
from .model_metadata_analytics_summary import ModelMetadataAnalyticsSummary
from .model_metadata_field_info import ModelMetadataFieldInfo
from .model_metadata_node_analytics import ModelMetadataNodeAnalytics
from .model_metadata_node_collection import ModelMetadataNodeCollection
from .model_metadata_node_info import ModelMetadataNodeInfo, ModelMetadataNodeType
from .model_metadata_usage_metrics import ModelMetadataUsageMetrics
from .model_metadata_value import ModelMetadataValue
from .model_node_info_summary import ModelNodeInfoSummary
from omnibase_core.models.core.model_semver import ModelSemVer
from .model_typed_dict_analytics_summary_data import TypedDictAnalyticsSummaryData
from .model_typed_dict_categorization_update_data import (
    TypedDictCategorizationUpdateData,
)
from .model_typed_dict_core_analytics import TypedDictCoreAnalytics
from .model_typed_dict_core_data import TypedDictCoreData
from .model_typed_dict_error_data import TypedDictErrorData
from .model_typed_dict_metadata_dict import TypedDictMetadataDict
from .model_typed_dict_node_core import TypedDictNodeCore
from .model_typed_dict_node_core_update_data import TypedDictNodeCoreUpdateData
from .model_typed_dict_node_info_summary_data import TypedDictNodeInfoSummaryData
from .model_typed_dict_performance_data import TypedDictPerformanceData
from .model_typed_dict_performance_update_data import (
    TypedDictPerformanceUpdateData,
)
from .model_typed_dict_quality_data import TypedDictQualityData
from .model_typed_dict_quality_update_data import TypedDictQualityUpdateData
from .model_typed_dict_timestamp_data import TypedDictTimestampData
from .model_typed_dict_timestamp_update_data import TypedDictTimestampUpdateData
from .model_typed_metrics import ModelTypedMetrics

__all__ = [
    "ModelGenericMetadata",
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
    "TypedDictCoreData",
    "TypedDictErrorData",
    "TypedDictNodeCore",
    "TypedDictNodeCoreUpdateData",
    "TypedDictNodeInfoSummaryData",
    "TypedDictPerformanceData",
    "TypedDictPerformanceUpdateData",
    "TypedDictQualityData",
    "TypedDictQualityUpdateData",
    "TypedDictTimestampData",
    "TypedDictTimestampUpdateData",
    "TypedDictMetadataDict",
    "ModelTypedMetrics",
    "ProtocolSupportedMetadataType",
]
