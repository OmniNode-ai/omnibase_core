"""
Registry Business Impact Model

Type-safe business impact assessment for registry validation.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ModelRegistryBusinessImpact(BaseModel):
    """
    Type-safe business impact assessment for registry validation.

    Provides structured business impact analysis.
    """

    operational_health_score: float = Field(
        ..., description="Overall operational health score (0.0 to 1.0)", ge=0.0, le=1.0
    )

    compliance_score: float = Field(
        ..., description="Compliance score (0.0 to 1.0)", ge=0.0, le=1.0
    )

    success_rate_percentage: float = Field(
        ..., description="Success rate as percentage", ge=0.0, le=100.0
    )

    critical_tools_missing: int = Field(
        0, description="Number of critical tools missing", ge=0
    )

    high_priority_tools_missing: int = Field(
        0, description="Number of high priority tools missing", ge=0
    )

    estimated_fix_effort: str = Field(
        ..., description="Estimated effort to fix all issues"
    )

    user_experience_impact: str = Field(..., description="Impact on user experience")

    system_reliability_impact: str = Field(
        ..., description="Impact on system reliability"
    )

    # Business risk components
    overall_risk_level: str = Field(
        "MINIMAL",
        description="Overall business risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    operational_impact: str = Field(
        "NONE",
        description="Operational impact assessment",
        pattern="^(NONE|MINOR|MODERATE|SEVERE)$",
    )

    security_risk: str = Field(
        "LOW",
        description="Security risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    compliance_risk: str = Field(
        "LOW",
        description="Compliance risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    performance_risk: str = Field(
        "MINIMAL",
        description="Performance risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    business_continuity_risk: str = Field(
        "MINIMAL",
        description="Business continuity risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    # Financial impact
    potential_revenue_impact: Optional[str] = Field(
        None, description="Potential revenue impact assessment"
    )

    estimated_cost_to_fix: Optional[str] = Field(
        None, description="Estimated cost to fix issues"
    )

    # Recommendations
    immediate_actions_required: int = Field(
        0, description="Number of immediate actions required", ge=0
    )

    recommended_priority: str = Field(
        "NORMAL",
        description="Recommended priority for fixes",
        pattern="^(LOW|NORMAL|HIGH|URGENT|CRITICAL)$",
    )
