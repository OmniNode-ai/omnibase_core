from typing import Any

from pydantic import Field

from .model_credentialsanalysis import ModelCredentialsAnalysis

"""
ModelCredentialsAnalysis: Credentials strength analysis results.

This model provides structured credentials analysis without using Any types.
"""

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
