# SPDX-FileCopyrightText: 2025 OmniNode.ai Inc.
# SPDX-License-Identifier: MIT

"""
Metadata Management Models

Models for metadata collection, analytics, and field information.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:
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


# PEP 562 lazy re-exports (OMN-17427). Importing this package used to import
# every module re-exported above, and Python runs a package's __init__ before
# any of its submodules, so even one leaf import paid for the whole subtree.
# Names now load on first access; ``from <package> import Name`` and
# ``<package>.Name`` behave as before.
_LAZY_IMPORTS: dict[str, tuple[str, str | None]] = {
    "ModelNumericValue": (
        "omnibase_core.models.common.model_numeric_value",
        "ModelNumericValue",
    ),
    "ModelSemVer": ("omnibase_core.models.primitives.model_semver", "ModelSemVer"),
    "ProtocolSupportedMetadataType": (
        "omnibase_core.protocols",
        "ProtocolSupportedMetadataType",
    ),
    "TypedDictAnalyticsSummaryData": (
        "omnibase_core.types.typed_dict_analytics_summary_data",
        "TypedDictAnalyticsSummaryData",
    ),
    "TypedDictCategorizationUpdateData": (
        "omnibase_core.types.typed_dict_categorization_update_data",
        "TypedDictCategorizationUpdateData",
    ),
    "TypedDictCoreAnalytics": (
        "omnibase_core.types.typed_dict_core_analytics",
        "TypedDictCoreAnalytics",
    ),
    "TypedDictNodeCore": (
        "omnibase_core.types.typed_dict_node_core",
        "TypedDictNodeCore",
    ),
    "TypedDictNodeInfoSummaryData": (
        "omnibase_core.types.typed_dict_node_info_summary_data",
        "TypedDictNodeInfoSummaryData",
    ),
    "TypedDictQualityData": (
        "omnibase_core.types.typed_dict_quality_data",
        "TypedDictQualityData",
    ),
    "TypedDictTimestampUpdateData": (
        "omnibase_core.types.typed_dict_timestamp_update_data",
        "TypedDictTimestampUpdateData",
    ),
    "ModelMetadataAnalyticsSummary": (
        "omnibase_core.models.metadata.model_metadata_analytics_summary",
        "ModelMetadataAnalyticsSummary",
    ),
    "ModelMetadataFieldInfo": (
        "omnibase_core.models.metadata.model_metadata_field_info",
        "ModelMetadataFieldInfo",
    ),
    "ModelMetadataNodeAnalytics": (
        "omnibase_core.models.metadata.model_metadata_node_analytics",
        "ModelMetadataNodeAnalytics",
    ),
    "ModelMetadataNodeCollection": (
        "omnibase_core.models.metadata.model_metadata_node_collection",
        "ModelMetadataNodeCollection",
    ),
    "ModelMetadataNodeInfo": (
        "omnibase_core.models.metadata.model_metadata_node_info",
        "ModelMetadataNodeInfo",
    ),
    "ModelMetadataNodeType": (
        "omnibase_core.models.metadata.model_metadata_node_info",
        "ModelMetadataNodeType",
    ),
    "ModelMetadataUsageMetrics": (
        "omnibase_core.models.metadata.model_metadata_usage_metrics",
        "ModelMetadataUsageMetrics",
    ),
    "ModelMetadataValue": (
        "omnibase_core.models.metadata.model_metadata_value",
        "ModelMetadataValue",
    ),
    "ModelNodeInfoSummary": (
        "omnibase_core.models.metadata.model_node_info_summary",
        "ModelNodeInfoSummary",
    ),
    "ModelTypedMetrics": (
        "omnibase_core.models.metadata.model_typed_metrics",
        "ModelTypedMetrics",
    ),
}


def __getattr__(name: str) -> object:
    target = _LAZY_IMPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = importlib.import_module(target[0])
    value = module if target[1] is None else getattr(module, target[1])
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *_LAZY_IMPORTS})
