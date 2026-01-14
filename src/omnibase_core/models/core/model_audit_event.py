"""
Audit Event Model.

Pydantic model for audit events used in security context tracking.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field


class ModelAuditEvent(BaseModel):
    """Audit event model for security context tracking."""

    model_config = ConfigDict(extra="forbid", from_attributes=True)

    event_id: UUID = Field(default_factory=uuid4, description="Unique event identifier")
    event_type: str = Field(description="Type of audit event")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp",
    )
    actor: str | None = Field(default=None, description="Actor performing action")
    resource: str | None = Field(default=None, description="Resource being accessed")
    action: str = Field(description="Action being performed")
    outcome: str = Field(description="Action outcome (success/failure)")
    additional_data: dict[str, str] = Field(
        default_factory=dict,
        description="Additional audit data",
    )
