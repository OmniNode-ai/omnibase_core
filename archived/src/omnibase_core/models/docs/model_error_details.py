"""
Error Details Model

Specific error details for worker operations with strong typing.
"""

from pydantic import BaseModel, ConfigDict, Field


class ModelErrorDetails(BaseModel):
    """Specific error details for worker operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    correlation_id: str | None = Field(
        default=None,
        description="Correlation ID for tracking",
    )
    file_path: str | None = Field(
        default=None,
        description="File path related to the error",
    )
    operation_type: str | None = Field(
        default=None,
        description="Type of operation that failed",
    )
    error_count: int | None = Field(
        default=None,
        ge=0,
        description="Number of errors encountered",
    )
    retry_attempted: bool | None = Field(
        default=None,
        description="Whether retry was attempted",
    )
    timeout_seconds: float | None = Field(
        default=None,
        ge=0.0,
        description="Timeout value in seconds if applicable",
    )
    exception_type: str | None = Field(
        default=None,
        description="Type of the underlying exception",
    )
    database_operation: str | None = Field(
        default=None,
        description="Database operation that failed",
    )
