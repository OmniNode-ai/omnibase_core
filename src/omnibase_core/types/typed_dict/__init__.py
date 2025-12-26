"""TypedDict definitions for mixin return types.

This module provides strongly-typed dictionaries for use in mixins,
replacing generic dict[str, Any] patterns with specific typed structures.
"""

from omnibase_core.types.typed_dict.typed_dict_cache_stats import TypedDictCacheStats
from omnibase_core.types.typed_dict.typed_dict_discovery_extended_stats import (
    TypedDictDiscoveryExtendedStats,
)
from omnibase_core.types.typed_dict.typed_dict_discovery_stats import (
    TypedDictDiscoveryStats,
)
from omnibase_core.types.typed_dict.typed_dict_event_bus_health import (
    TypedDictEventBusHealth,
)
from omnibase_core.types.typed_dict.typed_dict_event_metadata import (
    TypedDictEventMetadata,
)
from omnibase_core.types.typed_dict.typed_dict_executor_health import (
    TypedDictExecutorHealth,
)
from omnibase_core.types.typed_dict.typed_dict_filter_criteria import (
    TypedDictFilterCriteria,
)
from omnibase_core.types.typed_dict.typed_dict_fsm_context import TypedDictFSMContext
from omnibase_core.types.typed_dict.typed_dict_health_check_status import (
    TypedDictHealthCheckStatus,
)
from omnibase_core.types.typed_dict.typed_dict_introspection_data import (
    TypedDictIntrospectionData,
)
from omnibase_core.types.typed_dict.typed_dict_lazy_cache_stats import (
    TypedDictLazyCacheStats,
)
from omnibase_core.types.typed_dict.typed_dict_metric_entry import TypedDictMetricEntry
from omnibase_core.types.typed_dict.typed_dict_node_executor_health import (
    TypedDictNodeExecutorHealth,
)
from omnibase_core.types.typed_dict.typed_dict_performance_profile import (
    TypedDictPerformanceProfile,
)
from omnibase_core.types.typed_dict.typed_dict_redacted_data import (
    TypedDictRedactedData,
)
from omnibase_core.types.typed_dict.typed_dict_reducer_fsm_context import (
    TypedDictReducerFSMContext,
)
from omnibase_core.types.typed_dict.typed_dict_registry_stats import (
    TypedDictRegistryStats,
)
from omnibase_core.types.typed_dict.typed_dict_serialized_result import (
    TypedDictSerializedResult,
)
from omnibase_core.types.typed_dict.typed_dict_service_health import (
    TypedDictServiceHealth,
)
from omnibase_core.types.typed_dict.typed_dict_tool_execution_response import (
    TypedDictToolExecutionResponse,
)
from omnibase_core.types.typed_dict.typed_dict_tool_execution_result import (
    TypedDictToolExecutionResult,
)
from omnibase_core.types.typed_dict.typed_dict_workflow_step_config import (
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
