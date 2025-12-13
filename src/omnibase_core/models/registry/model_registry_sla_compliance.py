"""
Registry SLA Compliance Model

Type-safe SLA compliance tracking for registry health reporting.
"""

from pydantic import BaseModel, Field


class ModelRegistrySlaCompliance(BaseModel):
    """
    Type-safe SLA compliance tracking for registry health.

    Tracks SLA metrics across availability, reliability, and performance.
    """

    availability_sla: str = Field(
        default=...,
        description="Availability SLA status",
        pattern="^(met|at_risk|violated)$",
    )

    reliability_sla: str = Field(
        default=...,
        description="Reliability SLA status",
        pattern="^(met|at_risk|violated)$",
    )

    performance_sla: str = Field(
        default=...,
        description="Performance SLA status",
        pattern="^(met|at_risk|violated)$",
    )

    overall_compliance: str = Field(
        default=...,
        description="Overall SLA compliance status",
        pattern="^(compliant|non_compliant)$",
    )

    # Additional SLA metrics
    availability_target: float = Field(
        default=99.0,
        description="Availability SLA target percentage",
        ge=0.0,
        le=100.0,
    )

    reliability_target: float = Field(
        default=0.95,
        description="Reliability SLA target score",
        ge=0.0,
        le=1.0,
    )

    performance_target_ms: int = Field(
        default=500,
        description="Performance SLA target in milliseconds",
        gt=0,
    )
