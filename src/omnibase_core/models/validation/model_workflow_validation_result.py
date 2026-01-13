"""
Workflow Validation Result Model.

Complete result of workflow DAG validation.
"""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["ModelWorkflowValidationResult"]


class ModelWorkflowValidationResult(BaseModel):
    """Complete result of workflow validation."""

    model_config = ConfigDict(frozen=True, extra="forbid", from_attributes=True)

    is_valid: bool = Field(
        default=False,
        description="Whether the workflow passed all validation checks",
    )
    has_cycles: bool = Field(
        default=False,
        description="Whether the workflow contains cycles",
    )
    topological_order: list[UUID] = Field(
        default_factory=list,
        description="Valid topological order of step IDs (empty if cycles exist)",
    )
    missing_dependencies: list[UUID] = Field(
        default_factory=list,
        description="Step IDs referenced but not defined",
    )
    isolated_steps: list[UUID] = Field(
        default_factory=list,
        description="Step IDs with no connections",
    )
    duplicate_names: list[str] = Field(
        default_factory=list,
        description="Step names that appear multiple times",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="List of validation error messages",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warning messages",
    )
