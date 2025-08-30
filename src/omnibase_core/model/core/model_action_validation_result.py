"""
Action Validation Result Model.

Result of action validation with detailed information.
"""

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class ModelActionValidationResult(BaseModel):
    """Result of action validation with detailed information."""

    is_valid: bool = Field(..., description="Whether the action is valid")
    validation_errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    validation_warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
    security_checks: Dict[str, bool] = Field(
        default_factory=dict, description="Security validation results"
    )
    trust_score: float = Field(
        default=1.0, description="Calculated trust score for the action"
    )
    recommendations: List[str] = Field(
        default_factory=list, description="Recommendations for improvement"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional validation metadata"
    )
    validated_at: datetime = Field(
        default_factory=datetime.utcnow, description="When validation was performed"
    )
