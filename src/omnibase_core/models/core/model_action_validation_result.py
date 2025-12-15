"""
Action Validation Result Model.

Result of action validation with detailed information.
"""

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_action_validation_metadata import (
    ModelActionValidationMetadata,
)


class ModelActionValidationResult(BaseModel):
    """Result of action validation with detailed information."""

    is_valid: bool = Field(default=..., description="Whether the action is valid")
    validation_errors: list[str] = Field(
        default_factory=list,
        description="List of validation errors",
    )
    validation_warnings: list[str] = Field(
        default_factory=list,
        description="List of validation warnings",
    )
    security_checks: dict[str, bool] = Field(
        default_factory=dict,
        description="Security validation results",
    )
    trust_score: float = Field(
        default=1.0,
        description="Calculated trust score for the action",
    )
    recommendations: list[str] = Field(
        default_factory=list,
        description="Recommendations for improvement",
    )
    metadata: ModelActionValidationMetadata = Field(
        default_factory=ModelActionValidationMetadata,
        description="Additional validation metadata",
    )
    validated_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="When validation was performed",
    )
