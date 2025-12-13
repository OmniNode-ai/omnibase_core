"""
ModelCredentialStrengthAssessment: Credential strength assessment result.

This model represents the result of credential strength assessment.
"""

from pydantic import BaseModel, Field

from omnibase_core.enums.enum_credential_strength import EnumCredentialStrength


class ModelCredentialStrengthAssessment(BaseModel):
    """Result of credential strength assessment."""

    strength: EnumCredentialStrength = Field(
        default=EnumCredentialStrength.VERY_WEAK,
        description="Overall strength level",
    )

    score: int = Field(default=0, description="Numerical strength score", ge=0)

    length: int = Field(default=0, description="Character length of credential", ge=0)

    character_variety: int = Field(
        default=0,
        description="Number of different character types",
        ge=0,
        le=4,
    )

    issues: list[str] = Field(
        default_factory=list,
        description="List of identified issues",
    )

    detected_patterns: list[str] = Field(
        default_factory=list,
        description="List of detected credential patterns",
    )
