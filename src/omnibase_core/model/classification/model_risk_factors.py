"""
Model for risk factors.

Risk factors for autonomous execution assessment.
"""

from pydantic import BaseModel, Field


class ModelRiskFactors(BaseModel):
    """Risk factors for autonomous execution."""

    production_impact_risk: float = Field(
        ...,
        ge=0,
        le=1,
        description="Risk to production",
    )
    data_loss_risk: float = Field(..., ge=0, le=1, description="Risk of data loss")
    security_risk: float = Field(
        ...,
        ge=0,
        le=1,
        description="Security vulnerability risk",
    )
    rollback_difficulty: float = Field(
        ...,
        ge=0,
        le=1,
        description="Difficulty to rollback",
    )
    cascade_failure_risk: float = Field(
        ...,
        ge=0,
        le=1,
        description="Risk of cascade failures",
    )
    reputation_risk: float = Field(..., ge=0, le=1, description="Risk to reputation")

    def calculate_overall_risk(self) -> float:
        """Calculate weighted overall risk score."""
        weights = {
            "production_impact_risk": 0.25,
            "data_loss_risk": 0.20,
            "security_risk": 0.20,
            "rollback_difficulty": 0.15,
            "cascade_failure_risk": 0.15,
            "reputation_risk": 0.05,
        }

        total_risk = sum(
            getattr(self, risk) * weight for risk, weight in weights.items()
        )

        return min(1.0, total_risk)
