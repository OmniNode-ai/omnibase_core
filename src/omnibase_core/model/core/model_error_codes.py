"""
ErrorCodes model for node introspection.
"""

from typing import List

from pydantic import BaseModel, Field

from omnibase_core.model.core.model_error_code import ModelErrorCode


class ModelErrorCodes(BaseModel):
    """Model for error codes specification."""

    component: str = Field(
        ..., description="Error component identifier (e.g., 'STAMP', 'TREE')"
    )
    codes: List[ModelErrorCode] = Field(..., description="List of error codes")
    total_codes: int = Field(..., description="Total number of error codes defined")
