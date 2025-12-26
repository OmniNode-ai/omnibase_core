"""TypedDict definitions for mixin return types.

This module provides strongly-typed dictionaries for use in mixins,
replacing generic dict[str, Any] patterns with specific typed structures.

Re-exports TypedDict types from the typed_dict subpackage.
"""

from omnibase_core.types.typed_dict import (
    TypedDictCacheStats,
    TypedDictDiscoveryExtendedStats,
    TypedDictDiscoveryStats,
    TypedDictEventBusHealth,
    TypedDictEventMetadata,
    TypedDictExecutorHealth,
    TypedDictFilterCriteria,
    TypedDictFSMContext,
    TypedDictHealthCheckStatus,
    TypedDictIntrospectionData,
    TypedDictLazyCacheStats,
    TypedDictMetricEntry,
    TypedDictNodeExecutorHealth,
    TypedDictPerformanceProfile,
    TypedDictRedactedData,
    TypedDictReducerFSMContext,
    TypedDictRegistryStats,
    TypedDictSerializedResult,
    TypedDictServiceHealth,
    TypedDictToolExecutionResponse,
    TypedDictToolExecutionResult,
    TypedDictWorkflowStepConfig,
)

__all__ = [
    "TypedDictCacheStats",
    "TypedDictDiscoveryExtendedStats",
    "TypedDictDiscoveryStats",
    "TypedDictEventBusHealth",
    "TypedDictEventMetadata",
    "TypedDictExecutorHealth",
    "TypedDictFSMContext",
    "TypedDictFilterCriteria",
    "TypedDictHealthCheckStatus",
    "TypedDictIntrospectionData",
    "TypedDictLazyCacheStats",
    "TypedDictMetricEntry",
    "TypedDictNodeExecutorHealth",
    "TypedDictPerformanceProfile",
    "TypedDictRedactedData",
    "TypedDictReducerFSMContext",
    "TypedDictRegistryStats",
    "TypedDictSerializedResult",
    "TypedDictServiceHealth",
    "TypedDictToolExecutionResponse",
    "TypedDictToolExecutionResult",
    "TypedDictWorkflowStepConfig",
]
