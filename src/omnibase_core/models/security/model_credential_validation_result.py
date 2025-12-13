"""
ModelCredentialValidationResult: Credential validation results.

This model provides structured credential validation results without using Any types.
"""

from pydantic import BaseModel, Field


class ModelCredentialValidationResult(BaseModel):
    """Credential validation results."""

    is_valid: bool = Field(default=..., description="Overall validation status")
    errors: list[str] = Field(
        default_factory=list,
        description="Validation error messages",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Validation warning messages",
    )
    strength_score: int = Field(
        default=..., description="Credential strength score (0-100)"
    )
    compliance_status: str = Field(
        default=..., description="Compliance validation status"
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Improvement recommendations",
    )
