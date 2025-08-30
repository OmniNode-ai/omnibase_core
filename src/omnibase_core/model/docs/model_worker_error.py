"""
Worker Error Model

Error information for worker operations with specific type safety.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.model.docs.model_error_details import ModelErrorDetails


class ModelWorkerError(BaseModel):
    """Error information for worker operations."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",
    )

    error_code: str = Field(description="Standardized error code")
    error_message: str = Field(description="Human-readable error message")
    details: ModelErrorDetails | None = Field(
        default=None,
        description="Structured error details with strong typing",
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the error occurred",
    )
