"""
Result of validating a single node within a collection context.

Provides simplified validation results for nodes specifically when validating
them as part of a collection operation.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelCollectionNodeValidationResult(BaseModel):
    """Result of validating a single node in collection context."""

    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(
        ...,
        description="Whether the node is valid",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Validation errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Validation warnings",
    )
