"""
Workflow validation result model - Strongly typed validation results for workflow states.

Replaces Dict[str, Any] usage with strongly typed validation information.
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ModelWorkflowValidationResult(BaseModel):
    """Strongly typed workflow validation result."""

    validation_status: str = Field(
        description="Validation status (passed, failed, warning)"
    )
    validation_score: float = Field(description="Validation score (0.0-1.0)")
    validation_errors: List[str] = Field(
        default_factory=list, description="Validation errors"
    )
    validation_warnings: List[str] = Field(
        default_factory=list, description="Validation warnings"
    )
    validation_timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When validation was performed"
    )
    validator_id: Optional[str] = Field(default=None, description="ID of the validator")
    validation_context: Optional[str] = Field(
        default=None, description="Validation context"
    )
