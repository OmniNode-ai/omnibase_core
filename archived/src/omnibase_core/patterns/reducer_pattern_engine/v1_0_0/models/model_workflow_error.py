"""Workflow error model for Reducer Pattern Engine."""

from typing import Any

from pydantic import BaseModel, Field


class ModelWorkflowError(BaseModel):
    """Error model for workflow processing failures."""

    error_code: str = Field("", description="Error code identifying the type of error")
    error_message: str = Field("", description="Human-readable error message")
    error_context: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context about the error",
    )
    stack_trace: str = Field("", description="Stack trace if available")
    recoverable: bool = Field(False, description="Whether this error is recoverable")
