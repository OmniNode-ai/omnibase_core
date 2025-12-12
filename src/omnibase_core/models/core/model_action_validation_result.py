from pydantic import Field

"""
Action Validation Result Model.

Result of action validation with detailed information.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


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
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional validation metadata",
    )
    validated_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When validation was performed",
    )
