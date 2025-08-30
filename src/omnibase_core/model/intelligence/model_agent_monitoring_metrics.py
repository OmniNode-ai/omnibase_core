# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-08-08T00:00:00.000000'
# description: Agent Monitoring Metrics Model for Intelligence System
# entrypoint: python://model_agent_monitoring_metrics
# hash: generated
# last_modified_at: '2025-08-08T00:00:00.000000+00:00'
# lifecycle: active
# meta_type: model
# metadata_version: 0.1.0
# name: model_agent_monitoring_metrics.py
# namespace: python://omnibase.model.intelligence.model_agent_monitoring_metrics
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
Agent Monitoring Metrics Model for Intelligence System.

This module provides comprehensive metrics models for monitoring agent performance,
resource usage, and operational health in the ONEX intelligence system.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AgentStatus(Enum):
    """Status of an agent in the intelligence system."""

    INITIALIZING = "initializing"
    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"
    OFFLINE = "offline"


class AgentType(Enum):
    """Type of agent in the intelligence system."""

    CONTEXT_AGENT = "context_agent"
    EVENT_AGENT = "event_agent"
    MONITORING_AGENT = "monitoring_agent"
    ANALYSIS_AGENT = "analysis_agent"
    ORCHESTRATION_AGENT = "orchestration_agent"
    DEBUG_AGENT = "debug_agent"


class ResourceUsageLevel(Enum):
    """Resource usage levels for monitoring and alerting."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class ModelAgentResourceMetrics(BaseModel):
    """Resource usage metrics for a specific agent."""

    cpu_usage_percent: float = Field(
        description="CPU usage percentage for this agent", ge=0, le=100
    )
    memory_usage_mb: float = Field(
        description="Memory usage in MB for this agent", ge=0
    )
    memory_usage_percent: float = Field(
        description="Memory usage as percentage of available", ge=0, le=100
    )
    disk_io_bytes_read: int = Field(description="Bytes read from disk", ge=0)
    disk_io_bytes_written: int = Field(description="Bytes written to disk", ge=0)
    network_io_bytes_sent: int = Field(description="Network bytes sent", ge=0)
    network_io_bytes_received: int = Field(description="Network bytes received", ge=0)
    open_file_descriptors: int = Field(
        description="Number of open file descriptors", ge=0
    )
    thread_count: int = Field(description="Number of active threads", ge=0)
    heap_size_mb: Optional[float] = Field(
        None, description="Heap size in MB for managed languages", ge=0
    )


class ModelAgentPerformanceMetrics(BaseModel):
    """Performance metrics for agent operations."""

    tasks_completed: int = Field(description="Number of tasks completed", ge=0)
    tasks_failed: int = Field(description="Number of tasks that failed", ge=0)
    tasks_in_progress: int = Field(
        description="Number of tasks currently in progress", ge=0
    )
    average_task_duration_ms: float = Field(
        description="Average task completion time in milliseconds", ge=0
    )
    min_task_duration_ms: float = Field(
        description="Minimum task completion time in milliseconds", ge=0
    )
    max_task_duration_ms: float = Field(
        description="Maximum task completion time in milliseconds", ge=0
    )
    success_rate_percent: float = Field(
        description="Success rate as a percentage", ge=0, le=100
    )
    throughput_per_minute: float = Field(description="Tasks completed per minute", ge=0)
    error_rate_percent: float = Field(
        description="Error rate as a percentage", ge=0, le=100
    )
    queue_size: int = Field(description="Current task queue size", ge=0)
    retry_count: int = Field(description="Number of task retries", ge=0)
    timeout_count: int = Field(description="Number of task timeouts", ge=0)


class ModelAgentHealthIndicators(BaseModel):
    """Health indicators for agent monitoring."""

    last_heartbeat: datetime = Field(description="Timestamp of last heartbeat received")
    heartbeat_interval_ms: int = Field(
        description="Expected heartbeat interval in milliseconds", ge=1000
    )
    is_responsive: bool = Field(
        description="Whether the agent is responding to health checks"
    )
    consecutive_failures: int = Field(
        description="Number of consecutive health check failures", ge=0
    )
    uptime_seconds: int = Field(description="Agent uptime in seconds", ge=0)
    restart_count: int = Field(
        description="Number of times agent has been restarted", ge=0
    )
    last_error_timestamp: Optional[datetime] = Field(
        None, description="Timestamp of last error encountered"
    )
    last_error_message: Optional[str] = Field(
        None, description="Message from last error encountered"
    )
    health_score: float = Field(description="Overall health score", ge=0, le=1)


class ModelAgentMonitoringMetrics(BaseModel):
    """
    Comprehensive monitoring metrics for an intelligence system agent.

    This model captures all aspects of agent performance, resource usage,
    and health for complete observability and monitoring.
    """

    # Agent identification
    agent_id: str = Field(description="Unique identifier for the agent")
    agent_name: str = Field(description="Human-readable name of the agent")
    agent_type: AgentType = Field(description="Type of the agent")
    agent_version: str = Field(description="Version of the agent")

    # Status and operational state
    status: AgentStatus = Field(description="Current status of the agent")
    status_changed_at: datetime = Field(description="When the status last changed")
    environment: str = Field(
        description="Environment where agent is running (dev, staging, prod)"
    )
    node_id: Optional[str] = Field(None, description="ID of the node hosting the agent")

    # Metrics timestamp
    metrics_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When these metrics were collected"
    )
    collection_interval_ms: int = Field(
        description="Interval between metric collections in milliseconds", ge=1000
    )

    # Resource usage metrics
    resource_metrics: ModelAgentResourceMetrics = Field(
        description="Resource usage metrics for the agent"
    )
    resource_usage_level: ResourceUsageLevel = Field(
        description="Categorized resource usage level"
    )

    # Performance metrics
    performance_metrics: ModelAgentPerformanceMetrics = Field(
        description="Performance metrics for agent operations"
    )

    # Health indicators
    health_indicators: ModelAgentHealthIndicators = Field(
        description="Health and availability indicators"
    )

    # Configuration and metadata
    configuration_hash: Optional[str] = Field(
        None, description="Hash of current agent configuration"
    )
    configuration_version: Optional[str] = Field(
        None, description="Version of current agent configuration"
    )
    capabilities: List[str] = Field(
        default_factory=list, description="List of agent capabilities"
    )
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorizing and filtering agents"
    )

    # Context and correlation
    correlation_id: Optional[UUID] = Field(
        None, description="Correlation ID for related monitoring events"
    )
    session_id: Optional[str] = Field(
        None, description="Session ID if agent is part of a user session"
    )

    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional agent-specific metadata"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class ModelAgentMonitoringSummary(BaseModel):
    """Summary of agent monitoring metrics across multiple agents."""

    total_agents: int = Field(description="Total number of agents monitored", ge=0)
    active_agents: int = Field(description="Number of active agents", ge=0)
    idle_agents: int = Field(description="Number of idle agents", ge=0)
    error_agents: int = Field(description="Number of agents in error state", ge=0)
    offline_agents: int = Field(description="Number of offline agents", ge=0)

    # Aggregate resource metrics
    total_cpu_usage_percent: float = Field(
        description="Total CPU usage across all agents", ge=0
    )
    total_memory_usage_mb: float = Field(
        description="Total memory usage across all agents", ge=0
    )
    average_cpu_usage_percent: float = Field(
        description="Average CPU usage per agent", ge=0, le=100
    )
    average_memory_usage_mb: float = Field(
        description="Average memory usage per agent", ge=0
    )

    # Aggregate performance metrics
    total_tasks_completed: int = Field(
        description="Total tasks completed across all agents", ge=0
    )
    total_tasks_failed: int = Field(
        description="Total tasks failed across all agents", ge=0
    )
    overall_success_rate_percent: float = Field(
        description="Overall success rate across all agents", ge=0, le=100
    )
    average_response_time_ms: float = Field(
        description="Average response time across all agents", ge=0
    )

    # Health summary
    agents_with_high_resource_usage: int = Field(
        description="Number of agents with high resource usage", ge=0
    )
    agents_with_errors: int = Field(
        description="Number of agents that have had recent errors", ge=0
    )
    agents_needing_attention: int = Field(
        description="Number of agents requiring attention", ge=0
    )

    # Time range
    summary_start_time: datetime = Field(description="Start time of the summary period")
    summary_end_time: datetime = Field(description="End time of the summary period")

    # Alerts and recommendations
    active_alerts: int = Field(
        description="Number of active alerts related to agents", ge=0
    )
    scaling_recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for scaling agents"
    )

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class ModelAgentScalingTrigger(BaseModel):
    """Scaling trigger configuration for agent monitoring."""

    trigger_name: str = Field(description="Name of the scaling trigger")
    metric_name: str = Field(description="Metric that triggers scaling")
    threshold_value: float = Field(description="Threshold value for trigger")
    comparison_operator: str = Field(
        description="Comparison operator (>, <, >=, <=, ==)"
    )
    duration_seconds: int = Field(
        description="Duration threshold must be exceeded for trigger", ge=1
    )
    cooldown_seconds: int = Field(
        description="Cooldown period before next scaling action", ge=1
    )
    scaling_action: str = Field(
        description="Action to take (scale_up, scale_down, restart)"
    )
    target_agent_count: Optional[int] = Field(
        None, description="Target number of agents after scaling", ge=0
    )
    is_enabled: bool = Field(
        default=True, description="Whether this trigger is enabled"
    )

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
