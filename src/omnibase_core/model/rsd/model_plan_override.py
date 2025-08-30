#!/usr/bin/env python3
"""
RSD Plan Override Model - ONEX Standards Compliant.

Strongly-typed model for manual priority adjustments with audit trail.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ModelPlanOverride(BaseModel):
    """
    Model for manual priority adjustments with audit trail.

    Used in RSD algorithm to track manual interventions in priority
    calculations with full audit trail for compliance and transparency.
    """

    override_id: str = Field(description="Unique identifier for this override")

    ticket_id: str = Field(description="Ticket ID being overridden")

    previous_score: float = Field(description="Previous priority score before override")

    new_score: float = Field(description="New priority score after override")

    reason: str = Field(description="Reason for manual override")

    authorized_by: str = Field(description="User ID who authorized the override")

    timestamp: datetime = Field(
        description="When the override was applied", default_factory=datetime.now
    )

    expires_at: Optional[datetime] = Field(
        description="Optional expiration time for temporary overrides", default=None
    )

    class Config:
        """Pydantic model configuration for ONEX compliance."""

        validate_assignment = True
        json_encoders = {datetime: lambda v: v.isoformat()}
