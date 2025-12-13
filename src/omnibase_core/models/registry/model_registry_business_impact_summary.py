"""
Registry Business Impact Summary Model

Type-safe business impact summary for registry health reporting.
"""

from pydantic import BaseModel, Field

from .model_registry_sla_compliance import ModelRegistrySlaCompliance


class ModelRegistryBusinessImpactSummary(BaseModel):
    """
    Type-safe business impact summary for registry health.

    Provides comprehensive business impact assessment metrics.
    """

    operational_status: str = Field(
        default=..., description="Current operational status"
    )

    availability_percentage: float = Field(
        default=...,
        description="Tool availability percentage",
        ge=0.0,
        le=100.0,
    )

    service_availability_percentage: float = Field(
        default=...,
        description="Service availability percentage",
        ge=0.0,
        le=100.0,
    )

    reliability_score: float = Field(
        default=...,
        description="Overall reliability score (0.0 to 1.0)",
        ge=0.0,
        le=1.0,
    )

    reliability_category: str = Field(
        default=...,
        description="Reliability category based on score",
        pattern="^(excellent|good|acceptable|poor|critical)$",
    )

    critical_components_count: int = Field(
        default=...,
        description="Number of critical components",
        ge=0,
    )

    performance_impact: str = Field(
        default=...,
        description="Performance impact assessment",
        pattern="^(high_negative|medium_negative|low_negative|minimal)$",
    )

    business_continuity_risk: str = Field(
        default=...,
        description="Business continuity risk level",
        pattern="^(high|medium|low|minimal)$",
    )

    sla_compliance: ModelRegistrySlaCompliance = Field(
        default=...,
        description="SLA compliance status details",
    )
