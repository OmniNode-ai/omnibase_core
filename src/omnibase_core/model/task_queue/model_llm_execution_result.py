"""
LLM task execution result models for standardized response handling.

Provides strongly-typed success and error result models for LLM task
execution, replacing Dict[str, Any] usage with proper type safety.
"""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from omnibase_core.database.models.model_task import EnumTaskStatus

from .model_llm_task_result import ModelLLMTaskResult


class ModelLLMExecutionSuccess(BaseModel):
    """
    Success result for LLM task execution.

    Returned when an LLM task completes successfully with valid output.
    """

    success: bool = Field(default=True, description="Always True for success results")

    task_id: UUID = Field(description="Unique identifier of the completed task")

    task_result: ModelLLMTaskResult = Field(
        description="Complete LLM task result with response and metadata"
    )

    message: str = Field(
        default="LLM task completed successfully",
        description="Human-readable success message",
    )

    execution_time_seconds: float = Field(
        ge=0.0, description="Total execution time in seconds"
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "success": True,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "task_result": {
                    "task_id": "550e8400-e29b-41d4-a716-446655440000",
                    "task_name": "Document Analysis - Q4 Report",
                    "status": "COMPLETED",
                    "llm_response": {
                        "response": "Key insights from the Q4 report...",
                        "provider_used": "ollama",
                        "model_used": "mistral:7b",
                    },
                    "duration_seconds": 143.2,
                    "total_cost_usd": 0.0,
                },
                "message": "LLM task completed successfully",
                "execution_time_seconds": 143.2,
            }
        },
    )


class ModelLLMExecutionError(BaseModel):
    """
    Error result for LLM task execution.

    Returned when an LLM task fails during execution or validation.
    """

    success: bool = Field(default=False, description="Always False for error results")

    task_id: Optional[UUID] = Field(
        default=None, description="Unique identifier of the failed task (if available)"
    )

    error_message: str = Field(description="Human-readable error description")

    error_code: str = Field(
        description="Structured error code for programmatic handling"
    )

    error_type: str = Field(description="Type of error that occurred")

    error_phase: str = Field(
        description="Phase where error occurred: 'validation', 'execution', 'finalization'"
    )

    task_status: Optional[EnumTaskStatus] = Field(
        default=None, description="Final task status (if task was created)"
    )

    execution_time_seconds: float = Field(
        default=0.0, ge=0.0, description="Time spent before failure occurred"
    )

    error_traceback: Optional[str] = Field(
        default=None, description="Full error traceback for debugging"
    )

    retry_suggested: bool = Field(
        default=False, description="Whether retrying this task is recommended"
    )

    model_config = ConfigDict(
        use_enum_values=True,
        validate_assignment=True,
        extra="forbid",
        json_schema_extra={
            "example": {
                "success": False,
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "error_message": "Provider 'openai' is not available",
                "error_code": "PROVIDER_UNAVAILABLE",
                "error_type": "ProviderError",
                "error_phase": "execution",
                "task_status": "FAILED",
                "execution_time_seconds": 12.3,
                "retry_suggested": True,
            }
        },
    )


# Union type for all LLM execution results
ModelLLMExecutionResult = ModelLLMExecutionSuccess | ModelLLMExecutionError
