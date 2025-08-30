"""Retry execution result model."""

from pydantic import BaseModel, Field

from omnibase_core.model.runtime.model_execution_result_data import (
    ModelExecutionResultData,
)


class ModelRetryExecutionResult(BaseModel):
    """Result of retry execution attempt."""

    success: bool = Field(..., description="Whether execution succeeded")
    attempt_number: int = Field(..., description="Attempt number (1-based)")
    execution_time_ms: float = Field(..., description="Execution time in milliseconds")
    result_data: ModelExecutionResultData | None = Field(
        default=None,
        description="Execution result data",
    )
    error_message: str | None = Field(
        default=None,
        description="Error message if failed",
    )
    should_retry: bool = Field(default=False, description="Whether to attempt retry")
    next_delay_ms: int | None = Field(
        default=None,
        description="Delay before next retry",
    )
