"""
Models for incident reporting and alert management.

Defines structures for tracking incidents, alerts, and automated
recovery actions in the production monitoring system.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class EnumIncidentSeverity(str, Enum):
    """Incident severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class EnumIncidentStatus(str, Enum):
    """Incident status states."""

    OPEN = "open"
    INVESTIGATING = "investigating"
    MITIGATING = "mitigating"
    RESOLVED = "resolved"
    CLOSED = "closed"
    ESCALATED = "escalated"


class EnumAlertType(str, Enum):
    """Types of alerts that can be triggered."""

    SYSTEM_DOWN = "system_down"
    QUOTA_EXHAUSTION = "quota_exhaustion"
    CASCADE_FAILURE = "cascade_failure"
    DATA_LOSS_RISK = "data_loss_risk"
    HIGH_ERROR_RATE = "high_error_rate"
    QUOTA_DEPLETION = "quota_depletion"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    COST_OVERRUN = "cost_overrun"
    AGENT_FAILURE = "agent_failure"
    CAPACITY_LIMIT = "capacity_limit"
    ANOMALY_DETECTED = "anomaly_detected"


class EnumRecoveryAction(str, Enum):
    """Automated recovery actions."""

    RESTART_AGENT = "restart_agent"
    SCALE_UP = "scale_up"
    SCALE_DOWN = "scale_down"
    THROTTLE = "throttle"
    EMERGENCY_STOP = "emergency_stop"
    FAILOVER = "failover"
    ROLLBACK = "rollback"
    CIRCUIT_BREAK = "circuit_break"
    QUOTA_REALLOCATE = "quota_reallocate"
    NOTIFY_HUMAN = "notify_human"


class ModelAlertCondition(BaseModel):
    """Alert condition definition."""

    condition_id: str = Field(..., description="Unique condition identifier")
    metric_name: str = Field(..., description="Metric being monitored")
    operator: str = Field(..., description="Comparison operator (>, <, ==, etc.)")
    threshold_value: float = Field(..., description="Threshold value")
    duration_seconds: int = Field(
        0, ge=0, description="Duration condition must persist"
    )

    evaluation_window: int = Field(60, gt=0, description="Evaluation window in seconds")
    hysteresis_percent: float = Field(
        5.0, ge=0, description="Hysteresis percentage to prevent flapping"
    )

    enabled: bool = Field(True, description="Whether condition is active")

    def evaluate(self, current_value: float, duration_met: bool) -> bool:
        """Evaluate if condition is met."""
        if not self.enabled:
            return False

        # Simple evaluation - would be more sophisticated in production
        if self.operator == ">":
            condition_met = current_value > self.threshold_value
        elif self.operator == "<":
            condition_met = current_value < self.threshold_value
        elif self.operator == ">=":
            condition_met = current_value >= self.threshold_value
        elif self.operator == "<=":
            condition_met = current_value <= self.threshold_value
        elif self.operator == "==":
            condition_met = abs(current_value - self.threshold_value) < 0.001
        else:
            return False

        return condition_met and (self.duration_seconds == 0 or duration_met)


class ModelAlert(BaseModel):
    """Production monitoring alert."""

    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: EnumAlertType = Field(..., description="Type of alert")
    severity: EnumIncidentSeverity = Field(..., description="Alert severity")

    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")

    triggered_at: datetime = Field(
        default_factory=datetime.utcnow, description="When alert was triggered"
    )
    resolved_at: Optional[datetime] = Field(None, description="When alert was resolved")

    source_component: str = Field(..., description="Component that triggered alert")
    source_agent: Optional[str] = Field(None, description="Agent that triggered alert")

    metric_name: str = Field(..., description="Metric that triggered alert")
    metric_value: float = Field(..., description="Current metric value")
    threshold_value: float = Field(..., description="Threshold that was breached")

    auto_resolve: bool = Field(False, description="Whether alert auto-resolves")
    is_active: bool = Field(True, description="Whether alert is currently active")

    suggested_actions: List[str] = Field(
        default_factory=list, description="Suggested remediation actions"
    )

    automated_actions_taken: List[EnumRecoveryAction] = Field(
        default_factory=list, description="Automated actions already taken"
    )

    escalation_level: int = Field(0, ge=0, description="Current escalation level")
    escalated_at: Optional[datetime] = Field(
        None, description="When alert was escalated"
    )

    related_incidents: List[str] = Field(
        default_factory=list, description="Related incident IDs"
    )

    def resolve(self) -> None:
        """Mark alert as resolved."""
        self.is_active = False
        self.resolved_at = datetime.utcnow()

    def escalate(self) -> None:
        """Escalate alert to next level."""
        self.escalation_level += 1
        self.escalated_at = datetime.utcnow()

    def get_duration(self) -> float:
        """Get alert duration in seconds."""
        end_time = self.resolved_at or datetime.utcnow()
        return (end_time - self.triggered_at).total_seconds()


class ModelRecoveryAction(BaseModel):
    """Automated recovery action taken."""

    action_id: str = Field(..., description="Unique action identifier")
    action_type: EnumRecoveryAction = Field(..., description="Type of recovery action")

    triggered_by_alert: str = Field(..., description="Alert ID that triggered action")
    target_component: str = Field(..., description="Component being acted upon")
    target_agent: Optional[str] = Field(
        None, description="Specific agent if applicable"
    )

    initiated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When action was initiated"
    )
    completed_at: Optional[datetime] = Field(None, description="When action completed")

    success: Optional[bool] = Field(None, description="Whether action was successful")
    error_message: Optional[str] = Field(
        None, description="Error message if action failed"
    )

    parameters: Optional[str] = Field(
        None, description="Action parameters as JSON string"
    )

    impact_description: str = Field(..., description="Description of expected impact")

    def mark_completed(
        self, success: bool, error_message: Optional[str] = None
    ) -> None:
        """Mark action as completed."""
        self.completed_at = datetime.utcnow()
        self.success = success
        self.error_message = error_message

    def get_duration(self) -> Optional[float]:
        """Get action duration in seconds."""
        if not self.completed_at:
            return None
        return (self.completed_at - self.initiated_at).total_seconds()


class ModelIncidentTimeline(BaseModel):
    """Timeline entry for incident tracking."""

    entry_id: str = Field(..., description="Unique timeline entry ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="Entry timestamp"
    )
    entry_type: str = Field(..., description="Type of timeline entry")
    description: str = Field(..., description="Description of what happened")

    actor: str = Field(..., description="Who/what made this entry")
    severity_change: Optional[EnumIncidentSeverity] = Field(
        None, description="Severity change if any"
    )
    status_change: Optional[EnumIncidentStatus] = Field(
        None, description="Status change if any"
    )

    automated: bool = Field(False, description="Whether entry was automated")

    related_alerts: List[str] = Field(
        default_factory=list, description="Related alert IDs"
    )

    related_actions: List[str] = Field(
        default_factory=list, description="Related recovery action IDs"
    )


class ModelIncident(BaseModel):
    """Production incident tracking."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    incident_id: str = Field(..., description="Unique incident identifier")
    title: str = Field(..., description="Incident title")
    description: str = Field(..., description="Incident description")

    severity: EnumIncidentSeverity = Field(..., description="Incident severity")
    status: EnumIncidentStatus = Field(..., description="Current incident status")

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Incident creation time"
    )
    detected_at: datetime = Field(..., description="When incident was first detected")
    acknowledged_at: Optional[datetime] = Field(
        None, description="When incident was acknowledged"
    )
    resolved_at: Optional[datetime] = Field(
        None, description="When incident was resolved"
    )
    closed_at: Optional[datetime] = Field(None, description="When incident was closed")

    root_cause: Optional[str] = Field(None, description="Identified root cause")
    impact_description: str = Field(..., description="Description of incident impact")

    affected_components: List[str] = Field(
        default_factory=list, description="Components affected by incident"
    )

    affected_agents: List[str] = Field(
        default_factory=list, description="Agents affected by incident"
    )

    triggering_alerts: List[str] = Field(
        default_factory=list, description="Alert IDs that triggered this incident"
    )

    recovery_actions: List[str] = Field(
        default_factory=list, description="Recovery action IDs taken for this incident"
    )

    timeline: List[ModelIncidentTimeline] = Field(
        default_factory=list, description="Incident timeline entries"
    )

    escalation_level: int = Field(0, ge=0, description="Current escalation level")
    assigned_to: Optional[str] = Field(None, description="Who incident is assigned to")

    post_mortem_required: bool = Field(
        False, description="Whether post-mortem is required"
    )
    post_mortem_completed: bool = Field(
        False, description="Whether post-mortem is done"
    )

    lessons_learned: List[str] = Field(
        default_factory=list, description="Lessons learned from incident"
    )

    prevention_actions: List[str] = Field(
        default_factory=list, description="Actions to prevent recurrence"
    )

    def add_timeline_entry(
        self, entry_type: str, description: str, actor: str, automated: bool = False
    ) -> None:
        """Add entry to incident timeline."""
        entry = ModelIncidentTimeline(
            entry_id=f"timeline_{len(self.timeline) + 1}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            entry_type=entry_type,
            description=description,
            actor=actor,
            automated=automated,
        )
        self.timeline.append(entry)

    def acknowledge(self, assignee: str) -> None:
        """Acknowledge incident."""
        self.status = EnumIncidentStatus.INVESTIGATING
        self.acknowledged_at = datetime.utcnow()
        self.assigned_to = assignee
        self.add_timeline_entry(
            "acknowledged", f"Incident acknowledged by {assignee}", assignee
        )

    def resolve(self, resolution_description: str, resolver: str) -> None:
        """Resolve incident."""
        self.status = EnumIncidentStatus.RESOLVED
        self.resolved_at = datetime.utcnow()
        self.add_timeline_entry("resolved", resolution_description, resolver)

    def close(self, closer: str) -> None:
        """Close incident."""
        self.status = EnumIncidentStatus.CLOSED
        self.closed_at = datetime.utcnow()
        self.add_timeline_entry("closed", "Incident closed", closer)

    def get_mttr(self) -> Optional[float]:
        """Get Mean Time To Resolution in hours."""
        if not self.resolved_at:
            return None
        return (self.resolved_at - self.detected_at).total_seconds() / 3600

    def get_total_duration(self) -> float:
        """Get total incident duration in hours."""
        end_time = self.closed_at or self.resolved_at or datetime.utcnow()
        return (end_time - self.detected_at).total_seconds() / 3600


class ModelIncidentSummary(BaseModel):
    """Summary of incidents over a time period."""

    summary_id: str = Field(..., description="Unique summary identifier")
    period_start: datetime = Field(..., description="Summary period start")
    period_end: datetime = Field(..., description="Summary period end")

    total_incidents: int = Field(0, ge=0, description="Total incidents in period")
    critical_incidents: int = Field(0, ge=0, description="Critical incidents")
    high_incidents: int = Field(0, ge=0, description="High severity incidents")
    medium_incidents: int = Field(0, ge=0, description="Medium severity incidents")
    low_incidents: int = Field(0, ge=0, description="Low severity incidents")

    avg_mttr_hours: float = Field(0.0, ge=0, description="Average MTTR in hours")
    total_downtime_hours: float = Field(
        0.0, ge=0, description="Total downtime in hours"
    )

    top_failure_causes: List[str] = Field(
        default_factory=list, description="Most common failure causes"
    )

    most_affected_components: List[str] = Field(
        default_factory=list, description="Components with most incidents"
    )

    incidents_prevented: int = Field(
        0, ge=0, description="Incidents prevented by automation"
    )
    auto_resolved_incidents: int = Field(0, ge=0, description="Incidents auto-resolved")

    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Summary creation time"
    )

    def get_incident_rate(self) -> float:
        """Get incidents per day."""
        days = (self.period_end - self.period_start).days or 1
        return self.total_incidents / days

    def get_availability_percent(self) -> float:
        """Calculate availability percentage."""
        total_hours = (self.period_end - self.period_start).total_seconds() / 3600
        if total_hours == 0:
            return 100.0
        return max(0.0, (1 - self.total_downtime_hours / total_hours) * 100)
