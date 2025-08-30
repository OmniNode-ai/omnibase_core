"""
Model for incident summary.

Summary of incidents over a time period.
"""

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field


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
