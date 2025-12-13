"""
ModelBackendConfigValidation: Configuration validation for secret backends.

This model represents configuration requirements and validation for backends.
"""

from pydantic import BaseModel, Field


class ModelBackendConfigValidation(BaseModel):
    """Configuration validation result for a backend."""

    is_valid: bool = Field(
        default=True, description="Whether the configuration is valid"
    )

    issues: list[str] = Field(
        default_factory=list,
        description="List of configuration issues found",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="List of configuration warnings",
    )

    required_fields_missing: list[str] = Field(
        default_factory=list,
        description="List of missing required fields",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="Suggestions for fixing configuration issues",
    )
