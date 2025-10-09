"""
Structured TypedDict Definitions Module.

Re-exports TypedDict definitions from the types module.
All TypedDict classes are maintained in individual files following ONEX patterns.
"""

# Re-export all TypedDict definitions from the types module
from omnibase_core.types import (
    TypedDictAuditInfo,
    TypedDictBatchProcessingInfo,
    TypedDictCacheInfo,
    TypedDictConfigurationSettings,
    TypedDictConnectionInfo,
    TypedDictDependencyInfo,
    TypedDictErrorDetails,
    TypedDictEventInfo,
    TypedDictExecutionStats,
    TypedDictFeatureFlags,
    TypedDictHealthStatus,
    TypedDictLegacyError,
    TypedDictLegacyHealth,
    TypedDictLegacyStats,
    TypedDictMetrics,
    TypedDictOperationResult,
    TypedDictResourceUsage,
    TypedDictSecurityContext,
    TypedDictSemVer,
    TypedDictServiceInfo,
    TypedDictStatsCollection,
    TypedDictSystemState,
    TypedDictValidationResult,
    TypedDictWorkflowState,
    parse_datetime,
)

# Alias for _parse_datetime
_parse_datetime = parse_datetime

__all__ = [
    "TypedDictAuditInfo",
    "TypedDictBatchProcessingInfo",
    "TypedDictCacheInfo",
    "TypedDictConfigurationSettings",
    "TypedDictConnectionInfo",
    "TypedDictDependencyInfo",
    "TypedDictErrorDetails",
    "TypedDictEventInfo",
    "TypedDictExecutionStats",
    "TypedDictFeatureFlags",
    "TypedDictHealthStatus",
    "TypedDictLegacyError",
    "TypedDictLegacyHealth",
    "TypedDictLegacyStats",
    "TypedDictMetrics",
    "TypedDictOperationResult",
    "TypedDictResourceUsage",
    "TypedDictSecurityContext",
    "TypedDictSemVer",
    "TypedDictServiceInfo",
    "TypedDictStatsCollection",
    "TypedDictSystemState",
    "TypedDictValidationResult",
    "TypedDictWorkflowState",
    "parse_datetime",
    "_parse_datetime",
]
