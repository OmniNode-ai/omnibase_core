"""
Registry Business Risk Model

Type-safe business risk assessment for registry validation.
"""

from pydantic import BaseModel, Field


class ModelRegistryBusinessRisk(BaseModel):
    """
    Type-safe business risk assessment for registry validation.

    Provides structured risk analysis across multiple dimensions.
    """

    overall_risk_level: str = Field(
        ...,
        description="Overall business risk level",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    operational_impact: str = Field(
        ...,
        description="Operational impact assessment",
        pattern="^(NONE|MINOR|MODERATE|SEVERE)$",
    )

    security_risk: str = Field(
        ...,
        description="Security risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    compliance_risk: str = Field(
        ...,
        description="Compliance risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    performance_risk: str = Field(
        ...,
        description="Performance risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )

    business_continuity_risk: str = Field(
        ...,
        description="Business continuity risk assessment",
        pattern="^(MINIMAL|LOW|MEDIUM|HIGH|CRITICAL)$",
    )
