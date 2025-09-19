"""
Business impact model to replace dictionary usage for business metrics.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class ImpactSeverity(str, Enum):
    """Business impact severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class ModelBusinessImpact(BaseModel):
    """
    Business impact assessment with typed fields.
    Replaces dictionary for get_business_impact() returns.
    """

    # Impact assessment
    severity: ImpactSeverity = Field(..., description="Overall impact severity")
    affected_users: int | None = Field(None, description="Number of affected users")
    affected_services: list[str] | None = Field(
        default_factory=list,
        description="List of affected services",
    )
    revenue_impact_usd: float | None = Field(
        None,
        description="Estimated revenue impact in USD",
    )

    # Time metrics
    downtime_minutes: float | None = Field(
        None,
        description="Total downtime in minutes",
    )
    recovery_time_estimate_minutes: float | None = Field(
        None,
        description="Estimated recovery time",
    )
    time_to_detection_minutes: float | None = Field(
        None,
        description="Time to detect the issue",
    )
    time_to_resolution_minutes: float | None = Field(
        None,
        description="Time to resolve the issue",
    )

    # Business metrics
    sla_violated: bool | None = Field(None, description="Whether SLA was violated")
    customer_satisfaction_impact: float | None = Field(
        None,
        description="Impact on CSAT score",
    )
    reputation_risk: str | None = Field(
        None,
        description="Reputation risk assessment",
    )
    compliance_impact: list[str] | None = Field(
        default_factory=list,
        description="Compliance violations",
    )

    # Operational impact
    manual_interventions_required: int | None = Field(
        None,
        description="Number of manual interventions",
    )
    automated_recovery_successful: bool | None = Field(
        None,
        description="Whether automated recovery worked",
    )
    escalation_required: bool | None = Field(
        None,
        description="Whether escalation was needed",
    )
    incident_ticket_ids: list[str] | None = Field(
        default_factory=list,
        description="Related incident tickets",
    )

    # Financial impact
    operational_cost_usd: float | None = Field(
        None,
        description="Operational cost of the incident",
    )
    mitigation_cost_usd: float | None = Field(
        None,
        description="Cost of mitigation efforts",
    )
    opportunity_cost_usd: float | None = Field(None, description="Opportunity cost")
    total_cost_usd: float | None = Field(None, description="Total cost impact")

    # Recovery metrics
    recovery_actions_taken: list[str] | None = Field(
        default_factory=list,
        description="Recovery actions",
    )
    preventive_measures_implemented: list[str] | None = Field(
        default_factory=list,
        description="Preventive measures",
    )
    lessons_learned: list[str] | None = Field(
        default_factory=list,
        description="Lessons learned",
    )

    # Metadata
    assessment_timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When assessment was made",
    )
    assessed_by: str | None = Field(None, description="Who performed the assessment")
    confidence_score: float | None = Field(
        None,
        description="Confidence in the assessment (0-1)",
    )

    model_config = ConfigDict()

    @classmethod
    def from_dict(cls, data: dict) -> "ModelBusinessImpact":
        """Create from dictionary for easy migration."""
        return cls(**data)

    @field_serializer("assessment_timestamp")
    def serialize_datetime(self, value: datetime) -> str:
        if value and isinstance(value, datetime):
            return value.isoformat()
        return str(value) if value else ""
