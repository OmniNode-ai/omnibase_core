"""
ModelConfigValidationResult: Configuration validation result model.

This model represents the result of configuration validation.
"""

from pydantic import BaseModel, Field


class ModelConfigValidationResult(BaseModel):
    """Result of configuration validation."""

    is_valid: bool = Field(
        default=True, description="Whether the configuration is valid"
    )

    backend_valid: bool = Field(
        default=True,
        description="Whether the backend configuration is valid",
    )

    issues: list[str] = Field(
        default_factory=list,
        description="List of validation issues",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warnings",
    )

    recommendations: list[str] = Field(
        default_factory=list,
        description="List of recommendations for improvement",
    )
