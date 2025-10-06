from typing import Any, List

from pydantic import Field

"""
ModelValidationResult: Validation result with structured information.

This model represents the result of validation operations with proper typing.
"""

from pydantic import BaseModel, Field


class ModelValidationResult(BaseModel):
    """Result of a validation operation."""

    is_valid: bool = Field(default=..., description="Whether the validation passed")

    validated_value: str | None = Field(
        default=None,
        description="The validated and potentially normalized value",
    )

    errors: list[str] = Field(
        default_factory=list,
        description="List of validation errors",
    )

    warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warnings",
    )

    suggestions: list[str] = Field(
        default_factory=list,
        description="List of suggestions for fixing validation issues",
    )

    metadata: dict[str, Any] | None = Field(
        default=None, description="Additional validation metadata"
    )

    def add_error(self, error: str) -> None:
        """Add an error to the validation result."""
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(warning)

    def add_suggestion(self, suggestion: str) -> None:
        """Add a suggestion to the validation result."""
        self.suggestions.append(suggestion)

    @classmethod
    def create_valid(cls, value: str) -> "ModelValidationResult":
        """Create a valid result."""
        return cls(is_valid=True, validated_value=value)

    @classmethod
    def create_invalid(cls, errors: list[str]) -> "ModelValidationResult":
        """Create an invalid result."""
        return cls(is_valid=False, errors=errors)
