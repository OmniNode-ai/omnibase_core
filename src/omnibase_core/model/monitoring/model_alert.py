"""
Model for alert.

Production monitoring alert.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.model.monitoring.enum_alert_type import EnumAlertType
from omnibase_core.model.monitoring.enum_incident_severity import EnumIncidentSeverity
from omnibase_core.model.monitoring.enum_recovery_action import EnumRecoveryAction


class ModelAlert(BaseModel):
    """Production monitoring alert."""

    alert_id: str = Field(..., description="Unique alert identifier")
    alert_type: EnumAlertType = Field(..., description="Type of alert")
    severity: EnumIncidentSeverity = Field(..., description="Alert severity")

    title: str = Field(..., description="Alert title")
    message: str = Field(..., description="Alert message")

    triggered_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When alert was triggered",
    )
    resolved_at: datetime | None = Field(None, description="When alert was resolved")

    source_component: str = Field(..., description="Component that triggered alert")
    source_agent: str | None = Field(None, description="Agent that triggered alert")

    metric_name: str = Field(..., description="Metric that triggered alert")
    metric_value: float = Field(..., description="Current metric value")
    threshold_value: float = Field(..., description="Threshold that was breached")

    auto_resolve: bool = Field(False, description="Whether alert auto-resolves")
    is_active: bool = Field(True, description="Whether alert is currently active")

    suggested_actions: list[str] = Field(
        default_factory=list,
        description="Suggested remediation actions",
    )

    automated_actions_taken: list[EnumRecoveryAction] = Field(
        default_factory=list,
        description="Automated actions already taken",
    )

    escalation_level: int = Field(0, ge=0, description="Current escalation level")
    escalated_at: datetime | None = Field(
        None,
        description="When alert was escalated",
    )

    related_incidents: list[str] = Field(
        default_factory=list,
        description="Related incident IDs",
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
