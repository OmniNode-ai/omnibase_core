"""
Models for production monitoring and metrics.

Defines structures for tracking agent health, system performance,
and operational metrics for 24/7 automation monitoring.
"""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EnumAgentState(str, Enum):
    """Agent operational states."""

    RUNNING = "running"
    IDLE = "idle"
    FAILED = "failed"
    RECOVERING = "recovering"
    STOPPED = "stopped"
    STARTING = "starting"


class EnumSystemHealth(str, Enum):
    """System health status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


class EnumAlertSeverity(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EnumTrendDirection(str, Enum):
    """Trend direction indicators."""

    UP = "up"
    DOWN = "down"
    STABLE = "stable"
    VOLATILE = "volatile"


class ModelAgentHealthMetrics(BaseModel):
    """Health metrics for a single agent."""

    agent_id: str = Field(..., description="Unique agent identifier")
    status: EnumAgentState = Field(..., description="Current agent status")
    uptime_seconds: int = Field(..., ge=0, description="Agent uptime in seconds")
    last_heartbeat: datetime = Field(..., description="Last heartbeat timestamp")
    error_count: int = Field(0, ge=0, description="Total error count")
    success_rate: float = Field(
        ...,
        ge=0,
        le=100,
        description="Success rate percentage",
    )
    tasks_completed: int = Field(0, ge=0, description="Total tasks completed")
    avg_completion_time: float = Field(
        0.0,
        ge=0,
        description="Average task completion time",
    )
    tokens_consumed: int = Field(0, ge=0, description="Total tokens consumed")
    efficiency_score: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Agent efficiency score",
    )

    memory_usage_mb: float = Field(0.0, ge=0, description="Memory usage in megabytes")
    cpu_utilization: float = Field(
        0.0,
        ge=0,
        le=100,
        description="CPU utilization percentage",
    )
    network_io_bytes_sec: float = Field(
        0.0,
        ge=0,
        description="Network I/O bytes per second",
    )
    queue_depth: int = Field(0, ge=0, description="Current queue depth")

    window_id: str | None = Field(None, description="Current operational window")
    current_task: str | None = Field(None, description="Current task description")

    last_error: str | None = Field(None, description="Last error message")
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last metrics update",
    )

    def is_healthy(self) -> bool:
        """Check if agent is in healthy state."""
        return (
            self.status in [EnumAgentState.RUNNING, EnumAgentState.IDLE]
            and self.success_rate >= 85.0
            and self.error_count < 10
        )

    def time_since_heartbeat(self) -> float:
        """Get seconds since last heartbeat."""
        return (datetime.utcnow() - self.last_heartbeat).total_seconds()


class ModelSystemHealthMetrics(BaseModel):
    """System-wide health metrics."""

    api_availability: float = Field(
        ...,
        ge=0,
        le=100,
        description="API availability percentage",
    )
    database_connectivity: bool = Field(..., description="Database connection status")
    event_bus_latency_ms: float = Field(
        ...,
        ge=0,
        description="Event bus latency in milliseconds",
    )

    total_throughput_per_hour: int = Field(
        0,
        ge=0,
        description="Total system throughput per hour",
    )
    aggregate_success_rate: float = Field(
        0.0,
        ge=0,
        le=100,
        description="System-wide success rate",
    )
    system_efficiency: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Overall system efficiency",
    )
    cost_per_task: float = Field(0.0, ge=0, description="Average cost per task")

    available_quota: int = Field(0, ge=0, description="Available token quota")
    agent_pool_size: int = Field(0, ge=0, description="Total agent pool size")
    queue_capacity_percent: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Queue capacity utilization",
    )
    resource_headroom_percent: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Resource headroom percentage",
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp",
    )

    def get_overall_health(self) -> EnumSystemHealth:
        """Calculate overall system health status."""
        if (
            self.api_availability >= 99.0
            and self.database_connectivity
            and self.aggregate_success_rate >= 95.0
            and self.resource_headroom_percent >= 20.0
        ):
            return EnumSystemHealth.HEALTHY
        if (
            self.api_availability >= 90.0
            and self.database_connectivity
            and self.aggregate_success_rate >= 80.0
            and self.resource_headroom_percent >= 10.0
        ):
            return EnumSystemHealth.DEGRADED
        return EnumSystemHealth.CRITICAL


class ModelBusinessMetrics(BaseModel):
    """Business KPIs and trends."""

    development_velocity: float = Field(
        0.0,
        ge=0,
        description="Development velocity in tickets per day",
    )
    cost_efficiency: float = Field(
        0.0,
        ge=0,
        description="Cost efficiency in dollars per ticket",
    )
    quality_score: float = Field(0.0, ge=0, le=100, description="Quality score 0-100")
    roi_metric: float = Field(0.0, description="Return on investment ratio")

    velocity_trend: EnumTrendDirection = Field(
        ...,
        description="Velocity trend direction",
    )
    cost_trend: EnumTrendDirection = Field(..., description="Cost trend direction")
    quality_trend: EnumTrendDirection = Field(
        ...,
        description="Quality trend direction",
    )
    efficiency_improvement_percent: float = Field(
        0.0,
        description="Efficiency improvement percentage",
    )

    period_start: datetime = Field(..., description="Metrics period start")
    period_end: datetime = Field(..., description="Metrics period end")

    tickets_completed: int = Field(
        0,
        ge=0,
        description="Total tickets completed in period",
    )
    total_cost: float = Field(0.0, ge=0, description="Total cost in period")

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Metrics timestamp",
    )


class ModelServiceDependency(BaseModel):
    """Service dependency status."""

    service_name: str = Field(..., description="Service name")
    status: EnumSystemHealth = Field(..., description="Service status")
    url: str | None = Field(None, description="Service URL")
    last_check: datetime = Field(..., description="Last health check")
    response_time_ms: float = Field(
        0.0,
        ge=0,
        description="Response time in milliseconds",
    )
    error_message: str | None = Field(None, description="Error message if unhealthy")


class ModelProductionSnapshot(BaseModel):
    """Complete production monitoring snapshot."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    snapshot_id: str = Field(..., description="Unique snapshot identifier")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Snapshot timestamp",
    )

    system_health: ModelSystemHealthMetrics = Field(
        ...,
        description="System health metrics",
    )
    business_metrics: ModelBusinessMetrics = Field(..., description="Business KPIs")

    agent_metrics: list[ModelAgentHealthMetrics] = Field(
        default_factory=list,
        description="Individual agent metrics",
    )

    service_dependencies: list[ModelServiceDependency] = Field(
        default_factory=list,
        description="Service dependency statuses",
    )

    current_window: str | None = Field(
        None,
        description="Current operational window",
    )
    next_transition: datetime | None = Field(
        None,
        description="Next window transition",
    )

    alerts_active: int = Field(0, ge=0, description="Number of active alerts")
    incidents_open: int = Field(0, ge=0, description="Number of open incidents")

    def get_active_agents(self) -> int:
        """Get count of active agents."""
        return len(
            [
                agent
                for agent in self.agent_metrics
                if agent.status in [EnumAgentState.RUNNING, EnumAgentState.IDLE]
            ],
        )

    def get_failed_agents(self) -> int:
        """Get count of failed agents."""
        return len(
            [
                agent
                for agent in self.agent_metrics
                if agent.status == EnumAgentState.FAILED
            ],
        )

    def get_total_queue_depth(self) -> int:
        """Get total queue depth across all agents."""
        return sum(agent.queue_depth for agent in self.agent_metrics)

    def calculate_system_efficiency(self) -> float:
        """Calculate overall system efficiency."""
        if not self.agent_metrics:
            return 0.0

        total_efficiency = sum(agent.efficiency_score for agent in self.agent_metrics)
        return total_efficiency / len(self.agent_metrics)


class ModelMetricsAggregation(BaseModel):
    """Aggregated metrics over time periods."""

    aggregation_id: str = Field(..., description="Unique aggregation identifier")
    period_start: datetime = Field(..., description="Aggregation period start")
    period_end: datetime = Field(..., description="Aggregation period end")
    interval_minutes: int = Field(
        ...,
        gt=0,
        description="Aggregation interval in minutes",
    )

    avg_throughput: float = Field(0.0, ge=0, description="Average throughput")
    avg_success_rate: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Average success rate",
    )
    avg_efficiency: float = Field(0.0, ge=0, le=100, description="Average efficiency")
    avg_cost_per_task: float = Field(0.0, ge=0, description="Average cost per task")

    max_queue_depth: int = Field(0, ge=0, description="Maximum queue depth")
    total_errors: int = Field(0, ge=0, description="Total errors in period")
    total_tasks: int = Field(0, ge=0, description="Total tasks in period")
    total_cost: float = Field(0.0, ge=0, description="Total cost in period")

    uptime_percent: float = Field(
        0.0,
        ge=0,
        le=100,
        description="System uptime percentage",
    )

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Aggregation timestamp",
    )


class ModelPerformanceForecast(BaseModel):
    """Performance forecast based on historical data."""

    forecast_id: str = Field(..., description="Unique forecast identifier")
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Forecast creation time",
    )
    forecast_horizon_hours: int = Field(
        ...,
        gt=0,
        description="Forecast horizon in hours",
    )
    confidence_interval: float = Field(
        ...,
        ge=0,
        le=1,
        description="Confidence interval",
    )

    predicted_throughput: float = Field(0.0, ge=0, description="Predicted throughput")
    predicted_cost: float = Field(0.0, ge=0, description="Predicted cost")
    predicted_efficiency: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Predicted efficiency",
    )

    throughput_lower_bound: float = Field(
        0.0,
        ge=0,
        description="Throughput lower bound",
    )
    throughput_upper_bound: float = Field(
        0.0,
        ge=0,
        description="Throughput upper bound",
    )

    cost_lower_bound: float = Field(0.0, ge=0, description="Cost lower bound")
    cost_upper_bound: float = Field(0.0, ge=0, description="Cost upper bound")

    model_accuracy: float = Field(
        0.0,
        ge=0,
        le=100,
        description="Historical model accuracy",
    )
    based_on_samples: int = Field(0, ge=0, description="Number of samples used")

    recommendations: list[str] = Field(
        default_factory=list,
        description="Forecast-based recommendations",
    )

    risk_factors: list[str] = Field(
        default_factory=list,
        description="Identified risk factors",
    )

    def is_high_confidence(self) -> bool:
        """Check if forecast has high confidence."""
        return self.confidence_interval >= 0.8 and self.model_accuracy >= 85.0
