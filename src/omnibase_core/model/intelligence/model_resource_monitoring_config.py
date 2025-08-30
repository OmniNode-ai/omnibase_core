# === OmniNode:Metadata ===
# author: OmniNode Team
# copyright: OmniNode.ai
# created_at: '2025-08-08T00:00:00.000000'
# description: Resource Monitoring Configuration Model for Intelligence System
# entrypoint: python://model_resource_monitoring_config
# hash: generated
# last_modified_at: '2025-08-08T00:00:00.000000+00:00'
# lifecycle: active
# meta_type: model
# metadata_version: 0.1.0
# name: model_resource_monitoring_config.py
# namespace: python://omnibase.model.intelligence.model_resource_monitoring_config
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
Resource Monitoring Configuration Model for Intelligence System.

This module provides configuration models for resource monitoring, alerting
thresholds, and automatic scaling triggers in the ONEX intelligence system.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class ResourceType(Enum):
    """Types of resources that can be monitored."""

    CPU = "cpu"
    MEMORY = "memory"
    DISK = "disk"
    NETWORK = "network"
    DATABASE_CONNECTIONS = "database_connections"
    QUEUE_SIZE = "queue_size"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    THROUGHPUT = "throughput"


class AlertSeverity(Enum):
    """Severity levels for resource monitoring alerts."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class ScalingAction(Enum):
    """Actions that can be triggered by resource monitoring."""

    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    RESTART = "restart"
    THROTTLE = "throttle"
    NOTIFY_ONLY = "notify_only"


class MonitoringFrequency(Enum):
    """Frequency options for resource monitoring."""

    REALTIME = "realtime"  # Every few seconds
    HIGH = "high"  # Every 30 seconds
    NORMAL = "normal"  # Every minute
    LOW = "low"  # Every 5 minutes


class ModelResourceThreshold(BaseModel):
    """Configuration for a resource monitoring threshold."""

    threshold_id: str = Field(description="Unique identifier for this threshold")
    resource_type: ResourceType = Field(description="Type of resource being monitored")
    metric_name: str = Field(description="Specific metric name being monitored")

    # Threshold values
    warning_threshold: float = Field(description="Value that triggers a warning alert")
    critical_threshold: float = Field(
        description="Value that triggers a critical alert"
    )
    emergency_threshold: Optional[float] = Field(
        None, description="Value that triggers an emergency alert"
    )

    # Threshold behavior
    comparison_operator: str = Field(
        default=">", description="Comparison operator (>, <, >=, <=, ==, !=)"
    )
    duration_seconds: int = Field(
        default=60,
        description="Duration threshold must be exceeded before alerting",
        ge=1,
    )

    # Alert configuration
    alert_enabled: bool = Field(default=True, description="Whether alerting is enabled")
    notification_channels: List[str] = Field(
        default_factory=list,
        description="Notification channels for alerts (email, slack, webhook)",
    )

    # Automatic actions
    auto_scaling_enabled: bool = Field(
        default=False, description="Whether automatic scaling is enabled"
    )
    scaling_action: Optional[ScalingAction] = Field(
        None, description="Action to take when threshold is exceeded"
    )
    cooldown_seconds: int = Field(
        default=300, description="Cooldown period between scaling actions", ge=60
    )

    @validator("critical_threshold")
    def critical_must_be_higher_than_warning(cls, v, values):
        """Validate that critical threshold is more severe than warning."""
        if "warning_threshold" in values and "comparison_operator" in values:
            warning = values["warning_threshold"]
            operator = values.get("comparison_operator", ">")

            if operator in [">", ">="] and v <= warning:
                raise ValueError(
                    "Critical threshold must be greater than warning threshold"
                )
            elif operator in ["<", "<="] and v >= warning:
                raise ValueError(
                    "Critical threshold must be less than warning threshold"
                )
        return v


class ModelMonitoringTarget(BaseModel):
    """Configuration for a monitoring target (agent, service, system)."""

    target_id: str = Field(description="Unique identifier for the monitoring target")
    target_name: str = Field(description="Human-readable name for the target")
    target_type: str = Field(description="Type of target (agent, service, system)")

    # Target location and access
    host: Optional[str] = Field(None, description="Host where target is located")
    port: Optional[int] = Field(None, description="Port for monitoring endpoint")
    endpoint_url: Optional[str] = Field(None, description="URL for monitoring endpoint")

    # Monitoring configuration
    monitoring_enabled: bool = Field(
        default=True, description="Whether monitoring is enabled for this target"
    )
    monitoring_frequency: MonitoringFrequency = Field(
        default=MonitoringFrequency.NORMAL, description="Frequency of monitoring checks"
    )

    # Health check configuration
    health_check_endpoint: Optional[str] = Field(
        None, description="Health check endpoint URL"
    )
    health_check_timeout_seconds: int = Field(
        default=30, description="Timeout for health checks", ge=1, le=300
    )

    # Resource thresholds for this target
    thresholds: List[ModelResourceThreshold] = Field(
        default_factory=list,
        description="Resource thresholds configured for this target",
    )

    # Tags and metadata
    tags: List[str] = Field(
        default_factory=list, description="Tags for categorizing and filtering targets"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata for the target"
    )


class ModelResourceMonitoringConfig(BaseModel):
    """
    Comprehensive resource monitoring configuration for the intelligence system.

    This model configures all aspects of resource monitoring including targets,
    thresholds, alerting, and automatic scaling behaviors.
    """

    # Configuration identification
    config_id: str = Field(description="Unique identifier for this configuration")
    config_name: str = Field(description="Human-readable name for the configuration")
    config_version: str = Field(description="Version of this configuration")
    environment: str = Field(
        description="Environment this configuration applies to (dev, staging, prod)"
    )

    # Global monitoring settings
    monitoring_enabled: bool = Field(
        default=True, description="Global flag to enable/disable monitoring"
    )
    default_monitoring_frequency: MonitoringFrequency = Field(
        default=MonitoringFrequency.NORMAL,
        description="Default monitoring frequency for all targets",
    )

    # Data retention settings
    metrics_retention_days: int = Field(
        default=30, description="Days to retain detailed metrics", ge=1, le=365
    )
    alerts_retention_days: int = Field(
        default=90, description="Days to retain alert history", ge=1, le=365
    )

    # Global resource limits (SLA requirements)
    global_memory_limit_gb: float = Field(
        default=2.0, description="Global memory limit in GB", gt=0
    )
    global_cpu_limit_percent: float = Field(
        default=80.0, description="Global CPU limit percentage", gt=0, le=100
    )
    global_disk_limit_percent: float = Field(
        default=85.0, description="Global disk usage limit percentage", gt=0, le=100
    )
    global_response_time_limit_ms: float = Field(
        default=5000.0, description="Global response time limit in milliseconds", gt=0
    )

    # Monitoring targets
    targets: List[ModelMonitoringTarget] = Field(
        default_factory=list, description="List of targets to monitor"
    )

    # Global thresholds (apply to all targets unless overridden)
    global_thresholds: List[ModelResourceThreshold] = Field(
        default_factory=list, description="Global thresholds that apply to all targets"
    )

    # Alert configuration
    alerting_enabled: bool = Field(
        default=True, description="Global flag to enable/disable alerting"
    )
    alert_escalation_enabled: bool = Field(
        default=True, description="Whether to escalate unresolved alerts"
    )
    alert_escalation_delay_minutes: int = Field(
        default=15, description="Minutes to wait before escalating alerts", ge=1
    )

    # Notification settings
    notification_channels: List[str] = Field(
        default_factory=list, description="Default notification channels for alerts"
    )
    webhook_urls: List[str] = Field(
        default_factory=list, description="Webhook URLs for alert notifications"
    )

    # Automatic scaling configuration
    auto_scaling_enabled: bool = Field(
        default=False, description="Global flag to enable automatic scaling"
    )
    scaling_cooldown_seconds: int = Field(
        default=300, description="Default cooldown between scaling actions", ge=60
    )
    max_scale_up_instances: int = Field(
        default=10, description="Maximum number of instances to scale up to", ge=1
    )
    min_scale_down_instances: int = Field(
        default=1, description="Minimum number of instances to scale down to", ge=1
    )

    # Dashboard integration
    dashboard_integration_enabled: bool = Field(
        default=True, description="Whether to integrate with debug dashboard"
    )
    dashboard_update_interval_seconds: int = Field(
        default=30, description="Interval for updating dashboard metrics", ge=1
    )

    # Performance optimization
    metrics_aggregation_interval_seconds: int = Field(
        default=60, description="Interval for aggregating metrics", ge=1
    )
    batch_size_for_processing: int = Field(
        default=100, description="Batch size for processing metrics", ge=1
    )

    # Advanced configuration
    correlation_id: Optional[UUID] = Field(
        None, description="Correlation ID for configuration tracking"
    )
    created_by: str = Field(description="User/service that created this configuration")
    created_at: Optional[str] = Field(None, description="ISO timestamp of creation")
    updated_at: Optional[str] = Field(None, description="ISO timestamp of last update")

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True
        extra = "forbid"


class ModelResourceMonitoringStatus(BaseModel):
    """Current status of resource monitoring system."""

    monitoring_active: bool = Field(
        description="Whether monitoring is currently active"
    )
    total_targets: int = Field(description="Total number of monitoring targets", ge=0)
    active_targets: int = Field(
        description="Number of actively monitored targets", ge=0
    )
    failed_targets: int = Field(description="Number of failed monitoring targets", ge=0)

    # Current resource usage summary
    current_total_memory_gb: float = Field(
        description="Current total memory usage in GB", ge=0
    )
    current_avg_cpu_percent: float = Field(
        description="Current average CPU usage percentage", ge=0, le=100
    )
    current_max_response_time_ms: float = Field(
        description="Current maximum response time in milliseconds", ge=0
    )

    # Alert summary
    active_alerts: int = Field(description="Number of active alerts", ge=0)
    alerts_last_hour: int = Field(description="Alerts triggered in last hour", ge=0)
    critical_alerts: int = Field(description="Number of critical alerts", ge=0)

    # Scaling status
    recent_scaling_actions: int = Field(
        description="Number of scaling actions in last hour", ge=0
    )
    scaling_cooldown_active: bool = Field(
        description="Whether scaling is in cooldown period"
    )

    # System health indicators
    within_memory_limit: bool = Field(
        description="Whether system is within global memory limit"
    )
    within_cpu_limit: bool = Field(
        description="Whether system is within global CPU limit"
    )
    within_response_time_limit: bool = Field(
        description="Whether system is within response time limit"
    )
    overall_health_score: float = Field(
        description="Overall health score (0-1)", ge=0, le=1
    )

    last_updated: str = Field(description="ISO timestamp of last status update")

    class Config:
        """Pydantic configuration."""

        validate_assignment = True
        extra = "forbid"
