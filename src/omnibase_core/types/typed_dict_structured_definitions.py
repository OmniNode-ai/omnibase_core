"""
TypedDict definitions for simple structured dictionaries.

Replaces dict[str, Any] with TypedDict for known structure patterns.
Follows ONEX strong typing principles.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, NotRequired, TypedDict, TypeVar, Union
from uuid import UUID


def _parse_datetime(value: object) -> datetime:
    """Parse a datetime value from various input types."""
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value.strip():
        try:
            # Try ISO format first
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            # Fallback to current datetime for invalid strings
            return datetime.now()
    # Default for empty/None values
    return datetime.now()


class TypedDictSemVer(TypedDict):
    """TypedDict for semantic version structure following SemVer specification."""

    major: int
    minor: int
    patch: int


class TypedDictExecutionStats(TypedDict):
    """TypedDict for execution statistics."""

    execution_count: int
    success_count: int
    failure_count: int
    average_duration_ms: float
    last_execution: datetime
    total_duration_ms: int


class TypedDictHealthStatus(TypedDict):
    """TypedDict for health status information."""

    status: str  # "healthy", "degraded", "unhealthy"
    uptime_seconds: int
    last_check: datetime
    error_count: int
    warning_count: int
    checks_passed: int
    checks_total: int


class TypedDictResourceUsage(TypedDict):
    """TypedDict for resource usage metrics."""

    cpu_percent: float
    memory_mb: float
    disk_usage_mb: float
    network_in_mb: float
    network_out_mb: float
    open_connections: int


class TypedDictConfigurationSettings(TypedDict):
    """TypedDict for configuration settings."""

    environment: str
    debug_enabled: bool
    log_level: str
    timeout_ms: int
    retry_attempts: int
    batch_size: int


class TypedDictValidationResult(TypedDict):
    """TypedDict for validation results."""

    is_valid: bool
    error_count: int
    warning_count: int
    info_count: int
    validation_time_ms: int
    rules_checked: int


class TypedDictMetrics(TypedDict):
    """TypedDict for general metrics."""

    timestamp: datetime
    metric_name: str
    metric_value: float
    metric_unit: str
    tags: dict[str, str]


class TypedDictErrorDetails(TypedDict):
    """TypedDict for error details."""

    error_code: str
    error_message: str
    error_type: str
    timestamp: datetime
    stack_trace: NotRequired[str]
    context: NotRequired[dict[str, str]]


class TypedDictOperationResult(TypedDict):
    """TypedDict for operation results."""

    success: bool
    result_type: str
    execution_time_ms: int
    timestamp: datetime
    error_details: NotRequired[TypedDictErrorDetails]


class TypedDictWorkflowState(TypedDict):
    """TypedDict for workflow state."""

    workflow_id: UUID
    current_step: str
    total_steps: int
    completed_steps: int
    status: str  # "pending", "running", "completed", "failed"
    created_at: datetime
    updated_at: datetime


class TypedDictEventInfo(TypedDict):
    """TypedDict for event information."""

    event_id: UUID
    event_type: str
    timestamp: datetime
    source: str
    correlation_id: NotRequired[UUID]
    sequence_number: NotRequired[int]


class TypedDictConnectionInfo(TypedDict):
    """TypedDict for connection information."""

    connection_id: UUID
    connection_type: str
    status: str  # "connected", "disconnected", "error"
    established_at: datetime
    last_activity: datetime
    bytes_sent: int
    bytes_received: int


class TypedDictServiceInfo(TypedDict):
    """TypedDict for service information."""

    service_name: str
    service_version: TypedDictSemVer
    status: str  # "running", "stopped", "error"
    port: NotRequired[int]
    host: NotRequired[str]
    health_check_url: NotRequired[str]


class TypedDictDependencyInfo(TypedDict):
    """TypedDict for dependency information."""

    dependency_name: str
    dependency_version: TypedDictSemVer
    required_version: TypedDictSemVer
    status: str  # "satisfied", "missing", "outdated", "conflict"
    installed_at: NotRequired[datetime]


class TypedDictCacheInfo(TypedDict):
    """TypedDict for cache information."""

    cache_name: str
    cache_size: int
    max_size: int
    hit_count: int
    miss_count: int
    eviction_count: int
    hit_rate: float


class TypedDictBatchProcessingInfo(TypedDict):
    """TypedDict for batch processing information."""

    batch_id: UUID
    total_items: int
    processed_items: int
    successful_items: int
    failed_items: int
    started_at: datetime
    estimated_completion: NotRequired[datetime]


class TypedDictSecurityContext(TypedDict):
    """TypedDict for security context."""

    user_id: UUID
    session_id: UUID
    permissions: list[str]
    roles: list[str]
    authenticated_at: datetime
    expires_at: NotRequired[datetime]


class TypedDictAuditInfo(TypedDict):
    """TypedDict for audit information."""

    action: str
    resource: str
    user_id: UUID
    timestamp: datetime
    ip_address: NotRequired[str]
    user_agent: NotRequired[str]
    outcome: str  # "success", "failure", "partial"


class TypedDictFeatureFlags(TypedDict):
    """TypedDict for feature flags."""

    feature_name: str
    enabled: bool
    environment: str
    updated_at: datetime
    updated_by: str
    description: NotRequired[str]


# Container types for collections of the above
class TypedDictStatsCollection(TypedDict):
    """TypedDict for collections of statistics."""

    execution_stats: TypedDictExecutionStats
    health_status: TypedDictHealthStatus
    resource_usage: TypedDictResourceUsage
    last_updated: datetime


class TypedDictSystemState(TypedDict):
    """TypedDict for overall system state."""

    system_id: UUID
    system_name: str
    version: TypedDictSemVer
    environment: str
    status: str
    stats: TypedDictStatsCollection
    services: list[TypedDictServiceInfo]
    dependencies: list[TypedDictDependencyInfo]


# Field conversion types (using ModelSchemaValue for ONEX compliance)
# Import the ONEX-compliant value representation
# Use ModelSchemaValue directly in type annotations instead of alias

# ONEX-compliant input value type for structured data
# All inputs come as strings or None initially and are converted to proper types
