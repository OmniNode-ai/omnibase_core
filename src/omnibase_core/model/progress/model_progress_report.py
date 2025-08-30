"""
Model for progress tracking and reporting in multi-agent systems.

This model represents progress reports, metrics tracking, and performance
monitoring data for coordinating multiple Claude Code agents working
on parallel tickets.
"""

from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field


class ProgressStatus(str, Enum):
    """Progress status enumeration."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProgressPhase(str, Enum):
    """Progress phase enumeration."""

    PLANNING = "planning"
    ANALYSIS = "analysis"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    REVIEW = "review"
    DOCUMENTATION = "documentation"
    DEPLOYMENT = "deployment"
    CLEANUP = "cleanup"


class MetricType(str, Enum):
    """Metric type enumeration."""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    PERCENTAGE = "percentage"


class AlertLevel(str, Enum):
    """Alert level enumeration."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ModelProgressMetric(BaseModel):
    """Model for individual progress metrics."""

    metric_id: str = Field(description="Unique identifier for the metric")
    metric_name: str = Field(description="Human-readable name of the metric")
    metric_type: MetricType = Field(description="Type of metric")
    value: float = Field(description="Current value of the metric")
    unit: str | None = Field(default=None, description="Unit of measurement")
    target_value: float | None = Field(
        default=None,
        description="Target value for this metric",
    )
    min_value: float | None = Field(
        default=None,
        description="Minimum acceptable value",
    )
    max_value: float | None = Field(
        default=None,
        description="Maximum acceptable value",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the metric was recorded",
    )
    tags: dict[str, str] = Field(
        default_factory=dict,
        description="Additional tags for the metric",
    )

    @property
    def is_within_bounds(self) -> bool:
        """Check if metric value is within acceptable bounds."""
        if self.min_value is not None and self.value < self.min_value:
            return False
        return not (self.max_value is not None and self.value > self.max_value)

    @property
    def progress_percentage(self) -> float | None:
        """Calculate progress percentage if target is set."""
        if self.target_value is None or self.target_value == 0:
            return None
        return min(100.0, (self.value / self.target_value) * 100.0)

    @property
    def variance_from_target(self) -> float | None:
        """Calculate variance from target value."""
        if self.target_value is None:
            return None
        return self.value - self.target_value


class ModelProgressCheckpoint(BaseModel):
    """Model for progress checkpoints."""

    checkpoint_id: str = Field(description="Unique identifier for the checkpoint")
    checkpoint_name: str = Field(description="Human-readable name of the checkpoint")
    phase: ProgressPhase = Field(description="Phase this checkpoint belongs to")
    progress_percentage: float = Field(
        description="Progress percentage at this checkpoint (0-100)",
    )
    estimated_completion: datetime | None = Field(
        default=None,
        description="Estimated completion time for this checkpoint",
    )
    actual_completion: datetime | None = Field(
        default=None,
        description="Actual completion time",
    )
    dependencies: list[str] = Field(
        default_factory=list,
        description="List of checkpoint IDs this depends on",
    )
    blocking: list[str] = Field(
        default_factory=list,
        description="List of checkpoint IDs this blocks",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="Criteria that must be met to complete this checkpoint",
    )
    artifacts: list[str] = Field(
        default_factory=list,
        description="List of artifacts produced at this checkpoint",
    )
    notes: list[str] = Field(
        default_factory=list,
        description="Notes about this checkpoint",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the checkpoint was created",
    )

    @property
    def is_completed(self) -> bool:
        """Check if checkpoint is completed."""
        return self.actual_completion is not None

    @property
    def is_overdue(self) -> bool:
        """Check if checkpoint is overdue."""
        if not self.estimated_completion:
            return False
        return datetime.now() > self.estimated_completion and not self.is_completed

    @property
    def duration(self) -> timedelta | None:
        """Get duration of checkpoint completion."""
        if self.actual_completion and self.created_at:
            return self.actual_completion - self.created_at
        return None


class ModelProgressAlert(BaseModel):
    """Model for progress-related alerts."""

    alert_id: str = Field(description="Unique identifier for the alert")
    alert_level: AlertLevel = Field(description="Severity level of the alert")
    title: str = Field(description="Brief title of the alert")
    message: str = Field(description="Detailed alert message")
    source_entity: str = Field(
        description="Entity that triggered the alert (agent_id, ticket_id, etc.)",
    )
    source_type: str = Field(description="Type of source entity")
    metric_name: str | None = Field(
        default=None,
        description="Name of metric that triggered alert",
    )
    threshold_value: float | None = Field(
        default=None,
        description="Threshold value that was crossed",
    )
    actual_value: float | None = Field(
        default=None,
        description="Actual value that triggered the alert",
    )
    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested actions to resolve the alert",
    )
    auto_resolve: bool = Field(
        default=False,
        description="Whether this alert can be auto-resolved",
    )
    acknowledged: bool = Field(
        default=False,
        description="Whether the alert has been acknowledged",
    )
    resolved: bool = Field(
        default=False,
        description="Whether the alert has been resolved",
    )
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the alert was created",
    )
    acknowledged_at: datetime | None = Field(
        default=None,
        description="When the alert was acknowledged",
    )
    resolved_at: datetime | None = Field(
        default=None,
        description="When the alert was resolved",
    )

    def acknowledge(self) -> None:
        """Acknowledge the alert."""
        self.acknowledged = True
        self.acknowledged_at = datetime.now()

    def resolve(self) -> None:
        """Resolve the alert."""
        self.resolved = True
        self.resolved_at = datetime.now()
        if not self.acknowledged:
            self.acknowledge()


class ModelAgentProgress(BaseModel):
    """Model for individual agent progress tracking."""

    agent_id: str = Field(description="Unique identifier for the agent")
    current_status: ProgressStatus = Field(description="Current progress status")
    current_phase: ProgressPhase | None = Field(
        default=None,
        description="Current phase of work",
    )
    assigned_tickets: list[str] = Field(
        default_factory=list,
        description="List of assigned ticket IDs",
    )
    active_ticket: str | None = Field(
        default=None,
        description="Currently active ticket ID",
    )
    overall_progress: float = Field(
        default=0.0,
        description="Overall progress percentage (0-100)",
    )
    ticket_progress: dict[str, float] = Field(
        default_factory=dict,
        description="Progress percentage per ticket",
    )
    completed_tickets: list[str] = Field(
        default_factory=list,
        description="List of completed ticket IDs",
    )
    failed_tickets: list[str] = Field(
        default_factory=list,
        description="List of failed ticket IDs",
    )
    start_time: datetime | None = Field(
        default=None,
        description="When the agent started working",
    )
    last_activity: datetime = Field(
        default_factory=datetime.now,
        description="Last activity timestamp",
    )
    estimated_completion: datetime | None = Field(
        default=None,
        description="Estimated completion time",
    )
    productivity_score: float = Field(
        default=1.0,
        description="Productivity score (0.0 to 2.0)",
    )
    efficiency_score: float = Field(
        default=1.0,
        description="Efficiency score (0.0 to 2.0)",
    )
    quality_score: float = Field(default=1.0, description="Quality score (0.0 to 2.0)")
    bottlenecks: list[str] = Field(
        default_factory=list,
        description="List of identified bottlenecks",
    )
    achievements: list[str] = Field(
        default_factory=list,
        description="List of achievements or milestones",
    )
    metrics: list[ModelProgressMetric] = Field(
        default_factory=list,
        description="Agent-specific metrics",
    )
    checkpoints: list[ModelProgressCheckpoint] = Field(
        default_factory=list,
        description="Progress checkpoints",
    )
    alerts: list[ModelProgressAlert] = Field(
        default_factory=list,
        description="Active alerts for this agent",
    )

    @property
    def is_active(self) -> bool:
        """Check if agent is actively working."""
        return self.current_status == ProgressStatus.IN_PROGRESS

    @property
    def is_idle(self) -> bool:
        """Check if agent is idle."""
        return (
            self.current_status == ProgressStatus.NOT_STARTED
            and not self.assigned_tickets
        )

    @property
    def is_blocked(self) -> bool:
        """Check if agent is blocked."""
        return self.current_status == ProgressStatus.BLOCKED

    @property
    def work_duration(self) -> timedelta | None:
        """Get total work duration."""
        if self.start_time:
            return datetime.now() - self.start_time
        return None

    @property
    def time_since_activity(self) -> timedelta:
        """Get time since last activity."""
        return datetime.now() - self.last_activity

    @property
    def is_stale(self) -> bool:
        """Check if agent appears stale (no recent activity)."""
        return self.time_since_activity > timedelta(minutes=15)

    @property
    def completion_rate(self) -> float:
        """Calculate completion rate for assigned tickets."""
        total_tickets = (
            len(self.completed_tickets)
            + len(self.failed_tickets)
            + len(self.assigned_tickets)
        )
        if total_tickets == 0:
            return 0.0
        return len(self.completed_tickets) / total_tickets

    @property
    def success_rate(self) -> float:
        """Calculate success rate for completed work."""
        completed_attempts = len(self.completed_tickets) + len(self.failed_tickets)
        if completed_attempts == 0:
            return 1.0
        return len(self.completed_tickets) / completed_attempts

    @property
    def overall_score(self) -> float:
        """Calculate overall performance score."""
        return (
            self.productivity_score + self.efficiency_score + self.quality_score
        ) / 3.0

    def update_activity(self) -> None:
        """Update last activity timestamp."""
        self.last_activity = datetime.now()

    def add_metric(self, metric: ModelProgressMetric) -> None:
        """Add a progress metric."""
        self.metrics.append(metric)
        self.update_activity()

    def add_checkpoint(self, checkpoint: ModelProgressCheckpoint) -> None:
        """Add a progress checkpoint."""
        self.checkpoints.append(checkpoint)
        self.update_activity()

    def add_alert(self, alert: ModelProgressAlert) -> None:
        """Add a progress alert."""
        self.alerts.append(alert)

    def complete_ticket(self, ticket_id: str) -> None:
        """Mark a ticket as completed."""
        if ticket_id in self.assigned_tickets:
            self.assigned_tickets.remove(ticket_id)
        if ticket_id not in self.completed_tickets:
            self.completed_tickets.append(ticket_id)
        if ticket_id in self.ticket_progress:
            self.ticket_progress[ticket_id] = 100.0
        self.update_activity()

    def fail_ticket(self, ticket_id: str) -> None:
        """Mark a ticket as failed."""
        if ticket_id in self.assigned_tickets:
            self.assigned_tickets.remove(ticket_id)
        if ticket_id not in self.failed_tickets:
            self.failed_tickets.append(ticket_id)
        self.update_activity()


class ModelSystemProgress(BaseModel):
    """Model for overall system progress tracking."""

    system_id: str = Field(description="Unique identifier for the system")
    total_agents: int = Field(description="Total number of agents in the system")
    active_agents: int = Field(description="Number of actively working agents")
    idle_agents: int = Field(description="Number of idle agents")
    blocked_agents: int = Field(description="Number of blocked agents")
    total_tickets: int = Field(description="Total number of tickets in the system")
    completed_tickets: int = Field(description="Number of completed tickets")
    failed_tickets: int = Field(description="Number of failed tickets")
    in_progress_tickets: int = Field(
        description="Number of tickets currently in progress",
    )
    blocked_tickets: int = Field(description="Number of blocked tickets")
    overall_progress: float = Field(
        description="Overall system progress percentage (0-100)",
    )
    average_agent_efficiency: float = Field(
        description="Average efficiency across all agents",
    )
    system_throughput: float = Field(description="System throughput (tickets per hour)")
    estimated_completion: datetime | None = Field(
        default=None,
        description="Estimated completion time for all work",
    )
    bottleneck_analysis: dict[str, int] = Field(
        default_factory=dict,
        description="Analysis of system bottlenecks",
    )
    performance_trends: dict[str, list[float]] = Field(
        default_factory=dict,
        description="Performance trends over time",
    )
    resource_utilization: dict[str, float] = Field(
        default_factory=dict,
        description="Resource utilization metrics",
    )
    quality_metrics: dict[str, float] = Field(
        default_factory=dict,
        description="System-wide quality metrics",
    )
    alerts_summary: dict[str, int] = Field(
        default_factory=dict,
        description="Summary of alerts by level",
    )
    last_updated: datetime = Field(
        default_factory=datetime.now,
        description="When the progress was last updated",
    )

    @property
    def completion_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_tickets == 0:
            return 100.0
        return (self.completed_tickets / self.total_tickets) * 100.0

    @property
    def success_rate(self) -> float:
        """Calculate overall success rate."""
        completed_attempts = self.completed_tickets + self.failed_tickets
        if completed_attempts == 0:
            return 100.0
        return (self.completed_tickets / completed_attempts) * 100.0

    @property
    def agent_utilization(self) -> float:
        """Calculate agent utilization percentage."""
        if self.total_agents == 0:
            return 0.0
        return (self.active_agents / self.total_agents) * 100.0

    @property
    def has_bottlenecks(self) -> bool:
        """Check if system has identified bottlenecks."""
        return len(self.bottleneck_analysis) > 0

    @property
    def has_critical_alerts(self) -> bool:
        """Check if system has critical alerts."""
        return self.alerts_summary.get(AlertLevel.CRITICAL.value, 0) > 0

    @property
    def system_health_score(self) -> float:
        """Calculate overall system health score (0-100)."""
        # Base score on completion rate, success rate, and utilization
        completion_score = min(100.0, self.completion_percentage)
        success_score = self.success_rate
        utilization_score = min(100.0, self.agent_utilization)
        efficiency_score = min(
            100.0,
            self.average_agent_efficiency * 50.0,
        )  # Assuming 2.0 max efficiency

        # Deduct points for critical issues
        critical_penalty = self.alerts_summary.get(AlertLevel.CRITICAL.value, 0) * 10
        error_penalty = self.alerts_summary.get(AlertLevel.ERROR.value, 0) * 5

        base_score = (
            completion_score + success_score + utilization_score + efficiency_score
        ) / 4.0
        return max(0.0, base_score - critical_penalty - error_penalty)


class ModelProgressReport(BaseModel):
    """Model for comprehensive progress reports."""

    report_id: str = Field(description="Unique identifier for the report")
    report_type: str = Field(description="Type of progress report")
    period_start: datetime = Field(description="Start of the reporting period")
    period_end: datetime = Field(description="End of the reporting period")
    system_progress: ModelSystemProgress = Field(description="Overall system progress")
    agent_progress: list[ModelAgentProgress] = Field(
        default_factory=list,
        description="Progress for individual agents",
    )
    key_metrics: list[ModelProgressMetric] = Field(
        default_factory=list,
        description="Key system metrics",
    )
    achievements: list[str] = Field(
        default_factory=list,
        description="Key achievements during the period",
    )
    issues: list[str] = Field(
        default_factory=list,
        description="Issues encountered during the period",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )
    next_period_goals: list[str] = Field(
        default_factory=list,
        description="Goals for the next period",
    )
    generated_at: datetime = Field(
        default_factory=datetime.now,
        description="When the report was generated",
    )
    generated_by: str = Field(description="Who or what generated the report")

    @property
    def report_duration(self) -> timedelta:
        """Get duration of the reporting period."""
        return self.period_end - self.period_start

    @property
    def top_performing_agents(self) -> list[str]:
        """Get list of top performing agent IDs."""
        sorted_agents = sorted(
            self.agent_progress,
            key=lambda a: a.overall_score,
            reverse=True,
        )
        return [agent.agent_id for agent in sorted_agents[:5]]

    @property
    def underperforming_agents(self) -> list[str]:
        """Get list of underperforming agent IDs."""
        avg_score = sum(a.overall_score for a in self.agent_progress) / max(
            len(self.agent_progress),
            1,
        )
        return [
            agent.agent_id
            for agent in self.agent_progress
            if agent.overall_score < avg_score * 0.8
        ]

    @property
    def critical_issues(self) -> list[str]:
        """Get list of critical issues."""
        critical_issues = []

        # Add system-level critical alerts
        if self.system_progress.has_critical_alerts:
            critical_issues.append(
                "System has critical alerts requiring immediate attention",
            )

        # Add agent-level critical issues
        for agent in self.agent_progress:
            if agent.is_blocked:
                critical_issues.append(f"Agent {agent.agent_id} is blocked")
            if agent.is_stale:
                critical_issues.append(f"Agent {agent.agent_id} has been inactive")

        return critical_issues

    def get_metric_by_name(self, metric_name: str) -> ModelProgressMetric | None:
        """Get a specific metric by name."""
        for metric in self.key_metrics:
            if metric.metric_name == metric_name:
                return metric
        return None

    def get_agent_progress(self, agent_id: str) -> ModelAgentProgress | None:
        """Get progress for a specific agent."""
        for agent in self.agent_progress:
            if agent.agent_id == agent_id:
                return agent
        return None
