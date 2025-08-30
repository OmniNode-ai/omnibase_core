"""
Validation Result Model

ONEX-compliant model for validation operation results.
"""

from pydantic import BaseModel, Field


class ModelValidationResult(BaseModel):
    """Result of validation operations."""

    is_valid: bool = Field(description="Whether validation passed")
    errors: list[str] = Field(
        default_factory=list,
        description="List of validation errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warnings",
    )
    details: str | None = Field(
        default=None,
        description="Additional validation details",
    )
