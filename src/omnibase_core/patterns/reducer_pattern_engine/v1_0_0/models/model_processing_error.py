"""Processing error model for Reducer Pattern Engine."""

from pydantic import BaseModel, Field


class ModelProcessingError(BaseModel):
    """Common strongly typed processing error model."""

    error_code: str = Field(..., description="Error code identifying the error type")
    error_message: str = Field(..., description="Human-readable error message")
    error_context: str = Field("", description="Additional error context")
