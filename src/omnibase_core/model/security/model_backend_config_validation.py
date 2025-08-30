"""
ModelBackendConfigValidation: Configuration validation for secret backends.

This model represents configuration requirements and validation for backends.
"""

from typing import List

from pydantic import BaseModel, Field


class ModelBackendConfigValidation(BaseModel):
    """Configuration validation result for a backend."""

    is_valid: bool = Field(True, description="Whether the configuration is valid")

    issues: List[str] = Field(
        default_factory=list, description="List of configuration issues found"
    )

    warnings: List[str] = Field(
        default_factory=list, description="List of configuration warnings"
    )

    required_fields_missing: List[str] = Field(
        default_factory=list, description="List of missing required fields"
    )

    suggestions: List[str] = Field(
        default_factory=list, description="Suggestions for fixing configuration issues"
    )
