"""
ErrorCodes model for node introspection.
"""

from pydantic import BaseModel, Field

from omnibase_core.models.core.model_error_code import ModelErrorCode


class ModelErrorCodes(BaseModel):
    """Model for error codes specification."""

    component: str = Field(
        default=...,
        description="Error component identifier (e.g., 'STAMP', 'TREE')",
    )
    codes: list[ModelErrorCode] = Field(default=..., description="List of error codes")
    total_codes: int = Field(
        default=..., description="Total number of error codes defined"
    )
