# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-08-08T00:00:00.000000'
# description: Structured Log Event Model for Intelligence System Observability
# entrypoint: python://model_structured_log_event
# hash: generated
# last_modified_at: '2025-08-08T00:00:00.000000+00:00'
# lifecycle: active
# meta_type: model
# metadata_version: 0.1.0
# name: model_structured_log_event.py
# namespace: python://omnibase.model.intelligence.model_structured_log_event
# owner: OmniNode Team
# protocol_version: 0.1.0
# runtime_language_hint: python>=3.11
# schema_version: 0.1.0
# state_contract: state_contract://default
# tools: {}
# uuid: generated
# version: 1.0.0
# === /OmniNode:Metadata ===

"""
Structured Log Event Model for Intelligence System Observability.

This module provides comprehensive structured logging models for the ONEX intelligence
system, including event tracking, performance metrics, and audit trails.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_log_context import ModelLogContext


class IntelligenceLogLevel(Enum):
    """Log levels for intelligence system events."""

    TRACE = "trace"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"
    AUDIT = "audit"
    METRICS = "metrics"


class IntelligenceEventType(Enum):
    """Event types for intelligence system logging."""

    # Context events
    CONTEXT_VALIDATION = "context_validation"
    CONTEXT_EXTRACTION = "context_extraction"
    CONTEXT_ENRICHMENT = "context_enrichment"

    # Event coordination events
    EVENT_RECEIVED = "event_received"
    EVENT_PROCESSED = "event_processed"
    EVENT_FORWARDED = "event_forwarded"
    EVENT_AUDIT_LOGGED = "event_audit_logged"

    # Agent monitoring events
    AGENT_STARTED = "agent_started"
    AGENT_STOPPED = "agent_stopped"
    AGENT_HEARTBEAT = "agent_heartbeat"
    AGENT_ERROR = "agent_error"

    # Performance monitoring
    PERFORMANCE_SAMPLE = "performance_sample"
    RESOURCE_USAGE = "resource_usage"
    SCALING_EVENT = "scaling_event"

    # System events
    SYSTEM_STARTUP = "system_startup"
    SYSTEM_SHUTDOWN = "system_shutdown"
    CONFIGURATION_CHANGE = "configuration_change"

    # Alert events
    ALERT_TRIGGERED = "alert_triggered"
    ALERT_RESOLVED = "alert_resolved"
    THRESHOLD_EXCEEDED = "threshold_exceeded"


class IntelligenceComponent(Enum):
    """Components in the intelligence system."""

    STRUCTURED_LOGGER = "structured_logger"
    CONTEXT_VALIDATOR = "context_validator"
    EVENT_COORDINATOR = "event_coordinator"
    AGENT_MONITOR = "agent_monitor"
    RESOURCE_MONITOR = "resource_monitor"
    PERFORMANCE_COLLECTOR = "performance_collector"
    ALERT_MANAGER = "alert_manager"
    DEBUG_DASHBOARD = "debug_dashboard"
    AUDIT_LOGGER = "audit_logger"


class ModelIntelligenceMetrics(BaseModel):
    """Performance metrics for intelligence system operations."""

    cpu_usage_percent: float | None = Field(
        None,
        description="CPU usage percentage",
        ge=0,
        le=100,
    )
    memory_usage_mb: float | None = Field(
        None,
        description="Memory usage in MB",
        ge=0,
    )
    disk_usage_percent: float | None = Field(
        None,
        description="Disk usage percentage",
        ge=0,
        le=100,
    )
    network_io_bytes: int | None = Field(
        None,
        description="Network I/O in bytes",
        ge=0,
    )
    request_count: int | None = Field(
        None,
        description="Number of requests processed",
        ge=0,
    )
    error_count: int | None = Field(
        None,
        description="Number of errors encountered",
        ge=0,
    )
    response_time_ms: float | None = Field(
        None,
        description="Response time in milliseconds",
        ge=0,
    )
    throughput_per_second: float | None = Field(
        None,
        description="Operations per second",
        ge=0,
    )
    queue_size: int | None = Field(None, description="Current queue size", ge=0)
    active_connections: int | None = Field(
        None,
        description="Number of active connections",
        ge=0,
    )


class ModelIntelligenceAlert(BaseModel):
    """Alert information for intelligence system events."""

    alert_id: str = Field(description="Unique alert identifier")
    alert_name: str = Field(description="Alert rule name")
    severity: str = Field(description="Alert severity level")
    threshold_value: float | None = Field(
        None,
        description="Threshold value that triggered alert",
    )
    current_value: float | None = Field(None, description="Current metric value")
    threshold_condition: str | None = Field(
        None,
        description="Condition that triggered alert",
    )
    escalation_level: int = Field(
        default=1,
        description="Current escalation level",
        ge=1,
    )
    notification_sent: bool = Field(
        default=False,
        description="Whether notification was sent",
    )


class ModelStructuredLogEvent(BaseModel):
    """
    Structured log event for intelligence system observability.

    Provides comprehensive logging with metrics, alerts, and audit information
    for complete system observability.
    """

    # Core event identification
    event_id: str = Field(description="Unique event identifier")
    correlation_id: UUID | None = Field(
        None,
        description="Correlation ID for tracking related events",
    )
    session_id: str | None = Field(
        None,
        description="Session identifier for user/agent sessions",
    )

    # Event metadata
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="UTC timestamp of the event",
    )
    log_level: IntelligenceLogLevel = Field(description="Log level of the event")
    event_type: IntelligenceEventType = Field(
        description="Type of intelligence system event",
    )
    component: IntelligenceComponent = Field(
        description="Component that generated the event",
    )

    # Event content
    message: str = Field(description="Human-readable event message")
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event details and context",
    )

    # System context
    node_id: str | None = Field(
        None,
        description="Node identifier where event occurred",
    )
    service_name: str | None = Field(
        None,
        description="Service name that generated the event",
    )
    service_version: str | None = Field(None, description="Version of the service")
    environment: str | None = Field(
        None,
        description="Environment (dev, staging, prod)",
    )

    # Performance metrics
    metrics: ModelIntelligenceMetrics | None = Field(
        None,
        description="Performance metrics for the event",
    )

    # Alert information
    alert: ModelIntelligenceAlert | None = Field(
        None,
        description="Alert information if this is an alert event",
    )

    # Error information
    error_type: str | None = Field(
        None,
        description="Type of error if this is an error event",
    )
    error_code: str | None = Field(None, description="Error code for the error")
    stack_trace: str | None = Field(None, description="Stack trace for errors")

    # Audit trail information
    user_id: str | None = Field(None, description="User ID for audit events")
    action: str | None = Field(None, description="Action performed for audit events")
    resource: str | None = Field(None, description="Resource affected by the action")
    previous_value: str | None = Field(
        None,
        description="Previous value before change",
    )
    new_value: str | None = Field(None, description="New value after change")

    # Processing metadata
    processing_time_ms: float | None = Field(
        None,
        description="Time taken to process the event",
        ge=0,
    )
    memory_usage_bytes: int | None = Field(
        None,
        description="Memory used during event processing",
        ge=0,
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Tags for categorizing and filtering events",
    )

    # Source code context
    log_context: ModelLogContext | None = Field(
        None,
        description="Source code context where event was logged",
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class ModelIntelligenceLogFilter(BaseModel):
    """Filter criteria for querying intelligence log events."""

    start_time: datetime | None = Field(
        None,
        description="Start time for filtering events",
    )
    end_time: datetime | None = Field(
        None,
        description="End time for filtering events",
    )
    log_levels: list[IntelligenceLogLevel] = Field(
        default_factory=list,
        description="Log levels to include in results",
    )
    event_types: list[IntelligenceEventType] = Field(
        default_factory=list,
        description="Event types to include in results",
    )
    components: list[IntelligenceComponent] = Field(
        default_factory=list,
        description="Components to include in results",
    )
    correlation_id: UUID | None = Field(None, description="Filter by correlation ID")
    session_id: str | None = Field(None, description="Filter by session ID")
    node_id: str | None = Field(None, description="Filter by node ID")
    service_name: str | None = Field(None, description="Filter by service name")
    tags: list[str] = Field(
        default_factory=list,
        description="Tags that must be present in events",
    )
    text_search: str | None = Field(
        None,
        description="Search term for message and details",
    )
    limit: int = Field(
        default=100,
        description="Maximum number of events to return",
        ge=1,
        le=10000,
    )
    offset: int = Field(default=0, description="Number of events to skip", ge=0)


class ModelIntelligenceLogSummary(BaseModel):
    """Summary statistics for intelligence log events."""

    total_events: int = Field(description="Total number of events in the time period")
    events_by_level: dict[str, int] = Field(description="Count of events by log level")
    events_by_type: dict[str, int] = Field(description="Count of events by event type")
    events_by_component: dict[str, int] = Field(
        description="Count of events by component",
    )
    error_rate: float = Field(
        description="Percentage of events that are errors",
        ge=0,
        le=100,
    )
    average_response_time_ms: float | None = Field(
        None,
        description="Average response time across all events",
    )
    peak_memory_usage_mb: float | None = Field(
        None,
        description="Peak memory usage observed",
    )
    peak_cpu_usage_percent: float | None = Field(
        None,
        description="Peak CPU usage observed",
    )
    active_alerts: int = Field(description="Number of active alerts", ge=0)
    time_range_start: datetime = Field(description="Start time of the summary period")
    time_range_end: datetime = Field(description="End time of the summary period")
