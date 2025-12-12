"""
TypedDict definitions for mixin return types.

This module provides strongly-typed dictionaries for use in mixins,
replacing generic dict[str, Any] patterns with specific typed structures.
"""

from __future__ import annotations

from datetime import datetime
from typing import NotRequired, TypedDict
from uuid import UUID


class TypedDictMetricEntry(TypedDict):
    """TypedDict for a single metric entry in MixinMetrics."""

    value: float
    tags: NotRequired[dict[str, str]]


class TypedDictCacheStats(TypedDict):
    """TypedDict for cache statistics from MixinCaching."""

    enabled: bool
    entries: int
    keys: list[str]


class TypedDictLazyCacheStats(TypedDict):
    """TypedDict for lazy evaluation cache statistics."""

    total_entries: int
    computed_entries: int
    pending_entries: int
    cache_hit_ratio: float
    memory_efficiency: str


class TypedDictExecutorHealth(TypedDict):
    """TypedDict for executor health status from MixinNodeExecutor."""

    status: str
    total_executions: int
    successful_executions: int
    failed_executions: int
    average_execution_time_ms: float
    circuit_breaker_state: str
    last_execution_time: str | None


class TypedDictServiceHealth(TypedDict):
    """TypedDict for service health status from MixinNodeService."""

    status: str
    uptime_seconds: int
    active_invocations: int
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    success_rate: float
    node_id: str | UUID
    node_name: str
    shutdown_requested: bool


class TypedDictRegistryStats(TypedDict):
    """TypedDict for registry statistics from MixinServiceRegistry."""

    total_services: int
    online_services: int
    offline_services: int
    domain_filter: str | None
    registry_started: bool


class TypedDictDiscoveryStats(TypedDict):
    """TypedDict for discovery statistics from MixinDiscoveryResponder."""

    node_id: str
    node_name: str
    discovery_count: int
    last_discovery_time: str | None
    is_available: bool
    capabilities: list[str]


class TypedDictHealthCheckStatus(TypedDict):
    """TypedDict for health check status from MixinHealthCheck."""

    node_id: str
    is_healthy: bool
    status: str
    health_score: float
    issues: list[str]


class TypedDictPerformanceProfile(TypedDict):
    """TypedDict for performance profile from MixinNodeIntrospection."""

    typical_execution_time: str
    memory_usage: str
    cpu_intensive: bool


class TypedDictIntrospectionData(TypedDict):
    """TypedDict for introspection data from event-driven nodes."""

    node_name: str
    node_id: str
    version: str
    capabilities: list[str]
    status: str
    event_types_handled: list[str]


class TypedDictToolExecutionResult(TypedDict):
    """TypedDict for tool execution result."""

    success: bool
    result: object | None
    error: str | None
    execution_time_ms: int


class TypedDictFilterCriteria(TypedDict, total=False):
    """TypedDict for discovery filter criteria (all fields optional)."""

    capabilities: list[str]
    name_pattern: str
    node_type: str
    status: str


class TypedDictRedactedData(TypedDict):
    """
    TypedDict for data after redaction processing.

    This is intentionally an empty TypedDict since redaction
    can be applied to any structure - the output shape depends
    on the input shape with sensitive fields removed or masked.
    """


class TypedDictFSMContext(TypedDict, total=False):
    """TypedDict for FSM execution context (all fields optional)."""

    current_state: str
    previous_state: str | None
    transition_count: int
    last_transition_time: datetime | None


class TypedDictEventMetadata(TypedDict):
    """TypedDict for event metadata in lifecycle events."""

    event_type: str
    timestamp: str
    node_id: str
    correlation_id: NotRequired[str]


class TypedDictNodeExecutorHealth(TypedDict):
    """TypedDict for node executor health status from MixinNodeExecutor.get_executor_health()."""

    status: str
    uptime_seconds: int
    active_invocations: int
    total_invocations: int
    successful_invocations: int
    failed_invocations: int
    success_rate: float
    node_id: str | UUID
    node_name: str
    shutdown_requested: bool


class TypedDictReducerFSMContext(TypedDict, total=False):
    """TypedDict for FSM execution context in reducer nodes."""

    input_data: object
    reduction_type: str
    operation_id: str


class TypedDictSerializedResult(TypedDict, total=False):
    """TypedDict for serialized execution results."""

    result: object


class TypedDictToolExecutionResponse(TypedDict):
    """TypedDict for tool execution response data."""

    tool_name: str
    success: bool
    result: object | None
    execution_time: float
    error: str | None
    tool_version: str


class TypedDictWorkflowStepConfig(TypedDict, total=False):
    """TypedDict for workflow step configuration from YAML."""

    step_name: str
    step_type: str
    timeout_ms: NotRequired[int]
    depends_on: NotRequired[list[str]]


class TypedDictDiscoveryExtendedStats(TypedDict):
    """TypedDict for extended discovery stats including active status."""

    requests_received: int
    responses_sent: int
    throttled_requests: int
    filtered_requests: int
    last_request_time: float | None
    error_count: int
    active: bool
    throttle_seconds: float
    last_response_time: float


__all__ = [
    "TypedDictCacheStats",
    "TypedDictDiscoveryExtendedStats",
    "TypedDictDiscoveryStats",
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
