"""
Model for incident timeline.

Timeline entry for incident tracking.
"""

from datetime import datetime

from pydantic import BaseModel, Field

from omnibase_core.models.monitoring.enum_incident_severity import EnumIncidentSeverity
from omnibase_core.models.monitoring.enum_incident_status import EnumIncidentStatus


class ModelIncidentTimeline(BaseModel):
    """Timeline entry for incident tracking."""

    entry_id: str = Field(..., description="Unique timeline entry ID")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="Entry timestamp",
    )
    entry_type: str = Field(..., description="Type of timeline entry")
    description: str = Field(..., description="Description of what happened")

    actor: str = Field(..., description="Who/what made this entry")
    severity_change: EnumIncidentSeverity | None = Field(
        None,
        description="Severity change if any",
    )
    status_change: EnumIncidentStatus | None = Field(
        None,
        description="Status change if any",
    )

    automated: bool = Field(False, description="Whether entry was automated")

    related_alerts: list[str] = Field(
        default_factory=list,
        description="Related alert IDs",
    )

    related_actions: list[str] = Field(
        default_factory=list,
        description="Related recovery action IDs",
    )
