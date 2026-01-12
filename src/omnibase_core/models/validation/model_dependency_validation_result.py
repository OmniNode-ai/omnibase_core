"""
Dependency Validation Result Model.

Result of dependency validation in workflow DAG validation.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelDependencyValidationResult"]


class ModelDependencyValidationResult(BaseModel):
    """Result of dependency validation in workflow."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    is_valid: bool = Field(
        default=True,
        description="Whether all dependencies are valid",
    )
    missing_dependencies: list[UUID] = Field(
        default_factory=list,
        description="List of step IDs that are referenced but don't exist",
    )
    error_message: str = Field(
        default="",
        description="Human-readable error message including step names",
    )
