from __future__ import annotations

from pydantic import BaseModel, Field


class ModelManagerAssessment(BaseModel):
    """Manager-specific assessment details."""

    backend_security_level: str = Field(
        default=..., description="Backend security level"
    )
    audit_compliance: str = Field(default=..., description="Audit compliance status")
    fallback_resilience: str = Field(
        default=..., description="Fallback resilience level"
    )
