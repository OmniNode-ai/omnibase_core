"""
Model for incident.

Production incident tracking.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.models.monitoring.enum_incident_severity import EnumIncidentSeverity
from omnibase_core.models.monitoring.enum_incident_status import EnumIncidentStatus
from omnibase_core.models.monitoring.model_incident_timeline import (
    ModelIncidentTimeline,
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
        default_factory=datetime.utcnow,
        description="Incident creation time",
    )
    detected_at: datetime = Field(..., description="When incident was first detected")
    acknowledged_at: datetime | None = Field(
        None,
        description="When incident was acknowledged",
    )
    resolved_at: datetime | None = Field(
        None,
        description="When incident was resolved",
    )
    closed_at: datetime | None = Field(None, description="When incident was closed")

    root_cause: str | None = Field(None, description="Identified root cause")
    impact_description: str = Field(..., description="Description of incident impact")

    affected_components: list[str] = Field(
        default_factory=list,
        description="Components affected by incident",
    )

    affected_agents: list[str] = Field(
        default_factory=list,
        description="Agents affected by incident",
    )

    triggering_alerts: list[str] = Field(
        default_factory=list,
        description="Alert IDs that triggered this incident",
    )

    recovery_actions: list[str] = Field(
        default_factory=list,
        description="Recovery action IDs taken for this incident",
    )

    timeline: list[ModelIncidentTimeline] = Field(
        default_factory=list,
        description="Incident timeline entries",
    )

    escalation_level: int = Field(0, ge=0, description="Current escalation level")
    assigned_to: str | None = Field(None, description="Who incident is assigned to")

    post_mortem_required: bool = Field(
        False,
        description="Whether post-mortem is required",
    )
    post_mortem_completed: bool = Field(
        False,
        description="Whether post-mortem is done",
    )

    lessons_learned: list[str] = Field(
        default_factory=list,
        description="Lessons learned from incident",
    )

    prevention_actions: list[str] = Field(
        default_factory=list,
        description="Actions to prevent recurrence",
    )

    def add_timeline_entry(
        self,
        entry_type: str,
        description: str,
        actor: str,
        automated: bool = False,
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
            "acknowledged",
            f"Incident acknowledged by {assignee}",
            assignee,
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

    def get_mttr(self) -> float | None:
        """Get Mean Time To Resolution in hours."""
        if not self.resolved_at:
            return None
        return (self.resolved_at - self.detected_at).total_seconds() / 3600

    def get_total_duration(self) -> float:
        """Get total incident duration in hours."""
        end_time = self.closed_at or self.resolved_at or datetime.utcnow()
        return (end_time - self.detected_at).total_seconds() / 3600
