"""
Metadata Management Models

Models for metadata collection, analytics, and field information.
"""

# FIXME: ProtocolSupportedMetadataType not available in omnibase_spi
# from omnibase_spi.protocols.types import ProtocolSupportedMetadataType
# Temporarily using Protocol metadata as replacement
# from omnibase_spi.protocols.types import (
#     ProtocolMetadata as ProtocolSupportedMetadataType,
# )

# Temporary placeholder for missing omnibase_spi module
ProtocolSupportedMetadataType = dict[str, object]

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
from .model_semver import ModelSemVer
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
    "ModelTypedMetrics",
    "ProtocolSupportedMetadataType",
]
