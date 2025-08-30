"""
Validation Result Model

ONEX-compliant model for validation operation results.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class ModelValidationResult(BaseModel):
    """Result of validation operations."""

    is_valid: bool = Field(description="Whether validation passed")
    errors: List[str] = Field(
        default_factory=list, description="List of validation errors"
    )
    warnings: List[str] = Field(
        default_factory=list, description="List of validation warnings"
    )
    details: Optional[str] = Field(
        default=None, description="Additional validation details"
    )
