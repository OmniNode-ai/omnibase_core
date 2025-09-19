"""
Result of validating an entire node collection.

Provides validation results for collection-level validation including
per-node validation results and collection-wide errors.
"""

from pydantic import BaseModel, ConfigDict, Field

from .model_collection_node_validation_result import ModelCollectionNodeValidationResult


class ModelCollectionValidationResult(BaseModel):
    """Result of validating an entire collection."""

    model_config = ConfigDict(extra="forbid")

    valid: bool = Field(
        ...,
        description="Whether the entire collection is valid",
    )
    errors: list[str] = Field(
        default_factory=list,
        description="Collection-level errors",
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Collection-level warnings",
    )
    node_validations: dict[str, ModelCollectionNodeValidationResult] = Field(
        default_factory=dict,
        description="Per-node validation results",
    )
