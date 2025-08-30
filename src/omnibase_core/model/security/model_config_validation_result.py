"""
ModelConfigValidationResult: Configuration validation result model.

This model represents the result of configuration validation.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelConfigValidationResult(BaseModel):
    """Result of configuration validation."""

    is_valid: bool = Field(True, description="Whether the configuration is valid")

    backend_valid: bool = Field(
        True, description="Whether the backend configuration is valid"
    )

    issues: List[str] = Field(
        default_factory=list, description="List of validation issues"
    )

    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )

    recommendations: List[str] = Field(
        default_factory=list, description="List of recommendations for improvement"
    )
