"""
ModelEnforcementAction: Enforcement action taken by policy engine.

This model tracks security policy enforcement actions for audit trails
with structured enforcement data.
"""

from datetime import datetime

from pydantic import BaseModel, Field


class ModelEnforcementAction(BaseModel):
    """Enforcement action taken by policy engine."""

    timestamp: datetime = Field(..., description="When action was taken")
    envelope_id: str = Field(..., description="Envelope ID")
    policy_id: str = Field(..., description="Policy that triggered action")
    decision: str = Field(..., description="Decision made (allow, deny, etc)")
    confidence: float = Field(..., description="Confidence in decision")
    reasons: list[str] = Field(..., description="Reasons for decision")
    enforcement_actions: list[str] = Field(..., description="Actions taken")
    evaluation_time_ms: float = Field(..., description="Time to evaluate")
