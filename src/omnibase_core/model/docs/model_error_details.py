"""
Error Details Model

Specific error details for worker operations with strong typing.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorDetails(BaseModel):
    """Specific error details for worker operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True, validate_assignment=True, extra="forbid"
    )

    correlation_id: Optional[str] = Field(
        default=None, description="Correlation ID for tracking"
    )
    file_path: Optional[str] = Field(
        default=None, description="File path related to the error"
    )
    operation_type: Optional[str] = Field(
        default=None, description="Type of operation that failed"
    )
    error_count: Optional[int] = Field(
        default=None, ge=0, description="Number of errors encountered"
    )
    retry_attempted: Optional[bool] = Field(
        default=None, description="Whether retry was attempted"
    )
    timeout_seconds: Optional[float] = Field(
        default=None, ge=0.0, description="Timeout value in seconds if applicable"
    )
    exception_type: Optional[str] = Field(
        default=None, description="Type of the underlying exception"
    )
    database_operation: Optional[str] = Field(
        default=None, description="Database operation that failed"
    )
