"""
ErrorCode model for node introspection.
"""

from pydantic import BaseModel, Field


class ModelErrorCode(BaseModel):
    """Model for error code specification."""

    code: str = Field(
        default=...,
        description="Error code (e.g., 'ONEX_STAMP_001_FILE_NOT_FOUND')",
    )
    number: int = Field(default=..., description="Numeric error identifier")
    description: str = Field(
        default=..., description="Human-readable error description"
    )
    exit_code: int = Field(default=..., description="CLI exit code for this error")
    category: str = Field(
        default=...,
        description="Error category (e.g., 'file', 'validation')",
    )
