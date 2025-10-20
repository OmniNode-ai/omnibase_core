"""
ModelEnforcementAction: Enforcement action taken by policy engine.

This model tracks security policy enforcement actions for audit trails
with structured enforcement data.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModelEnforcementAction(BaseModel):
    """Enforcement action taken by policy engine."""

    timestamp: datetime = Field(default=..., description="When action was taken")
    envelope_id: UUID = Field(default=..., description="Envelope ID")
    policy_id: UUID = Field(default=..., description="Policy that triggered action")
    decision: str = Field(default=..., description="Decision made (allow, deny, etc)")
    confidence: float = Field(default=..., description="Confidence in decision")
    reasons: list[str] = Field(default=..., description="Reasons for decision")
    enforcement_actions: list[str] = Field(default=..., description="Actions taken")
    evaluation_time_ms: float = Field(default=..., description="Time to evaluate")
