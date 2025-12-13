"""
Validation summary models.

Provides typed models for validation error/warning summaries,
replacing dict[str, int] return types in validation methods.
"""

from pydantic import BaseModel, Field


class ModelValidationErrorSummary(BaseModel):
    """
    Typed model for validation error summary.

    Replaces dict[str, int] return from get_error_summary() methods.
    """

    errors: int = Field(
        default=0,
        description="Number of validation errors",
        ge=0,
    )
    warnings: int = Field(
        default=0,
        description="Number of validation warnings",
        ge=0,
    )
    critical_errors: int = Field(
        default=0,
        description="Number of critical validation errors",
        ge=0,
    )
    total_issues: int = Field(
        default=0,
        description="Total number of issues (errors + warnings)",
        ge=0,
    )


__all__ = ["ModelValidationErrorSummary"]
