"""
ModelCredentialValidationResult: Credential validation results.

This model provides structured credential validation results without using Any types.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelCredentialValidationResult(BaseModel):
    """Credential validation results."""

    is_valid: bool = Field(..., description="Overall validation status")
    errors: List[str] = Field(
        default_factory=list, description="Validation error messages"
    )
    warnings: List[str] = Field(
        default_factory=list, description="Validation warning messages"
    )
    strength_score: int = Field(..., description="Credential strength score (0-100)")
    compliance_status: str = Field(..., description="Compliance validation status")
    recommendations: List[str] = Field(
        default_factory=list, description="Improvement recommendations"
    )
